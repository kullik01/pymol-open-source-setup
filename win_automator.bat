@echo off
REM A* -------------------------------------------------------------------
REM B* A simple wrapper script for running automation tasks more smoothly
REM -* without needing to know the exact python interpreter path
REM C* Copyright 2026 by Martin Urban.
REM D* -------------------------------------------------------------------
REM E* It is unlawful to modify or remove this copyright notice.
REM F* -------------------------------------------------------------------
REM G* Please see the accompanying LICENSE file for further information.
REM H* -------------------------------------------------------------------
REM I* Additional authors of this source file include:
REM -* Hannah Kullik
REM -*
REM -*
REM Z* -------------------------------------------------------------------
cd /d "%~dp0"
if not exist .\.venv\Scripts\python.exe (
    echo Virtual environment does not exist yet! Please create it first, see README.md. 1>&2
    exit /b 1
)
.\.venv\Scripts\python.exe .\automations\my_automator.py %*
exit /b %errorlevel%
