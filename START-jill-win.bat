@echo off
REM Jill Launcher - Windows
REM Calls PowerShell script for health-checked startup

cd /d "%~dp0"

REM Check if setup was run
if not exist "venv\Scripts\python.exe" (
    echo [x] Virtual environment not found.
    echo     Run setup-jill-win.bat first.
    pause
    exit /b 1
)

REM Check Java and capture its path (PowerShell may have different PATH)
where java >nul 2>&1
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
for /f "delims=" %%i in ('where java') do set "JAVA_PATH=%%i" & goto :found_java
:found_java

REM Launch PowerShell script (handles ExecutionPolicy, uses JAVA_PATH if needed)
powershell -ExecutionPolicy Bypass -File "%~dp0setup\start.ps1"
if %errorlevel% neq 0 (
    echo.
    echo Startup failed. See error above.
    pause
)
