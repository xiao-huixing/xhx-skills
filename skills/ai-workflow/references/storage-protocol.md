# Storage Protocol

`.ai-workflow/` is the project-local, Git-versioned source for requirements,
decisions, progress, verification, and release references. Do not put secrets,
raw credentials, full production logs, or personal data in it.

## Directory

```text
.ai-workflow/
├── README.md
├── project/
│   ├── overview.md
│   └── modules.yaml
├── capabilities/
│   └── index.yaml
├── indexes/
│   ├── active.yaml
│   └── catalog.jsonl
└── work-items/
    └── YYYY/REQ-YYYYMMDD-NNN-slug/
        ├── manifest.yaml
        ├── context.md
        ├── summary.md
        ├── revisions/R001/
        │   ├── input.md
        │   ├── questions.md
        │   ├── plan.md
        │   └── delta.md
        ├── tasks.yaml
        ├── decisions.md
        ├── execution/
        │   ├── state.yaml
        │   ├── events.ndjson
        │   └── handoff.md
        ├── review.md
        ├── releases/
        └── evidence/
```

`BUG-YYYYMMDD-NNN-slug` uses the same layout. It is created by the separate
`bug-fix` Skill and has bug-specific intake and baseline files when needed.

## Identity and revisions

- `REQ-*` identifies a product requirement; `BUG-*` identifies a defect.
- `R001`, `R002`, ... identify revisions within one work item.
- The work-item directory never moves. `indexes/active.yaml` changes when an
  item is completed, cancelled, or superseded.
- Before plan approval, edits may remain in the current revision and Git records
  the diff. After approval or implementation, a material change creates a new
  revision with a `delta.md` and an impact analysis.
- A new post-release product initiative creates a new REQ linked by `extends` or
  `supersedes`; do not reopen the old item as if it were current behavior.

## Manifest state

Keep these fields separate:

```yaml
id: REQ-20260807-001-example
kind: requirement
title: Example requirement
phase: plan                 # plan | execute | review | done
state: waiting_plan_approval # active | waiting_input | blocked | paused | completed | cancelled
delivery: not_started        # not_started | implemented | merged | deployed | verified
current_revision: R001
base_commit: <git-sha>
parent: null
supersedes: []
next_action: TASK-001
```

`manifest.yaml` is machine state. It must not be inferred from a prose summary.
Plan approval, review approval, release approval, and external side effects are
separate gates.

## Task and event facts

`tasks.yaml` is the only task-progress source:

```yaml
- id: TASK-001
  revision: R001
  title: Implement the validation rule
  status: pending       # pending | in_progress | passed | failed | blocked | skipped
  depends_on: []
  requirements: [REQ-EXAMPLE-001]
  acceptance: [AC-001]
  scope: [src/validation]
  validation: ["npm test -- validation"]
  evidence: []
  last_event: null
```

`execution/events.ndjson` is append-only. Each event records one fact and keeps
large output in an external evidence file:

```json
{"id":"EVT-001","at":"2026-08-07T12:00:00+08:00","actor":"codex","type":"task.started","task":"TASK-001","git":"abc123","refs":[]}
```

Use event types such as `question.answered`, `plan.approved`, `task.started`,
`task.passed`, `task.failed`, `task.blocked`, `review.completed`, and
`release.deployed`. Never record passwords, tokens, cookies, JWTs, or complete
command output in an event.

## Derived views and retrieval

`context.md`, `summary.md`, `progress.md`, `indexes/active.yaml`, and
`indexes/catalog.jsonl` are derived views. Regenerate them after meaningful
state changes; if they conflict with manifest/tasks/events, the structured facts
win.

Default session loading is intentionally small: project overview, module index,
active index, target manifest, context, tasks, state, and handoff. Query detailed
decisions, old revisions, reviews, releases, and evidence only by requirement
ID, capability, path, release, date, or keyword.

## Initialization

When `.ai-workflow/` is missing, create the minimal project files and one work
item only when the user has supplied a requirement. Do not populate empty
history directories or invent project facts. Mark unknown project facts as
unknown and let `plan` collect them.
