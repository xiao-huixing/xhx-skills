#!/usr/bin/env python3
"""兼容入口：校验 .ai-workflow 目录。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from workflow_validation import validate_root


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
