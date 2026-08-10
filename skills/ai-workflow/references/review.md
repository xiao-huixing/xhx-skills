# Review Mode

Review is read-only by default and produces evidence, not an automatic merge.

## Review sequence

1. Rebuild context from the manifest, current revision, plan, tasks, state,
   handoff, code diff, and recorded evidence.
2. Confirm the plan and acceptance criteria are the intended revision.
3. Check each requirement and acceptance criterion against implementation and a
   real validation result.
4. Inspect unplanned files, compatibility, edge cases, error paths, concurrency,
   performance, data migrations, security, observability, and rollback.
5. Run focused tests and project-required checks when authorized and available.
6. Verify links across `REQ → TASK → TEST → commit/PR → deployment`.
7. Write findings with severity, evidence, affected requirement/file, blocking
   status, and a concrete remediation task when needed.

## Result

Write `review.md` and update `manifest.yaml`:

- `passed`: no accepted actionable findings and required evidence is complete;
- `passed_with_risks`: the user explicitly accepts listed non-blocking risks;
- `needs_changes`: create remediation tasks and return to `execute`;
- `blocked`: missing environment, authority, evidence, or product decision.

Do not treat formatting or an agent's self-report as proof of correctness. Do
not fix findings in the review pass unless the user explicitly requests
`review --fix`; any fix must be executed and reviewed again.

## Release readiness

Review may produce a release checklist and ask whether to create a PR, merge, or
deploy. A successful review does not imply production deployment. Record the
actual commit, CI run, environment, deployment, observation, and rollback
reference before setting `delivery: verified`.
