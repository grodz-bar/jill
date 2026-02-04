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
    echo [x] python is required.
    echo     download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo [+] python found

REM Check Java
java -version >nul 2>&1
if %errorlevel% neq 0 (
    echo [x] java 17+ is required for lavalink.
    echo.
    echo     1. download from: https://adoptium.net/temurin/releases/
    echo        select: Windows x64, JRE, version 17+, .msi installer
    echo     2. run the installer
    echo     3. restart this terminal and try again
    pause
    exit /b 1
)
echo [+] java found

REM Check if existing venv is broken (missing python.exe or won't run)
if exist "venv" (
    if not exist "venv\Scripts\python.exe" (
        echo rebuilding virtual environment...
        rd /s /q "venv" 2>nul
        if exist "venv" rd /s /q "venv" 2>nul
        if exist "venv" (
            echo [x] could not delete venv folder. close any programs using it.
            pause
            exit /b 1
        )
    ) else (
        venv\Scripts\python.exe --version >nul 2>&1
        if errorlevel 1 (
            echo rebuilding virtual environment...
            rd /s /q "venv" 2>nul
            if exist "venv" rd /s /q "venv" 2>nul
            if exist "venv" (
                echo [x] could not delete venv folder. close any programs using it.
                pause
                exit /b 1
            )
        )
    )
)

REM Create venv if missing (or was just deleted above)
if not exist "venv" (
    echo creating virtual environment...
    %PYTHON_CMD% -m venv venv
) else (
    echo [+] virtual environment found
)

REM Install dependencies
echo installing dependencies...
venv\Scripts\python.exe -m pip install -q -r requirements.txt

REM Run Python setup wizard
echo.
venv\Scripts\python.exe -m setup
if %errorlevel% neq 0 (
    echo.
    echo setup did not complete successfully.
    pause
    exit /b 1
)

pause
