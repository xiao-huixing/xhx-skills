# Execute Mode

## Preconditions

Read the target work item and verify:

- the current revision has an approved plan;
- the current Git head matches the recorded base or drift is understood;
- there are no unrelated user changes that would be overwritten;
- the selected task is pending and its dependencies passed;
- a single-writer lease can be obtained for the work item.

If any precondition is false, set `state: blocked` or `waiting_input`, record the
reason, and stop. Do not guess a plan from a title or partial notes.

## Task loop

For each selected task:

1. Read its requirements, acceptance criteria, scope, prior evidence, and
   relevant `context.md`.
2. Append `task.started` and set `status: in_progress`.
3. Inspect existing code and follow project conventions. Preserve unrelated user
   changes and avoid opportunistic refactors.
4. Implement the smallest change that satisfies the task, including tests and
   documentation required by the plan.
5. Run the task's validation commands. Add redacted evidence references.
6. On success, set `status: passed`, update traceability, append `task.passed`,
   and regenerate `context.md` and `handoff.md`.
7. On failure, set `failed` or `blocked`, append the error class and evidence,
   preserve the worktree, and state the next action.

Never mark a task passed because code was written. The acceptance condition and
its validation must pass. Do not run unlimited retries; classify build, test,
lint, network, authentication, merge, and unclear-requirement failures.

## Scope and side effects

- Default execution may edit code on a feature branch or isolated worktree and
  run local tests.
- Creating or updating external Issues/PRs, pushing, merging, deploying,
  restarting services, changing production data, and closing work items require
  explicit authorization and repository gates.
- A discovered requirement change pauses execution and creates a new revision.
  Do not rewrite approved plan sections to make the current implementation fit.
- Do not bypass dependencies, protected branches, security checks, or rollback
  gates because a task is urgent.

## Completion

After all eligible tasks pass, run the planned integration/build/security checks,
write verification evidence, set `delivery: implemented`, and stop at
`phase: review`. Report completed/remaining/blocked tasks, tests, changed files,
and the exact review command.

`--task` executes only the named task. `--until` stops after the named task.
`--resume` continues from the last successful event after rechecking Git and
external facts. Safe parallel execution is opt-in and requires disjoint scope.
