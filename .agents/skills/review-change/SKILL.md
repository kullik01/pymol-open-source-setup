---
name: review-change
description: Independently review a pull request, commit, patch, or working-tree diff for correctness, regressions, security, test quality, maintainability, scope, and conformance to an accepted brief or design. Use when a developer requests code review, a second AI pass, pre-merge assurance, or an evidence-based quality gate. Review only the exact supplied snapshot and do not modify code unless explicitly asked afterward.
---

# Review Change

Act as an independent reviewer, not a second implementer. Review the exact
base-to-head snapshot and state the snapshot when possible.

## Preconditions

Read the issue or work item, acceptance criteria, relevant brief/design/API,
repository instructions, complete diff, and validation evidence. Inspect enough
surrounding code to understand behavior. If the target or evidence is ambiguous,
identify the limitation instead of guessing.

## Review order

Prioritize:

1. incorrect or missing required behavior;
2. security, privacy, permission, data-loss, concurrency, and compatibility risk;
3. error handling and material edge cases;
4. test quality, missing tests, and weakened or misleading tests;
5. architecture/API conformance and unnecessary scope;
6. maintainability, clarity, documentation, and repository conventions; and
7. rollout, monitoring, migration, and rollback concerns.

Passing checks are evidence, not proof. Rerun proportionate checks when useful
and authorized. Prefer a few representative integration tests at important
boundaries over exhaustive unit-test enumeration. Coverage percentages are
diagnostic only, never a required quality gate. Do not block on theoretical,
rare, low-impact edge cases unless they create a credible correctness, safety,
data-integrity, compatibility, or regression risk. Do not invent requirements
or block on personal style.

## Findings

Lead with actionable findings, ordered by severity:

- **P0:** immediate security, data-loss, or production-critical defect.
- **P1:** incorrect behavior or likely serious regression; blocks merge.
- **P2:** material maintainability, test, or edge-case problem; normally fix.
- **P3:** optional improvement; never disguise it as a blocker.

For each finding give the location, observed evidence, impact, and a precise
testable correction. Keep line ranges tight. If no actionable finding exists,
say so and list residual risks or validation gaps.

End with one recommendation: `READY FOR HUMAN APPROVAL`, `CHANGES REQUIRED`, or
`BLOCKED BY MISSING EVIDENCE`. Reviewer readiness never authorizes merge or
release.
