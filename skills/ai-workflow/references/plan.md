# Plan Mode

Planning turns a requirement into an approved execution contract. It may write
workflow artifacts but must not modify product code.

## Start

1. Read applicable repository rules and the supplied PRD.
2. Select `light`, `standard`, or `strict` using the router criteria.
3. If no work item exists, run `workflow.py init` with the real date, title,
   track, and current base commit. When the title is not Latin text, also pass a
   concise lowercase ASCII `--slug`. For a revision, resolve and validate the
   existing item; do not create a duplicate.
4. Inspect only relevant entry points, module boundaries, interfaces, data,
   configuration, tests, and delivery rules. Cite paths, symbols, or commands
   behind important conclusions.
5. Search workflow history only when the existing active/catalog index contains
   a plausible related item; a newly initialized empty catalog needs no search.

Batch related discovery and file reads. After successful `init`, use its JSON
output as the ID and do not reread generated placeholders or run a pre-edit
validation; initialization is already deterministic. Existing items still
require validation before edits.

## Clarification

Ask only questions that can change scope, behavior, architecture, data/security,
compatibility, acceptance, rollout, or verification. Group blockers into one
concise round where possible. Record conservative non-blocking assumptions and
make them visible at approval; never present assumptions as facts.

## Artifacts

Write the current revision's `input.md` and `plan.md`; add questions, delta, or
decisions only when they carry information. The plan covers goal, non-goals,
current behavior, proposed behavior, risks, rollback, and verification.

Write dependency-ordered `tasks.yaml`. Every task must include all fields in
[schemas.md](schemas.md), stay within one focused execution slice, and trace
requirements to acceptance criteria, exact scope, validation, evidence,
rollback, and done condition. Mark parallel work only when scope is disjoint.

## Approval gate

Run `workflow.py validate`. Before approval, verify that no blocker remains and
every requirement maps to a task and real validation. Planning-ready state is:

```yaml
phase: plan
state: waiting_input
next_action: approve_plan
```

The CLI does not infer semantic readiness. Once the artifacts validate, run
`workflow.py plan-ready` to update canonical state and derived views atomically,
then validate again. Present the work-item ID, track, impact, task count,
assumptions, risks, and approval command. Run `workflow.py approve-plan` only
after explicit user approval.
