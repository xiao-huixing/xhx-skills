#!/usr/bin/env python3
"""ai-workflow 的确定性状态 CLI。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from workflow_store import (
    EVENTS_FILE,
    UsageError,
    WORK_ITEM_FILE,
    WORK_ITEM_SCHEMA_VERSION,
    WorkflowError,
    WriterLock,
    commit_files,
    dump_data,
    dump_events,
    event_by_idempotency,
    index_records,
    iter_work_items,
    load_data,
    load_events,
    next_event,
    now_iso,
    recover_transactions,
    slugify,
    work_item_path,
)
from workflow_validation import validate_item_data, validate_root


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _item_data(root: Path, work_item: str) -> tuple[Path, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    item = work_item_path(root, work_item)
    if not item.is_dir():
        raise WorkflowError(f"work item not found: {work_item}")
    record = load_data(item / WORK_ITEM_FILE)
    events = load_events(item / EVENTS_FILE)
    if not isinstance(record, dict) or not isinstance(record.get("tasks"), list):
        raise WorkflowError(f"invalid structured state: {item}")
    return item, record, record["tasks"], events


def _ensure_valid(root: Path, work_item: str) -> None:
    errors = validate_root(root, work_item)
    if errors:
        raise WorkflowError("workflow validation failed:\n" + "\n".join(errors))


def _writes_for_item(
    item: Path,
    record: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[Path, str]:
    return {
        item / EVENTS_FILE: dump_events(events),
        item / WORK_ITEM_FILE: dump_data(record),
    }


def _updated_revisions(record: dict[str, Any], **values: Any) -> list[dict[str, Any]]:
    current = record["current_revision"]
    return [
        {**revision, **values} if revision.get("id") == current else revision
        for revision in record["revisions"]
    ]


def _current_revision(record: dict[str, Any]) -> dict[str, Any]:
    current = record["current_revision"]
    revision = next((item for item in record["revisions"] if item.get("id") == current), None)
    if revision is None:
        raise WorkflowError(f"current revision not found: {current}")
    return revision


def _allocate_id(root: Path, date: str, title: str, kind: str, explicit_slug: str | None = None) -> str:
    prefix = "REQ" if kind == "requirement" else "BUG"
    existing = [item.name for item in iter_work_items(root) if item.name.startswith(f"{prefix}-{date}-")]
    numbers = [int(identifier.split("-", 3)[2]) for identifier in existing]
    slug = slugify(explicit_slug or title)
    if explicit_slug and slug != explicit_slug:
        raise UsageError("slug must contain only lowercase ASCII letters, digits, and hyphens")
    return f"{prefix}-{date}-{max(numbers, default=0) + 1:03d}-{slug}"


def command_init(args: argparse.Namespace) -> int:
    root = args.root
    if len(args.date) != 8 or not args.date.isdigit():
        raise UsageError("date must use YYYYMMDD")
    if args.slug is not None and slugify(args.slug) != args.slug:
        raise UsageError("slug must contain only lowercase ASCII letters, digits, and hyphens")
    with WriterLock(root):
        recover_transactions(root)
        if (root / "work-items").exists():
            errors = validate_root(root)
            if errors:
                raise WorkflowError("workflow validation failed:\n" + "\n".join(errors))
        elif any(entry.name != ".writer.lock" for entry in root.iterdir()):
            raise WorkflowError(f"workflow root is not empty: {root}")
        work_item = _allocate_id(root, args.date, args.title, args.kind, args.slug)
        item = work_item_path(root, work_item)
        timestamp = now_iso()
        event = next_event([], work_item, "work_item.created", refs=[])
        record = {
            "schema_version": WORK_ITEM_SCHEMA_VERSION,
            "id": work_item,
            "kind": args.kind,
            "title": args.title,
            "aliases": [],
            "track": args.track,
            "phase": "plan",
            "state": "waiting_input",
            "delivery": "not_started",
            "current_revision": "R001",
            "revisions": [
                {
                    "id": "R001",
                    "input": args.title,
                    "plan": None,
                    "delta": None,
                    "status": "draft",
                    "approved_at": None,
                }
            ],
            "base_commit": args.base_commit,
            "capabilities": [],
            "modules": [],
            "parent": None,
            "supersedes": [],
            "gates": {
                "plan_approved": False,
                "review_approved": False,
                "release_approved": False,
            },
            "active_task": None,
            "next_action": "write_plan",
            "last_event": event["id"],
            "updated_at": timestamp,
            "tasks": [],
            "decisions": [],
            "review": {"result": None, "at": None, "findings": []},
            "summary": args.title,
            "evidence": [],
        }
        events = [event]
        commit_files(root, _writes_for_item(item, record, events))
    _print_json({"status": "initialized", "root": str(root), "work_item": work_item, "track": args.track})
    return 0


def _resolve(root: Path, query: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    lowered = query.casefold()
    for item in iter_work_items(root):
        record = load_data(item / WORK_ITEM_FILE)
        if not isinstance(record, dict):
            continue
        aliases = [str(alias).casefold() for alias in record.get("aliases", [])]
        if query == item.name or lowered == str(record.get("title", "")).casefold() or lowered in aliases:
            matches.append(record)
    if not matches:
        raise WorkflowError(f"work item not found: {query}")
    if len(matches) > 1:
        candidates = ", ".join(str(match.get("id")) for match in matches)
        raise WorkflowError(f"ambiguous work item: {query}; candidates: {candidates}")
    return matches[0]


def command_resolve(args: argparse.Namespace) -> int:
    record = _resolve(args.root, args.query)
    _print_json({"work_item": record["id"], "title": record["title"]})
    return 0


def command_status(args: argparse.Namespace) -> int:
    root = args.root
    if not root.is_dir():
        payload = {"status": "not_initialized", "root": str(root)}
    elif not args.work_item:
        active = [
            record for record in index_records(root) if record.get("state") not in {"completed", "cancelled"}
        ]
        payload = {"status": "initialized", "active": active}
    else:
        _, record, tasks, _ = _item_data(root, args.work_item)
        payload = {
            "status": "ok",
            "work_item": record["id"],
            "title": record["title"],
            "track": record["track"],
            "phase": record["phase"],
            "state": record["state"],
            "delivery": record["delivery"],
            "active_task": record.get("active_task"),
            "next_action": record.get("next_action"),
            "tasks": {
                "total": len(tasks),
                "passed": sum(task.get("status") == "passed" for task in tasks),
                "blocked": sum(task.get("status") == "blocked" for task in tasks),
            },
        }
    if args.format == "json":
        _print_json(payload)
    else:
        print(" | ".join(f"{key}={value}" for key, value in payload.items()))
    return 0


def command_history(args: argparse.Namespace) -> int:
    if not args.root.is_dir():
        _print_json({"matches": []})
        return 0
    query = args.query.casefold()
    matches = [record for record in index_records(args.root) if query in json.dumps(record, ensure_ascii=False).casefold()]
    _print_json({"matches": matches[: args.limit]})
    return 0


def command_validate(args: argparse.Namespace) -> int:
    errors = validate_root(args.root, args.work_item)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    _print_json({"status": "valid", "root": str(args.root), "work_item": args.work_item})
    return 0


def command_set_plan(args: argparse.Namespace) -> int:
    plan = args.plan_file.read_text(encoding="utf-8").strip()
    if not plan:
        raise UsageError("set-plan requires a non-empty --plan-file")
    tasks = load_data(args.tasks_file)
    if not isinstance(tasks, list) or not tasks or any(not isinstance(task, dict) for task in tasks):
        raise UsageError("set-plan requires --tasks-file containing a non-empty task list")
    if any(task.get("status") != "pending" for task in tasks):
        raise UsageError("set-plan requires every task to start with pending status")
    supplied_input = args.input_file.read_text(encoding="utf-8").strip() if args.input_file else None
    if args.input_file and not supplied_input:
        raise UsageError("set-plan requires a non-empty --input-file")
    with WriterLock(args.root):
        recover_transactions(args.root)
        _ensure_valid(args.root, args.work_item)
        item, record, _, events = _item_data(args.root, args.work_item)
        repeated = event_by_idempotency(events, args.idempotency_key)
        if repeated:
            _print_json({"status": "idempotent", "event": repeated["id"], "work_item": args.work_item})
            return 0
        if record.get("phase") != "plan" or record.get("gates", {}).get("plan_approved"):
            raise WorkflowError("set-plan requires an unapproved plan phase")
        revision = _current_revision(record)
        event = next_event(
            events,
            args.work_item,
            "plan.updated",
            refs=[],
            idempotency_key=args.idempotency_key,
        )
        updated_record = {
            **record,
            "revisions": _updated_revisions(
                record,
                input=supplied_input or revision["input"],
                plan=plan,
                status="draft",
                approved_at=None,
            ),
            "tasks": tasks,
            "state": "waiting_input",
            "next_action": "plan_ready",
            "last_event": event["id"],
            "updated_at": event["at"],
        }
        updated_events = [*events, event]
        errors = validate_item_data(item, updated_record, updated_events)
        if errors:
            raise WorkflowError("plan update validation failed:\n" + "\n".join(errors))
        commit_files(args.root, _writes_for_item(item, updated_record, updated_events))
    _print_json({"status": "updated", "work_item": args.work_item, "tasks": len(tasks)})
    return 0


def command_plan_ready(args: argparse.Namespace) -> int:
    with WriterLock(args.root):
        recover_transactions(args.root)
        _ensure_valid(args.root, args.work_item)
        item, record, tasks, events = _item_data(args.root, args.work_item)
        repeated = event_by_idempotency(events, args.idempotency_key)
        if repeated:
            _print_json({"status": "idempotent", "event": repeated["id"], "work_item": args.work_item})
            return 0
        if record.get("phase") != "plan" or record.get("gates", {}).get("plan_approved"):
            raise WorkflowError("plan-ready requires an unapproved plan phase")
        if not tasks:
            raise WorkflowError("plan-ready requires at least one task")
        revision = _current_revision(record)
        if not isinstance(revision.get("plan"), str) or not revision.get("plan", "").strip():
            raise WorkflowError("plan-ready requires a stored plan")
        event = next_event(
            events,
            args.work_item,
            "plan.ready",
            refs=[],
            idempotency_key=args.idempotency_key,
        )
        updated_record = {
            **record,
            "revisions": _updated_revisions(record, status="ready"),
            "state": "waiting_input",
            "next_action": "approve_plan",
            "last_event": event["id"],
            "updated_at": event["at"],
        }
        commit_files(args.root, _writes_for_item(item, updated_record, [*events, event]))
    _print_json({"status": "ready", "work_item": args.work_item, "next_action": "approve_plan"})
    return 0


def command_approve_plan(args: argparse.Namespace) -> int:
    with WriterLock(args.root):
        recover_transactions(args.root)
        _ensure_valid(args.root, args.work_item)
        item, record, tasks, events = _item_data(args.root, args.work_item)
        repeated = event_by_idempotency(events, args.idempotency_key)
        if repeated:
            _print_json({"status": "idempotent", "event": repeated["id"], "work_item": args.work_item})
            return 0
        if record.get("phase") != "plan":
            raise WorkflowError("plan approval requires plan phase")
        if record.get("next_action") != "approve_plan":
            raise WorkflowError("plan approval requires plan-ready transition")
        if not tasks:
            raise WorkflowError("plan approval requires at least one task")
        if _current_revision(record).get("status") != "ready":
            raise WorkflowError("plan approval requires ready revision")
        event = next_event(
            events,
            args.work_item,
            "plan.approved",
            refs=[],
            idempotency_key=args.idempotency_key,
        )
        first_task = next((task["id"] for task in tasks if task.get("status") == "pending"), None)
        updated_record = {
            **record,
            "phase": "execute",
            "state": "active",
            "gates": {**record["gates"], "plan_approved": True},
            "revisions": _updated_revisions(record, status="approved", approved_at=event["at"]),
            "next_action": first_task,
            "last_event": event["id"],
            "updated_at": event["at"],
        }
        commit_files(args.root, _writes_for_item(item, updated_record, [*events, event]))
    _print_json({"status": "approved", "work_item": args.work_item, "next_action": first_task})
    return 0


def _task_update(
    task: dict[str, Any], action: str, event: dict[str, Any], evidence: str | None, error_class: str | None
) -> dict[str, Any]:
    if action == "begin":
        return {
            **task,
            "status": "in_progress",
            "attempt": int(task.get("attempt", 0)) + 1,
            "failure": None,
            "last_event": event["id"],
        }
    if action == "pass":
        return {
            **task,
            "status": "passed",
            "evidence": [*task.get("evidence", []), evidence],
            "failure": None,
            "last_event": event["id"],
        }
    status = "failed" if action == "fail" else "blocked"
    return {**task, "status": status, "failure": error_class or action, "last_event": event["id"]}


def command_task(args: argparse.Namespace) -> int:
    if args.action == "pass" and not args.evidence:
        raise UsageError("task pass requires --evidence")
    with WriterLock(args.root):
        recover_transactions(args.root)
        _ensure_valid(args.root, args.work_item)
        item, record, tasks, events = _item_data(args.root, args.work_item)
        repeated = event_by_idempotency(events, args.idempotency_key)
        if repeated:
            _print_json({"status": "idempotent", "event": repeated["id"], "task": args.task})
            return 0
        if record.get("phase") != "execute" or not record.get("gates", {}).get("plan_approved"):
            raise WorkflowError("task transition requires approved execute phase")
        current = next((task for task in tasks if task.get("id") == args.task), None)
        if current is None:
            raise WorkflowError(f"task not found: {args.task}")
        allowed = {"begin": {"pending", "failed", "blocked"}, "pass": {"in_progress"}, "fail": {"in_progress"}, "block": {"in_progress"}}
        if current.get("status") not in allowed[args.action]:
            expected = ", ".join(sorted(allowed[args.action]))
            raise WorkflowError(f"task {args.action} requires status {expected}; got {current.get('status')}")
        if args.action == "begin":
            by_id = {task["id"]: task for task in tasks}
            unmet = [dependency for dependency in current.get("depends_on", []) if by_id[dependency].get("status") != "passed"]
            if unmet:
                raise WorkflowError(f"task dependency not passed: {', '.join(unmet)}")
        event_type = {"begin": "task.started", "pass": "task.passed", "fail": "task.failed", "block": "task.blocked"}[args.action]
        event = next_event(
            events,
            args.work_item,
            event_type,
            task=args.task,
            refs=[args.evidence] if args.evidence else [],
            error_class=args.error_class,
            idempotency_key=args.idempotency_key,
        )
        updated_task = _task_update(current, args.action, event, args.evidence, args.error_class)
        updated_tasks = [updated_task if task.get("id") == args.task else task for task in tasks]
        all_done = all(task.get("status") in {"passed", "skipped"} for task in updated_tasks)
        if args.action == "begin":
            record_values = {"state": "active", "active_task": args.task, "next_action": args.task}
        elif args.action == "pass" and all_done:
            record_values = {
                "phase": "review",
                "state": "active",
                "delivery": "implemented",
                "active_task": None,
                "next_action": "review",
            }
        elif args.action == "pass":
            pending = next((task["id"] for task in updated_tasks if task.get("status") == "pending"), None)
            record_values = {"state": "active", "active_task": None, "next_action": pending}
        else:
            record_values = {"state": "blocked", "active_task": None, "next_action": args.task}
        updated_record = {
            **record,
            **record_values,
            "tasks": updated_tasks,
            "last_event": event["id"],
            "updated_at": event["at"],
        }
        updated_events = [*events, event]
        commit_files(args.root, _writes_for_item(item, updated_record, updated_events))
    _print_json({"status": updated_task["status"], "task": args.task, "event": event["id"]})
    return 0


def command_review(args: argparse.Namespace) -> int:
    findings = args.findings_file.read_text(encoding="utf-8").strip() if args.findings_file else None
    remediation_tasks: list[dict[str, Any]] = []
    if args.remediation_tasks_file:
        supplied_tasks = load_data(args.remediation_tasks_file)
        if not isinstance(supplied_tasks, list) or not supplied_tasks or any(
            not isinstance(task, dict) for task in supplied_tasks
        ):
            raise UsageError(
                "review requires --remediation-tasks-file containing a non-empty task list"
            )
        remediation_tasks = supplied_tasks
    if args.result == "needs_changes" and not remediation_tasks:
        raise UsageError("needs_changes requires --remediation-tasks-file")
    if args.result != "needs_changes" and remediation_tasks:
        raise UsageError("--remediation-tasks-file is only valid for needs_changes")
    if any(task.get("status") != "pending" for task in remediation_tasks):
        raise UsageError("remediation tasks must start with pending status")
    with WriterLock(args.root):
        recover_transactions(args.root)
        _ensure_valid(args.root, args.work_item)
        item, record, tasks, events = _item_data(args.root, args.work_item)
        repeated = event_by_idempotency(events, args.idempotency_key)
        if repeated:
            _print_json({"status": "idempotent", "event": repeated["id"], "work_item": args.work_item})
            return 0
        if record.get("phase") != "review":
            raise WorkflowError("review result requires review phase")
        event = next_event(
            events,
            args.work_item,
            "review.completed",
            result=args.result,
            refs=[],
            idempotency_key=args.idempotency_key,
        )
        if args.result in {"passed", "passed_with_risks"}:
            values = {"phase": "done", "state": "completed", "next_action": None}
        elif args.result == "needs_changes":
            next_task = remediation_tasks[0]["id"]
            values = {"phase": "execute", "state": "active", "next_action": next_task}
        else:
            values = {"state": "blocked", "next_action": "resolve_review_blocker"}
        updated_record = {
            **record,
            **values,
            "gates": {**record["gates"], "review_approved": args.result in {"passed", "passed_with_risks"}},
            "review": {
                "result": args.result,
                "at": event["at"],
                "findings": [findings] if findings else [],
            },
            "tasks": [*tasks, *remediation_tasks],
            "last_event": event["id"],
            "updated_at": event["at"],
        }
        updated_events = [*events, event]
        errors = validate_item_data(item, updated_record, updated_events)
        if errors:
            raise WorkflowError("review update validation failed:\n" + "\n".join(errors))
        commit_files(args.root, _writes_for_item(item, updated_record, updated_events))
    _print_json({"status": args.result, "work_item": args.work_item})
    return 0


def command_refresh_index(args: argparse.Namespace) -> int:
    if not args.root.is_dir():
        raise WorkflowError(f"missing workflow directory: {args.root}")
    _print_json({"status": "derived", "records": len(index_records(args.root))})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage deterministic .ai-workflow state")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--root", type=Path, default=Path(".ai-workflow"))
    init.add_argument("--title", required=True)
    init.add_argument("--slug")
    init.add_argument("--date", required=True)
    init.add_argument("--track", choices=("light", "standard", "strict"), default="standard")
    init.add_argument("--kind", choices=("requirement", "bugfix"), default="requirement")
    init.add_argument("--base-commit")
    init.set_defaults(handler=command_init)

    status = subparsers.add_parser("status")
    status.add_argument("--root", type=Path, default=Path(".ai-workflow"))
    status.add_argument("--work-item")
    status.add_argument("--format", choices=("json", "text"), default="text")
    status.set_defaults(handler=command_status)

    resolve = subparsers.add_parser("resolve")
    resolve.add_argument("--root", type=Path, default=Path(".ai-workflow"))
    resolve.add_argument("query")
    resolve.set_defaults(handler=command_resolve)

    history = subparsers.add_parser("history")
    history.add_argument("--root", type=Path, default=Path(".ai-workflow"))
    history.add_argument("query")
    history.add_argument("--limit", type=int, default=20)
    history.set_defaults(handler=command_history)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--root", type=Path, default=Path(".ai-workflow"))
    validate.add_argument("--work-item")
    validate.set_defaults(handler=command_validate)

    set_plan = subparsers.add_parser("set-plan")
    set_plan.add_argument("--root", type=Path, default=Path(".ai-workflow"))
    set_plan.add_argument("--work-item", required=True)
    set_plan.add_argument("--input-file", type=Path)
    set_plan.add_argument("--plan-file", type=Path, required=True)
    set_plan.add_argument("--tasks-file", type=Path, required=True)
    set_plan.add_argument("--idempotency-key")
    set_plan.set_defaults(handler=command_set_plan)

    ready = subparsers.add_parser("plan-ready")
    ready.add_argument("--root", type=Path, default=Path(".ai-workflow"))
    ready.add_argument("--work-item", required=True)
    ready.add_argument("--idempotency-key")
    ready.set_defaults(handler=command_plan_ready)

    approve = subparsers.add_parser("approve-plan")
    approve.add_argument("--root", type=Path, default=Path(".ai-workflow"))
    approve.add_argument("--work-item", required=True)
    approve.add_argument("--idempotency-key")
    approve.set_defaults(handler=command_approve_plan)

    task = subparsers.add_parser("task")
    task.add_argument("action", choices=("begin", "pass", "fail", "block"))
    task.add_argument("--root", type=Path, default=Path(".ai-workflow"))
    task.add_argument("--work-item", required=True)
    task.add_argument("--task", required=True)
    task.add_argument("--evidence")
    task.add_argument("--error-class")
    task.add_argument("--idempotency-key")
    task.set_defaults(handler=command_task)

    review = subparsers.add_parser("review")
    review.add_argument("--root", type=Path, default=Path(".ai-workflow"))
    review.add_argument("--work-item", required=True)
    review.add_argument("--result", choices=("passed", "passed_with_risks", "needs_changes", "blocked"), required=True)
    review.add_argument("--findings-file", type=Path)
    review.add_argument("--remediation-tasks-file", type=Path)
    review.add_argument("--idempotency-key")
    review.set_defaults(handler=command_review)

    refresh = subparsers.add_parser("refresh-index")
    refresh.add_argument("--root", type=Path, default=Path(".ai-workflow"))
    refresh.set_defaults(handler=command_refresh_index)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.handler(args))
    except UsageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except (WorkflowError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
