---
name: define-product
description: Turn a software idea, product proposal, or feature request into a clear product or feature brief and select the lightest safe workflow. Use when a developer needs help clarifying users, outcomes, scope, success measures, constraints, assumptions, or whether work is a quick change, feature, or product. Do not design the technical solution or create implementation tasks.
---

# Define Product

Guide the developer from an idea to an accepted brief. Explain the purpose of
each step in plain language and keep the conversation focused on product intent.

Use `assets/brief.template.md` when a durable brief is useful.

## 1. Choose the workflow size

Recommend one path and explain why:

- **Quick change:** local, reversible, low-risk work with obvious acceptance.
  Hand off directly to `build-change`; an issue is enough.
- **Feature:** a user-visible or cross-file outcome with limited architectural
  impact. Create a feature brief, then use `design-solution` only if needed.
- **Product:** a new product, major capability, cross-team effort, migration, or
  high-risk change. Create a product brief and continue through all lifecycle
  skills.

Risk overrides size. Security, privacy, permissions, public APIs, persistent
data, billing, compliance, and destructive operations require at least the
feature path and an explicit design review.

## 2. Discover intent

Read supplied material completely. Inspect existing product documentation when
available. Establish:

- target users and their problem;
- desired outcome and measurable evidence of success;
- essential scenarios and failure expectations;
- first-release scope and explicit non-goals;
- fixed business, legal, safety, accessibility, platform, cost, and timing
  constraints; and
- assumptions that need evidence before committing to the full solution.

Never fabricate a numerical target. When no baseline or accountable target
exists, name the measure, define how to establish its baseline, and leave target
selection as an explicit product decision before accepting the brief.

Ask at most four related questions at once. Recommend an answer when evidence
supports one. Do not ask for repository facts that can be inspected later.

## 3. Shape the smallest useful release

Prefer one end-to-end outcome over a catalogue of components. Separate:

- **Now:** required to demonstrate value;
- **Next:** plausible follow-up, not committed;
- **Not planned:** deliberately excluded.

If the central user or outcome is still unknown, propose a bounded discovery
experiment rather than pretending the product is ready for engineering.

## 4. Save and accept the brief

For a feature, write `docs/features/<slug>/brief.md`. For a product, write
`docs/product/<slug>/brief.md`. Adapt to an existing repository convention
instead of creating a parallel structure.

Set `Status: Draft` until the human confirms the outcome, scope, non-goals, and
success measures. Then set `Status: Accepted`. Git history is the revision
record; do not invent a second revision scheme.

## Handoff

Recommend the next action:

- Quick change -> `build-change`
- Feature with no material design choice -> `plan-delivery` or `build-change`
- Feature with architectural/risk decisions -> `design-solution`
- Product -> `design-solution`

Never convert the brief into architecture, staffing, or code-level tasks.
