# Tracked Bug Protocol

Read this protocol only after the tracked-lane gate passes. Simple fixes use the
fast lane and create no workflow storage.

## Storage

Every tracked defect uses the same two-file contract as `ai-workflow`:

```text
.ai-workflow/
└── work-items/YYYY/BUG-YYYYMMDD-NNN-slug/
    ├── work-item.yaml
    └── events.jsonl
```

`work-item.yaml` contains current identity, lifecycle, revision input and plan,
tasks, decisions, review, summary, and evidence references. `events.jsonl`
contains the ordered audit log. Do not add persisted intake, baseline, context,
root-cause, handoff, verification, index, or evidence directories.

Create and mutate the item only through the `ai-workflow` CLI. From its Skill
directory:

```text
python3 scripts/workflow.py init --root <repo>/.ai-workflow --title <title> --date YYYYMMDD --track light|standard|strict --kind bugfix [--slug ascii-slug] [--base-commit SHA]
```

Prepare intake, plan, task lists, and review findings as temporary files outside
`.ai-workflow`; import them with `set-plan` or `review`, then remove them.

## Investigation gate

Capture only evidence needed to recover or audit the defect:

- original report, later comments, affected version/environment, and impact;
- expected and actual behavior, exact reproduction steps, and frequency;
- redacted logs, screenshots, requests, traces, or external links;
- observations, hypotheses tested, root cause, affected boundary, and rollback;
- targeted, regression, and boundary-check commands with results.

A first failed reproduction is not closure. Re-check conditions and record the
next experiment. If blocked by authority, environment, data, or a product
decision, use a blocked task transition with a stable error class.

## Lifecycle

Use the shared `plan -> execute -> review -> done` lifecycle instead of a second
bug-only state machine:

- `plan`: reproduce or bound the failure, identify the root cause, and import a
  minimal fix plan plus validation tasks;
- `execute`: record task begin/pass/fail/block transitions and redacted evidence;
- `review`: compare baseline, fix, regression evidence, remaining risk, and
  rollback; import remediation tasks for `needs_changes`;
- `done`: means review passed, not that deployment or production observation
  occurred.

If evidence shows expected behavior changed, stop the defect path and create or
link a tracked requirement only when the user wants durable requirement work.

## Resume and delivery boundary

Resume from `work-item.yaml`, the latest event, Git facts, and external issue
facts; never reconstruct durable state from chat. Commits, pushes, PRs, merges,
deployments, production observation, and closing external issues require their
own authorization and evidence.
