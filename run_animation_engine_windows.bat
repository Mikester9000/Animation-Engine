@echo off
setlocal

cd /d "%~dp0"
echo [Animation-Engine] Working directory: %CD%

set "PYTHON_EXE="
set "PYTHON_ARGS="
where py >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
) else (
    where python >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_EXE=python"
    )
)

if "%PYTHON_EXE%"=="" (
    echo [Animation-Engine] ERROR: Neither 'py' nor 'python' was found.
    echo Install Python 3.10+ from https://www.python.org/downloads/ and try again.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [Animation-Engine] Creating virtual environment...
    if "%PYTHON_ARGS%"=="" (
        "%PYTHON_EXE%" -m venv .venv
    ) else (
        "%PYTHON_EXE%" %PYTHON_ARGS% -m venv .venv
    )
    if %errorlevel% neq 0 (
        echo [Animation-Engine] ERROR: Failed to create virtual environment.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"
if %errorlevel% neq 0 (
    echo [Animation-Engine] ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

echo [Animation-Engine] Installing/updating dependencies...
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
if %errorlevel% neq 0 (
    echo [Animation-Engine] ERROR: Dependency installation failed.
    pause
    exit /b 1
)

set MODE=%~1
if /I "%MODE%"=="--editor" (
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
