---
name: ai-workflow
description: >-
  Execute a project-aware, file-backed AI development workflow from PRD to
  implementation and review. Use whenever the user asks to analyze an existing
  project before development, turn a PRD into an actionable plan, execute a
  development plan, review an implementation, resume interrupted work, revise
  an existing requirement, inspect progress, or run the complete plan-execute-
  review flow. Supports plan, execute, review, all, status, resume, revise, and
  history modes without requiring the user to manage workflow files.
user-invocable: true
---

# AI Workflow

This Skill exposes three development modes and a few read-only helpers:

```text
ai-workflow plan <PRD or requirement>
ai-workflow execute <REQ-ID>
ai-workflow review <REQ-ID>
ai-workflow all <PRD or requirement>
ai-workflow status [REQ-ID]
ai-workflow resume <REQ-ID>
ai-workflow revise <REQ-ID> <new requirement>
ai-workflow history <keyword>
```

Natural-language requests map to the same modes. Do not make the user learn the
file layout or manually create IDs.

## Routing

1. Resolve an explicit mode from the command or user intent.
2. If the intent is ambiguous, ask one short choice: plan, execute, review, or
   all. Do not begin implementation while the mode is unclear.
3. Read [storage-protocol.md](references/storage-protocol.md) before creating or
   updating `.ai-workflow/`.
4. Read only the mode reference that applies:
   - `plan`: [plan.md](references/plan.md)
   - `execute` or `resume`: [execute.md](references/execute.md)
   - `review`: [review.md](references/review.md)
   - `all`: read them in that order and pause at every human gate.

## Shared startup protocol

Before any mode:

1. Locate the repository root and read applicable `AGENTS.md`, `CLAUDE.md`,
   `README`, build/test instructions, and security rules.
2. If `.ai-workflow/` does not exist, initialize it from the storage reference
   and the bundled templates. Record that initialization in the response.
3. Read `project/overview.md`, `project/modules.yaml`, `capabilities/index.yaml`,
   `indexes/active.yaml`, and the target work item's current `context.md` when
   they exist. Do not load the entire history directory.
4. Resolve IDs by exact ID, title, or alias. If more than one active item
   matches, list candidates and ask the user to choose; never guess.
5. Treat summaries as derived views. Use `manifest.yaml`, `tasks.yaml`,
   `execution/state.yaml`, and the latest valid event as the structured facts.
6. Keep facts, inferences, assumptions, and unknowns separate. Record an
   assumption before relying on it.

## Mode contracts

### `plan`

Read `references/plan.md`. Analyze the supplied PRD against the current code,
architecture, interfaces, data, tests, configuration, and deployment. Ask only
questions that can change scope, behavior, architecture, acceptance, safety, or
verification; group 3-7 blocking questions per round. Record answers and
assumptions in the work item. Do not modify product code.

Stop at `waiting_plan_approval` after producing a complete plan. A plan is ready
only when every requirement maps to acceptance criteria, tasks, validation, and
rollback information.

### `execute`

Read `references/execute.md`. Require an approved plan or an explicitly
validated imported plan. Execute all pending tasks by dependency order unless
the user provides `--task`, `--from`, or `--until`. Update task state and append
an event before and after each task. Preserve failed work for diagnosis and
write a handoff for the next session.

Do not silently change the plan. A material requirement change creates a new
revision and pauses execution. Do not merge, deploy, close external issues, or
change production state unless the user explicitly authorizes that action and
the repository gates allow it.

### `review`

Read `references/review.md`. Review the plan, current revision, code diff,
tests, evidence, and external links as one traceability chain. Review is
read-only by default. Findings become remediation tasks; apply fixes only when
the user explicitly asks, then return to `execute` and review again.

### `all`

Run `plan`, wait for plan approval, run `execute`, then run `review`. If review
creates remediation tasks, return to `execute` and repeat review. After a clean
review, ask whether to create a PR, merge, or deploy; these are explicit
side-effect gates, not automatic consequences of a passing review.

## Helpers

- `status` reads structured state and prints phase, delivery state, completed
  tasks, blocked tasks, progress, and next action. It should not call an LLM.
- `resume` validates the current Git head, worktree, PR/CI links, and latest
  event, then continues from the last successful task. If facts drift, mark the
  work item blocked and return to `plan`.
- `revise` creates a new revision under the existing REQ and compares the new
  input with the current plan and capability baseline.
- `history` searches `indexes/catalog.jsonl` first, then loads matching
  `summary.md` files and only the details needed to answer the question.

## Completion response

Always report the work-item ID, mode, current phase, progress, files changed,
tests or review evidence, blockers, and the exact next command. Never claim
deployment or production verification when only local code was changed.
