# Windows x86_64 Standalone Bundle Proof of Concept

**Status:** Accepted
**Owner:** Project developer
**Reviewer:** Independent reviewer subagent
**Risk:** Normal
**Base commit:** `ffbe888a06d8a7464cd5239f88b99a1bc803a4e5`
**Brief/design:** Accepted migration brief and technical design in the planning conversation

## Focus card

- **Change:** Add a reproducible Windows x86_64 bundle builder using CPython 3.11.15, locked PyMOL/Qt binary wheels, the existing repository overlays, a provenance manifest, a relative launcher, and the x64 ZIP/Inno wrapper outputs.
- **Success:** On Windows, one command builds a bundle that can be moved and launch a headless PyMOL smoke command without host Python/virtualenv, uv, network, cx_Freeze, or `VC_redist.x64.exe`.
- **Non-goals:** Windows x86 packaging; macOS/Linux work; installer shortcut validation; GUI acceptance; removal of cx_Freeze; Python 3.12; release publication. Installer execution/install remains human-owned.
- **Allowed scope:** `pyproject.toml`, generated `uv.lock`, `pymakefile.py`, new bundle-support code under `scripts/python/`, Windows build inputs under `os_specific/windows/`, tests, and directly affected documentation.
- **Validation:** Locked and binary-only dependency resolution; unit tests for layout, launcher, overlay, and manifest; relocated offline headless launch; Windows import/DLL evidence; existing test/lint/format checks.
- **Stop if:** PyMOL/Qt cannot run on the runtime; required DLLs cannot legally be bundled; source URL/hash evidence is unavailable; the launcher requires an absolute path, network, or external VC++ installer; or scope must expand to installers/other platforms.
- **Work style:** Bounded delegated implementation followed by independent fresh-context review.

## Repository evidence

- `pymakefile.py:279-298`: current `build_app` mutates an active virtualenv and invokes cx_Freeze.
- `pymakefile.py:227-249`: existing PyMOL, Qt, CSS, logo, and splash overlays must be preserved.
- `os_specific/windows/setup_build_exe.py:5-61`: current Windows packaging is cx_Freeze-based.
- `os_specific/windows/inno_setup/setup_x64.iss:42-51`: the x64 Inno wrapper consumes the standalone bundle staging tree; installer execution/install and shortcut validation remain out of scope for builder validation.
- `pyproject.toml:1-25`: project metadata currently lacks runtime dependency declarations and lock configuration.
- `uv 0.12.3`: matches the committed lock metadata and Windows workflow pin; it supports locked export and binary-only installation; standalone runtimes are installed natively.
- The supported Windows flow invokes `python pymakefile.py build_windows_bundle`, `python pymakefile.py package_windows_bundle`, and `python pymakefile.py prepare_inno_setup`; the x64 Inno script is compiled separately with ISCC.
- All six overlays target `runtime/python/Lib/site-packages/...`: `pmg_qt/pymol_qt_gui.py`, `pymol/base.css`, `pymol/__init__.py`, `pymol/startup_wrapper.py`, `pymol/data/pymol/icons/alt_logo.png`, and `pymol/data/pymol/splash.png`.
- Binary-only dry-run resolution succeeded for PyMOL 3.1.0.4, NumPy 1.26.4, and PyQt5 dependencies on Windows CPython 3.11.

## Proposed change

1. Declare runtime and build/test dependency groups and generate a committed hash-bearing `uv.lock`, pinning CPython 3.11.15 as bundle configuration.
2. Add focused bundle assembly that installs the standalone runtime, installs locked binary-only dependencies, applies the existing overlays, discovers the runtime without hard-coded patch-directory names, generates a relative launcher, and writes `manifest.json` with target, runtime/dependency source URLs and hashes, lock identity, Git commit, timestamp, and CI metadata when present.
3. Add a Windows-only `pymake` task that fails rather than falling back to cx_Freeze, a virtualenv, network launch behavior, or VC++ installation.
4. Add unit tests for manifest content, overlay inventory, runtime/launcher relativity, and task delegation, plus a relocated/offline headless smoke command.
5. Preserve existing cx_Freeze implementation only where still used, while making the standalone Windows x64 ZIP and Inno wrapper the supported packaging path; Windows x86 CI/package coverage is retired.

## Validation

- `uv lock` (using uv 0.12.3)
- `uv export --locked --format requirements.txt --output-file <temporary path>`
- `python pymakefile.py build_windows_bundle`
- `python pymakefile.py package_windows_bundle`
- `python pymakefile.py prepare_inno_setup`
- ISCC compilation of `os_specific/windows/inno_setup/setup_x64.iss` (without installer execution/install)
- Relocated/offline bundled launcher with a minimal `-cq` PyMOL command
- Windows DLL/import inspection
- `git diff --check`

## Risks and rollout

- Native launch and DLL failures stop expansion to installers and other platforms.
- Missing provenance metadata fails the build rather than producing an incomplete manifest.
- Existing cx_Freeze outputs remain unchanged; this slice has no release rollout.
- macOS/Linux compatibility remains unproven until native follow-up work.

## Decisions

- CPython **3.11.15** is approved for the first bundle.
- Upstream-download-at-build-time provenance is approved.
- Final artifacts must operate offline after construction.
- Windows x86_64 is the supported standalone implementation target.
- Windows x86_64 ZIP and Inno wrapper conversion are explicitly authorized in scope; Windows x86 CI/package coverage is retired and must not be restored. The retained `setup_x86.iss` and private legacy staging helper are historical references only; no active task or workflow invokes them.
- Installer execution, installation, and shortcut validation remain human-owned acceptance activities.
- Implementation must use the builder-reviewer subagent pattern.

## Completion evidence

- **Delivered:** Windows x86_64 standalone-bundle proof of concept.
- **Changed:** Exact file list returned by the builder.
- **Head snapshot:** Exact builder snapshot.
- **Validation:** Exact commands and outcomes from the builder evidence receipt.
- **Acceptance:** Bundle assembly, overlays, manifest, relative launcher, relocated offline smoke test, and DLL/import audit mapped individually.
- **Scope deviations:** None unless explicitly reported.
- **Known limitations:** Installer execution/install and shortcut validation remain human-owned; GUI test, macOS/Linux work, and any remaining cx_Freeze retirement remain follow-ups. Windows x86 CI/package coverage is retired.
- **Review state:** Pending independent reviewer result.
