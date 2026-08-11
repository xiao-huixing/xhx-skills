# Storage Protocol

`.ai-workflow/` is project-local, Git-versioned workflow storage. Never write
secrets, credentials, personal data, raw production logs, or full command
output to it.

## Two-file contract

Every requirement owns one directory and exactly two persistent files:

```text
.ai-workflow/
└── work-items/YYYY/REQ-YYYYMMDD-NNN-slug/
    ├── work-item.yaml
    └── events.jsonl
```

`work-item.yaml` is the complete current snapshot: identity, lifecycle, gates,
revisions, plans, tasks, decisions, review, summary, and evidence references.
`events.jsonl` is the ordered audit log. The CLI assigns each event a monotonic
sequence and links the snapshot through `last_event`.

Do not persist indexes, context summaries, state mirrors, handoffs, empty
placeholders, or SQLite databases. `status`, `resolve`, `history`, and
`refresh-index` derive views by scanning the snapshots. The root may briefly
contain `.writer.lock` and `.transactions/` while a writer is active.

Use `scripts/workflow.py` for initialization and every mutation. It serializes
writers, validates the candidate snapshot and event log, and commits both files
through a recoverable transaction. Never hand-edit either file.

## Command contract

From the Skill directory:

```text
python3 scripts/workflow.py init --root <repo>/.ai-workflow --title <title> --date YYYYMMDD --track light|standard|strict [--slug ascii-slug] [--base-commit SHA]
python3 scripts/workflow.py resolve --root <repo>/.ai-workflow <ID|title|alias>
python3 scripts/workflow.py validate --root <repo>/.ai-workflow [--work-item ID]
python3 scripts/workflow.py set-plan --root <repo>/.ai-workflow --work-item ID --plan-file <path> --tasks-file <path> [--input-file <path>] [--idempotency-key KEY]
python3 scripts/workflow.py plan-ready --root <repo>/.ai-workflow --work-item ID [--idempotency-key KEY]
python3 scripts/workflow.py approve-plan --root <repo>/.ai-workflow --work-item ID [--idempotency-key KEY]
python3 scripts/workflow.py task begin|pass|fail|block --root <repo>/.ai-workflow --work-item ID --task TASK-NNN [--evidence REF] [--error-class CLASS] [--idempotency-key KEY]
python3 scripts/workflow.py review --root <repo>/.ai-workflow --work-item ID --result passed|passed_with_risks|needs_changes|blocked [--findings-file <path>] [--remediation-tasks-file <path>] [--idempotency-key KEY]
```

Create planning and review inputs outside `.ai-workflow`, import them with the
CLI, then remove the temporary files. Use stable idempotency keys for retries.
Exit code `0` means success, `1` invalid workflow/state, and `2` invalid usage.

## Lifecycle

Valid phases are `plan`, `execute`, `review`, and `done`. Valid states are
`active`, `waiting_input`, `blocked`, `paused`, `completed`, and `cancelled`.
Planning ready for approval is:

```yaml
phase: plan
state: waiting_input
next_action: approve_plan
```

Approval moves to execute; the final passed task moves to review; a passed
review moves to done/completed. `needs_changes` requires a pending remediation
task and returns to execute. Release authorization remains independent.

## Identity and revisions

`REQ-*` identifies requirements and `BUG-*` defects. `R001`, `R002`, and later
revisions live inside the snapshot. A material change after approval creates a
new revision with delta and impact analysis; do not rewrite approved history.
Resolve ambiguous titles or aliases by presenting candidates, never guessing.

The validator rejects earlier layouts with an explicit compatibility error.
Do not delete or rewrite existing workflow data automatically; migration needs
a separately authorized, backed-up conversion.
