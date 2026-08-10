---
name: bug-fix
description: >-
  Run an evidence-driven, stack-agnostic bug triage and repair workflow. Use
  whenever a user reports, investigates, reproduces, fixes, verifies, or
  regresses a software defect. The skill records evidence and progress in the
  project's .ai-workflow directory and distinguishes defects from requirement
  changes.
user-invocable: true
---

# Bug Fix

This is the single generic bug workflow. It uses the same file-backed history
as `ai-workflow`, but creates a `BUG-*` work item and applies bug-specific
evidence gates.

```text
bug-fix <issue, description, link, or BUG-ID>
bug-fix status <BUG-ID>
bug-fix resume <BUG-ID>
```

Read [bug-protocol.md](references/bug-protocol.md) before creating or updating
an item. Read the project workflow instructions and the relevant
`ai-workflow` storage protocol first when `.ai-workflow/` already exists.

## Non-negotiable gates

1. Read all available issue information: original description, attachments,
   related items, change history, and later comments.
2. Establish the environment and a reproducible baseline before claiming a
   root cause. A first failed reproduction is not closure; re-check the
   problem definition, conditions, and verification path.
3. Separate facts, observations, hypotheses, and assumptions. Record evidence
   with timestamps and commands or links.
4. Fix the smallest root-cause boundary. If the behavior is actually a new or
   changed product requirement, create or link a `REQ-*` revision and stop the
   bug path without forcing a code patch.
5. Verify the fix with the narrowest automated test, relevant regression tests,
   and an end-to-end check when the defect crosses a user-visible boundary.

## Safety

The default is read-only triage plus local changes requested by the user. Do
not alter external issue state, merge, deploy, or change production data unless
the user explicitly authorizes that side effect. Do not expose secrets in
evidence or logs.

## Completion response

Report the `BUG-*` ID, current state, reproduction result, root cause, files
changed, tests and evidence, unresolved risks, and the next command. A bug is
not closed when it was merely not reproduced or when a test was skipped.
