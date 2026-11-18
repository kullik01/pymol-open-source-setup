# Suggested Edit

**Status:** Suggested only — not applied.
**Snapshot:** `<base or working-tree snapshot>`
**Source finding:** `<review, presubmit, lint, or developer comment>`
**Severity:** `<P0/P1/P2/P3 or tool severity>`
**Location:** `<path:line or symbol>`

## Observed impact

<What the current code does and why it matters.>

## Proposed diff

```diff
<minimal unified diff; do not claim it was applied>
```

## Rationale

<Why this patch addresses the finding.>

## Non-goals

<Behavior and files intentionally left unchanged.>

## Validation after acceptance

```text
<focused commands and expected evidence>
```

## Explicit handoff

**Suggested only — not applied.** A developer must accept, reject, or revise
this diff. To apply it, explicitly hand it to `build-change` for interactive
implementation or ask the developer to apply it. After application, run the
requested validation and a fresh independent `review-change` pass.
