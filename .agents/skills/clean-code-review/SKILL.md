---
name: clean-code-review
description: Perform a read-only, catalog-driven review of an exact Git diff for Clean Code practices, design-pattern opportunities, Python-specific hazards, and prioritized actionable findings.
---

# Clean Code Review

Emphasize good coding practices through a focused, read-only review of the
exact change. Complement the broader `review-change` skill without modifying
code.

## Review contract

- The target branch argument is optional.
- Run all five steps in order. Do not invent findings.
- Cite catalog IDs verbatim from the lists below.

## Step 1 — Ingest

Read the complete diff before analyzing it. It contains both the committed
changes versus the base (three-dot `base...HEAD`) and working-tree changes
(staged plus unstaged).

Resolve the base branch from the optional argument. If it is absent, use the
symbolic remote HEAD, then `origin/main`, then `main`, and fail clearly if the
result does not resolve. Collect both statistics and full `-U10` diffs:

```bash
BASE="$1"
if [ -z "$BASE" ]; then
  BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed "s@^refs/remotes/@@")
  [ -z "$BASE" ] && BASE="origin/main"
  git rev-parse "$BASE" >/dev/null 2>&1 || BASE="main"
fi
if ! git rev-parse "$BASE" >/dev/null 2>&1; then
  echo "ERROR: base $BASE not found. Pass an explicit target branch."
  exit 1
fi
echo "===== BASE: $BASE ====="
echo
echo "----- Stat (committed vs $BASE) -----"
git diff --stat "$BASE"...HEAD || true
echo
echo "----- Stat (working tree, staged+unstaged) -----"
git diff --stat HEAD || true
echo
echo "===== Committed diff (vs $BASE, -U10) ====="
git diff -U10 "$BASE"...HEAD || true
echo
echo "===== Working-tree diff (staged + unstaged, -U10) ====="
git diff -U10 HEAD || true
```

Use the host platform's repository inspection tools to perform the equivalent
operations when the shell syntax above is unavailable. Preserve the selected
base and both diff sources in the report.

## Step 2 — Classify

Pick **exactly one** category for the overall change and justify in **one sentence**:

- `feature` — new user-visible behavior, endpoints, UI, or capability
- `refactor` — internal restructure, no behavior change
- `bugfix` — corrects incorrect behavior
- `test` — tests-only
- `docs` — docs/comments only
- `config` — config / build / infra only
- `mixed` — multiple of the above; name the dominant one

## Step 3 — Weight the lens

Decide whether to emphasize **Clean Code**, **Gang of Four**, or **Mixed**.
State your choice and a one-sentence rationale.

Heuristic:

- Diff introduces new classes / hierarchies / abstractions / extension points → **Gang of Four lens**.
- Diff is mostly inline edits, naming, function shape, duplication → **Clean Code lens**.
- Both → **Mixed**.

### Clean Code reminder (Robert C. Martin, 2008)

- **Functions**: small, do one thing, one level of abstraction (G34), ≤3 args (F1), no boolean flag args (F3), no output args (F2).
- **Names**: reveal intent (N1), unambiguous (N4), longer for longer scopes (N5), describe side effects (N7).
- **Comments**: explain *why* not *what*; delete obsolete (C2), redundant (C3), commented-out (C5).
- **General**: duplication is the worst smell (G5); polymorphism over switch (G23); encapsulate conditionals (G28); avoid Law-of-Demeter violations (G36); replace magic numbers with named constants (G25).
- **Tests**: F.I.R.S.T. — Fast, Independent, Repeatable, Self-validating, Timely; test boundary conditions (T5).

### Gang of Four reminder (Gamma/Helm/Johnson/Vlissides, 1994; design smells from Martin)

- **23 patterns** in three groups:
  - **Creational**: Abstract Factory, Builder, Factory Method, Prototype, Singleton.
  - **Structural**: Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy.
  - **Behavioral**: Chain of Responsibility, Command, Interpreter, Iterator, Mediator, Memento, Observer, State, Strategy, Template Method, Visitor.
- **Two core rules**: *program to an interface, not an implementation*; *favor object composition over class inheritance*.
- **SOLID**: SRP, OCP, LSP, ISP, DIP.
- **Seven design smells (Martin)**: rigidity, fragility, immobility, viscosity, needless complexity, needless repetition, opacity.
- **Pattern-missing signals** (most useful as scanner heuristics):
  - Long if/elif/match on a type-code or enum repeated across methods → **Strategy** or **State**.
  - Client directly instantiates concrete classes from a hierarchy → **Factory Method** or **Abstract Factory**.
  - Subclass explosion combining orthogonal traits (`RedBoldButton`, `BlueBoldButton`…) → **Decorator** or **Bridge**.
  - Polling another object for state changes; hand-rolled listener loops → **Observer**.
  - Two near-identical methods differing in 1–2 steps → **Template Method**.
  - Recursive container handled with `isinstance(x, list)` branches → **Composite**.
  - Inline call-translation to a foreign API surface → **Adapter**.
  - Ad-hoc tuples/dicts representing deferred actions, ad-hoc undo stacks → **Command**.
  - Index-based traversal of a custom collection (`for i in range(c.size())`) → **Iterator**.
  - Clients reach into many internals of one subsystem → **Facade**.

## Step 4 — Analyze

Walk every hunk. For each issue you find, cite **exactly one** catalog ID from
the lists below. Quote the smallest possible code excerpt. Give a one-sentence
why and a one-sentence fix. Do not invent IDs that are not in this list.

### Clean Code IDs (language-agnostic)

- **CC.C1** Inappropriate Information (non-technical info in comments)
- **CC.C2** Obsolete Comment (doesn't match the code)
- **CC.C3** Redundant Comment (restates what the code says)
- **CC.C5** Commented-Out Code
- **CC.F1** Too Many Arguments (>3)
- **CC.F2** Output Arguments (params mutated as outputs)
- **CC.F3** Flag Arguments (boolean param → function does >1 thing)
- **CC.F4** Dead Function (never called)
- **CC.G5** Duplication (most important smell)
- **CC.G6** Code at Wrong Level of Abstraction
- **CC.G8** Too Much Information (overly wide interface)
- **CC.G9** Dead Code (unreachable branches / unused symbols)
- **CC.G11** Inconsistency (same idea expressed two ways)
- **CC.G12** Clutter (empty ctors, unused vars, useless comments)
- **CC.G14** Feature Envy (method uses another class's data more than its own)
- **CC.G15** Selector Arguments (magic flags that change behavior)
- **CC.G16** Obscured Intent (magic numbers, dense expressions, cryptic names)
- **CC.G19** Use Explanatory Variables (break dense expressions into named intermediates)
- **CC.G20** Function Names Should Say What They Do
- **CC.G23** Prefer Polymorphism to If/Else or Switch/Case
- **CC.G25** Replace Magic Numbers with Named Constants
- **CC.G28** Encapsulate Conditionals (extract booleans into named predicates)
- **CC.G29** Avoid Negative Conditionals
- **CC.G30** Functions Should Do One Thing (SRP at function level)
- **CC.G34** Functions Should Descend Only One Level of Abstraction
- **CC.G36** Avoid Transitive Navigation (Law of Demeter)
- **CC.N1** Choose Descriptive Names
- **CC.N4** Unambiguous Names
- **CC.N5** Use Long Names for Long Scopes
- **CC.N7** Names Should Describe Side-Effects
- **CC.T1** Insufficient Tests
- **CC.T5** Test Boundary Conditions
- **CC.T9** Tests Should Be Fast

### Gang of Four IDs — missing-pattern signals

- **GOF.STRATEGY-MISSING** — long if/elif/match on type-code or enum, repeated across methods.
- **GOF.FACTORY-MISSING** — client `new`s concrete classes from a hierarchy.
- **GOF.DECORATOR-MISSING** — subclass explosion combining orthogonal traits.
- **GOF.OBSERVER-MISSING** — polling, or hand-rolled `for listener in listeners`.
- **GOF.TEMPLATE-MISSING** — two near-identical methods differing in 1–2 steps.
- **GOF.COMPOSITE-MISSING** — recursive container w/ `isinstance(x, list)` branches.
- **GOF.ADAPTER-MISSING** — inline call-translation to a foreign API.
- **GOF.COMMAND-MISSING** — ad-hoc tuples/dicts as deferred actions; ad-hoc undo stacks.
- **GOF.ITERATOR-MISSING** — `for i in range(c.size())` over a custom collection.
- **GOF.FACADE-MISSING** — clients touch many internals of one subsystem.

### Gang of Four IDs — design smells (Martin, *Agile Software Development*)

- **DS.RIGIDITY** — one change cascades widely
- **DS.FRAGILITY** — changes break unrelated parts
- **DS.IMMOBILITY** — components hard to extract for reuse
- **DS.VISCOSITY** — hacks are easier than correct fixes
- **DS.NEEDLESS-COMPLEXITY** — infrastructure not justified by current need
- **DS.NEEDLESS-REPETITION** — same logic in multiple places
- **DS.OPACITY** — hard to understand

### Python-specific IDs (apply only to `.py` files; tool codes for cross-reference)

- **PY.MUTABLE-DEFAULT** — `def f(x=[])` / `={}` shares one object across calls (B006)
- **PY.CALL-IN-DEFAULT** — `def f(x=time.now())` evaluated once at def-time (B008)
- **PY.BARE-EXCEPT** — `except:` swallows `KeyboardInterrupt`/`SystemExit` (E722)
- **PY.BROAD-EXCEPT** — `except Exception:` hides bugs (BLE001)
- **PY.EXCEPT-PASS** — silent swallow (S110 / TRY203)
- **PY.RAISE-WITHOUT-FROM** — `raise X()` in except loses chain (B904)
- **PY.NONE-EQ** — `== None` instead of `is None` (E711)
- **PY.BOOL-EQ** — `== True` / `== False` (E712)
- **PY.TYPE-EQ** — `type(x) == T` instead of `isinstance` (E721)
- **PY.RANGE-LEN** — `for i in range(len(x))` (PLR1736)
- **PY.STAR-IMPORT** — `from x import *` (F403)
- **PY.UNUSED-IMPORT** (F401)
- **PY.UNUSED-VAR** (F841)
- **PY.LAMBDA-NAMED** — `f = lambda: ...` (E731)
- **PY.AMBIG-NAME** — `l`, `O`, `I` (E741)
- **PY.BUILTIN-SHADOW** — rebinding `list`, `dict`, `id`, etc. (A001/A002)
- **PY.MUTABLE-CLASS-ATTR** — `class C: items = []` (RUF012)
- **PY.FILE-NO-WITH** — open() without context manager (SIM115)
- **PY.EVAL** — `eval()` on user input (S307)
- **PY.EXEC** — `exec()` (S102)
- **PY.ASSERT-RUNTIME** — `assert` for runtime validation (stripped under `-O`) (S101)
- **PY.SHELL-TRUE** — `subprocess(..., shell=True)` (S602)
- **PY.PICKLE-LOAD** — `pickle.load` on untrusted data (S301)
- **PY.YAML-LOAD** — `yaml.load` without `SafeLoader` (S506)
- **PY.LATE-BIND** — late-binding closure in loop (B023)
- **PY.IS-LITERAL** — `is` with non-singleton literal (F632)
- **PY.UNUSED-LOOP-VAR** — loop variable never used (B007)
- **PY.PRINT-IN-LIB** — `print()` in non-CLI library code (T201)
- **PY.BLOCKING-IN-ASYNC** — blocking I/O inside `async def` (ASYNC101)
- **PY.DICT-KEYS-ITER** — `for k in d.keys():` (SIM118)
- **PY.LOG-NO-EXC** — `except: logger.error(...)` without `.exception` (TRY400)

## Step 5 — Prioritize & report

### Severity definitions

- **BLOCKER** — security, correctness, data-loss, or runtime-crash risk
- **HIGH** — clearly wrong; will regress maintainability or behavior
- **MEDIUM** — design weakness worth fixing now
- **LOW** — minor; in-passing fix
- **NIT** — style preference, no real cost

Sort findings by severity (desc), then by file path. Emit exactly this structure:

````markdown
# Clean Code Review Report
**Base:** `<BASE>`
**Classification:** `<feature|refactor|bugfix|test|docs|config|mixed>`
**Primary lens:** `<Clean Code | Gang of Four | Mixed>`

## Summary
- Files changed: N
- Findings: X blocker, Y high, Z medium, W low, V nit
- Top risk: <one sentence>

## Findings

### [BLOCKER] `PY.BARE-EXCEPT` — `path/file.py:142`
```python
<smallest meaningful excerpt>
```
**Why:** <one sentence>
**Fix:** <one sentence>

### [HIGH] `GOF.STRATEGY-MISSING` — `path/file.py:55-90`
...

## Synthesis
<one paragraph: dominant theme of the diff and the top 3 actions to take before merge>
````

If the diff has no findings, emit the same structure with an empty Findings
section and an explicit `No catalog findings on this diff.` line, plus the
Synthesis paragraph.

Begin with Step 1 when this skill is invoked.
