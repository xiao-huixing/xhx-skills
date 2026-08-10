# Execute Mode

## Preconditions

Resolve the target and run `workflow.py validate` once. Require plan approval,
understood Git drift, a clean preservation strategy for user changes, an
eligible task, passed dependencies, and authority for planned side effects.
If any condition fails, record a blocker through the CLI and stop.

## One-task loop

1. Load the selected task, current context, its requirement/acceptance slice,
   and relevant code only.
2. Run `workflow.py task begin ... --idempotency-key <stable-key>`.
3. Implement the smallest planned change. Do not opportunistically refactor or
   rewrite the approved plan.
4. Run the task's declared checks and project-required gates.
5. On success, save a concise redacted evidence reference and run
   `workflow.py task pass ... --evidence <reference> --idempotency-key <key>`.
6. On failure or dependency outside current authority, run `task fail` or
   `task block` with a stable error class. Preserve the worktree and report the
   recovery action.

A material requirement change returns to plan as a new revision. Code written
without a passing acceptance check is not a passed task. Limit retries and
classify build, test, lint, network, authentication, merge, environment, and
unclear-requirement failures.

`task begin/pass/fail/block` validates under its lock and regenerates derived
views. Do not add validation calls around each transition or evidence-file
write. Run one final validate at the phase boundary or when diagnosing drift.

## Scope and completion

Execute all eligible tasks by dependency order unless the user limits the
scope. `resume` uses structured state and the latest event, then rechecks Git
and external facts; it never relies on chat memory.

Do not create external issues/PRs, push, merge, deploy, restart services, change
production data, or close work items without explicit authorization. After the
last task passes, the CLI sets `delivery: implemented`, moves to `phase: review`,
and regenerates state/context/indexes. Report changed files, checks, remaining
work, blockers, and the exact review command.
