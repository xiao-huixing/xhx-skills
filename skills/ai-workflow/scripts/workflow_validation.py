"""ai-workflow 双文件 schema 与状态一致性校验。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from workflow_store import (
    DELIVERIES,
    EVENTS_FILE,
    EVENT_SCHEMA_VERSION,
    PHASES,
    REQUIRED_WORK_ITEM_FILES,
    REVISION_ID,
    STATES,
    TASK_ID,
    TASK_STATUSES,
    TRACKS,
    WORK_ITEM_FILE,
    WORK_ITEM_ID,
    WORK_ITEM_SCHEMA_VERSION,
    WorkflowError,
    iter_work_items,
    load_data,
)


WORK_ITEM_FIELDS = (
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
    "revisions",
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
    "tasks",
    "decisions",
    "review",
    "summary",
    "evidence",
)
REVISION_FIELDS = ("id", "input", "plan", "delta", "status", "approved_at")
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
EVENT_FIELDS = (
    "schema_version",
    "id",
    "work_item_id",
    "sequence",
    "at",
    "actor",
    "type",
    "refs",
)
REVISION_STATUSES = frozenset({"draft", "ready", "approved", "superseded"})
REVIEW_RESULTS = frozenset({"passed", "passed_with_risks", "needs_changes", "blocked"})
ALLOWED_ROOT_ENTRIES = frozenset({"work-items", ".transactions", ".writer.lock"})


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


def _validate_revisions(record: dict[str, Any], errors: list[str]) -> set[str]:
    revisions = record.get("revisions")
    if not isinstance(revisions, list) or not revisions or any(not isinstance(item, dict) for item in revisions):
        errors.append("work-item revisions must be a non-empty list of objects")
        return set()
    identifiers: list[str] = []
    for revision in revisions:
        _required(revision, REVISION_FIELDS, "revision", errors)
        identifier = str(revision.get("id", ""))
        identifiers.append(identifier)
        if not REVISION_ID.fullmatch(identifier):
            errors.append(f"invalid revision ID: {identifier}")
        if not isinstance(revision.get("input"), str) or not revision.get("input", "").strip():
            errors.append(f"revision input must be a non-empty string: {identifier}")
        for field in ("plan", "delta", "approved_at"):
            if revision.get(field) is not None and not isinstance(revision.get(field), str):
                errors.append(f"revision {field} must be a string or null: {identifier}")
        if revision.get("status") not in REVISION_STATUSES:
            errors.append(f"invalid revision status for {identifier}: {revision.get('status')}")
    if len(set(identifiers)) != len(identifiers):
        errors.append("duplicate revision ID")
    current = record.get("current_revision")
    if current not in identifiers:
        errors.append(f"unknown current_revision: {current}")
    return set(identifiers)


def _validate_work_item(record: dict[str, Any], item: Path, errors: list[str]) -> set[str]:
    _required(record, WORK_ITEM_FIELDS, "work-item", errors)
    if record.get("schema_version") != WORK_ITEM_SCHEMA_VERSION:
        errors.append(f"unsupported work-item schema_version: {record.get('schema_version')}")
    if record.get("id") != item.name:
        errors.append(f"work-item id does not match directory: {item}")
    if record.get("kind") not in {"requirement", "bugfix"}:
        errors.append(f"invalid kind: {record.get('kind')}")
    if not isinstance(record.get("title"), str) or not record.get("title", "").strip():
        errors.append("work-item title must be a non-empty string")
    for field in ("aliases", "capabilities", "modules", "supersedes", "decisions", "evidence"):
        if not isinstance(record.get(field), list):
            errors.append(f"work-item {field} must be a list")
    if record.get("track") not in TRACKS:
        errors.append(f"invalid track: {record.get('track')}")
    if record.get("phase") not in PHASES:
        errors.append(f"invalid phase: {record.get('phase')}")
    if record.get("state") not in STATES:
        errors.append(f"invalid state: {record.get('state')}")
    if record.get("delivery") not in DELIVERIES:
        errors.append(f"invalid delivery: {record.get('delivery')}")
    if not REVISION_ID.fullmatch(str(record.get("current_revision", ""))):
        errors.append(f"invalid current_revision: {record.get('current_revision')}")
    revision_ids = _validate_revisions(record, errors)
    if record.get("base_commit") is not None and not isinstance(record.get("base_commit"), str):
        errors.append("work-item base_commit must be a string or null")
    for field in ("parent", "active_task", "next_action", "last_event"):
        if record.get(field) is not None and not isinstance(record.get(field), str):
            errors.append(f"work-item {field} must be a string or null")
    if not isinstance(record.get("updated_at"), str) or not record.get("updated_at", "").strip():
        errors.append("work-item updated_at must be a non-empty string")
    if not isinstance(record.get("summary"), str) or not record.get("summary", "").strip():
        errors.append("work-item summary must be a non-empty string")
    gates = record.get("gates")
    if not isinstance(gates, dict):
        errors.append("work-item gates must be an object")
    else:
        for gate in ("plan_approved", "review_approved", "release_approved"):
            if not isinstance(gates.get(gate), bool):
                errors.append(f"work-item gates.{gate} must be boolean")
    if record.get("phase") in {"execute", "review", "done"} and not (
        isinstance(gates, dict) and gates.get("plan_approved") is True
    ):
        errors.append("plan gate must be approved after plan phase")
    if record.get("phase") == "done" and record.get("state") != "completed":
        errors.append("done phase requires completed state")
    review = record.get("review")
    if not isinstance(review, dict):
        errors.append("work-item review must be an object")
    else:
        _required(review, ("result", "at", "findings"), "review", errors)
        if review.get("result") is not None and review.get("result") not in REVIEW_RESULTS:
            errors.append(f"invalid review result: {review.get('result')}")
        if review.get("at") is not None and not isinstance(review.get("at"), str):
            errors.append("review at must be a string or null")
        if not isinstance(review.get("findings"), list):
            errors.append("review findings must be a list")
    return revision_ids


def _validate_tasks(tasks: Any, revision_ids: set[str], errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(tasks, list) or any(not isinstance(task, dict) for task in tasks):
        errors.append("work-item tasks must be a list of objects")
        return []
    identifiers = [task.get("id") for task in tasks]
    known = set(identifiers)
    if len(known) != len(identifiers):
        errors.append("duplicate task ID")
    for task in tasks:
        label = str(task.get("id", "task"))
        _required(task, TASK_FIELDS, label, errors)
        if not TASK_ID.fullmatch(label):
            errors.append(f"invalid task ID: {label}")
        if task.get("revision") not in revision_ids:
            errors.append(f"unknown task revision for {label}: {task.get('revision')}")
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
    return tasks


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


def _validate_events(events: list[dict[str, Any]], item: Path, errors: list[str]) -> None:
    identifiers: list[str] = []
    idempotency: list[str] = []
    for expected_sequence, event in enumerate(events, 1):
        _required(event, EVENT_FIELDS, "event", errors)
        identifier = str(event.get("id", ""))
        identifiers.append(identifier)
        if event.get("schema_version") != EVENT_SCHEMA_VERSION:
            errors.append(f"unsupported event schema_version: {event.get('schema_version')}")
        if event.get("work_item_id") != item.name:
            errors.append(f"event work_item_id does not match directory: {identifier}")
        if event.get("sequence") != expected_sequence:
            errors.append(f"event sequence must be {expected_sequence}: {identifier}")
        if identifier != f"EVT-{expected_sequence:06d}":
            errors.append(f"event ID does not match sequence: {identifier}")
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


def _validate_links(
    record: dict[str, Any],
    tasks: list[dict[str, Any]],
    events: list[dict[str, Any]],
    errors: list[str],
) -> None:
    task_ids = {task.get("id") for task in tasks}
    event_ids = {event.get("id") for event in events}
    if record.get("active_task") is not None and record.get("active_task") not in task_ids:
        errors.append(f"unknown active_task: {record.get('active_task')}")
    if record.get("last_event") is not None and record.get("last_event") not in event_ids:
        errors.append(f"unknown work-item last_event: {record.get('last_event')}")
    if events and record.get("last_event") != events[-1].get("id"):
        errors.append("work-item last_event is not the latest event")
    in_progress = [task.get("id") for task in tasks if task.get("status") == "in_progress"]
    if len(in_progress) > 1:
        errors.append("multiple tasks are in_progress")
    if in_progress != ([record.get("active_task")] if record.get("active_task") else []):
        errors.append("active_task does not match in_progress task")
    for task in tasks:
        last_event = task.get("last_event")
        if last_event is not None and last_event not in event_ids:
            errors.append(f"unknown last_event for {task.get('id')}: {last_event}")


def validate_item_data(item: Path, record: dict[str, Any], events: list[dict[str, Any]]) -> list[str]:
    """校验尚未写入磁盘的单工作项候选状态。"""
    errors: list[str] = []
    revision_ids = _validate_work_item(record, item, errors)
    tasks = _validate_tasks(record.get("tasks"), revision_ids, errors)
    _validate_events(events, item, errors)
    _validate_links(record, tasks, events, errors)
    return errors


def _validate_item(item: Path, errors: list[str]) -> None:
    if not WORK_ITEM_ID.fullmatch(item.name):
        errors.append(f"invalid work item ID: {item.name}")
    actual_files = {
        str(path.relative_to(item))
        for path in item.rglob("*")
        if path.is_file()
    }
    for required in REQUIRED_WORK_ITEM_FILES:
        if required not in actual_files:
            errors.append(f"missing file: {item / required}")
    for unexpected in sorted(actual_files - set(REQUIRED_WORK_ITEM_FILES)):
        errors.append(f"unexpected work-item file: {unexpected}")
    if "manifest.yaml" in actual_files and WORK_ITEM_FILE not in actual_files:
        errors.append(f"legacy storage layout is unsupported: {item}")
    record = _load_mapping(item / WORK_ITEM_FILE, "work-item", errors)
    events = _load_events(item / EVENTS_FILE, errors)
    if record is not None:
        errors.extend(validate_item_data(item, record, events))


def validate_root(root: Path, work_item: str | None = None) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return [f"missing workflow directory: {root}"]
    for entry in root.iterdir():
        if entry.name not in ALLOWED_ROOT_ENTRIES:
            errors.append(f"unexpected workflow root entry: {entry.name}")
    transactions = root / ".transactions"
    if transactions.is_dir() and any(transactions.iterdir()):
        errors.append(f"incomplete transaction: {transactions}")
    if not (root / "work-items").is_dir():
        errors.append(f"missing directory: {root / 'work-items'}")
        return errors
    candidates = iter_work_items(root)
    if work_item:
        candidates = [item for item in candidates if item.name == work_item]
        if not candidates:
            errors.append(f"work item not found: {work_item}")
            return errors
    for item in candidates:
        _validate_item(item, errors)
    return errors
