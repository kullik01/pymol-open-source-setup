# Google Python Audit Check Matrix

## Authority

Use the attached Google Python Style Guide as the primary authority. Its major
areas are Python language rules, imports and packages, exceptions, mutable
global state, nested definitions, comprehensions, iterators, generators,
decorators, threading, power features, modern Python, type annotations, style
rules, documentation, naming, main guards, and consistency.

## Tool ownership

| Area | Primary check | Interpretation |
| --- | --- | --- |
| Ruff lint rules | `pymake lint` | Report configured Ruff findings. |
| Formatting | `pymake format dry_run=true` | Report formatter failures; do not auto-fix. |
| Type correctness | `pymake check_types` | Report type-checker failures separately from style. |
| Syntax and lexical bans | `scripts/check_google_rules.py` | Report confirmed findings. |
| Documentation and design | Agent judgment plus supplemental checker | Inspect every public and private documentable symbol, including summary, `Args`, `Returns`/`Yields`, and `Raises` sections. |

## Important local policy

The guide's Pylint instructions are not executable requirements here. Ruff is
the repository's lint and formatting tool, and `pymake` is the required task
wrapper. Never install or run Pylint to satisfy this audit.

The repository's Ruff configuration intentionally ignores some upstream rules,
including line length and certain docstring rules. The agent must therefore
review those Google-style requirements independently rather than treating a
passing Ruff run as proof of compliance.

## Hard versus judgment findings

Treat syntax errors, relative imports, wildcard imports, semicolons, explicit
line continuations, disallowed type comments, and `typing.Text` as
deterministic candidates. Treat broad exceptions, assertions, mutable globals,
long lines, long functions, nested definitions, and legacy typing aliases as
review items unless repository context proves a direct violation. Missing or
incomplete documentation for documentable public or private symbols is a
strict audit finding under this skill's project policy. Verify a complete
first-line summary, `Args:` for meaningful parameters, `Returns:` for returned
values, `Yields:` for generators, and `Raises:` when exceptions are part of the
contract.

## Scope

Exclude `node_modules`, `.venv`, caches, build output, vendored code, generated
sources, and `.agents` by default. Include tests by default. Record exclusions
and accepted exceptions in the audit report.
