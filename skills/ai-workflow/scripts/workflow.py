#!/usr/bin/env python3
"""ai-workflow 的确定性状态 CLI。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from workflow_store import (
    UsageError,
    WorkflowError,
    WriterLock,
    commit_files,
    dump_data,
    dump_events,
    event_by_idempotency,
    index_records,
    index_writes,
    iter_work_items,
    load_data,
    load_events,
    make_context,
    make_state,
    next_event,
    now_iso,
    recover_transactions,
    slugify,
    work_item_path,
)
from workflow_validation import validate_root


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _item_data(root: Path, work_item: str) -> tuple[Path, dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    item = work_item_path(root, work_item)
    if not item.is_dir():
        raise WorkflowError(f"work item not found: {work_item}")
    manifest = load_data(item / "manifest.yaml")
    tasks = load_data(item / "tasks.yaml")
    events = load_events(item / "execution/events.ndjson")
    if not isinstance(manifest, dict) or not isinstance(tasks, list):
        raise WorkflowError(f"invalid structured state: {item}")
    return item, manifest, tasks, events


def _ensure_valid(root: Path, work_item: str) -> None:
    errors = validate_root(root, work_item)
    if errors:
        raise WorkflowError("workflow validation failed:\n" + "\n".join(errors))


def _writes_for_item(
    root: Path,
    item: Path,
    manifest: dict[str, Any],
    tasks: list[dict[str, Any]],
    events: list[dict[str, Any]],
) -> dict[Path, str]:
    writes = {
        item / "manifest.yaml": dump_data(manifest),
        item / "tasks.yaml": dump_data(tasks),
        item / "execution/events.ndjson": dump_events(events),
        item / "execution/state.yaml": dump_data(make_state(manifest, tasks, events)),
        item / "context.md": make_context(manifest, tasks),
    }
    return {**writes, **index_writes(root, manifest)}


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
        work_item = _allocate_id(root, args.date, args.title, args.kind, args.slug)
        item = work_item_path(root, work_item)
        timestamp = now_iso()
        event = next_event([], "work_item.created", refs=[])
        manifest = {
            "schema_version": 1,
            "id": work_item,
            "kind": args.kind,
            "title": args.title,
            "aliases": [],
            "track": args.track,
            "phase": "plan",
            "state": "waiting_input",
            "delivery": "not_started",
            "current_revision": "R001",
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
        }
        tasks: list[dict[str, Any]] = []
        events = [event]
        root_writes = {
            root / "README.md": "# AI Workflow\n\nUse the bundled workflow CLI to inspect and mutate state.\n",
            root / "project/overview.md": "# Project Overview\n\n- Purpose: unknown\n- Architecture: unknown\n- Quality gates: unknown\n",
            root / "project/modules.yaml": dump_data([]),
            root / "capabilities/index.yaml": dump_data([]),
            item / "revisions/R001/input.md": f"# Input\n\n{args.title}\n",
        }
        commit_files(root, {**root_writes, **_writes_for_item(root, item, manifest, tasks, events)})
    _print_json({"status": "initialized", "root": str(root), "work_item": work_item, "track": args.track})
    return 0


def _resolve(root: Path, query: str) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    lowered = query.casefold()
    for item in iter_work_items(root):
        manifest = load_data(item / "manifest.yaml")
        if not isinstance(manifest, dict):
            continue
        aliases = [str(alias).casefold() for alias in manifest.get("aliases", [])]
        if query == item.name or lowered == str(manifest.get("title", "")).casefold() or lowered in aliases:
            matches.append(manifest)
    if not matches:
        raise WorkflowError(f"work item not found: {query}")
    if len(matches) > 1:
        candidates = ", ".join(str(match.get("id")) for match in matches)
        raise WorkflowError(f"ambiguous work item: {query}; candidates: {candidates}")
    return matches[0]


def command_resolve(args: argparse.Namespace) -> int:
    manifest = _resolve(args.root, args.query)
    _print_json({"work_item": manifest["id"], "title": manifest["title"]})
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
        _, manifest, tasks, _ = _item_data(root, args.work_item)
        payload = {
            "status": "ok",
            "work_item": manifest["id"],
            "title": manifest["title"],
            "track": manifest["track"],
            "phase": manifest["phase"],
            "state": manifest["state"],
            "delivery": manifest["delivery"],
            "active_task": manifest.get("active_task"),
            "next_action": manifest.get("next_action"),
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


def command_plan_ready(args: argparse.Namespace) -> int:
    with WriterLock(args.root):
        recover_transactions(args.root)
        _ensure_valid(args.root, args.work_item)
        item, manifest, tasks, events = _item_data(args.root, args.work_item)
        repeated = event_by_idempotency(events, args.idempotency_key)
        if repeated:
            _print_json({"status": "idempotent", "event": repeated["id"], "work_item": args.work_item})
            return 0
        if manifest.get("phase") != "plan" or manifest.get("gates", {}).get("plan_approved"):
            raise WorkflowError("plan-ready requires an unapproved plan phase")
        if not tasks:
            raise WorkflowError("plan-ready requires at least one task")
        event = next_event(events, "plan.ready", refs=[], idempotency_key=args.idempotency_key)
        updated_manifest = {
            **manifest,
            "state": "waiting_input",
            "next_action": "approve_plan",
            "last_event": event["id"],
            "updated_at": event["at"],
        }
        commit_files(args.root, _writes_for_item(args.root, item, updated_manifest, tasks, [*events, event]))
    _print_json({"status": "ready", "work_item": args.work_item, "next_action": "approve_plan"})
    return 0


def command_approve_plan(args: argparse.Namespace) -> int:
    with WriterLock(args.root):
        recover_transactions(args.root)
        _ensure_valid(args.root, args.work_item)
        item, manifest, tasks, events = _item_data(args.root, args.work_item)
        repeated = event_by_idempotency(events, args.idempotency_key)
        if repeated:
            _print_json({"status": "idempotent", "event": repeated["id"], "work_item": args.work_item})
            return 0
        if manifest.get("phase") != "plan":
            raise WorkflowError("plan approval requires plan phase")
        if manifest.get("next_action") != "approve_plan":
            raise WorkflowError("plan approval requires plan-ready transition")
        if not tasks:
            raise WorkflowError("plan approval requires at least one task")
        event = next_event(events, "plan.approved", refs=[], idempotency_key=args.idempotency_key)
        first_task = next((task["id"] for task in tasks if task.get("status") == "pending"), None)
        updated_manifest = {
            **manifest,
            "phase": "execute",
            "state": "active",
            "gates": {**manifest["gates"], "plan_approved": True},
            "next_action": first_task,
            "last_event": event["id"],
            "updated_at": event["at"],
        }
        commit_files(args.root, _writes_for_item(args.root, item, updated_manifest, tasks, [*events, event]))
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
        item, manifest, tasks, events = _item_data(args.root, args.work_item)
        repeated = event_by_idempotency(events, args.idempotency_key)
        if repeated:
            _print_json({"status": "idempotent", "event": repeated["id"], "task": args.task})
            return 0
        if manifest.get("phase") != "execute" or not manifest.get("gates", {}).get("plan_approved"):
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
            manifest_values = {"state": "active", "active_task": args.task, "next_action": args.task}
        elif args.action == "pass" and all_done:
            manifest_values = {
                "phase": "review",
                "state": "active",
                "delivery": "implemented",
                "active_task": None,
                "next_action": "review",
            }
        elif args.action == "pass":
            pending = next((task["id"] for task in updated_tasks if task.get("status") == "pending"), None)
            manifest_values = {"state": "active", "active_task": None, "next_action": pending}
        else:
            manifest_values = {"state": "blocked", "active_task": None, "next_action": args.task}
        updated_manifest = {
            **manifest,
            **manifest_values,
            "last_event": event["id"],
            "updated_at": event["at"],
        }
        updated_events = [*events, event]
        commit_files(args.root, _writes_for_item(args.root, item, updated_manifest, updated_tasks, updated_events))
    _print_json({"status": updated_task["status"], "task": args.task, "event": event["id"]})
    return 0


def command_review(args: argparse.Namespace) -> int:
    with WriterLock(args.root):
        recover_transactions(args.root)
        _ensure_valid(args.root, args.work_item)
        item, manifest, tasks, events = _item_data(args.root, args.work_item)
        repeated = event_by_idempotency(events, args.idempotency_key)
        if repeated:
            _print_json({"status": "idempotent", "event": repeated["id"], "work_item": args.work_item})
            return 0
        if manifest.get("phase") != "review":
            raise WorkflowError("review result requires review phase")
        if args.result == "needs_changes" and not any(task.get("status") == "pending" for task in tasks):
            raise WorkflowError("needs_changes requires a pending remediation task")
        event = next_event(
            events,
            "review.completed",
            result=args.result,
            refs=[],
            idempotency_key=args.idempotency_key,
        )
        if args.result in {"passed", "passed_with_risks"}:
            values = {"phase": "done", "state": "completed", "next_action": None}
        elif args.result == "needs_changes":
            next_task = next(task["id"] for task in tasks if task.get("status") == "pending")
            values = {"phase": "execute", "state": "active", "next_action": next_task}
        else:
            values = {"state": "blocked", "next_action": "resolve_review_blocker"}
        updated_manifest = {
            **manifest,
            **values,
            "gates": {**manifest["gates"], "review_approved": args.result in {"passed", "passed_with_risks"}},
            "review": {"result": args.result, "at": event["at"]},
            "last_event": event["id"],
            "updated_at": event["at"],
        }
        commit_files(args.root, _writes_for_item(args.root, item, updated_manifest, tasks, [*events, event]))
    _print_json({"status": args.result, "work_item": args.work_item})
    return 0


def command_refresh_index(args: argparse.Namespace) -> int:
    if not args.root.is_dir():
        raise WorkflowError(f"missing workflow directory: {args.root}")
    with WriterLock(args.root):
        recover_transactions(args.root)
        commit_files(args.root, index_writes(args.root))
    _print_json({"status": "refreshed", "records": len(index_records(args.root))})
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
