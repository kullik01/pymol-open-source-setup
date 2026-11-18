# [Project Name] Specification

**Status:** Draft
**Product frame:** Draft
**Technical design:** Draft
**Product owner:** [name or team]
**Technical owner:** [name or team]
**Required reviewers:** [technical and specialist reviewers]
**Last reviewed:** [YYYY-MM-DD]

## Executive summary

<!-- State the user problem, intended outcome, and recommended system in plain language. -->

## Problem, users, and evidence

<!-- Identify users, current problem, supporting evidence, and affected stakeholders. -->

## Product vision and desired outcomes

<!-- Describe changed user or system behavior, not shipped components. -->

## Success measures and guardrails

| Measure | Baseline or baseline plan | Target/decision rule | Window | Source | Owner |
|---|---|---|---|---|---|
| [measure] | [baseline] | [target] | [window] | [source] | [owner] |

## Essential scenarios

- <!-- Primary end-to-end user behavior. -->
- <!-- Important failure, denial, or recovery behavior. -->

## V1 scope

### Included

- <!-- Smallest complete first-release outcome. -->

### Later possibilities

- <!-- Plausible follow-up; not committed. -->

## Non-goals

- <!-- Explicitly excluded behavior, client, abstraction, or operational promise. -->

## Constraints

- <!-- Business, legal, safety, privacy, accessibility, platform, cost, or timing constraint. -->

## Assumptions and unresolved questions

| Item | Classification | Blocking | Owner | Evidence/action | Decision point |
|---|---|---|---|---|---|
| [item] | [assumption/open] | [yes/no] | [owner] | [evidence] | [point] |

## Architectural context

<!-- Describe existing systems, external actors, constraints, and verified sources. -->

## System architecture

<!-- Show the major components and important data/control flows using text, ASCII, or Mermaid. -->

## Components and ownership

| Component | Responsibility | Owner | Inputs | Outputs | Dependencies |
|---|---|---|---|---|---|
| [component] | [responsibility] | [owner] | [inputs] | [outputs] | [dependencies] |

## Domain model and state transitions

<!-- Define important entities/value types, invariants, relationships, lifecycle, and transitions. -->

## Data lifecycle and retention

<!-- Define creation, validation, storage, classification, access, audit, retention, export, and deletion. -->

## APIs, protocols, and contracts

| Contract | Owner | Consumers | Shape/reference | Guarantees | Validation/errors/timeouts | Compatibility | Test/fixture |
|---|---|---|---|---|---|---|---|
| [contract] | [owner] | [consumers] | [shape] | [guarantees] | [behavior] | [policy] | [evidence] |

## Supported clients and interfaces

<!-- Specify applicable web, mobile, desktop, CLI, API, event, tool, or AI interfaces. -->

## Component orchestration rules

<!-- Define sequencing, isolation, coordination, authority, cancellation, and duplicate handling. -->

## Security, privacy, and abuse controls

<!-- Define trust boundaries, identity, permissions, input/output handling, secrets, sensitive data, and abuse controls. -->

## Failure modes and resilience

| Failure | User/system effect | Detection | Containment/fallback | Recovery | Owner |
|---|---|---|---|---|---|
| [failure] | [effect] | [signal] | [behavior] | [recovery] | [owner] |

## Concurrency, capacity, performance, and cost

<!-- Define only justified limits, targets, resource bounds, and scale assumptions. -->

## Configuration and deployment topology

<!-- Define configuration precedence, secrets, environments, processes/containers, state, regions, and dependencies. -->

## Observability and operations

<!-- Define logs, metrics, traces, dashboards, alerts, SLOs, support/on-call, backup, restore, and runbooks. -->

## Test and evaluation strategy

<!-- Trace unit, contract, integration, end-to-end, performance, resilience, security, and acceptance evidence. -->

## Compatibility and migration

<!-- Define schema/API versioning, old/new coexistence, migration ordering, validation, and cleanup. -->

## Rollout, rollback, and cleanup

<!-- Define flags, stages, success/guardrail thresholds, observation, rollback, and temporary-code removal. -->

## Alternatives and trade-offs

| Option | Benefits | Costs/risks | Decision and evidence |
|---|---|---|---|
| [option] | [benefits] | [costs] | [chosen/rejected and why] |

## Risks and open decisions

| Risk/decision | Impact | Blocking | Owner | Mitigation/evidence | Due/decision point |
|---|---|---|---|---|---|
| [risk] | [impact] | [yes/no] | [owner] | [action] | [point] |

## Source references

- <!-- Link canonical product evidence, repository facts, policies, designs, or external standards. -->

## Acceptance

- [ ] Product frame accepted by the accountable product owner.
- [ ] Material technical decisions resolved.
- [ ] Required technical and specialist reviews complete.
- [ ] No blocking unknown or decision remains.
- [ ] Acceptance scenarios trace to contracts, tests, and rollout evidence.
- [ ] Accountable human accepts delivery planning against this specification.
