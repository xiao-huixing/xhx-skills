# AI Workflow Evaluations

`evals.json` contains three fixture-backed cases for the status fast path,
planning quality, and deterministic execution. Paths are relative to the Skill
directory. Never run a mutating case against the source fixture; copy the whole
fixture, including hidden files, to an isolated workspace first.

## Deterministic preflight

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s skills/ai-workflow/tests -v
python3 skills/ai-workflow/scripts/workflow.py validate \
  --root skills/ai-workflow/evals/fixtures/execute-approved/.ai-workflow \
  --work-item REQ-20260810-001-enable-beta
```

## Agent comparison

For each case:

1. Copy its fixture into two isolated workspaces.
2. Run the prompt once with the current Skill and once with a frozen baseline.
3. Save the final response, execution transcript, filesystem output, and timing.
4. Grade every expectation against both the transcript and real files.
5. Blind the two output directories as A/B before comparing quality.

The optimization workspace at the repository root demonstrates the expected
layout: `ai-workflow-workspace/iteration-*/eval-*`. A single trial detects large
regressions but is not a stable latency benchmark; use at least three trials per
configuration before treating timing variance as a performance result.
