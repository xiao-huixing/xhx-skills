# Schema Version 1

The CLI writes JSON-compatible YAML so it works without a YAML dependency. It
can also read conventional YAML when PyYAML is installed. Keep field names and
enum meanings stable.

## Manifest

```yaml
{
  "schema_version": 1,
  "id": "REQ-20260810-001-example",
  "kind": "requirement",
  "title": "Example requirement",
  "aliases": [],
  "track": "standard",
  "phase": "plan",
  "state": "waiting_input",
  "delivery": "not_started",
  "current_revision": "R001",
  "base_commit": null,
  "capabilities": [],
  "modules": [],
  "parent": null,
  "supersedes": [],
  "gates": {
    "plan_approved": false,
    "review_approved": false,
    "release_approved": false
  },
  "active_task": null,
  "next_action": "approve_plan",
  "last_event": "EVT-000001",
  "updated_at": "2026-08-10T00:00:00+00:00"
}
```

## Task

```yaml
[
  {
    "id": "TASK-001",
    "revision": "R001",
    "title": "Implement the first behavior",
    "status": "pending",
    "depends_on": [],
    "requirements": ["REQ-EXAMPLE-001"],
    "acceptance": ["AC-001"],
    "scope": ["src/example.py"],
    "expected_behavior": "The documented behavior is observable",
    "validation": ["python3 -m unittest"],
    "evidence": [],
    "rollback": "Revert the scoped change",
    "done_condition": "The acceptance check passes",
    "attempt": 0,
    "failure": null,
    "last_event": null
  }
]
```

Statuses are `pending`, `in_progress`, `passed`, `failed`, `blocked`, and
`skipped`. Every dependency must exist and the graph must be acyclic. A passed
task must contain evidence.

## Event and derived state

```json
{"id":"EVT-000001","at":"2026-08-10T00:00:00+00:00","actor":"ai-workflow","type":"work_item.created","refs":[]}
```

Every event requires `id`, `at`, `actor`, `type`, and list-valued `refs`.
Transition events may add `task`, `result`, `error_class`, or
`idempotency_key`. The CLI derives state with `schema_version`, `phase`,
`state`, `active_task`, `last_success`, `blocked_by`, `next_action`, and
`updated_at`; its matching manifest fields must never drift.
