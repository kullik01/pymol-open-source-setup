---
name: audit-google-python-style
description: Audit Python code against the Google Python Style Guide using this repository's Ruff and pymake toolchain plus supplemental analysis, then propose a short grouped remediation plan for explicit human approval before modifying approved source files. Invoke only when the user explicitly requests this audit or invokes $audit-google-python-style. Do not use for ordinary code reviews, pull-request reviews, linting, or implementation tasks.
---

# Audit Google Python Style

Perform a specialist Google Python Style audit with Ruff and `pymake` as the
deterministic baseline. This skill has two explicit phases: plan, then apply
after approval.

## Invocation boundary

Use this skill only for an explicit request such as:

```text
$audit-google-python-style
Audit the Python codebase and propose approved style fixes.
```

Do not invoke it implicitly as part of `review-change`, `clean-code-review`,
`pr-review`, a normal code review, or a generic linting request.

Invoking the skill is not approval to modify code. Keep the audit and plan
phase read-only. Require a separate affirmative human response to the exact
plan before entering the apply phase.

## Tooling policy

The attached guide mentions Pylint, but this repository deliberately uses Ruff.
Never invoke, install, configure, or require Pylint. Use the repository wrapper:

```powershell
.\pymake.bat lint
.\pymake.bat format dry_run=true
.\pymake.bat check_types
```

Use `pymake` rather than invoking Ruff, formatters, or type checkers directly.
The supplemental standard-library checker is the only extra command because no
existing `pymake` task wraps it.

## Phase A: audit and approval plan

1. Read repository instructions, `ruff.toml`, `pyproject.toml`, `pyrefly.toml`,
   package-specific configurations, generated-code conventions, local
   exceptions, and the current working-tree state.
2. Define the in-scope `.py` files. Include tests unless explicitly excluded.
   Exclude dependencies, caches, build output, vendored code, generated code,
   and `.agents` only with repository evidence.
3. Run the deterministic `pymake` checks before making judgments.
4. Run `scripts/check_google_rules.py` for each Python package.
5. Perform the agent judgment pass over imports, naming, documentation,
   exceptions, resources, global state, type annotations, and consistency.
6. Produce a short remediation plan grouped by source-file collection and rule
   family. Include:
   - approved scope and excluded files;
   - grouped files or directories;
   - exact style changes proposed;
   - whether each change is Ruff-assisted or manual;
   - non-goals and behavior-preservation constraints; and
   - post-approval validation commands.
7. Stop and ask the human to approve, reject, or revise this exact plan. Do not
   edit files, run `pymake` write-mode format/lint fixes, or apply automated
   changes before approval.

If the plan depends on missing scope, a project-policy decision, uncertain
generated-code status, or a behavior/public-API/architecture change, ask for
clarification instead of silently expanding the plan.

## Strict documentation contract

Treat documentation as a style requirement for every documentable symbol,
whether it is public or private. This includes modules, functions, async
functions, classes, methods, constructors, properties, and other named
callables. Do not exempt a private or internal symbol merely because its name
starts with an underscore. Generated code is excluded only when the repository
provides evidence that it is generated and out of scope.

Every docstring must contain a concise summary sentence on its first line,
terminated as a complete sentence. For functions and methods, use Google
Python docstring sections as applicable:

- `Args:` describes every meaningful parameter, including keyword-only,
  variadic, optional, and private parameters; `self` and `cls` do not need
  entries.
- `Returns:` describes every returned value when the callable returns a value.
- `Yields:` describes yielded values for generators instead of `Returns:`.
- `Raises:` describes exceptions that are part of the callable's contract.

Do not accept an empty docstring, a placeholder, a name restatement, or a
summary without required parameter or return documentation. A callable with no
meaningful parameters does not need an `Args:` section, and a callable that
only returns `None` does not need `Returns:`, but its summary must still
describe the behavior. Missing docstrings or missing applicable sections are
style fixes for the approval plan unless their wording requires a human API or
behavior decision.

## Phase B: approved remediation

Enter this phase only after explicit approval of the plan. Treat approval as
limited to the named files, rule families, and non-goals.

1. Re-check the working tree and re-audit the approved scope. If relevant files
   changed since the plan, stop and present an updated plan.
2. Apply only the approved style changes. Preserve runtime behavior, public
   APIs, tests, and unrelated user changes. Do not alter dependencies,
   configuration, or generated sources unless explicitly approved.
3. Use Ruff's formatter and safe fixes through the repository wrapper when the
   approved scope covers the formatter's full target. For a partial scope,
   make targeted edits and use `pymake` check-only validation to avoid changing
   unapproved files.
4. Make remaining documentation, import, exception, type, naming, and design
   corrections manually.
5. Re-run `pymake lint`, `pymake format dry_run=true`, `pymake check_types`, and
   the supplemental checker. Run tests when edits could affect behavior.
6. Inspect the exact diff for scope expansion, accidental behavior changes,
   weakened tests, and formatter churn.
7. Report applied changes, validation evidence, residual findings, and any
   items that require a new approval. Do not merge, commit, or release.

## Supplemental checks

The checker identifies relative and wildcard imports, semicolons, explicit
line continuations, type comments, Pylint suppressions, `typing.Text`, legacy
typing aliases, broad exception handlers, assertions outside tests, missing or
incomplete docstrings for public and private documentable symbols, mutable
module/class state, nested definitions, lambdas, long functions, long lines,
malformed TODO comments, syntax errors, and unreadable source files.

Use Python's standard-library `ast` and `tokenize` modules. Hard syntactic
violations exit non-zero; judgment items are review findings until the agent
decides whether the guide and repository context establish a violation.

## Style judgment

Apply the guide's normative language precisely. Treat recommendations as
context-sensitive unless Ruff, the type checker, or local policy makes them
mandatory. Review module structure, docstring completeness and quality,
comments, exception design, resource lifetime and context managers,
comprehensions, decorators, generators, properties, logging, error messages,
TODO context, `__main__` guards, function size, annotations, `None` handling,
generics, and local consistency. The documentation contract above is an
explicit project audit policy and applies to private symbols as well as public
ones. Do not turn Pylint-specific instructions into requirements for this
Ruff-based repository.

## Plan and completion reports

The plan report must end with `APPROVAL REQUIRED` unless no changes are needed.
The apply report must include exact commands and results, approved scope,
changed files, residual findings, and one verdict: `COMPLETED`, `PARTIALLY
COMPLETED`, or `CLARIFICATION REQUIRED`.

Never claim compliance solely because Ruff passes. Human approval authorizes
only the approved remediation plan and never authorizes merge or release.
