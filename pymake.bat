@echo off
if not exist "%~dp0.venv\Scripts\python.exe" (
    echo Virtual environment does not exist. Create .venv and install the platform requirements first.
    exit /b 1
)
"%~dp0.venv\Scripts\python.exe" "%~dp0pymakefile.py" %*
exit /b %ERRORLEVEL%
