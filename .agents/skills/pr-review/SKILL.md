---
name: pr-review
description: Review an existing GitHub Pull Request as an exact merge candidate and prepare evidence-based inline review comments for GitHub. Use only when a developer asks to review a GitHub PR before merge, inspect its PR description and checks, or publish a pending PR review; do not use for general code review, commit review, branch review, or working-tree review.
---

# GitHub Pull Request Review

Act as an independent, read-only reviewer of one GitHub Pull Request. The
Pull Request and its current head commit are the unit of review. Do not turn
this into a general branch, commit, or working-tree review.

## Review contract

1. Identify the repository, PR number, base SHA, head SHA, merge base, title,
   description, draft state, linked work item, changed files, CI/check status,
   existing review comments, and current checkout state.
2. Stop if the PR cannot be resolved, the head changed during inspection, the
   required brief or acceptance evidence is missing, or local changes would be
   mixed into the PR snapshot. State the missing evidence precisely.
3. Read repository instructions, the complete PR diff, relevant surrounding
   code, tests, migrations, configuration, and the PR's stated intent.
4. Check correctness, security and privacy, data integrity, concurrency,
   compatibility, error handling, test adequacy, scope, operational impact,
   migrations, rollback, and CI evidence. Do not invent requirements or block
   on personal style.
5. Report only actionable, evidence-backed findings. Prefer a few high-value
   findings over speculative noise.

Use the existing CoDev severity scale:

- **P0:** immediate security, data-loss, or production-critical defect.
- **P1:** incorrect behavior or likely serious regression; blocks merge.
- **P2:** material test, edge-case, compatibility, or maintainability issue;
  normally fix before merge.
- **P3:** optional improvement; never present it as a merge blocker.

Each finding must include a stable `finding_id`, severity, confidence, exact
file, changed-line location when possible, observed evidence, impact, and a
testable correction. Missing tests are findings only when the changed behavior
has meaningful regression risk and the available evidence does not cover it.

## GitHub comment locations

For an inline finding, record:

- repository-relative `path`;
- `line` and `side` (`RIGHT` for additions/current context, `LEFT` for
  deletions/old context);
- optional `start_line` and `start_side` for a contiguous multi-line comment;
- the exact `head_sha` reviewed.

Only anchor comments to lines present in the PR diff. Use a file-level or
summary comment for issues that cannot be anchored to a changed line. Never
guess an anchor. Revalidate every anchor against the current PR head immediately
before publishing.

## Required artifacts

Produce both:

1. A concise Markdown report with PR identity, snapshot, verdict, findings,
   residual risks, validation evidence, and publication state.
2. A JSON review payload containing `head_sha`, `summary`, and `comments`. Each
   comment contains `finding_id`, `body`, `path`, and either a valid inline
   location or `subject_type: "file"`.

Make `summary` a brief index of the findings, not a duplicate of the inline
comment prose. GitHub displays the submitted review body separately from its
inline comments. For example, use `One inline P2 finding:
PR2-BRADFORD-FLAT-RESPONSE.` as the summary, and keep the evidence, impact,
and correction in that finding's inline body.

## Publication workflow

Use `scripts/publish_review.py` to fetch PR context, validate the payload, and
create a GitHub review. It is dry-run by default. Authentication uses the
authenticated `gh` CLI automatically when no `GITHUB_TOKEN` or `GH_TOKEN` is
present; use `--auth gh` or `--auth token` to select a backend explicitly. Run
it with `--publish` only after the developer explicitly authorizes posting.
Never submit `APPROVE` on behalf of a human.

For a new review that the developer has authorized to be visible immediately,
create and submit it in one operation:

```text
python .agents/skills/pr-review/scripts/publish_review.py \
  --repo OWNER/REPO --pr 123 --review .codev/pr-review/123/review.json \
  --auth gh --publish --submit comment
```

Use `--submit request-changes` only when the developer has explicitly
authorized that formal review event. Without `--submit`, `--publish` creates a
pending review. A pending review is a draft lifecycle state, not a second
standalone PR comment; GitHub can show both the original “started a review”
timeline event and the later submitted review.

The current publisher creates reviews; it does not submit an existing pending
review by ID. Therefore, never retry a pending-review submission by rerunning
`--review ... --publish --submit ...`: that is a new create operation and can
produce a second review. Submit the original pending review through GitHub's
review UI, or first extend the publisher with an explicit, validated
submit-existing-review operation. Before any retry, fetch `reviews` and
`comments` and confirm the current head SHA, review state, review ID, and
finding markers. Treat an existing matching review as a successful no-op,
rather than posting another payload.

The publisher must use authenticated `gh api` or `GITHUB_TOKEN`/`GH_TOKEN`, must
verify the current head SHA, must reject stale or invalid anchors, and must
avoid duplicate comments using the stable finding IDs. Review payloads should
also use a stable, review-level identity when the publisher supports it, so a
complete retry can detect an already-created review before creating another.
Do not print or extract the `gh` credential. If the agent does not inherit the
Windows machine PATH, use the standard install location or set `CODEV_GH_PATH`.
Do not hardcode a provider, model, token, or endpoint outside GitHub.

## Fetch PR context

Before analysis, fetch the authoritative GitHub context when it is not already
available:

```text
python .agents/skills/pr-review/scripts/publish_review.py \
  --repo OWNER/REPO --pr 123 --fetch \
  --output-dir .codev/pr-review/123
```

The fetch mode can collect `metadata`, `diff`, `files`, `commits`, `reviews`,
`comments`, and `checks`; it collects all parts by default. Use repeated
`--include` options to limit the request. Read `metadata.json`, `diff.patch`,
and the relevant JSON files before producing findings. The output is evidence
for the review and does not modify source files.

For a terminal or CLI agent that cannot access the user's GitHub keyring, dot-
source `scripts/set-github-token.ps1` in the same PowerShell process before
launching the agent. It sets `GH_TOKEN` only for that process and its children.

When the CoDev Junie adapter is installed, the same workflow is available as
the project slash command `/pr-review repo=OWNER/REPO pr=123`. It fetches the
context through `gh api` and then applies this skill inside Junie CLI.

End the report with exactly one recommendation:

- `READY FOR HUMAN APPROVAL`
- `CHANGES REQUIRED`
- `BLOCKED BY MISSING EVIDENCE`

Reviewer readiness never authorizes merge, publication, or release.
