# Storage Protocol

`.ai-workflow/` is project-local, Git-versioned workflow storage. Never write
secrets, credentials, personal data, raw production logs, or full command output
to it.

## Ownership

Use `scripts/workflow.py` for initialization and every state transition. The CLI
serializes writers with `.writer.lock`, recovers staged `.transactions`, writes
multi-file state through a recoverable transaction, appends idempotent events,
and refreshes derived views.

Canonical facts:

- `work-items/<year>/<ID>/manifest.yaml`
- `work-items/<year>/<ID>/tasks.yaml`
- `work-items/<year>/<ID>/execution/events.ndjson`

Derived views, safe to regenerate:

- `execution/state.yaml`, `context.md`
- `indexes/active.yaml`, `indexes/catalog.jsonl`

Semantic documents such as revision input, plan, decisions, review, handoff,
and evidence references remain agent-authored and do not need standalone
validation. When manually changing task definitions or semantic manifest
links, follow the mode's validation budget. Never hand-edit structured progress
to force a transition.

## Layout by track

Every track creates the root indexes, project overview, canonical files, state,
context, and current revision input. Add documents only when needed:

```text
.ai-workflow/
├── project/{overview.md,modules.yaml}
├── capabilities/index.yaml
├── indexes/{active.yaml,catalog.jsonl}
└── work-items/YYYY/REQ-YYYYMMDD-NNN-slug/
    ├── manifest.yaml
    ├── tasks.yaml
    ├── context.md
    ├── revisions/R001/{input.md,plan.md}
    ├── execution/{state.yaml,events.ndjson,handoff.md}
    ├── decisions.md
    ├── review.md
    └── evidence/
```

`light` normally needs input, plan, tasks, context, and targeted evidence.
`standard` adds decisions, handoff, integration evidence, and rollback detail.
`strict` also records threat/risk analysis, migration/rollback proof, and
release evidence. Do not create empty directories or boilerplate files.

## Command contract

From the Skill directory:

```text
python3 scripts/workflow.py init --root <repo>/.ai-workflow --title <title> --date YYYYMMDD --track light|standard|strict [--slug ascii-slug] [--base-commit SHA]
python3 scripts/workflow.py resolve --root <repo>/.ai-workflow <ID|title|alias>
python3 scripts/workflow.py validate --root <repo>/.ai-workflow [--work-item ID]
python3 scripts/workflow.py plan-ready --root <repo>/.ai-workflow --work-item ID [--idempotency-key KEY]
python3 scripts/workflow.py approve-plan --root <repo>/.ai-workflow --work-item ID [--idempotency-key KEY]
python3 scripts/workflow.py task begin|pass|fail|block --root <repo>/.ai-workflow --work-item ID --task TASK-NNN [--evidence REF] [--error-class CLASS] [--idempotency-key KEY]
python3 scripts/workflow.py review --root <repo>/.ai-workflow --work-item ID --result passed|passed_with_risks|needs_changes|blocked [--idempotency-key KEY]
```

Use a stable idempotency key for retried approval/task commands. Exit code `0`
means success, `1` means invalid workflow/state, and `2` means invalid usage.

## Lifecycle

Valid phases are `plan`, `execute`, `review`, and `done`. Valid states are
`active`, `waiting_input`, `blocked`, `paused`, `completed`, and `cancelled`.
Planning ready for approval is represented as:

```yaml
phase: plan
state: waiting_input
next_action: approve_plan
```

Approval moves to execute; the final passed task moves to review; a passed
review moves to done/completed. `needs_changes` requires a pending remediation
task and returns to execute. Delivery state is independent of review and release
authorization.

## Identity and revisions

`REQ-*` identifies requirements and `BUG-*` identifies defects. `R001`, `R002`,
and later revisions remain under the stable work-item directory. A material
change after approval creates a new revision with delta and impact analysis;
do not rewrite approved history. Resolve ambiguous titles/aliases by presenting
candidates, never guessing.
