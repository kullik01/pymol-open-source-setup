---
name: specify-project
description: Interview a developer one question at a time to create or revise a canonical SPECIFICATION.md that combines an accepted product frame with a high-level technical blueprint. Use for a new greenfield product, a whole-product redesign, or an explicit request for a comprehensive project specification. Do not use for a bounded feature, implementation plan, roadmap, task breakdown, or code change.
---

# Specify Project

Guide a developer through one continuous, recommendation-led interview while
preserving two internal decisions: first accept the product frame, then accept
the technical design. Produce one canonical `SPECIFICATION.md`; do not also copy
the same facts into a separate brief and design.

Read `references/interview-coverage.md` completely before beginning the
interview. Read `assets/specification.template.md` completely before creating or
revising the artifact.

## 1. Confirm this is the right path

Use this skill for a new product or whole-system blueprint where the user wants
a thorough guided interview and one combined specification.

Redirect instead when:

- a bounded brownfield feature needs `define-product` and, if material,
  `design-solution`;
- a local fix or refactor can start with `build-change`;
- an accepted specification needs milestones and work items from
  `plan-delivery`; or
- the request is to implement code.

Risk overrides apparent size. Do not use the combined format to avoid required
security, privacy, data, reliability, accessibility, or domain review.

## 2. Establish the working context

Read all supplied source material. If a repository exists, inspect its
instructions, current architecture, code, interfaces, schemas, tests, build,
deployment, ownership, and prior decisions before asking technical questions.
Do not ask the developer for discoverable repository facts.

Choose one canonical artifact location:

- single-product repository: `SPECIFICATION.md` at the repository root;
- monorepo or multi-product repository:
  `docs/product/<slug>/SPECIFICATION.md`; or
- an established repository convention when one already exists.

State the proposed location early. Do not overwrite an unrelated specification.
Use Git as revision history; do not invent document revision identifiers.

Maintain a decision ledger during the interview with four categories:

- **Verified:** supported by repository or authoritative evidence;
- **Decision:** explicitly accepted by the responsible human;
- **Assumption:** plausible but not yet supported;
- **Open:** unresolved and either blocking or non-blocking.

## 3. Follow the interview contract

During discovery, ask exactly one targeted question per response. End the
response with one interrogative sentence and avoid other question marks.

Use this response shape:

```markdown
**Current understanding:** [one short synthesis]

**Recommendation:** [one concrete default and why]

**Trade-offs:** [only for a material choice; two or three real alternatives]

**Question:** [exactly one question]
```

Apply these rules:

- Ask the highest-impact unresolved question, not a fixed questionnaire.
- Include a recommendation the developer can accept with "yes".
- Ground the recommendation in known constraints and label uncertainty.
- Challenge vague, contradictory, unsafe, or non-viable answers respectfully.
- Do not invent users, evidence, numerical targets, scale, policy, or constraints.
- Do not force irrelevant topics, technologies, agents, services, or APIs into
  the design.
- Answer a user's side question before continuing with one next interview
  question.
- Briefly summarize progress every five to eight answers without adding another
  question.
- Revisit an accepted decision only when new evidence creates a material conflict.

The one-question rule governs the interview, not the final artifact handoff or a
requested read-only status summary.

## 4. Accept the product frame first

Establish the product half before selecting architecture:

- problem, evidence, target users, and affected stakeholders;
- desired outcome, measures, guardrails, and baseline plan;
- essential user and failure scenarios;
- first-release scope, explicit non-goals, and plausible later work;
- business, legal, safety, privacy, accessibility, platform, cost, and timing
  constraints; and
- assumptions that need evidence.

Prefer a bounded discovery experiment if the central user, problem, or outcome
is not supported. Never turn a proposed technology into the product problem.

When the product frame is coherent, summarize it, recommend acceptance, and ask
the human for one explicit acceptance decision. Record `Product frame: Accepted`
only after confirmation. Do not begin detailed architecture while a blocking
product decision remains open.

## 5. Design the high-level system

After product-frame acceptance, settle only technical decisions that must be
shared before delivery planning or parallel implementation. Cover applicable
areas from `references/interview-coverage.md`, including:

- system context, components, responsibilities, ownership, and dependencies;
- domain model, state transitions, data lifecycle, schemas, and auditability;
- public and internal contracts, clients, protocols, errors, and compatibility;
- trust boundaries, identity, permissions, privacy, abuse, and secrets;
- failure isolation, timeouts, retries, idempotency, recovery, and degradation;
- concurrency, capacity, performance, availability, and cost;
- configuration, environments, deployment topology, and operations;
- observability, test/evaluation strategy, migration, rollout, rollback, and
  cleanup; and
- credible alternatives and consequences.

For each cross-component contract define its owner, consumers, behavior,
validation, errors/timeouts, compatibility, and contract evidence. Do not
prescribe private classes, file layouts, algorithms, sprint work, or code unless
they are genuinely part of the external architectural contract.

Use text, ASCII, or Mermaid diagrams according to repository convention. Explain
the important paths and boundaries in prose; a diagram is not a specification by
itself.

## 6. Determine completeness honestly

Do not claim that every possible unknown is resolved. The specification is ready
for acceptance only when:

- the product outcome, V1 scope, and non-goals are accepted;
- interfaces, data, ownership, security, failure behavior, and deployment are
  precise enough for delivery planning;
- acceptance scenarios trace to components, contracts, tests, and rollout
  evidence;
- no open decision blocks safe planning;
- every remaining non-blocking unknown has an owner, evidence-producing action,
  and decision point; and
- required domain reviewers are named.

Run a consistency pass before acceptance. Identify contradictions, unsupported
claims, orphan components, unowned contracts, untestable requirements, unsafe
migrations, and rollback paths that cannot restore a supported state.

## 7. Create and accept `SPECIFICATION.md`

Use `assets/specification.template.md`. Adapt headings only when a section is
genuinely inapplicable; say why rather than silently omitting a production
concern.

Set the document and both checkpoints to `Draft` initially. Mark the product
frame and technical design separately as `Accepted` after their human decisions.
Set the document `Status: Accepted` only when both checkpoints are accepted,
blocking decisions are closed, required reviews are complete, and the accountable
human approves planning against the exact file.

For a substantive specification, run:

```bash
python .agents/skills/specify-project/scripts/validate_specification.py <path>
```

The validator checks structure, not architectural correctness. Report its exact
result and any limitations.

## 8. Handoff without implementation planning

Conclude with:

- artifact path and status;
- accepted product and technical checkpoints;
- important decisions and non-blocking unknowns;
- required follow-up evidence and domain reviews; and
- the recommended next action.

For multi-developer or multi-milestone work, hand the accepted specification to
`plan-delivery`. For a single bounded first slice, hand it to `build-change`.
Do not generate a roadmap, sprint plan, staffing allocation, task checklist, or
code while using this skill.

## Stop conditions

Stop with verified facts, a recommendation, and one precise question when:

- product answers conflict or the central outcome lacks evidence;
- a material API, data, security, cost, ownership, or architecture decision has
  no accountable human;
- the repository contradicts the proposed design;
- required specialist input is unavailable;
- the specification would describe an unsafe or unverifiable system; or
- the user asks to proceed to implementation before the required acceptance
  checkpoint.
