# PyMOL quits without crashing (issue #51)

**Goal:** PyMOL-Open-Source quits with its exit code instead of a segfault and core dump, on every way of quitting, and the version becomes 3.2.0.3+2 for the next draft release.

**Architecture:** PyMOL quits through `_cmd.quit` → `PExit` → C `exit()` inside the Qt event loop; `exit()` runs shiboken's static `BindingManager` destructor, which crashes on wrappers of Qt objects Qt already freed. `execapp()` in `edited/pmg_qt/pymol_qt_gui.py` replaces `pymol._cmd.quit` (Linux, macOS) with a function that flushes stdout/stderr and calls `os._exit(code)`; `pymol.internal._quit` still flushes and closes the log and joins the reaper first. Menu Quit (`QApplication.quit()`) closes the window first in Qt 6, so it runs `closeEvent` → `cmd.quit`. When `app.exec()` returns anyway (`QApplication.exit(n)`), `execapp()` waits at most 5 s for PyMOL's API lock and quits the same way with the event loop's exit code.

**Spec:** https://github.com/kullik01/pymol-open-source-setup/issues/51

## Global Constraints

- `edited/` holds upstream PyMOL files with marked edits (`BEGIN EDITED CODE SEGMENT`).
- The version lives only in `pyproject.toml`; a tag `v<version>` builds a draft release.

## Review Focus

- Embedded PyMOL instances (`pymol2`, `no_quit`) must keep PyMOL's own quit: the replacement passes through every `_COb` other than `pymol.cmd._COb`.
- Exit code: `cmd.quit(n)` must still end with `n` (checked with 0, 3 and 5).
- Windows keeps PyMOL's own quit: DLL destructors run at `ExitProcess` even after `os._exit`, so the change would not help there.

## Scope

edited/pmg_qt/pymol_qt_gui.py
tests/run_smoke_test.sh
pyproject.toml
.opp/plans/fix/quit-crash.md

## Done

The reproduction of issue #51 exits with code 0 on every quit path (cmd.quit, window close, menu Quit), and the GUI and headless smoke tests pass with the frozen app.

## Non-goals

- Fixing the crash in shiboken or upstream PyMOL (worth reporting upstream separately).
- Changing Windows behaviour, which could not be tested here.
- Freeing PyMOL's memory before the process ends (`PExit` only frees memory; the OS reclaims it).

## Edge cases

- `cmd.quit` from a non-GUI thread (startup scripts, smoke test): queued `cmd._quit` reaches the replaced `_cmd.quit`.
- Unflushed Python output on a pipe is flushed before `os._exit`; a missing (`None`) or closed stream is skipped.
- C stdio buffers (native `printf` without `fflush`) are flushed with `fflush(NULL)`, as C `exit()` did.
- `QApplication.exit(n)` while another thread holds the API lock: quits after at most 5 s instead of hanging (upstream hung).

## Acceptance criteria

- The issue's reproduction script exits 0 with no core dump when quitting via `cmd.quit`, `window.close()` and `confirm_quit`.
- `cmd.quit(n)` ends the process with exit code `n`.
- A PyMOL log opened with `log_open` holds every command after quitting.
- `./automator.sh test` and `./automator.sh test gui` pass with the frozen app.
- `tests/run_smoke_test.sh` fails at once, without a retry, when the smoke test passed but PyMOL crashed on quit (exit 139 or 134).
- `pyproject.toml` has version `3.2.0.3+2`.

## Verification

- Before the fix: the reproduction under Xvfb with the venv's PyMOL crashed (exit 139) in 4 of 5 runs on each of cmd.quit, window close and menu Quit.
- After the fix, with `edited/pmg_qt` overlaid on the venv's `pmg_qt`: 10 of 10 exit 0 on each path; `REPRO_CODE=3` exits 3.
- Edge script (log_open, unflushed `sys.stdout.write`, `cmd.quit(5)` from the script thread): exit 5, the line printed, the log complete.
- `./automator.sh build app`, then `./automator.sh test` and `./automator.sh test gui` print `SMOKE TEST OK`; the frozen app's reproduction exits 0 on all three paths (5 runs each).
- `QApplication.exit(4)` with a thread holding the API lock: exit 4 after about 5 s (without the fix: hangs); C `printf` output reaches the pipe.
- `tests/run_smoke_test.sh --gui` with a stub that prints SMOKE TEST OK: exit 139 fails at once, 0 passes, 1 fails after two attempts.
- `uvx pre-commit run --all-files` passes.
