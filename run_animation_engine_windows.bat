@echo off
setlocal EnableExtensions

cd /d "%~dp0"
echo [Animation-Engine] Working directory: %CD%

:: ── Locate a Python interpreter ───────────────────────────────────────────────
set "PYTHON_EXE="
set "PYTHON_ARGS="
where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
)
if "%PYTHON_EXE%"=="" (
    where python >nul 2>&1
    if not errorlevel 1 set "PYTHON_EXE=python"
)

if "%PYTHON_EXE%"=="" (
    echo [Animation-Engine] ERROR: Neither 'py' nor 'python' was found.
    echo Install Python 3.10+ from https://www.python.org/downloads/ and try again.
    pause
    exit /b 1
)

:: ── Verify Python version is 3.10+ ────────────────────────────────────────────
set "PY_MAJOR="
set "PY_MINOR="
for /f "tokens=2" %%V in ('"%PYTHON_EXE%" %PYTHON_ARGS% --version 2^>^&1') do (
    for /f "tokens=1,2 delims=." %%A in ("%%V") do (
        set "PY_MAJOR=%%A"
        set "PY_MINOR=%%B"
    )
)

if not defined PY_MAJOR (
    echo [Animation-Engine] ERROR: Could not determine Python version. Install Python 3.10+.
    pause
    exit /b 1
)
if not defined PY_MINOR (
    echo [Animation-Engine] ERROR: Could not determine Python minor version. Install Python 3.10+.
    pause
    exit /b 1
)
if %PY_MAJOR% lss 3 goto :version_error
if %PY_MAJOR% gtr 3 goto :version_ok
if %PY_MINOR% lss 10 goto :version_error
goto :version_ok

:version_error
echo [Animation-Engine] ERROR: Python 3.10+ required (found %PY_MAJOR%.%PY_MINOR%).
echo Install Python 3.10+ from https://www.python.org/downloads/ and try again.
pause
exit /b 1

:version_ok
:: ── Create virtual environment if needed ──────────────────────────────────────
if not exist ".venv\Scripts\python.exe" (
    echo [Animation-Engine] Creating virtual environment...
    if not "%PYTHON_ARGS%"=="" (
        "%PYTHON_EXE%" %PYTHON_ARGS% -m venv .venv
    ) else (
        "%PYTHON_EXE%" -m venv .venv
    )
    if errorlevel 1 (
        echo [Animation-Engine] ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: ── Activate virtual environment ──────────────────────────────────────────────
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [Animation-Engine] ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

:: ── Install / update dependencies ─────────────────────────────────────────────
echo [Animation-Engine] Updating pip...
python -m pip install --upgrade pip --progress-bar off
echo [Animation-Engine] Installing/updating dependencies...
python -m pip install -e ".[dev]"
if errorlevel 1 (
    echo [Animation-Engine] ERROR: Dependency installation failed.
    pause
    exit /b 1
)

:: ── Launch selected mode ───────────────────────────────────────────────────────
if /I "%~1"=="--editor" (
    echo [Animation-Engine] Launching editor GUI (PS2 preview)...
    python -m animation_engine.editor.main
) else (
    echo [Animation-Engine] Launching production GUI...
    echo [Animation-Engine] Tip: pass --editor to launch the PS2 preview editor window.
    python -m animation_engine.cli launch-production-gui
)
set EXIT_CODE=%errorlevel%

if %EXIT_CODE% neq 0 (
    echo [Animation-Engine] GUI exited with code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
