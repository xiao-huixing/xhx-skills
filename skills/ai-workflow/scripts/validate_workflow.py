#!/usr/bin/env python3
"""Validate the deterministic parts of a .ai-workflow directory."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


WORK_ITEM_ID = re.compile(r"^(?:REQ|BUG)-\d{8}-\d{3}-[a-z0-9-]+$")
REQUIRED_ROOT_FILES = (
    "project/overview.md",
    "project/modules.yaml",
    "capabilities/index.yaml",
    "indexes/active.yaml",
)
REQUIRED_WORK_ITEM_FILES = (
    "manifest.yaml",
    "context.md",
    "tasks.yaml",
    "execution/state.yaml",
    "execution/events.ndjson",
)


def _readable(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        errors.append(f"missing file: {path}")


def _validate_events(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        return
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
        for key in ("id", "at", "actor", "type", "refs"):
            if key not in event:
                errors.append(f"event missing {key} at {path}:{line_number}")


def validate_root(root: Path, work_item: str | None = None) -> list[str]:
    """Return validation errors; an empty list means the workflow is valid."""
    errors: list[str] = []
    if not root.is_dir():
        return [f"missing workflow directory: {root}"]

    for relative_path in REQUIRED_ROOT_FILES:
        _readable(root / relative_path, errors)

    work_items_root = root / "work-items"
    if not work_items_root.is_dir():
        errors.append(f"missing directory: {work_items_root}")
        return errors

    candidates = []
    for year_dir in sorted(work_items_root.iterdir()):
        if not year_dir.is_dir():
            continue
        for item_dir in sorted(year_dir.iterdir()):
            if item_dir.is_dir() and (item_dir.name.startswith("REQ-") or item_dir.name.startswith("BUG-")):
                candidates.append(item_dir)

    if work_item:
        candidates = [item for item in candidates if item.name == work_item]
        if not candidates:
            errors.append(f"work item not found: {work_item}")
            return errors

    for item_dir in candidates:
        if not WORK_ITEM_ID.fullmatch(item_dir.name):
            errors.append(f"invalid work item ID: {item_dir.name}")
        for relative_path in REQUIRED_WORK_ITEM_FILES:
            _readable(item_dir / relative_path, errors)
        _validate_events(item_dir / "execution/events.ndjson", errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate .ai-workflow structure and event logs")
    parser.add_argument("--root", type=Path, default=Path(".ai-workflow"))
    parser.add_argument("--work-item", help="validate one exact REQ-* or BUG-* directory")
    args = parser.parse_args(argv)
    errors = validate_root(args.root, args.work_item)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"valid workflow: {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
