---
name: bug-fix
description: >-
  Diagnose and repair non-trivial software defects with evidence-driven gates.
  Use for intermittent or unreproduced failures, production-impacting bugs,
  cross-component defects, existing BUG IDs or external issue histories, and
  requests for formal triage, tracking, or verification. If explicitly invoked
  for a clear low-risk same-session fix, use the non-persistent fast lane.
  Do not use automatically for obvious typos, small local behavior fixes with
  a clear expected result, routine dependency bumps, or product requirement changes.
---

# Bug Fix

Route before reading references or creating files. The purpose of durable
tracking is recovery and auditability; it should not make a quick fix slower
than the fix itself.

## Fast lane

Use this default when the expected behavior is clear, the change is local and
reversible, targeted verification fits in the current session, and there is no
production, security, auth, money, destructive-data, or cross-team risk.

1. Read the relevant code, report, and test only.
2. Confirm the cause at the smallest useful boundary.
3. Apply the requested fix and run the narrowest meaningful check.
4. Report cause, changed files, and validation.

Do not create `.ai-workflow`, a BUG ID, planning artifacts, or event records.
Do not read [bug-protocol.md](references/bug-protocol.md) in this lane.

## Tracked lane

Use durable tracking when any condition applies:

- the user asks to record, track, resume, audit, or create a BUG item;
- an existing BUG ID, external issue, attachments, comments, or history matters;
- the failure is intermittent, unreproduced, recurring, production-impacting,
  cross-component, or likely to span sessions or owners;
- security, privacy, auth, money, migration, destructive data, release, or
  rollback evidence is required.

Read [bug-protocol.md](references/bug-protocol.md) only for this lane. Use the
`ai-workflow` CLI as the sole writer and create a `BUG-*` item with
`--kind bugfix`.

## Evidence gates

For both lanes, read all issue material that is actually in scope. Establish a
reproducible baseline before claiming a root cause; a first failed reproduction
is not closure. Separate observations from hypotheses, fix the smallest root
cause, and run targeted plus relevant regression checks.

If behavior is a new product requirement, stop expanding the patch and route it
to requirement planning. Do not alter external issue state, commit, push, merge,
deploy, restart services, or change production data without authorization.

## Response

For the fast lane, report cause, files, checks, and remaining risk without a
workflow ID. For the tracked lane, also report the BUG ID, phase/state, evidence,
blockers, and exact next CLI command. Never claim release or production
verification without direct evidence.
