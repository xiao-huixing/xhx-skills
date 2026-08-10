# First-Version Schemas

The first version uses human-readable YAML for machine facts and JSON Lines for
append-only events. Keep field names stable; add fields rather than changing
the meaning of existing ones.

## Manifest

```yaml
id: REQ-20260807-001-example
kind: requirement
title: Example requirement
phase: plan
state: waiting_plan_approval
delivery: not_started
current_revision: R001
base_commit: null
capabilities: []
modules: []
parent: null
supersedes: []
gates:
  plan_approved: false
  review_approved: false
  release_approved: false
next_action: answer questions
updated_at: 2026-08-07T00:00:00+08:00
```

## Task

```yaml
- id: TASK-001
  revision: R001
  title: Implement the first behavior
  status: pending
  depends_on: []
  requirements: [REQ-EXAMPLE-001]
  acceptance: [AC-001]
  scope: [src/example]
  validation:
    - npm test -- example
  evidence: []
  last_event: null
```

## Event

```json
{"id":"EVT-001","at":"2026-08-07T00:00:00+08:00","actor":"ai-workflow","type":"task.started","task":"TASK-001","git":null,"refs":[]}
```

Required event fields are `id`, `at`, `actor`, `type`, and `refs`. Include
`task`, `git`, `result`, or `error_class` when relevant. Never put secrets or
complete command output in an event.
