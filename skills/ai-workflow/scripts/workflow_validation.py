"""ai-workflow 结构、schema 与状态一致性校验。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_store import (
    DELIVERIES,
    PHASES,
    REQUIRED_ROOT_FILES,
    REQUIRED_WORK_ITEM_FILES,
    REVISION_ID,
    STATES,
    TASK_ID,
    TASK_STATUSES,
    TRACKS,
    WORK_ITEM_ID,
    WorkflowError,
    iter_work_items,
    load_data,
)


MANIFEST_FIELDS = (
    "schema_version",
    "id",
    "kind",
    "title",
    "aliases",
    "track",
    "phase",
    "state",
    "delivery",
    "current_revision",
    "base_commit",
    "capabilities",
    "modules",
    "parent",
    "supersedes",
    "gates",
    "active_task",
    "next_action",
    "last_event",
    "updated_at",
)
TASK_FIELDS = (
    "id",
    "revision",
    "title",
    "status",
    "depends_on",
    "requirements",
    "acceptance",
    "scope",
    "expected_behavior",
    "validation",
    "evidence",
    "rollback",
    "done_condition",
    "attempt",
    "failure",
    "last_event",
)
EVENT_FIELDS = ("id", "at", "actor", "type", "refs")
STATE_FIELDS = (
    "schema_version",
    "phase",
    "state",
    "active_task",
    "last_success",
    "blocked_by",
    "next_action",
    "updated_at",
)


def _readable(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"missing file: {path}")


def _load_mapping(path: Path, label: str, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = load_data(path)
    except WorkflowError as exc:
        errors.append(str(exc))
        return None
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object: {path}")
        return None
    return value


def _load_tasks(path: Path, errors: list[str]) -> list[dict[str, Any]] | None:
    if not path.is_file():
        return None
    try:
        value = load_data(path)
    except WorkflowError as exc:
        errors.append(str(exc))
        return None
    if not isinstance(value, list) or any(not isinstance(task, dict) for task in value):
        errors.append(f"tasks must be a list of objects: {path}")
        return None
    return value


def _load_events(path: Path, errors: list[str]) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw_line.strip():
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            errors.append(f"invalid JSON at {path}:{line_number}: {exc.msg}")
            continue
        if not isinstance(event, dict):
            errors.append(f"event must be an object at {path}:{line_number}")
            continue
        events.append(event)
    return events


def _required(mapping: dict[str, Any], fields: tuple[str, ...], label: str, errors: list[str]) -> None:
    for field in fields:
        if field not in mapping:
            errors.append(f"{label} missing {field}")


def _validate_manifest(manifest: dict[str, Any], item: Path, errors: list[str]) -> None:
    _required(manifest, MANIFEST_FIELDS, "manifest", errors)
    if manifest.get("schema_version") != 1:
        errors.append(f"unsupported manifest schema_version: {manifest.get('schema_version')}")
    if manifest.get("id") != item.name:
        errors.append(f"manifest id does not match directory: {item}")
    if manifest.get("kind") not in {"requirement", "bugfix"}:
        errors.append(f"invalid kind: {manifest.get('kind')}")
    if not isinstance(manifest.get("title"), str) or not manifest.get("title", "").strip():
        errors.append("manifest title must be a non-empty string")
    for field in ("aliases", "capabilities", "modules", "supersedes"):
        if not isinstance(manifest.get(field), list):
            errors.append(f"manifest {field} must be a list")
    if manifest.get("track") not in TRACKS:
        errors.append(f"invalid track: {manifest.get('track')}")
    if manifest.get("phase") not in PHASES:
        errors.append(f"invalid phase: {manifest.get('phase')}")
    if manifest.get("state") not in STATES:
        errors.append(f"invalid state: {manifest.get('state')}")
    if manifest.get("delivery") not in DELIVERIES:
        errors.append(f"invalid delivery: {manifest.get('delivery')}")
    if not REVISION_ID.fullmatch(str(manifest.get("current_revision", ""))):
        errors.append(f"invalid current_revision: {manifest.get('current_revision')}")
    if manifest.get("base_commit") is not None and not isinstance(manifest.get("base_commit"), str):
        errors.append("manifest base_commit must be a string or null")
    for field in ("parent", "active_task", "next_action", "last_event"):
        if manifest.get(field) is not None and not isinstance(manifest.get(field), str):
            errors.append(f"manifest {field} must be a string or null")
    if not isinstance(manifest.get("updated_at"), str) or not manifest.get("updated_at", "").strip():
        errors.append("manifest updated_at must be a non-empty string")
    gates = manifest.get("gates")
    if not isinstance(gates, dict):
        errors.append("manifest gates must be an object")
    else:
        for gate in ("plan_approved", "review_approved", "release_approved"):
            if not isinstance(gates.get(gate), bool):
                errors.append(f"manifest gates.{gate} must be boolean")
    if manifest.get("phase") in {"execute", "review", "done"} and not (
        isinstance(gates, dict) and gates.get("plan_approved") is True
    ):
        errors.append("plan gate must be approved after plan phase")
    if manifest.get("phase") == "done" and manifest.get("state") != "completed":
        errors.append("done phase requires completed state")


def _validate_tasks(tasks: list[dict[str, Any]], errors: list[str]) -> None:
    identifiers = [task.get("id") for task in tasks]
    known = set(identifiers)
    if len(known) != len(identifiers):
        errors.append("duplicate task ID")
    for task in tasks:
        label = str(task.get("id", "task"))
        _required(task, TASK_FIELDS, label, errors)
        if not TASK_ID.fullmatch(label):
            errors.append(f"invalid task ID: {label}")
        if not REVISION_ID.fullmatch(str(task.get("revision", ""))):
            errors.append(f"invalid task revision for {label}")
        if task.get("status") not in TASK_STATUSES:
            errors.append(f"invalid task status for {label}: {task.get('status')}")
        for field in ("depends_on", "requirements", "acceptance", "scope", "validation", "evidence"):
            if not isinstance(task.get(field), list):
                errors.append(f"{label}.{field} must be a list")
        for field in ("requirements", "acceptance", "scope", "validation"):
            if isinstance(task.get(field), list) and not task[field]:
                errors.append(f"{label}.{field} must not be empty")
        for field in ("expected_behavior", "rollback", "done_condition"):
            if not isinstance(task.get(field), str) or not task.get(field, "").strip():
                errors.append(f"{label}.{field} must not be empty")
        if not isinstance(task.get("attempt"), int) or task.get("attempt", -1) < 0:
            errors.append(f"{label}.attempt must be a non-negative integer")
        for dependency in task.get("depends_on", []):
            if dependency not in known:
                errors.append(f"unknown dependency for {label}: {dependency}")
        if task.get("status") == "passed" and not task.get("evidence"):
            errors.append(f"passed task requires evidence: {label}")
    _validate_dag(tasks, errors)


def _validate_dag(tasks: list[dict[str, Any]], errors: list[str]) -> None:
    dependencies = {str(task.get("id")): list(task.get("depends_on", [])) for task in tasks}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identifier: str) -> None:
        if identifier in visiting:
            errors.append(f"task dependency cycle at {identifier}")
            return
        if identifier in visited:
            return
        visiting.add(identifier)
        for dependency in dependencies.get(identifier, []):
            if dependency in dependencies:
                visit(dependency)
        visiting.remove(identifier)
        visited.add(identifier)

    for identifier in dependencies:
        visit(identifier)


def _validate_events(events: list[dict[str, Any]], errors: list[str]) -> None:
    identifiers: list[str] = []
    idempotency: list[str] = []
    for event in events:
        _required(event, EVENT_FIELDS, "event", errors)
        identifier = str(event.get("id", ""))
        identifiers.append(identifier)
        if not re_event_id(identifier):
            errors.append(f"invalid event ID: {identifier}")
        for field in ("at", "actor", "type"):
            if not isinstance(event.get(field), str) or not event.get(field, "").strip():
                errors.append(f"event {field} must be a non-empty string: {identifier}")
        if not isinstance(event.get("refs"), list):
            errors.append(f"event refs must be a list: {identifier}")
        if event.get("idempotency_key") is not None and not isinstance(event.get("idempotency_key"), str):
            errors.append(f"event idempotency_key must be a string: {identifier}")
        if event.get("idempotency_key"):
            idempotency.append(str(event["idempotency_key"]))
    if len(set(identifiers)) != len(identifiers):
        errors.append("duplicate event ID")
    if len(set(idempotency)) != len(idempotency):
        errors.append("duplicate event idempotency_key")


def re_event_id(value: str) -> bool:
    return value.startswith("EVT-") and value.removeprefix("EVT-").isdigit()


def _validate_links(
    manifest: dict[str, Any],
    state: dict[str, Any],
    tasks: list[dict[str, Any]],
    events: list[dict[str, Any]],
    errors: list[str],
) -> None:
    _required(state, STATE_FIELDS, "state", errors)
    if state.get("schema_version") != 1:
        errors.append(f"unsupported state schema_version: {state.get('schema_version')}")
    if state.get("state") not in STATES:
        errors.append(f"invalid state: {state.get('state')}")
    for field in ("phase", "state", "active_task", "next_action"):
        if state.get(field) != manifest.get(field):
            errors.append(f"state drift for {field}")
    task_ids = {task.get("id") for task in tasks}
    event_ids = {event.get("id") for event in events}
    if manifest.get("active_task") is not None and manifest.get("active_task") not in task_ids:
        errors.append(f"unknown active_task: {manifest.get('active_task')}")
    if manifest.get("last_event") is not None and manifest.get("last_event") not in event_ids:
        errors.append(f"unknown manifest last_event: {manifest.get('last_event')}")
    in_progress = [task.get("id") for task in tasks if task.get("status") == "in_progress"]
    if len(in_progress) > 1:
        errors.append("multiple tasks are in_progress")
    if in_progress != ([manifest.get("active_task")] if manifest.get("active_task") else []):
        errors.append("active_task does not match in_progress task")
    for task in tasks:
        last_event = task.get("last_event")
        if last_event is not None and last_event not in event_ids:
            errors.append(f"unknown last_event for {task.get('id')}: {last_event}")


def _validate_item(item: Path, errors: list[str]) -> None:
    if not WORK_ITEM_ID.fullmatch(item.name):
        errors.append(f"invalid work item ID: {item.name}")
    for relative_path in REQUIRED_WORK_ITEM_FILES:
        _readable(item / relative_path, errors)
    manifest = _load_mapping(item / "manifest.yaml", "manifest", errors)
    state = _load_mapping(item / "execution/state.yaml", "state", errors)
    tasks = _load_tasks(item / "tasks.yaml", errors)
    events = _load_events(item / "execution/events.ndjson", errors)
    if manifest is not None:
        _validate_manifest(manifest, item, errors)
    if tasks is not None:
        _validate_tasks(tasks, errors)
    _validate_events(events, errors)
    if manifest is not None and state is not None and tasks is not None:
        _validate_links(manifest, state, tasks, events, errors)


def validate_root(root: Path, work_item: str | None = None) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return [f"missing workflow directory: {root}"]
    for relative_path in REQUIRED_ROOT_FILES:
        _readable(root / relative_path, errors)
    transactions = root / ".transactions"
    if transactions.is_dir() and any(transactions.iterdir()):
        errors.append(f"incomplete transaction: {transactions}")
    candidates = iter_work_items(root)
    if work_item:
        candidates = [item for item in candidates if item.name == work_item]
        if not candidates:
            errors.append(f"work item not found: {work_item}")
            return errors
    if not (root / "work-items").is_dir():
        errors.append(f"missing directory: {root / 'work-items'}")
        return errors
    for item in candidates:
        _validate_item(item, errors)
    return errors
