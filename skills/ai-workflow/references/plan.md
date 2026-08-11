# Plan Mode

Planning turns a requirement into an approved execution contract. It may write
workflow state but must not modify product code.

## Start

1. Read applicable repository rules and the supplied PRD.
2. Select `light`, `standard`, or `strict` using the router criteria.
3. Resolve the supplied item. If none exists, run `workflow.py init` with the
   real date, title, track, current base commit, and an ASCII slug when needed.
4. Inspect only relevant entry points, boundaries, interfaces, data,
   configuration, tests, and delivery rules. Cite evidence behind conclusions.
5. Search history only when the title, aliases, or user context suggest a
   related item.

After `init`, use its JSON output as the ID; initialization is deterministic.
Existing items require validation before revision work.

## Clarification

Ask only questions that can change scope, behavior, architecture, data or
security, compatibility, acceptance, rollout, or verification. Group blockers
where possible. Make conservative non-blocking assumptions visible at approval.

## Import the plan

Create three temporary files outside `.ai-workflow`:

- input text describing the requirement and assumptions;
- plan text covering goal, non-goals, current/proposed behavior, risks,
  rollback, and verification;
- a JSON or YAML list of dependency-ordered tasks matching [schemas.md](schemas.md).

Every task stays within one focused slice and traces requirements to acceptance,
scope, validation, evidence, rollback, and done condition. Import the files:

```text
python3 scripts/workflow.py set-plan --root <repo>/.ai-workflow --work-item ID --input-file <input> --plan-file <plan> --tasks-file <tasks> --idempotency-key <key>
```

Remove the temporary files after successful import. Do not hand-edit stored
state.

## Approval gate

Run `workflow.py plan-ready`, then `workflow.py validate`. Confirm no blocker
remains and every requirement maps to a task and real validation. Ready state is:

```yaml
phase: plan
state: waiting_input
next_action: approve_plan
```

Present the ID, track, impact, task count, assumptions, risks, and approval
command. Run `workflow.py approve-plan` only after explicit user approval.
