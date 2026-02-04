@echo off
REM Jill - Windows Setup
REM Uses Python setup wizard for better cross-platform experience.

cd /d "%~dp0"

echo === Jill Setup ===
echo.

REM Check Python - try py launcher first (doesn't need PATH), then python
set PYTHON_CMD=
py --version >nul 2>&1 && set PYTHON_CMD=py
if not defined PYTHON_CMD python --version >nul 2>&1 && set PYTHON_CMD=python

if not defined PYTHON_CMD (
    echo [x] Python is required.
    echo     Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check Java
java -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [x] Java 17+ is required for Lavalink.
    echo.
    echo     1. Download from: https://adoptium.net/temurin/releases/
    echo        Select: Windows x64, JRE, version 17+, .msi installer
    echo     2. Run the installer
    echo     3. Restart this terminal and try again
    pause
    exit /b 1
)

REM Create venv if missing
if not exist "venv" (
    echo Creating virtual environment...
    %PYTHON_CMD% -m venv venv
) else (
    echo [+] Virtual environment exists
)

REM Install dependencies
echo Installing dependencies...
venv\Scripts\python.exe -m pip install -q -r requirements.txt

REM Run Python setup wizard
echo.
venv\Scripts\python.exe -m setup
if %errorlevel% neq 0 (
    echo.
    echo Setup did not complete successfully.
    pause
    exit /b 1
)

pause
