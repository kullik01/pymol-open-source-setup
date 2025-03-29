REM A* -------------------------------------------------------------------
REM B* A simple wrapper script for running automation tasks more smoothly
REM -* without needing to know the exact python interpreter path
REM C* Copyright 2025 by Martin Urban.
REM D* -------------------------------------------------------------------
REM E* It is unlawful to modify or remove this copyright notice.
REM F* -------------------------------------------------------------------
REM G* Please see the accompanying LICENSE file for further information.
REM H* -------------------------------------------------------------------
REM I* Additional authors of this source file include:
REM -*
REM -*
REM -*
REM Z* -------------------------------------------------------------------
if exist .\.venv\Scripts\python.exe (
    .\.venv\Scripts\python.exe .\automations\my_automator.py %*
) else (
    echo Virtual environment does not exist yet! Please run run_automation.bat init
)
