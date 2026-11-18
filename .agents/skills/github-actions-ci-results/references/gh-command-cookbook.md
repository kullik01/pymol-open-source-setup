# GitHub Actions read-only command cookbook

Use the narrowest command that answers the question. Replace `OWNER/REPO` and identifiers with values resolved from the user’s request. Keep command output local to the task and redact secrets before quoting it.

## Check access and discover runs

```bash
gh auth status
gh run list --repo OWNER/REPO --limit 10
gh run list --repo OWNER/REPO --branch BRANCH --limit 10
gh run list --repo OWNER/REPO --workflow WORKFLOW.yml --commit SHA --limit 10
```

Use the run list to resolve ambiguity. Prefer a completed run for a completed commit, and report the selected run’s URL.

## Inspect a selected run

```bash
gh run view RUN_ID --repo OWNER/REPO --json name,displayTitle,number,attempt,status,conclusion,event,headBranch,headSha,createdAt,startedAt,updatedAt,url,jobs
```

To show job and step details compactly:

```bash
gh run view RUN_ID --repo OWNER/REPO --verbose
```

To inspect a specific job or failed steps:

```bash
gh run view RUN_ID --repo OWNER/REPO --log-failed
gh run view --job JOB_ID --repo OWNER/REPO --log-failed
gh run view --job JOB_ID --repo OWNER/REPO --log
```

Use `--attempt ATTEMPT` when the run has multiple attempts. `--exit-status` is useful as a signal, but do not mistake a non-zero exit for inability to retrieve the run.

## REST fallback

When `gh run view` does not expose enough detail, use read-only endpoints such as:

```bash
gh api repos/OWNER/REPO/actions/runs/RUN_ID
gh api repos/OWNER/REPO/actions/runs/RUN_ID/jobs?per_page=100
gh api repos/OWNER/REPO/check-runs/CHECK_RUN_ID/annotations
gh api repos/OWNER/REPO/actions/jobs/JOB_ID/logs
```

The logs endpoint may return a redirect or an archive depending on the endpoint and client. Do not assume logs exist indefinitely; report expiration or access errors plainly.

## Interpretation notes

- Run `status` describes lifecycle state; `conclusion` describes the terminal result.
- A workflow can have successful jobs and still fail overall because another job failed, a required check failed, or a workflow-level error occurred.
- A skipped step is not automatically a failure. Explain whether it was expected from conditions or prevented a dependent job from running.
- Prefer the failing command and its immediate error over long setup or dependency logs.
- Redact values after common secret markers such as `token`, `password`, `secret`, `authorization`, and masked GitHub values before presenting excerpts.

Official references:

- [gh run view manual](https://cli.github.com/manual/gh_run_view)
- [Viewing workflow run history](https://docs.github.com/en/actions/monitoring-and-troubleshooting-workflows/monitoring-workflows/viewing-workflow-run-history)
- [REST API: workflow runs](https://docs.github.com/en/rest/actions/workflow-runs)
- [REST API: workflow jobs](https://docs.github.com/en/rest/actions/workflow-jobs)
- [REST API: check-run annotations](https://docs.github.com/en/rest/checks/runs)
