# Project Specification Interview Coverage

Use this reference as a coverage map, not a questionnaire. Ask only the
highest-impact unresolved question and skip topics that are demonstrably
inapplicable. Every recommendation must be grounded in accepted context.

## Contents

1. Product frame
2. Domain and lifecycle
3. System boundaries and ownership
4. Interfaces and contracts
5. Data
6. Security, privacy, and abuse
7. Failure and resilience
8. Concurrency, scale, performance, and cost
9. Clients and human interfaces
10. AI, agents, and tool use
11. Configuration and deployment
12. Observability and operations
13. Testing and evaluation
14. Compatibility, migration, and release
15. Completeness and consistency

## 1. Product frame

Establish:

- the primary user and the situation in which the problem occurs;
- evidence that the problem exists, its frequency, and current workaround;
- affected users, administrators, operators, and non-users;
- the desired change in behavior or system state;
- leading measures, durable outcomes, guardrails, baseline plan, and owner;
- primary success, denial, degraded, and recovery scenarios;
- the smallest complete V1 outcome;
- explicit non-goals and later possibilities;
- fixed legal, policy, accessibility, platform, cost, and timing constraints;
- assumptions whose failure would invalidate the project.

Recommend a discovery experiment instead of architecture when the central user,
problem, or outcome remains speculative. Never invent numerical targets.

## 2. Domain and lifecycle

Identify only concepts with architectural consequences:

- core entities, value types, identities, and invariants;
- ownership and authoritative source for each concept;
- valid states and transitions;
- commands, events, and side effects that cause transitions;
- uniqueness, ordering, temporal, and consistency rules;
- creation, activation, suspension, expiry, deletion, and restoration;
- audit or historical reconstruction requirements;
- human override and exceptional-state behavior.

Prefer domain language used by actual users. Do not convert every noun into a
class or database table.

## 3. System boundaries and ownership

Determine:

- external actors and systems;
- major components and one responsibility for each;
- existing capability to reuse rather than recreate;
- component and interface owners;
- dependency direction and prohibited dependencies;
- synchronous and asynchronous control flow;
- source of truth and cache/materialized-view boundaries;
- trust, deployment, failure, and scaling boundaries;
- isolation between users, tenants, workloads, or plugins;
- decisions local implementers may make independently.

Every component must contribute to an accepted scenario. Remove orphan
components and abstractions without a demonstrated responsibility.

## 4. Interfaces and contracts

For each human or machine interface establish:

- owner, consumers, purpose, and stability promise;
- protocol and authoritative schema location;
- operation, request/event/resource shape, and response/result;
- validation and normalization;
- authentication and authorization context;
- error taxonomy and retryability;
- timeout, cancellation, pagination, streaming, and size limits;
- idempotency, ordering, deduplication, and concurrency behavior;
- compatibility, versioning, deprecation, and removal;
- rate limits and quota semantics;
- contract fixtures or tests.

Specify semantics rather than private implementation. Use REST, gRPC, events,
MCP, GraphQL, CLI commands, or another protocol only when context supports it.

## 5. Data

Cover applicable lifecycle stages:

- collection or creation and lawful purpose;
- validation and canonical representation;
- classification and sensitive fields;
- storage technology constraints and authoritative copy;
- indexes, relationships, consistency, and transaction boundaries;
- encryption, key ownership, and access control;
- audit, lineage, provenance, and change history;
- backup, restore, export, portability, and legal hold;
- retention, expiry, deletion, and deletion propagation;
- residency and cross-region/cross-tenant constraints;
- schema evolution, migration, and old-reader/new-writer compatibility;
- test-data strategy and prohibition on uncontrolled production data.

Do not select a datastore until access patterns, consistency, lifecycle, and
operational ownership justify it.

## 6. Security, privacy, and abuse

Identify:

- assets, actors, trust boundaries, and attacker capabilities;
- identity source and session or workload identity lifecycle;
- authorization decisions and least-privilege roles;
- untrusted input and destination-specific output handling;
- secret storage, delivery, rotation, revocation, and audit;
- personal or regulated data purpose, minimization, consent, and retention;
- tenant isolation and confused-deputy risks;
- administrative and emergency access;
- abuse, enumeration, scraping, denial-of-service, and fraud controls;
- dependency and build supply-chain protections;
- security event evidence and private reporting/incident ownership.

Escalate material choices to the appropriate specialist. Do not interpret
absence of a stated regulation as permission to collect data.

## 7. Failure and resilience

For each important dependency or operation establish:

- expected local and downstream failures;
- visible user behavior under failure;
- timeout and cancellation propagation;
- retry eligibility, limit, backoff, and jitter;
- idempotency and duplicate handling;
- circuit breaking, load shedding, or queue backpressure;
- fault containment and blast radius;
- degraded but supported modes;
- detection and diagnostic evidence;
- automatic versus human recovery;
- recovery point and recovery time expectations;
- rollback or forward-repair path.

Retries are not a default. They can amplify overload or duplicate non-idempotent
work.

## 8. Concurrency, scale, performance, and cost

Seek evidence for:

- expected and peak users, requests, events, or data volume;
- latency and throughput expectations tied to a user outcome;
- concurrency model, contention points, and ordering requirements;
- queue, connection, thread/process, memory, storage, and payload bounds;
- admission control, quotas, and noisy-neighbor protection;
- horizontal or vertical scaling boundaries;
- load, stress, endurance, and capacity evaluation;
- infrastructure, third-party, model, storage, egress, and support cost;
- cost limits, measurement, and owner.

When no baseline exists, specify how to establish it. Do not invent internet
scale for a small internal tool.

## 9. Clients and human interfaces

For applicable web, mobile, desktop, CLI, API, or assistive clients cover:

- supported clients, platforms, versions, and ownership;
- primary journeys and recovery behavior;
- client/server responsibility and offline behavior;
- accessibility, keyboard, screen-reader, contrast, and reduced-motion needs;
- localization, time zones, currencies, units, and text expansion;
- authentication, session expiry, and permission-denied experience;
- optimistic updates, conflict handling, and stale data;
- client compatibility and update policy;
- telemetry and privacy-respecting user feedback.

Do not make a UI framework an architectural requirement without a client and
maintenance reason.

## 10. AI, agents, and tool use

Use this section only when the product contains an AI capability. Establish:

- model purpose and behavior that remains deterministic outside the model;
- model/provider/version selection and change policy;
- prompt, retrieval corpus, context, and memory ownership;
- data use, retention, residency, and training restrictions;
- model-output validation and safe fallback;
- prompt injection and untrusted-content boundaries;
- allowed tools and per-tool permission scope;
- human authorization for consequential actions;
- isolation between agents, users, and tenants;
- maximum steps, time, tokens, cost, retries, and cancellation;
- offline evaluation set, provenance, owner, and contamination control;
- quality, safety, latency, availability, and cost thresholds;
- monitoring for drift, regressions, abuse, and unexpected tool use;
- rollback across prompt, model, tools, retrieval data, and application versions.

Never specify "the model decides" where a stable contract, authorization rule,
or safety invariant is required.

## 11. Configuration and deployment

Determine:

- runtime and supported platform versions;
- processes, containers, functions, jobs, or device topology;
- environment boundaries and promotion flow;
- configuration schema, source precedence, validation, and versioning;
- secret and workload-identity delivery;
- stateful and stateless boundaries;
- network ingress, egress, service discovery, and trust boundaries;
- regional, availability-zone, residency, or edge requirements;
- deployment ownership and least-privilege automation;
- immutable artifact identity and provenance;
- infrastructure creation, update, drift, and deletion;
- local development and representative preproduction topology.

Separate required properties from a vendor choice unless organizational policy
already fixes the provider.

## 12. Observability and operations

Define:

- product, correctness, security, reliability, and cost signals;
- structured logs and correlation without sensitive payloads;
- metrics, traces, dashboards, and actionable alerts;
- service-level indicators, objectives, and error-budget response when relevant;
- health, readiness, dependency, queue, and saturation signals;
- on-call or support ownership and escalation route;
- runbooks for common and dangerous failure modes;
- backup/restore, disaster recovery, and operational drills;
- incident evidence, communication, and post-incident learning;
- dependency maintenance, deprecation, and end-of-life ownership.

Every signal needs a decision or operational action. Avoid telemetry collected
without an owner or purpose.

## 13. Testing and evaluation

Trace accepted scenarios and risks to:

- unit evidence for deterministic rules;
- contract evidence for shared interfaces;
- integration evidence for real adapters and infrastructure;
- end-to-end evidence for critical user journeys;
- negative authorization, abuse, and validation cases;
- migration, compatibility, and rollback tests;
- performance, capacity, resilience, and restore evaluation;
- accessibility and internationalization evidence;
- evaluator ownership and independence;
- test-data boundaries and flake control;
- release-candidate and production verification.

For critical or AI-generated behavior, protect evaluation integrity with
independent, immutable, hidden, property-based, fuzz, mutation, or differential
tests as appropriate. Passing visible tests is not complete evidence.

## 14. Compatibility, migration, and release

Establish:

- supported old and new clients, readers, writers, and artifacts;
- additive or breaking contract changes;
- expand/migrate/contract ordering;
- backfill, dual-read/write, validation, and reconciliation;
- feature-flag ownership and safe default;
- internal, staging, shadow, canary, and broader cohorts;
- product and reliability success thresholds;
- guardrails, observation duration, stop conditions, and decision owner;
- rollback to a supported data and code state;
- cleanup of flags, compatibility paths, temporary infrastructure, and data;
- user, operator, support, and developer communication.

Do not include sprint sequencing or work assignment. This section specifies safe
states and release constraints for later delivery planning.

## 15. Completeness and consistency

Before recommending technical-design acceptance, verify:

- each V1 scenario has an owning component and contract path;
- each external dependency has failure and operational behavior;
- each sensitive data flow crosses identified trust boundaries safely;
- each state transition has authority, validation, and recovery;
- each shared interface has one owner and compatibility policy;
- each material claim has evidence or is labeled an assumption;
- each accepted quality target has test or production evidence;
- each migration step preserves a supported intermediate state;
- rollback does not depend on an irreversible schema or data change;
- every open item is classified as blocking or non-blocking;
- every non-blocking item has an owner and decision point;
- the specification contains no implementation roadmap or task checklist.
