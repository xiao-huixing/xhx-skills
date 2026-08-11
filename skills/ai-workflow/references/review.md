# Review Mode

Review is read-only by default. It produces evidence, not fixes, merge, or
deployment.

## Review

1. Validate the item, then load its snapshot, current revision, tasks, diff,
   and recorded evidence. Load detailed history only for a disputed link.
2. Trace each requirement and acceptance criterion to implementation and a
   real validation result.
3. Inspect scope drift, compatibility, edge cases, error paths, and rollback.
   For `standard`, also inspect integration and observability. For `strict`,
   inspect security, concurrency, migrations, privacy, performance limits,
   release gates, and recovery proof.
4. Run focused checks when authorized and available.
5. Write findings to a temporary file outside `.ai-workflow`. Include severity,
   evidence, affected requirement or file, and blocking status. For
   `needs_changes`, also write a non-empty task list matching [schemas.md](schemas.md).

Do not treat formatting, generated summaries, or an agent self-report as proof.
Do not fix findings during review unless the user explicitly returns to execute;
every fix must be reviewed again.

## Result

Import findings and record exactly one result:

```text
python3 scripts/workflow.py review --root <repo>/.ai-workflow --work-item ID --result <result> --findings-file <path> [--remediation-tasks-file <path>] --idempotency-key <key>
```

- `passed`: required evidence is complete and no actionable finding remains.
- `passed_with_risks`: the user explicitly accepts named non-blocking risks.
- `needs_changes`: import pending remediation tasks and return to execute.
- `blocked`: environment, authority, evidence, or product decision is missing.

Remove all temporary import files after success. A passing review
does not imply release. Record the actual commit, CI run, environment,
deployment, observation, and rollback reference before claiming delivery
verification.
