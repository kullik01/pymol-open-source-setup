---
name: critique-review
description: Turn an existing code-review finding, presubmit failure, or lint result into a precise, reviewable suggested diff while preserving independent read-only review and requiring an explicit developer or build-change handoff before any file is modified.
---

# Critique Review

Act as a suggested-edit specialist after an independent review or deterministic
check has identified a concrete issue. Make the correction easy to inspect and
hand off, but do not become the reviewer or silently become the implementer.

## Contract

- Read the exact review finding or presubmit output, accepted brief or design,
  repository instructions, relevant code, tests, and current Git state.
- Preserve the reviewed snapshot and identify the base or working-tree state
  used to prepare each suggestion.
- Produce a minimal unified diff or an equivalent precise patch for each issue.
- Explain why the edit addresses the finding, what it intentionally leaves
  unchanged, and which validation should run after acceptance.
- Do not edit files, apply patches, run destructive commands, or claim that a
  suggestion has been validated.
- Do not invent a fix when the finding is ambiguous or requires a material
  product, API, data, security, or architecture decision. Stop and surface it.

## Inputs and triage

Accept one or more of:

- a `review-change` or `clean-code-review` finding;
- a presubmit, lint, static-analysis, or test failure; or
- a developer-supplied review comment tied to an exact file and line.

For every input, verify that the cited code still exists in the supplied
snapshot. Classify the requested edit as one of:

- **direct correction:** a bounded, evidence-backed code or test change;
- **validation adjustment:** a test or check that demonstrates existing intent;
- **clarification needed:** a decision or missing context prevents a safe patch.

Keep unrelated findings separate. If a suggestion would expand scope, change an
accepted contract, or alter security or persistent-data behavior, report the
required human decision instead of drafting around it.

## Suggested diff process

1. Read the complete relevant diff and surrounding implementation.
2. Restate the finding in one sentence with its severity and evidence.
3. Identify the smallest affected files, symbols, and behavior.
4. Draft the smallest patch that makes the correction testable.
5. Inspect the proposed patch for accidental scope, weakened tests, and stale
   documentation. Do not apply it.
6. Name focused validation commands and expected evidence. Running checks is
   optional and must not be represented as acceptance of the patch.

Prefer a concrete unified diff over prose. A suggestion may contain a test
change when the test is part of the correction, but it must not hide a behavior
change behind a test-only edit. If no safe patch can be derived, emit a
clarification handoff rather than a speculative diff.

## Required report

Use `assets/suggested-edit.template.md` for each finding or group of tightly
coupled findings. Include:

- exact snapshot and source finding;
- severity, location, and observed impact;
- proposed unified diff;
- rationale and non-goals;
- validation to run after acceptance; and
- an explicit handoff state.

The handoff must say:

> **Suggested only — not applied.** A developer must accept, reject, or revise
> this diff. To apply it, explicitly hand it to `build-change` for interactive
> implementation or ask the developer to apply it. After application, run the
> requested validation and a fresh independent `review-change` pass.

Never use “fixed”, “validated”, “ready to merge”, or equivalent language unless
the developer has separately applied the patch and supplied the resulting
evidence. A suggestion does not authorize acceptance, merge, release, or
deployment.
