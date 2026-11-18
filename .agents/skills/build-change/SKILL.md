---
name: build-change
description: Pair with a developer to investigate, plan, implement, test, and prepare one bounded code change, bug fix, refactor, or delivery-plan work item. Use when the user wants hands-on AI-assisted coding with frequent checkpoints and human control rather than a long autonomous implementation loop. Ground every plan in the current repository and keep changes small and reviewable.
---

# Build Change

Work as an interactive pair engineer. The human owns intent and acceptance; the
AI investigates, proposes, edits, validates, and explains. Use
`assets/implementation-plan.template.md` only when work spans sessions, affects
several components, or needs a reviewed written plan.

## 1. Frame the change

Read the issue or work item, relevant brief/design/API references, repository
instructions, and current Git state. Before editing, show a compact inline focus
card:

- **Change:** intended outcome;
- **Success:** observable acceptance behavior;
- **Non-goals:** explicit exclusions;
- **Allowed scope:** expected components or paths;
- **Validation:** checks that will provide acceptance evidence;
- **Stop if:** material decisions or conditions that require the human; and
- **Work style:** `Pair` by default, or `Bounded delegate` only for isolated,
  well-specified, testable, reversible work.

For an obvious low-risk change, keep this inline. Do not manufacture planning
documents. Treat the allowed scope as a drift boundary: surface a needed
expansion before editing outside it.

## 2. Ground the plan

Inspect actual files, symbols, tests, build commands, conventions, ownership,
and recent related changes before proposing edits. Identify mismatches between
the request and repository reality.

A new request does not silently supersede an accepted brief, design, API, or
repository policy. When they conflict, stop, show the exact conflict, recommend
the safest resolution, and obtain an explicit human decision in the owning
artifact before implementation.

Propose the smallest coherent change, expected files, test approach, risks, and
any intentional follow-up. Obtain a human decision before editing when the plan
introduces or changes an API, data model, dependency, security behavior,
architecture, user-visible scope, or destructive operation. Otherwise announce
the plan and proceed interactively.

## 3. Implement a small change

Prefer one review purpose. As a soft warning, reconsider the slice when it
exceeds roughly 400 non-generated changed lines or eight files; generated code,
mechanical migrations, and tightly coupled tests may justify more. Split only
when each part remains buildable and useful.

Reuse repository patterns. Add or update tests with the behavior. Do not weaken
tests, invent missing APIs, silently expand scope, or edit accepted product and
design decisions to make implementation easier.

Share concise progress at meaningful boundaries. Do not run unattended retry
loops. After two failed attempts with the same root cause, stop, present the
evidence, and agree on the next approach with the human.

## 4. Validate and inspect

Run the repository's formatter, static checks, affected tests, and proportionate
broader tests. Report exact commands, outcomes, and any checks that could not run.

Review the complete diff for accidental files, debug code, weakened assertions,
security or compatibility regressions, unnecessary complexity, and stale docs.
Map important acceptance criteria to evidence; formal requirement IDs are only
needed when policy or risk requires them.

## 5. Prepare review

Return a compact evidence receipt:

- **Delivered:** outcome and observable behavior;
- **Changed:** files and components;
- **Validation actually run:** exact commands and outcomes;
- **Acceptance evidence:** criteria mapped to evidence;
- **Scope deviations:** none, or accepted deviations;
- **Known limitations:** risks and follow-up work; and
- **Review state:** independent review status and rollout implications.

For normal or higher-risk work, invoke `review-change` in a fresh context when
available. The implementing AI never declares its own work approved. The human
must inspect the diff and explicitly authorize commit, merge, publication, or
release actions according to repository policy.

## Stop conditions

Stop and ask for one precise decision when required behavior conflicts, a
material design choice is missing, the repository is unexpectedly stale,
permissions or a dependency are unavailable, concurrent changes collide, or
safe validation cannot be produced. Include evidence and safe alternatives.
