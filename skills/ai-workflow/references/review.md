# Review Mode

Review is read-only by default. It produces evidence, not fixes, merge, or
deployment.

## Review

1. Validate the work item, then load the manifest, current plan, tasks, diff,
   and recorded evidence. Load detailed history only for a disputed link.
2. Trace each requirement and acceptance criterion to implementation and a
   real validation result.
3. Always inspect scope drift, compatibility, edge cases, error paths, and
   rollback. For `standard`, also inspect integration and observability. For
   `strict`, additionally inspect security, concurrency, migrations, privacy,
   performance limits, release gates, and recovery proof.
4. Run focused checks when authorized and available.
5. Write `review.md` with severity, evidence, affected requirement/file,
   blocking status, and a concrete remediation task where needed.

Do not treat formatting, generated summaries, or an agent self-report as proof.
Do not fix findings during review unless the user explicitly requests a return
to execute; every fix must be reviewed again.

## Result

Record exactly one result through `workflow.py review`:

- `passed`: required evidence is complete and no actionable finding remains.
- `passed_with_risks`: the user explicitly accepts named non-blocking risks.
- `needs_changes`: pending remediation tasks exist; return to execute.
- `blocked`: an environment, authority, evidence, or product decision is
  missing.

A passing review does not imply release. Record the actual commit, CI run,
environment, deployment, observation, and rollback reference before claiming
delivery verification.
