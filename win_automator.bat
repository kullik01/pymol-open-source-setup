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
REM "setup" creates .venv with Python 3.11 and installs requirements.txt
if /i "%~1"=="setup" (
    where uv >nul 2>nul || (
        echo uv is missing, see https://docs.astral.sh/uv/getting-started/installation/ 1>&2
        exit /b 1
    )
    uv venv --allow-existing --python 3.11 .venv || exit /b 1
    uv pip install --python .venv\Scripts\python.exe -r requirements.txt || exit /b 1
    exit /b 0
)
if not exist .\.venv\Scripts\python.exe (
    echo The virtual environment does not exist yet. Create it with: win_automator.bat setup 1>&2
    exit /b 1
)
.\.venv\Scripts\python.exe .\automations\my_automator.py %*
exit /b %errorlevel%
