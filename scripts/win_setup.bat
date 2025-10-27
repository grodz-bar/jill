@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Change to parent directory (project root)
cd /d "%~dp0.." || (
    echo ERROR: Unable to locate project root.
    pause
    exit /b 1
)

if exist scripts\win_setup.bat (
    REM Ensure we are really in project root by verifying requirements file
    if not exist requirements.txt (
        echo ERROR: Could not find requirements.txt in project root.
        pause
        exit /b 1
    )
)

echo ========================================
echo Jill Discord Bot - Setup Wizard
echo ========================================
echo.
echo This wizard will set up Jill in a few easy steps.
echo You can press Ctrl+C at any time to exit and run this again later.
echo.

REM STEP 0: PYTHON CHECK
echo Checking for Python...
for /f "tokens=*" %%p in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%p"
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo ERROR: Python not found
    echo Please install Python 3.11 or newer and add it to PATH.
    echo See 03-SETUP-Windows.txt for instructions.
    echo.
    pause
    exit /b 1
)

echo Found Python:
echo %PYTHON_VERSION%
echo.
python -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,11) else 1)" 2>nul
if errorlevel 1 (
    echo ERROR: Python 3.11 or newer is required. Found: %PYTHON_VERSION%
    echo Please upgrade Python and try again.
    echo.
    pause
    exit /b 1
)
echo.

echo ========================================
echo What This Setup Will Do
echo ========================================
echo.
echo - Create a Python virtual environment (venv)
echo - Install required dependencies (disnake, PyNaCl, python-dotenv)
echo - Ask you to configure your bot token and music folder
echo - Optionally convert audio files to .opus format
echo - Create a .env configuration file
echo.
set /p "CONTINUE=Do you want to continue? (Y/n): "
if /i "%CONTINUE%"=="n" (
    echo.
    echo Setup cancelled.
    pause
    exit /b 0
)
echo.

REM STEP 1: VIRTUAL ENVIRONMENT
if exist "venv\" (
    echo Virtual environment already exists, skipping creation...
) else (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
    timeout /t 2 /nobreak >nul
)
echo.

if not exist "venv\Scripts\activate" (
    echo ERROR: Virtual environment activation script not found.
    echo Please delete the venv folder and rerun this setup.
    pause
    exit /b 1
)
call venv\Scripts\activate
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

echo Installing dependencies...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo.
    echo ERROR: Failed to upgrade pip
    pause
    exit /b 1
)
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully.
timeout /t 2 /nobreak >nul
echo.

echo ========================================
echo Configuration
echo ========================================
echo.

if exist ".env" (
    echo WARNING: .env file already exists.
	echo.
    set /p "OVERWRITE=Do you want to overwrite it? (y/N): "
    for /f "tokens=1" %%A in ("!OVERWRITE!") do set "OVERWRITE=%%A"
    set "OVERWRITE=!OVERWRITE:~0,1!"
    if /i not "!OVERWRITE!"=="y" (
        echo.
        echo Setup cancelled. Your existing .env file was not modified.
        echo.
        pause
        exit /b 0
    )
    echo.
    echo Overwriting existing .env file...
	echo.
    timeout /t 2 /nobreak >nul
)

echo Step 1: Discord Bot Token
echo --------------------------
echo Enter your Discord bot token from the Discord Developer Portal.
echo See 02-Getting-Discord-Token.txt if you need help getting your token.
echo.
:ASK_TOKEN
set "BOT_TOKEN="
set /p "BOT_TOKEN=Bot Token: "
if "%BOT_TOKEN%"=="" (
    echo.
    echo ERROR: Bot token cannot be empty.
    echo Please enter your token.
    goto ASK_TOKEN
)
echo.
timeout /t 1 /nobreak >nul

echo.
echo Step 2: Music Folder Location
echo --------------------------
echo Where should Jill look for your music files?
echo.
echo Default location: music\ - inside Jill's folder
echo.
echo Options:
echo - Press Enter to use the default location (recommended for portability)
echo - Type a custom path (e.g., D:\Music\jill\)
echo - Type 'exit' to cancel setup
echo.
echo If the folder doesn't exist, this script will create it for you.
echo.
set "DEFAULT_PATH=0"
set /p "MUSIC_PATH=Music folder path: "
if /i "%MUSIC_PATH%"=="exit" (
    echo.
    echo Setup cancelled.
    pause
    exit /b 0
)
if "%MUSIC_PATH%"=="" (
    set "MUSIC_PATH=music"
    set "DEFAULT_PATH=1"
) else (
    set "MUSIC_PATH=!MUSIC_PATH:"=!"
)

if not "%MUSIC_PATH:~-1%"=="\" set "MUSIC_PATH=%MUSIC_PATH%\"

if not exist "%MUSIC_PATH%" (
    echo.
    echo Music folder does not exist. Creating: %MUSIC_PATH%
    mkdir "%MUSIC_PATH%" 2>nul
    if errorlevel 1 (
        echo WARNING: Could not create music folder automatically.
        echo Please create it manually before running the bot.
    ) else (
        echo Music folder created successfully.
        timeout /t 2 /nobreak >nul
    )
) else (
	timeout /t 1 /nobreak >nul
    echo Music folder found: %MUSIC_PATH%
)
echo.
timeout /t 1 /nobreak >nul
echo.
echo OPTIONAL STEP:
echo --------------------------
set "CONVERSION_SUCCESS=false"
echo Ready to convert and move your music files into !MUSIC_PATH! as .opus files.
echo.
echo In this step, we'll:
echo 1. Scan a folder for music files
echo 2. Convert them to .opus
echo 3. Make sure they're inside the music folder you set for Jill
echo 4. Delete the pre-conversion music files (IF you want)
echo Note: The subfolder structure will stay the exact same
echo.
echo.
set /p "CONVERT_FILES=Start the guided conversion now? (y/N): "
if /i "%CONVERT_FILES%"=="y" (
    call :RUN_CONVERSION
) else (
    echo Skipping conversion.
    timeout /t 2 /nobreak >nul
)
goto AFTER_CONVERSION

:RUN_CONVERSION
echo.
echo Checking for FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ERROR: FFmpeg is not installed or not in PATH.
    echo Please install FFmpeg and add it to PATH, or follow the manual conversion guide:
    echo See 03-SETUP-Windows.txt and 04-Converting-To-Opus.txt
    echo.
    echo Press any key to continue without conversion...
    pause >nul
    echo Skipping conversion.
    timeout /t 2 /nobreak >nul
    goto :EOF
)

echo FFmpeg found.
timeout /t 2 /nobreak >nul

:CONVERSION_GUIDE
echo.
echo ========================================
echo Conversion Overview
echo ========================================
echo We'll copy your audio into Jill's music folder so she can play it.
echo Destination (the folder you just configured): %MUSIC_PATH%
echo Folder structure is preserved ^(subfolders become playlists^).
echo.
echo Quick steps this helper will walk you through:
echo   1. Choose the file format we should look for.
echo   2. Point to the folder that holds your existing audio.
echo   3. We'll mirror that structure into %MUSIC_PATH% as .opus files.
echo.
timeout /t 1 /nobreak >nul

:ASK_SOURCE_FOLDER
echo.
echo -------- Step 1: Choose the audio format --------
set /p "FILE_FORMAT=What audio format are your files? (mp3/flac/wav/m4a/other): "
if "%FILE_FORMAT%"=="" set "FILE_FORMAT=mp3"
if /i "%FILE_FORMAT%"=="other" (
    set /p "FILE_FORMAT=Enter the file extension (without dot): "
)
for /f "tokens=1" %%A in ("!FILE_FORMAT!") do set "FILE_FORMAT=%%~A"
echo.
timeout /t 1 /nobreak >nul
echo -------- Step 2: Tell us where the originals live --------
set "SOURCE_FOLDER="
echo This is the folder we will read from before writing to %MUSIC_PATH%.
echo.
echo Enter the full folder path (for example: D:\Downloads\Albums\).
echo or
echo Press Enter to use Jill's music folder for both.
echo.
set /p "SOURCE_FOLDER=Source folder path: "
if "%SOURCE_FOLDER%"=="" (
    set "SOURCE_FOLDER=%MUSIC_PATH%"
    echo.
    echo Using your Jill music folder as both the source and destination.
    timeout /t 1 /nobreak >nul
)
timeout /t 1 /nobreak >nul

set "SOURCE_FOLDER=!SOURCE_FOLDER:"=!"
if not "%SOURCE_FOLDER:~-1%"=="\" set "SOURCE_FOLDER=%SOURCE_FOLDER%\"

set "SOURCE_IS_DEST=false"
if /i "%SOURCE_FOLDER%"=="%MUSIC_PATH%" set "SOURCE_IS_DEST=true"

if not exist "%SOURCE_FOLDER%" (
    echo.
    echo ERROR: Source folder not found: %SOURCE_FOLDER%
    echo Please check the path and try again.
    echo.
    set /p "TRY_AGAIN=Would you like to try again? (Y/n): "
    if /i "%TRY_AGAIN%"=="n" (
        echo Skipping conversion.
        timeout /t 2 /nobreak >nul
        goto :EOF
    )
    goto ASK_SOURCE_FOLDER
)

echo Destination: %MUSIC_PATH%
echo Format: %FILE_FORMAT% ^> .opus
echo Folder structure will be mirrored so playlists stay organized.
echo.
set /p "CONFIRM=Proceed with conversion? (Y/n): "
if /i "%CONFIRM%"=="n" (
    echo Conversion cancelled.
    echo Skipping conversion.
    timeout /t 2 /nobreak >nul
    goto :EOF
)

set "FILE_COUNT=0"
for /r "%SOURCE_FOLDER%" %%f in (*.%FILE_FORMAT%) do (
    set /a FILE_COUNT+=1
)

if !FILE_COUNT! EQU 0 (
    echo.
    echo No %FILE_FORMAT% files found in: %SOURCE_FOLDER%
    echo Add your %FILE_FORMAT% files to this folder and try again.
    set /p "TRY_AGAIN=Would you like to try again? (Y/n): "
    if /i "!TRY_AGAIN!"=="n" (
        echo Skipping conversion.
        timeout /t 2 /nobreak >nul
        goto :EOF
    )
    goto ASK_SOURCE_FOLDER
)

echo Found !FILE_COUNT! %FILE_FORMAT% file(s).
echo Starting conversion...
echo This may take a while depending on the number of files.
echo.

set "SOURCE_BASE=!SOURCE_FOLDER!"
set "SUCCESSFUL=0"
for /r "%SOURCE_FOLDER%" %%f in (*.%FILE_FORMAT%) do (
    set "CURRENT_FILE=%%f"
    set "REL_PATH=!CURRENT_FILE:%SOURCE_BASE%=!"
    set "DEST_PATH=!MUSIC_PATH!!REL_PATH!"
    for %%I in ("!DEST_PATH!") do set "DEST_DIR=%%~dpI"
    if not exist "!DEST_DIR!" mkdir "!DEST_DIR!" >nul 2>&1
    for %%I in ("!DEST_PATH!") do set "DEST_FILE=%%~dpnI"
    set "FFMPEG_ARGS=-c:a libopus -b:a 256k -ar 48000 -ac 2 -frame_duration 20"
    if /i "!FILE_FORMAT!"=="opus" set "FFMPEG_ARGS=-c copy"
    ffmpeg -i "%%f" !FFMPEG_ARGS! "!DEST_FILE!.opus" -loglevel error -n < nul
    if errorlevel 1 (
        echo WARNING: Failed to convert: %%f
    ) else (
        set /a SUCCESSFUL+=1
    )
)

echo.
echo Successfully converted !SUCCESSFUL! file(s).
timeout /t 2 /nobreak >nul

set /p "DELETE_ORIGINALS=Delete original files after conversion? (y/N): "
if /i "!DELETE_ORIGINALS!"=="y" (
    if /i "!FILE_FORMAT!"=="opus" (
        if /i "!SOURCE_IS_DEST!"=="true" (
		    timeout /t 1 /nobreak >nul
            echo.
            echo Skipping deletion: source and destination are the same folder and files are already .opus.
            timeout /t 2 /nobreak >nul
        ) else (
            goto :_DO_DELETE
        )
    ) else (
        goto :_DO_DELETE
    )
)

goto :_AFTER_DELETE

:_DO_DELETE
echo.
echo WARNING: This will permanently delete the original files from %SOURCE_FOLDER%
echo.
set /p "DELETE_CONFIRM=Are you sure? Type 'yes' to confirm: "
if /i "!DELETE_CONFIRM!"=="yes" (
    timeout /t 1 /nobreak >nul
    echo Deleting original files...
    for /r "%SOURCE_FOLDER%" %%f in (*.%FILE_FORMAT%) do (
        set "CURRENT_FILE=%%f"
        set "REL_PATH=!CURRENT_FILE:%SOURCE_BASE%=!"
        set "DEST_PATH=!MUSIC_PATH!!REL_PATH!"
        for %%I in ("!DEST_PATH!") do set "DEST_FILE=%%~dpnI"
        if exist "!DEST_FILE!.opus" del "%%f" /f /q
    )
    timeout /t 1 /nobreak >nul
    echo Original files deleted.
    timeout /t 2 /nobreak >nul
) else (
    echo Original files kept.
    timeout /t 2 /nobreak >nul
)

:_AFTER_DELETE


set "CONVERSION_SUCCESS=true"
goto :EOF

:AFTER_CONVERSION

timeout /t 1 /nobreak >nul
echo.
echo ========================================
echo Creating Configuration
echo ========================================
echo.

set "DEFAULT_PATH_VALUE=%DEFAULT_PATH%"
set "BOT_TOKEN_ESC=%BOT_TOKEN%"
set "MUSIC_PATH_ESC=%MUSIC_PATH%"
powershell -NoProfile -Command ^
  "$ErrorActionPreference='Stop';" ^
  "$lines = @('DISCORD_BOT_TOKEN=' + $env:BOT_TOKEN_ESC);" ^
  "if ($env:DEFAULT_PATH_VALUE -eq '0') { $lines += 'MUSIC_FOLDER=' + $env:MUSIC_PATH_ESC }" ^
  "Set-Content -Path '.env' -Value $lines -Encoding ASCII"

if "%DEFAULT_PATH%"=="1" (
    echo Using default music folder: music\ ^(inside Jill's folder^)
    timeout /t 2 /nobreak >nul
) else (
    echo Music folder saved to .env: %MUSIC_PATH%
    timeout /t 2 /nobreak >nul
)

echo.
if exist ".env.example" (
    set /p "DELETE_EXAMPLE=Delete .env.example (no longer needed)? (Y/n): "
    if /i not "%DELETE_EXAMPLE%"=="n" (
        del ".env.example" 2>nul
        echo .env.example deleted.
        timeout /t 2 /nobreak >nul
        echo.
    )
)

echo ========================================
echo SETUP COMPLETED - SAFE TO CLOSE SCRIPT
echo ========================================
echo.
echo Configuration saved to .env file.
echo.
if "%DEFAULT_PATH%"=="1" (
    echo Music folder: music\ - inside Jill's folder
    echo.
    echo	Your bot folder is fully portable:
    echo   - Virtual environment: venv\ - inside Jill's folder
    echo   - Music folder: music\ - inside Jill's folder
) else (
    echo Music folder: %MUSIC_PATH%
    echo.
    echo NOTE: Update .env file if you move the music folder somewhere else.
)
if "%CONVERSION_SUCCESS%"=="true" (
    echo.
    echo Next step:
    echo   1. Run scripts/win_run_bot.bat to start your bot.
) else (
    echo.
    echo Next steps:
    echo   1. Add .opus music files to your music folder.
    echo      See 04-Converting-To-Opus.txt for help converting audio files.
    echo   2. Run scripts/win_run_bot.bat to start your bot.
)
echo.
echo For help, see the README folder or 06-troubleshooting.txt
echo.
pause
