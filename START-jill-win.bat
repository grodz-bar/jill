@echo off
REM Jill Launcher - Windows
REM Calls PowerShell script for health-checked startup

cd /d "%~dp0"

REM Check if setup was run
if not exist "venv\Scripts\python.exe" (
    powershell -Command "Write-Host '[x] virtual environment not found.' -ForegroundColor Red"
    echo     run: setup-jill-win.bat
    pause
    exit /b 1
)

REM Check if venv is broken (e.g., Python was uninstalled)
venv\Scripts\python.exe --version >nul 2>&1
if errorlevel 1 (
    powershell -Command "Write-Host '[x] virtual environment is broken.' -ForegroundColor Red"
    echo     run: setup-jill-win.bat
    pause
    exit /b 1
)

REM Check Java and capture its path (PowerShell may have different PATH)
where java >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Write-Host '[x] java 17+ is required for lavalink.' -ForegroundColor Red"
    echo.
    echo     1. download from: https://adoptium.net/temurin/releases/
    echo        select: Windows x64, JRE, version 17+, .msi installer
    echo     2. run the installer
    echo     3. restart this terminal and try again
    pause
    exit /b 1
)
for /f "delims=" %%i in ('where java') do set "JAVA_PATH=%%i" & goto :found_java
:found_java

REM Launch PowerShell script (handles ExecutionPolicy, uses JAVA_PATH if needed)
powershell -ExecutionPolicy Bypass -File "%~dp0setup\start.ps1"
if %errorlevel% neq 0 (
    echo.
    powershell -Command "Write-Host '[x] startup failed. see error above.' -ForegroundColor Red"
    pause
    exit /b 1
)
