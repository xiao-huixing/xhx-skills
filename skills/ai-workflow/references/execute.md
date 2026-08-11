# Execute Mode

## Preconditions

Resolve the target and run `workflow.py validate` once. Require plan approval,
understood Git drift, a preservation strategy for user changes, an eligible
task, passed dependencies, and authority for planned side effects. If a
condition fails, record a blocker through the CLI and stop.

## One-task loop

1. Load the selected task and current revision from `work-item.yaml`, then read
   only its requirement, acceptance, and code slice.
2. Run `workflow.py task begin ... --idempotency-key <stable-key>`.
3. Implement the smallest planned change without unrelated refactoring.
4. Run the task's declared checks and project-required gates.
5. On success, run `workflow.py task pass ... --evidence <redacted-reference>
   --idempotency-key <stable-key>`.
6. On failure or an external dependency, run `task fail` or `task block` with a
   stable error class. Preserve the worktree and report recovery action.

A material requirement change returns to plan as a new revision. Code without
a passing acceptance check is not a passed task. Limit retries and classify
build, test, lint, network, authentication, merge, environment, and unclear
requirement failures.

Each transition atomically updates `work-item.yaml` and `events.jsonl` and
validates under the writer lock. Run one final validate at the phase boundary or
when diagnosing drift; do not add redundant checks around every transition.

## Scope and completion

Execute eligible tasks by dependency order unless the user limits scope.
`resume` uses the snapshot and latest event, then rechecks Git and external
facts; it never relies on chat memory.

Do not create external issues or PRs, push, merge, deploy, restart services,
change production data, or close work items without explicit authorization.
After the last task passes, the CLI sets `delivery: implemented` and moves to
`phase: review`. Report changed files, checks, remaining work, blockers, and the
exact review command.
