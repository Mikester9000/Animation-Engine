@echo off
setlocal

cd /d "%~dp0"
echo [Animation-Engine] Working directory: %CD%

where py >nul 2>&1
if %errorlevel% neq 0 (
    echo [Animation-Engine] ERROR: Python launcher 'py' was not found.
    echo Install Python 3.10+ from https://www.python.org/downloads/ and try again.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [Animation-Engine] Creating virtual environment...
    py -3 -m venv .venv
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

echo [Animation-Engine] Launching production GUI...
python -m animation_engine.cli launch-production-gui
set EXIT_CODE=%errorlevel%

if %EXIT_CODE% neq 0 (
    echo [Animation-Engine] GUI exited with code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%

