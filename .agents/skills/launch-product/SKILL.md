---
name: launch-product
description: Prepare and guide a safe release of a completed feature or product through readiness review, migration, feature flags, internal testing, staged rollout, observability, rollback, and post-launch learning. Use when code is approaching deployment, a team needs a launch checklist or rollout plan, or production evidence must determine expansion. Do not deploy, publish, or enable users without explicit human authorization.
---

# Launch Product

Treat launch as the start of a learning loop, not the end of implementation. Use
`assets/launch-plan.template.md` for material launches; a pull-request checklist
is sufficient for low-risk routine releases.

## 1. Classify launch risk

Assess blast radius, reversibility, novelty, data changes, dependency changes,
security/privacy impact, user visibility, operational maturity, and regulatory
requirements. State required approvers and evidence. Risk, not code size,
determines rigor.

## 2. Verify readiness

Check proportionately:

- accepted outcome and release scope;
- reviewed code and green required validation;
- exact artifact/configuration being released;
- migration and backward/forward compatibility;
- security, privacy, legal, accessibility, and support readiness;
- dashboards, logs, alerts, SLOs, capacity, runbook, and on-call ownership;
- feature flag or other containment mechanism; and
- tested rollback or safe-disable procedure.

Unverified critical items are blockers. Record owner and evidence for every
exception; never turn an unchecked box into approval.

## 3. Plan progressive exposure

Define stages appropriate to the product: local/staging, team dogfood, internal
users, trusted testers, small production percentage, broader rollout, and full
availability. For every stage specify:

- eligible users or traffic;
- duration or minimum evidence window;
- product success and system health measures;
- explicit proceed, pause, and rollback thresholds;
- monitoring owner and decision maker; and
- communications or support actions.

Prefer configuration or feature-flag changes over rebuilding different
artifacts between stages.

## 4. Execute only with authorization

Present the readiness result and next rollout step. Obtain explicit human
authorization before deploying, publishing, migrating data, changing a flag, or
expanding exposure. Observe the named signals after every stage. Pause or roll
back when thresholds fail; do not optimize for completing the rollout.

## 5. Learn and close

After the evidence window, compare outcomes to the brief. Record unexpected
behavior, incidents, support feedback, cost, and follow-up work. Remove temporary
flags, compatibility paths, and migration tooling when safe. Update product or
design documentation when the learned behavior changes future decisions.

Return a concise decision: expand, hold, roll back, or revise—plus evidence and
owners for remaining actions.
