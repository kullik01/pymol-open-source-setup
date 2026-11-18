---
name: plan-delivery
description: Turn an accepted product or feature brief and any required design into a lightweight, team-profile-aware multi-developer delivery plan. Use when a team needs outcome-based milestones, unassigned capability lanes or ready work items, owners, independent reviewers, simple dependencies, integration checkpoints, WIP limits, risks, or rolling-wave planning. Do not create a separate architecture or capacity bureaucracy.
---

# Plan Delivery

Create a plan that helps a team choose the next useful work, not a prediction of
every future edit. A completed delivery plan is a durable, reviewable project
artifact, not a chat-only response.

## 0. Persist the plan

First inspect the repository for an existing delivery-plan location and for a
linked project tracker. The repository plan is the durable coordination
baseline, even when an external tracker holds routine, high-churn status.

For an explicit request to create or update a delivery plan, create or update
the plan in the repository. Default to
`docs/delivery/<milestone-slug>.md`; use an established equivalent location
when the project already has one. Start from
`assets/delivery-plan.template.md` when creating a new plan.

An initial request to *show* or frame a milestone without creating a plan may
remain an unassigned, chat-only planning brief. Make that limitation explicit
and do not describe it as a completed delivery plan.

Before writing, verify that every referenced brief and design is a durable
repository artifact or stable tracker record. Never use a conversation as an
authority link. If accepted product or architectural decisions exist only in
conversation, return to `define-product` or `design-solution` to persist the
appropriate authority before making work items ready.

Before updating an existing plan, inspect its current content and the Git
working tree. Do not silently overwrite a locally changed plan; surface the
conflict and ask for direction. Preserve the plan's document state using only
`Draft`, `Accepted`, `Active`, or `Superseded`; Git history is its revision
record.

## 1. Verify planning inputs

Read the accepted brief and applicable design. Confirm the next outcome, fixed
contracts, important risks, current commitments, and required reviewers. Return
unresolved product questions to `define-product` and architectural questions to
`design-solution`.

Classify uncertain facts before planning:

- **fixed:** accepted product or architectural decisions;
- **hard blocker:** a missing decision or contract that prevents a specific item
  from starting safely;
- **risk track:** evidence that can be retired independently without blocking
  unrelated work;
- **staffing input:** capability, capacity, ownership, or reviewer information;
  and
- **deferred:** a decision that is not needed for the current milestone.

Do not call a risk track, staffing input, or deferred decision a blocker unless
it actually prevents the named work from starting.

### Team-profile gate

Headcount is not a delivery profile. Do not infer a developer's skills,
availability, component ownership, review authority, or security/domain
qualification from a team size, title, or anonymous label.

Before assigning ready work, establish the smallest useful profile for each
developer: stable name or label, relevant strengths, current capacity or WIP,
component/API ownership, and independent-review restrictions. Inspect existing
ownership and tracker facts first; ask only for missing information.

If profiles are incomplete:

1. recommend the next milestone and show **unassigned capability lanes**, not
   `Developer 1`, `Developer 2`, or similar placeholders;
2. show only candidate concurrency, conditional on named contracts or fixtures;
3. do not claim that work items are ready or assign reviewers; and
4. ask exactly one recommendation-led question for the missing team profile.

When the human explicitly asks for an initial milestone framing first, provide
that framing as an unassigned planning brief, then make the team profile the
single remaining input before producing assignments.

## 2. Define outcome milestones

Each milestone must demonstrate observable value or retire a named risk, such as
"internal user completes the primary workflow." Avoid component-completion
milestones such as "backend done."

For a requested first **useful product** milestone, name the target user, the
observable action, and the durable result. A foundation-only milestone is valid
when it retires a named risk, but label it as an enabling or risk-retirement
milestone rather than presenting it as user value. Include the smallest
in-scope product object when that is necessary to make the demonstration useful.

Plan the current milestone in detail. Keep later milestones coarse and revise
them using evidence from working software.

## 3. Create reviewable work items

Before team profiles are available, create only capability lanes. For every lane
that could proceed concurrently, name the accepted API, schema, decision, or
contract fixture that makes it safe. If no such authority exists, state
**Blocked by** the missing contract; do not imply parallelism from technical
layer names alone.

Each current work item must include:

- outcome and acceptance criteria;
- relevant design/API links;
- owner and independent reviewer;
- dependencies and integration checkpoint;
- risk level: low, normal, high, or critical;
- expected validation; and
- status: discovery, ready, in progress, review, blocked, or done.

A work item should normally produce one small pull request or a short stack of
independently valid pull requests. Split by behavior, not by technical layer.
Use a bounded discovery item when a needed contract cannot be resolved from
accepted authority. Never turn an unresolved decision into an implementation
assignment.

Use only ordinary dependency language:

- **Blocked by:** work cannot begin safely.
- **Integrates with:** work can proceed against an agreed contract or fixture;
  integration happens later.
- **Lands after:** source-control or migration order matters.

## 4. Coordinate the team

Default maximum work in progress to one implementation item per developer.
Assign only after the team-profile gate passes. Map by relevant capability,
capacity, ownership, and support needs, not title or headcount. Ensure owners do
not approve their own changes. Name an integration owner only for milestones
that cross ownership boundaries.

Treat review capacity as real work. Confirm reviewer availability before an item
becomes ready and define a small review queue limit (default two active reviews
per reviewer unless the team chooses otherwise). For high- or critical-risk
work, separately name any policy-authorized security, privacy, compliance, or
operations approver; never assume an ordinary code reviewer has that authority.

Track changing assignments, availability, and status in the delivery plan or a
linked project tracker. Do not version them as architecture. When a tracker is
used, retain the milestone outcome, work-item definitions, ownership/reviewer
commitments, dependencies, checkpoints, risks, and tracker link in the
repository plan.

## 5. Check readiness

An item is ready only when its outcome, acceptance, required design decisions,
dependencies, owner, reviewer, and test environment are known. Use a bounded
discovery item when evidence is missing. Never disguise uncertainty as an
implementation task.

Do not assign an item merely because there are idle developers. Keep it
unassigned or blocked until its contract, owner, and independent reviewer are
known. If the plan is still awaiting team profiles, report it as an unassigned
planning brief rather than a ready delivery plan.

Review the plan with the team in one pass: current milestone, ready work,
parallel work, blockers, integration points, and risks. Update routine status
without formal approval; seek human decisions only for scope, priority, risk,
ownership conflicts, or commitments.

## 6. Complete the artifact handoff

After creating or updating the plan, report its exact repository path, document
state, and the Git change summary. Link to the saved artifact rather than
leaving the complete plan only in chat. Summarize the decision and next action;
do not duplicate the full document unless the user asks.

## Handoff

Give each developer only their work item, relevant brief/design/API links,
integration constraints, and acceptance criteria. Start `build-change` for the
next ready item.
