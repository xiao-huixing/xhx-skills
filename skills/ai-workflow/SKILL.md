---
name: ai-workflow
description: >-
  Run a durable project-backed plan-execute-review workflow only when the user
  explicitly names ai-workflow, supplies a PRD and asks for a tracked delivery
  lifecycle, references an existing REQ/BUG work item, or asks to resume,
  revise, audit, or inspect recorded workflow state. Do not use for ad-hoc code
  edits, simple same-session fixes, ordinary code review, one-off planning,
  unrelated status questions, or defect diagnosis already handled by a
  dedicated bug-fix workflow.
---

# AI Workflow

Use `scripts/workflow.py` as the only writer of workflow state. Run it from this
Skill directory with `python3`; pass the target repository's `.ai-workflow`
path through `--root`.

## Admission gate

Durable tracking is opt-in. Initialize storage only when the user explicitly
selects `ai-workflow` or asks for tracked PRD delivery, or when continuing an
existing REQ/BUG item. If a request is a clear, local, reversible change that
can be completed and verified in the current session, exit this Skill and
handle it normally. Do not initialize `.ai-workflow` merely because an edit has
multiple steps or needs tests.

The `light` track is the smallest tracked workflow after admission; it is not a
reason to record ordinary quick fixes.

## Route first

Resolve one mode: `plan`, `execute`, `review`, `all`, `status`, `resume`,
`revise`, or `history`. Ask one short question only when the mode or a
materially different risk choice is genuinely ambiguous.

Fast paths do not initialize storage or scan the repository:

- `status`: run `workflow.py status --root <repo>/.ai-workflow [--work-item ID]`.
- `history`: run `workflow.py history --root <repo>/.ai-workflow <query>`.

For other modes, read [storage-protocol.md](references/storage-protocol.md),
then only the applicable reference:

- `plan` or `revise`: [plan.md](references/plan.md)
- `execute` or `resume`: [execute.md](references/execute.md)
- `review`: [review.md](references/review.md)
- `all`: read each reference immediately before that phase and stop at every
  human gate.

## Work depth

Choose the smallest sufficient track and store it in `work-item.yaml`:

- `light`: local, reversible, low-risk work; targeted discovery and tests.
- `standard`: multi-file or externally visible behavior; normal traceability,
  integration checks, and rollback.
- `strict`: security, auth, money, destructive migration, production control,
  or regulated data; explicit threat/risk review and stronger evidence.

Read repository rules plus only the modules, tests, and workflow slices needed
for the current phase and task.

## State rules

- Each requirement has exactly two persistent files: `work-item.yaml` is the
  current snapshot and `events.jsonl` is its ordered audit log.
- Never edit those files by hand. Use `set-plan`, `plan-ready`, `approve-plan`,
  `task`, and `review`; mutating commands validate under the writer lock.
- The planning gate uses `phase: plan`, `state: waiting_input`, and
  `next_action: approve_plan`. Only explicit user approval permits
  `workflow.py approve-plan`.
- Passing a task requires a redacted evidence reference. External issues,
  commits, pushes, PRs, merges, deploys, service restarts, and production
  changes require their own authorization.

## Mode outcomes

- `plan`: create a temporary input, plan, and task list; import them with
  `set-plan`; mark ready; never modify product code; stop for approval.
- `execute`: require an approved plan, work one eligible task at a time, run its
  declared validation, and record evidence through the CLI.
- `resume`: resolve and validate stored state plus Git facts, then continue the
  recorded next task; do not reconstruct state from chat.
- `review`: default to read-only; trace requirements to diff and evidence;
  import findings and any remediation tasks with `review`, then record one result.
- `all`: plan, approval, execute, review; remediation returns to execute.

## Response

Report the work-item ID, mode, track, phase/state, progress, changed files,
evidence, blockers, and exact next command. Never claim a merge, deployment, or
production verification without direct evidence.
