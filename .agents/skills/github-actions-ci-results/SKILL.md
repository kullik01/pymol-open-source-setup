---
name: github-actions-ci-results
description: Read, inspect, and summarize GitHub Actions workflow runs, including run status, jobs, steps, annotations, and relevant logs. Use when a user asks what happened in a GitHub Actions CI run, why CI failed, which job or step failed, whether a run is still in progress, or for a concise CI result suitable for a pull request or incident update.
---

# GitHub Actions CI Results

Read GitHub Actions results without changing repository or workflow state. Identify the exact workflow run, summarize its outcome, drill into failed jobs and steps, and quote only the smallest useful log excerpts needed to explain the result.

## Operating rules

- Treat this as a read-only investigation. Do not rerun, cancel, approve, dispatch, or alter a workflow unless the user separately requests that action.
- Prefer an available authenticated GitHub connector. Otherwise use the authenticated `gh` CLI; use `gh auth status` to check readiness without exposing tokens.
- Use the repository supplied by the user, the current repository, or the repository encoded in a run URL. If none is available, ask for the repository rather than guessing.
- Never print access tokens, secret values, environment dumps, or unredacted log sections that may contain credentials.
- Preserve the run attempt. A rerun can have the same run ID but a different attempt, so report the attempt when it is available.
- Distinguish `status` from `conclusion`: an in-progress run has a status such as `queued` or `in_progress` and may have no conclusion; a completed run has a conclusion such as `success`, `failure`, `cancelled`, or `skipped`.

## Workflow

### 1. Resolve the run

Accept any of these inputs:

- A workflow run URL or numeric run ID.
- A pull request number or URL.
- A branch, commit SHA, workflow name, or a time hint such as “latest CI”.
- No identifier, in which case inspect recent runs and select the most recent relevant CI run.

For an ambiguous request, list recent candidate runs and state which one you selected, including workflow name, run number, branch, commit, event, creation time, and URL. Do not silently choose between multiple runs for the same commit.

### 2. Read the run summary first

Collect the run-level fields before reading logs:

- workflow name and display title
- run ID/number and attempt
- status and conclusion
- event, branch, commit SHA
- created, started, and updated/completed times
- run URL
- jobs, including each job’s name, status, conclusion, URL/ID, and step results when available

If the run is queued or in progress, report that clearly and avoid labeling it passed or failed. If it is completed, identify the first useful failure boundary: failed job, failed step, or workflow-level error.

### 3. Inspect failures selectively

For a failed or cancelled run:

1. Find jobs whose conclusion is not `success` or that contain a failed, cancelled, timed-out, or skipped step.
2. Inspect the failed job’s failed-step log first (`--log-failed` when using `gh`).
3. If the failure is unclear, fetch the full log for that job, then inspect adjacent setup, dependency, test, build, and teardown steps.
4. Check annotations or check-run details when available; use them to locate file paths, line numbers, and error categories.
5. Separate the observed error from an inferred root cause. Label hypotheses as hypotheses and name the evidence that supports them.

For a successful run, do not dump logs. Report the successful conclusion and any noteworthy warnings or skipped jobs only when they materially affect confidence in the result.

### 4. Produce the result

Use this compact structure:

```text
Result: PASS | FAIL | IN PROGRESS | CANCELLED | UNKNOWN
Workflow: <name> · Run: <number> · Attempt: <attempt>
Commit: <sha> · Ref: <branch/tag> · Event: <event>
URL: <run URL>

Failed jobs/steps:
- <job> → <step>: <one-line error or outcome>

Evidence:
- <short, redacted log excerpt or annotation>

Assessment: <observed cause, or a clearly labeled hypothesis>
Next action: <specific diagnostic or code/config action, if requested or useful>
```

For a user who asks only to “read out the results,” omit speculative remediation and keep the report to the result, failed jobs/steps, and decisive evidence. Include timestamps in UTC when timing matters.

## Tool selection and fallback

Use this order:

1. GitHub connector/API already available in the environment.
2. `gh run list` to discover runs and `gh run view` for a selected run.
3. `gh api` or the GitHub REST API for details unavailable through the first two options.
4. The GitHub web UI only for human-readable confirmation or when command/API access is unavailable.

Read [references/gh-command-cookbook.md](references/gh-command-cookbook.md) when using the CLI or REST fallback. Adapt field names to the tool actually available; do not claim that a field was checked if the tool did not return it.

## Failure handling

- If authentication fails, say that repository read access is unavailable and provide the exact non-secret prerequisite (`gh auth login`, connector sign-in, or repository permission) without asking the user to paste a token.
- If the run ID is invalid or not found, verify the repository and attempt number before trying other runs.
- If logs are expired, unavailable, or incomplete, report that limitation and use job metadata, annotations, check runs, and the run URL as evidence.
- If a job is missing from the run summary, note that GitHub may not have associated its log and inspect the job endpoint or per-job log fallback if available.
- If the command exits non-zero because the run failed, treat that as run status—not as a tool malfunction—and continue extracting the output.
