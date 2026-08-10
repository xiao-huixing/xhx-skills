"""ai-workflow 的文件存储、锁和派生视图工具。"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
import unicodedata
import uuid
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


WORK_ITEM_ID = re.compile(r"^(?:REQ|BUG)-\d{8}-\d{3}-[a-z0-9-]+$")
TASK_ID = re.compile(r"^TASK-\d{3,}$")
REVISION_ID = re.compile(r"^R\d{3,}$")
PHASES = frozenset({"plan", "execute", "review", "done"})
STATES = frozenset({"active", "waiting_input", "blocked", "paused", "completed", "cancelled"})
DELIVERIES = frozenset({"not_started", "implemented", "merged", "deployed", "verified"})
TRACKS = frozenset({"light", "standard", "strict"})
TASK_STATUSES = frozenset({"pending", "in_progress", "passed", "failed", "blocked", "skipped"})
REQUIRED_ROOT_FILES = (
    "project/overview.md",
    "project/modules.yaml",
    "capabilities/index.yaml",
    "indexes/active.yaml",
    "indexes/catalog.jsonl",
)
REQUIRED_WORK_ITEM_FILES = (
    "manifest.yaml",
    "context.md",
    "tasks.yaml",
    "execution/state.yaml",
    "execution/events.ndjson",
)


class WorkflowError(RuntimeError):
    """工作流状态或输入不合法。"""


class UsageError(WorkflowError):
    """CLI 参数组合不完整。"""


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug[:48] or "item"


def load_data(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:
            raise WorkflowError(
                f"cannot parse YAML without PyYAML: {path}; install PyYAML or use JSON-compatible YAML"
            ) from exc
        try:
            return yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise WorkflowError(f"invalid YAML at {path}: {exc}") from exc


def dump_data(value: Any) -> str:
    """JSON 是 YAML 1.2 子集，可在无第三方依赖时稳定读写。"""
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise WorkflowError(f"invalid JSON at {path}:{line_number}: {exc.msg}") from exc
        if not isinstance(event, dict):
            raise WorkflowError(f"event must be an object at {path}:{line_number}")
        events.append(event)
    return events


def dump_events(events: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n" for event in events)


def work_item_path(root: Path, work_item: str) -> Path:
    if not WORK_ITEM_ID.fullmatch(work_item):
        raise WorkflowError(f"invalid work item ID: {work_item}")
    year = work_item.split("-", 2)[1][:4]
    return root / "work-items" / year / work_item


def iter_work_items(root: Path) -> list[Path]:
    base = root / "work-items"
    if not base.is_dir():
        return []
    return sorted(
        item
        for year in base.iterdir()
        if year.is_dir()
        for item in year.iterdir()
        if item.is_dir() and (item.name.startswith("REQ-") or item.name.startswith("BUG-"))
    )


def next_event(events: list[dict[str, Any]], event_type: str, **values: Any) -> dict[str, Any]:
    numbers = [int(str(event.get("id", "EVT-0")).removeprefix("EVT-")) for event in events]
    event = {
        "id": f"EVT-{max(numbers, default=0) + 1:06d}",
        "at": now_iso(),
        "actor": values.pop("actor", "ai-workflow"),
        "type": event_type,
        "refs": values.pop("refs", []),
    }
    return {**event, **{key: value for key, value in values.items() if value is not None}}


def event_by_idempotency(events: list[dict[str, Any]], key: str | None) -> dict[str, Any] | None:
    if not key:
        return None
    return next((event for event in events if event.get("idempotency_key") == key), None)


def _contained_path(base: Path, relative: str, label: str) -> Path:
    if not relative or Path(relative).is_absolute():
        raise WorkflowError(f"invalid {label} path: {relative}")
    resolved_base = base.resolve()
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(resolved_base)
    except ValueError as exc:
        raise WorkflowError(f"{label} path is outside workflow root: {relative}") from exc
    return candidate


class WriterLock(AbstractContextManager["WriterLock"]):
    def __init__(self, root: Path, owner: str | None = None, ttl_seconds: int = 30):
        self.root = root
        self.path = root / ".writer.lock"
        self.owner = owner or f"pid-{os.getpid()}"
        self.ttl_seconds = ttl_seconds

    def __enter__(self) -> "WriterLock":
        self.root.mkdir(parents=True, exist_ok=True)
        payload = {
            "owner": self.owner,
            "acquired_at": now_iso(),
            "expires_epoch": time.time() + self.ttl_seconds,
        }
        for attempt in range(2):
            try:
                descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            except FileExistsError:
                if attempt == 0 and self._expired():
                    self.path.unlink(missing_ok=True)
                    continue
                raise WorkflowError(f"writer lease is held: {self.path}")
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(dump_data(payload))
            return self
        raise WorkflowError(f"cannot acquire writer lease: {self.path}")

    def _expired(self) -> bool:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return float(payload.get("expires_epoch", 0)) <= time.time()
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return False

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if payload.get("owner") == self.owner:
            self.path.unlink(missing_ok=True)


def recover_transactions(root: Path) -> None:
    transactions = root / ".transactions"
    if not transactions.is_dir():
        return
    for transaction in sorted(path for path in transactions.iterdir() if path.is_dir()):
        metadata_path = transaction / "transaction.json"
        if not metadata_path.is_file():
            shutil.rmtree(transaction)
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict) or not isinstance(metadata.get("files"), list):
            raise WorkflowError(f"invalid transaction metadata: {transaction}")
        for entry in metadata["files"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("target"), str) or not isinstance(
                entry.get("staged"), str
            ):
                raise WorkflowError(f"invalid transaction entry: {transaction}")
            staged = _contained_path(transaction, entry["staged"], "staged transaction")
            target = _contained_path(root, entry["target"], "transaction target")
            if staged.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(staged, target)
        shutil.rmtree(transaction)
    try:
        transactions.rmdir()
    except OSError:
        pass


def commit_files(root: Path, writes: dict[Path, str]) -> None:
    prepared: list[tuple[Path, Path, str]] = []
    for target, content in writes.items():
        try:
            relative_target = target.resolve().relative_to(root.resolve())
        except ValueError as exc:
            raise WorkflowError(f"transaction target path is outside workflow root: {target}") from exc
        prepared.append((target, relative_target, content))
    transactions = root / ".transactions"
    transactions.mkdir(parents=True, exist_ok=True)
    transaction = transactions / uuid.uuid4().hex
    transaction.mkdir()
    entries: list[dict[str, str]] = []
    for index, (_, relative_target, content) in enumerate(prepared):
        staged = transaction / f"{index:04d}.tmp"
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=transaction, delete=False
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.replace(temporary, staged)
        entries.append({"target": str(relative_target), "staged": staged.name})
    metadata = transaction / "transaction.json"
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=transaction, delete=False) as handle:
        handle.write(dump_data({"schema_version": 1, "files": entries}))
        handle.flush()
        os.fsync(handle.fileno())
        temporary_metadata = Path(handle.name)
    os.replace(temporary_metadata, metadata)
    for entry in entries:
        target = root / entry["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(transaction / entry["staged"], target)
    shutil.rmtree(transaction)
    try:
        transactions.rmdir()
    except OSError:
        pass


def make_state(manifest: dict[str, Any], tasks: list[dict[str, Any]], events: list[dict[str, Any]]) -> dict[str, Any]:
    passed_events = [event for event in events if event.get("type") == "task.passed"]
    return {
        "schema_version": 1,
        "phase": manifest["phase"],
        "state": manifest["state"],
        "active_task": manifest.get("active_task"),
        "last_success": passed_events[-1]["id"] if passed_events else None,
        "blocked_by": [task["id"] for task in tasks if task.get("status") == "blocked"],
        "next_action": manifest.get("next_action"),
        "updated_at": manifest["updated_at"],
    }


def make_context(manifest: dict[str, Any], tasks: list[dict[str, Any]]) -> str:
    completed = [task["id"] for task in tasks if task.get("status") == "passed"]
    blocked = [task["id"] for task in tasks if task.get("status") == "blocked"]
    return "\n".join(
        (
            "# Current Context",
            "",
            f"- Work item: {manifest['id']}",
            f"- Current revision: {manifest['current_revision']}",
            f"- Goal: {manifest['title']}",
            f"- Track: {manifest['track']}",
            f"- Phase/state/delivery: {manifest['phase']} / {manifest['state']} / {manifest['delivery']}",
            f"- Completed: {', '.join(completed) if completed else 'none'}",
            f"- In progress: {manifest.get('active_task') or 'none'}",
            f"- Blocked: {', '.join(blocked) if blocked else 'none'}",
            f"- Next action: {manifest.get('next_action') or 'none'}",
            "",
        )
    )


def index_records(root: Path, extra: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    manifests: list[tuple[dict[str, Any], Path]] = []
    for item in iter_work_items(root):
        path = item / "manifest.yaml"
        if path.is_file():
            manifest = load_data(path)
            if isinstance(manifest, dict):
                manifests.append((manifest, item))
    if extra:
        manifests = [pair for pair in manifests if pair[0].get("id") != extra.get("id")]
        manifests.append((extra, work_item_path(root, extra["id"])))
    return [
        {
            "id": manifest.get("id"),
            "title": manifest.get("title"),
            "track": manifest.get("track"),
            "phase": manifest.get("phase"),
            "state": manifest.get("state"),
            "delivery": manifest.get("delivery"),
            "aliases": manifest.get("aliases", []),
            "updated_at": manifest.get("updated_at"),
            "path": str(path.relative_to(root)),
        }
        for manifest, path in sorted(manifests, key=lambda pair: str(pair[0].get("id", "")))
    ]


def index_writes(root: Path, extra: dict[str, Any] | None = None) -> dict[Path, str]:
    records = index_records(root, extra)
    active = [record for record in records if record.get("state") not in {"completed", "cancelled"}]
    catalog = "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    return {
        root / "indexes/active.yaml": dump_data(active),
        root / "indexes/catalog.jsonl": catalog,
    }
