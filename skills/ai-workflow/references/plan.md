# Plan Mode

## Goal

Turn a PRD or requirement into a plan another agent can execute without
repeating the discovery conversation. Planning is analysis and artifact writing;
it does not modify product code.

## Discovery order

1. Read repository instructions, project overview, build/test commands, and
   current workflow state.
2. Inspect entry points, module boundaries, relevant interfaces, data models,
   configuration, external services, tests, CI, and deployment notes.
3. Read the supplied PRD and normalize requirements to stable `REQ-*` and
   acceptance criteria to `AC-*` IDs.
4. Compare desired behavior with current behavior. Cite file paths, symbols,
   commands, or existing tests for important conclusions.
5. Inspect related active and completed work items by capability, module, API,
   and path. Load details only when relevant.

## Questions

Ask only questions whose answers can change scope, behavior, architecture,
data/security, compatibility, validation, or rollout. Group 3-7 blocking
questions per round and explain why each is needed. For non-blocking unknowns,
choose a conservative assumption, label it `[Assumption]`, and include it in the
approval summary. Never hide an assumption as a confirmed requirement.

If the user says to proceed without answering, preserve the assumptions and ask
for confirmation at plan approval.

## Plan output

Write the current revision's files:

- `input.md`: source PRD, scope, source links, and normalized requirements.
- `questions.md`: questions, answers, assumptions, and unresolved blockers.
- `plan.md`: goal, non-goals, current behavior, design, risks, rollback, and
  verification strategy.
- `delta.md`: changes from the previous revision, if this is a revision.
- `tasks.yaml`: dependency-ordered tasks with exact scope and validation.
- `decisions.md`: durable decisions and rejected alternatives.
- `context.md`: a short recovery summary.

Each task must be small enough for one focused execution session and contain:

```text
TASK ID, requirements, acceptance criteria, dependencies, scope,
expected behavior, validation commands, evidence, rollback, and done condition
```

Group tasks by dependency and mark safe parallel work only when file scope does
not overlap. Include integration, migration, security, UI, and documentation
work when the requirement needs them.

## Plan gate

Before setting `state: waiting_plan_approval`, verify:

- goals, non-goals, affected capabilities, and acceptance criteria are explicit;
- every requirement maps to at least one task and validation;
- dependencies, file scope, commands, rollback, and risk are present;
- the base Git commit and relevant existing behavior are recorded;
- no blocking questions remain;
- assumptions and decisions are visible to the user.

Return a concise approval summary with the work-item ID, impact, task count,
blocking/assumed items, risks, and the next command. Do not start execution
until the plan is approved.
