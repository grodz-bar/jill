@echo off
REM Jill - Windows Setup
REM Uses Python setup wizard for better cross-platform experience.

cd /d "%~dp0"

echo === jill setup ===
echo.

REM Check Python - try py launcher first (doesn't need PATH), then python
set PYTHON_CMD=
py --version >nul 2>&1 && set PYTHON_CMD=py
if not defined PYTHON_CMD python --version >nul 2>&1 && set PYTHON_CMD=python

if not defined PYTHON_CMD (
    powershell -Command "Write-Host '[x] Python is required.' -ForegroundColor Red"
    echo     download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
powershell -Command "Write-Host '[+] Python found' -ForegroundColor Green"

REM Check Java
java -version >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Write-Host '[x] Java 17+ is required for Lavalink.' -ForegroundColor Red"
    echo.
    echo     1. download from: https://adoptium.net/temurin/releases/
    echo        select: Windows x64, JRE, version 17+, .msi installer
    echo     2. run the installer
    echo     3. restart this terminal and try again
    pause
    exit /b 1
)
powershell -Command "Write-Host '[+] Java found' -ForegroundColor Green"

REM Check if existing venv is broken (missing python.exe, won't run, or no pip)
if exist "venv" (
    if not exist "venv\Scripts\python.exe" (
        powershell -Command "Write-Host '[!] Rebuilding virtual environment...' -ForegroundColor Yellow"
        rd /s /q "venv" 2>nul
        if exist "venv" rd /s /q "venv" 2>nul
        if exist "venv" (
            powershell -Command "Write-Host '[x] Could not delete venv folder. Close any programs using it.' -ForegroundColor Red"
            pause
            exit /b 1
        )
    ) else (
        venv\Scripts\python.exe -c "import pip" >nul 2>&1
        if errorlevel 1 (
            powershell -Command "Write-Host '[!] Rebuilding virtual environment...' -ForegroundColor Yellow"
            rd /s /q "venv" 2>nul
            if exist "venv" rd /s /q "venv" 2>nul
            if exist "venv" (
                powershell -Command "Write-Host '[x] Could not delete venv folder. Close any programs using it.' -ForegroundColor Red"
                pause
                exit /b 1
            )
        )
    )
)

REM Create venv if missing (or was just deleted above)
if not exist "venv" (
    powershell -Command "Write-Host '[.] Creating virtual environment...' -ForegroundColor Cyan"
    %PYTHON_CMD% -m venv venv
) else (
    powershell -Command "Write-Host '[+] Virtual environment found' -ForegroundColor Green"
)

REM Verify pip exists (some Python installs create venv without pip)
venv\Scripts\python.exe -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Write-Host '[.] Bootstrapping pip...' -ForegroundColor Cyan"
    venv\Scripts\python.exe -m ensurepip --default-pip >nul 2>&1
    if %errorlevel% neq 0 (
        powershell -Command "Write-Host '[x] Could not install pip in virtual environment.' -ForegroundColor Red"
        echo     delete the venv folder and re-run this script.
        echo     if that fails, reinstall python.
        pause
        exit /b 1
    )
)

REM Install dependencies
powershell -Command "Write-Host '[.] Installing dependencies...' -ForegroundColor Cyan"
venv\Scripts\python.exe -m pip install -q -r requirements.txt
if %errorlevel% neq 0 (
    powershell -Command "Write-Host '[x] Failed to install dependencies' -ForegroundColor Red"
    echo     check your internet connection and try again
    pause
    exit /b 1
)

REM Run Python setup wizard
echo.
venv\Scripts\python.exe -m setup
if %errorlevel% neq 0 (
    echo.
    powershell -Command "Write-Host '[x] Setup did not complete successfully.' -ForegroundColor Red"
    pause
    exit /b 1
)

pause
