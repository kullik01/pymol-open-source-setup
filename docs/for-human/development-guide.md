# The CoDev Workflow

*Start here. This is the short version — the mental model, the lifecycle, and
the rules you need to work day to day. For stage-by-stage depth, worked
examples, and team mechanics, see the
[Idea-to-Production Handbook](../handbooks/IDEA-TO-PRODUCTION-HANDBOOK.md). The
cookbook, prompt templates, and detailed handbooks are also available as
dedicated Wiki pages.*

## The problem this solves

AI can now write plausible code faster than a human can review it. That
creates a new failure mode: velocity without accountability. A model can
invent an API that doesn't exist, "fix" a test by weakening it, or quietly
expand a bug fix into a redesign — and do all of it fluently enough that a
tired reviewer skims past it.

CoDev is a small set of files — an `AGENTS.md` policy, a handful of skills, an
optional three-agent topology, and this documentation — installed into a Git
repository to make AI-assisted development **fast without being unaccountable**.
It does this by fixing three things that ad-hoc "chat with an AI" workflows
usually get wrong:

1. **Plans are grounded in the repository, not the model's memory.** The AI
   reads your actual code, tests, and conventions before proposing anything.
2. **Process scales with risk and coordination, not with ceremony.** A typo
   fix and a payments migration should not go through the same amount of
   paperwork.
3. **Authority stays human at the points that matter.** An AI can investigate,
   propose, implement, and review. It cannot approve its own work, and it
   never merges, deploys, migrates data, or expands production exposure.

## The mental model

Think of CoDev as a **narrow waist between intent and code**. On one side is
what you actually want (a product outcome, an architecture decision, a bug
report). On the other is a diff. Everything in between exists to keep those
two things connected as the work passes through however many hands — human or
AI — touch it.

Three ideas carry almost all of the workflow's behavior:

- **Repository grounding.** An AI's claims about "how the code works" are
  worth nothing until checked against the actual files. Every skill starts
  with inspection, not proposal.
- **One fact, one owner.** Outcome and scope live in a brief or specification.
  Architecture and contracts live in a design document. Assignment and status
  live in a tracker. Code behavior lives in code and tests. Nothing is copied
  between documents — later documents *link* to earlier ones. If you find
  yourself updating the same fact in two places, one of those places is wrong.
- **Small, reviewable, evidence-backed changes.** A change is not "done"
  because the AI says so. It is done when it is small enough to review, has
  been validated with commands you can rerun, and an independent reviewer —
  human, and optionally AI — has looked at the *exact* diff.

If you remember nothing else: **the AI supplies evidence, you supply
authority.**

## The four steps

Every piece of work, from a one-line fix to a new product, moves through the
same four human-facing steps. You do not need to name a skill or memorize the
internal routing — describe what you want in plain language, and the AI
resolves it to the right step and the right internal skill
(`specify-project`, `define-product`, `design-solution`, `plan-delivery`,
`build-change`, `review-change`, `pr-review`, `clean-code-review`, `critique-review`,
`launch-product`).

| Step | Question it answers | Deepens into |
|---|---|---|
| **Understand** | What are we building, and what must be decided before code is safe to write? | `design-solution` for shared architecture; `plan-delivery` for multi-developer coordination |
| **Build** | What is the smallest change that delivers this, with evidence it works? | interactive pairing, or bounded delegation to a `builder` subagent |
| **Review** | Is this exact change correct, safe, and consistent with what we agreed? | a fresh, read-only reviewer pass; `clean-code-review` for a maintainability-focused scan |
| **Ship** | Are we ready to expose this to real users, and how do we find out if it's working? | staged rollout, observation, and a decision to expand, hold, or roll back |

A small, local, reversible fix can go **Understand → Build → Review → Ship**
in minutes, with Understand collapsing to "here's the bug, here's the
expected behavior." A new product spends real time in Understand, because
getting the outcome and architecture right is what makes everything after it
cheap. **The step names don't change. Only how much work each step requires
changes** — and that's decided by risk and coordination need, not by habit.

### When a step needs more than a conversation

Design and delivery planning are not extra stages you must pass through —
they're *conditional depth inside Understand*, triggered by specific
properties of the change:

- Touches a **public or shared API, contract, or persistent data model** →
  needs `design-solution`.
- Touches **authentication, permissions, privacy, or abuse controls** → needs
  `design-solution`.
- Needs **more than one developer working concurrently** → needs
  `plan-delivery`, and any contracts between their work need
  `design-solution` first.
- Is a **genuinely new product or a whole-product redesign** → consider the
  single guided interview, `specify-project`, which walks through product
  framing and technical design in one conversation and produces one canonical
  `SPECIFICATION.md`. Use this *or* the modular `define-product` +
  `design-solution` path — never both for the same facts.

Everything else stays a conversation. Risk always overrides size: a five-line
change to a permission check gets a design discussion and independent review
even though the diff is tiny.

## The interaction model

### Who does what

| | Human | AI |
|---|---|---|
| **Understand** | States the problem, accepts or corrects the framing, makes product/architecture decisions | Investigates the repository, proposes framing, drafts briefs/designs, asks one targeted question at a time |
| **Build** | Approves the plan, answers stop-condition questions | Grounds the plan in real code, implements, tests, self-checks |
| **Review** | Reads the exact diff, decides whether it may merge | Produces an independent, read-only review with prioritized findings |
| **Ship** | Authorizes exposure and expansion | Assembles readiness evidence, proposes rollout stages and thresholds |

### Handoff points

Two artifacts carry the handoff between AI activity and human control, and
neither requires bureaucracy for routine work:

- **The focus card**, presented before any editing begins: what's changing,
  what success looks like, what's explicitly out of scope, which files are
  fair game, how the change will be validated, and the exact conditions that
  should stop work and return to you.
- **The evidence receipt**, returned when implementation is "done": what
  changed, the exact commands run and their output, which acceptance
  criteria map to which evidence, any deviations from the plan, and current
  review status.

Neither has to be a separate document for ordinary work — for a small change
both can be a few lines in the conversation. They become written artifacts
(using the templates under `.agents/skills/*/assets/`) once work spans
sessions, touches several components, or carries enough risk that a
reconstructable record matters.

### Review loops

Every code change gets an **independent human review** — the person who wrote
it, human or AI, does not approve it. For normal- or higher-risk work, add a
fresh AI review (`review-change`) as a second, independent pass before the
human looks at it; use `clean-code-review` alongside it when maintainability
and idiom matter as much as correctness. If a review turns up a concrete,
bounded fix, `critique-review` will draft the exact suggested diff — but it
never applies it. An explicit handoff to `build-change`, or the developer
applying it directly, is required before the correction lands, and the
corrected diff gets reviewed again from scratch.

### Where it breaks down (and how CoDev catches it)

| Failure mode | What it looks like | The guardrail |
|---|---|---|
| Hallucinated implementation | AI invents an API or config key that doesn't exist | Mandatory repository inspection before proposing; the reviewer checks claims against the diff |
| Scope creep | A bug fix quietly becomes a refactor | The focus card's allowed scope is a drift boundary; expansion must be surfaced before acting on it |
| Self-approval | The implementing AI declares its own work done | The builder cannot invoke another agent or approve; the reviewer is a fresh, independent context |
| Retry spiral | Repeated attempts at the same broken approach | Stop after two failed attempts with the same root cause; escalate to the human |
| Stale plan drift | The repository moved under the plan mid-implementation | Base-commit and snapshot checks; a changed base is a stop condition, not something to paper over |
| Rubber-stamp review | A review that restates the diff instead of finding problems | Reviews must cite evidence and end in one of three explicit states: `READY FOR HUMAN APPROVAL`, `CHANGES REQUIRED`, `BLOCKED BY MISSING EVIDENCE` |

## On a subagent-capable platform

Where the platform supports it, the three-agent topology (`orchestrator`,
`builder`, `reviewer`) automates the mechanical parts of this loop without
changing who has authority. You stay in one conversation with the
orchestrator; it plans, delegates to a bounded `builder`, and sends the exact
resulting diff to a fresh, read-only `reviewer`. You are not copying messages
between agents — but you still approve the plan before delegation, and you
still approve merge, release, and any expansion of production exposure. Use a
separate branch or worktree and a separate orchestrator session for each
concurrently executing work item; do not run two implementation streams
through one conversation.

## Multi-developer rules, briefly

- **Own components and APIs.** Every important component or contract has one
  responsible owner for design, review, compatibility, and operation.
- **Agree on contracts before working in parallel.** Two developers may work
  concurrently once they share an accepted schema or signature and a contract
  fixture to test against it.
- **Keep branches short-lived and changes small.** Prefer feature flags over
  long-lived branches for incomplete but safe intermediate states.
- **Limit work in progress.** One active implementation item per developer by
  default; the owner and reviewer are always different people.

The full mechanics — dependency vocabulary, integration checkpoints, rolling-
wave planning, and a worked multi-developer example — live in the
[Idea-to-Production Handbook](../handbooks/IDEA-TO-PRODUCTION-HANDBOOK.md#15-multi-developer-coordination-in-detail).

## Canonical artifacts

| Artifact | Owns | Needed when |
|---|---|---|
| `SPECIFICATION.md` | Product frame *and* technical blueprint, with two acceptance checkpoints | Guided greenfield or whole-product path (`specify-project`) |
| Brief | Outcome, users, success measures, scope, non-goals | Every feature or product (`define-product`) |
| Design | Architecture, ownership, contracts, trade-offs, rollout | Material or risky technical change (`design-solution`) |
| Delivery plan | Milestones, ready work, owners, reviewers, dependencies | Multi-developer work (`plan-delivery`) |
| Implementation plan | Repository-grounded steps and validation for one work item | Complex, risky, or cross-session changes (`build-change`) |
| Pull request | The actual change, with tests | Every code change |
| Launch plan | Readiness, rollout stages, thresholds, rollback | Material releases (`launch-product`) |

Git history is the revision record for all of them — use `Draft`, `Accepted`,
`Active`, and `Superseded` as document status, and don't invent a second
versioning scheme for planning documents. Link to upstream facts; never copy
them.

## How the companion documents fit together

| Document | Answers | Audience |
|---|---|---|
| **This document** | What is CoDev, and what's the model for using it? | You, once |
| [AI Agent Reference](../for-ai/ai-agent-guidelines.md) | Exactly how must an AI behave inside this workflow? | The AI, every session |
| [Workflow Cookbook](../WORKFLOW-COOKBOOK.md) | What do I actually type for the four common shapes of work? | You, while working |
| [Prompt Templates](../AI-WORKFLOW-PROMPTS.md) | What's a ready-to-paste prompt for this specific situation? | You, while working |
| [Idea-to-Production Handbook](../handbooks/IDEA-TO-PRODUCTION-HANDBOOK.md) | What's the full stage-by-stage detail, quality gates, and team mechanics? | You, when you need depth |
| [Python Project Handbook](../handbooks/PYTHON-PROJECT-HANDBOOK.md) | How should a Python repository using this workflow be structured and operated? | You, setting up or maintaining a Python project |
| [Language-Agnostic Project Handbook](../handbooks/LANGUAGE-AGNOSTIC-PROJECT-HANDBOOK.md) | Same question, for any other language or stack | You, setting up or maintaining a non-Python project |

If a rule appears in more than one of these, that's a bug in the
documentation, not a feature — each document above owns a distinct question.
