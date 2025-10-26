@echo off
REM Change to parent directory (project root)
cd /d %~dp0..

echo ========================================
echo Jill Discord Bot - Setup Wizard
echo ========================================
echo.
echo This wizard will set up your bot in a few easy steps.
echo You can press Ctrl+C at any time to exit and run this again later.
echo.

REM Check Python first
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    echo.
    echo Please install Python 3.11 or newer and add it to PATH.
    echo See 03-SETUP-Windows.txt for instructions.
    pause
    exit /b 1
)

echo Found Python:
python --version
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
set /p CONTINUE="Do you want to continue? (Y/n): "
if /i "%CONTINUE%"=="n" (
    echo.
    echo Setup cancelled.
    pause
    exit /b 0
)
echo.

REM Create venv (idempotent - skip if exists)
if exist "venv\" (
    echo Virtual environment already exists, skipping creation...
) else (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
)
echo.

REM Activate venv
call venv\Scripts\activate

REM Install/update dependencies
echo Installing dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully.
echo.

REM Configuration section
echo ========================================
echo Configuration
echo ========================================
echo.

REM Check if .env already exists
if exist ".env" (
    echo WARNING: .env file already exists.
    set /p OVERWRITE="Do you want to overwrite it? (y/N): "
    if /i not "%OVERWRITE%"=="y" (
        echo.
        echo Setup cancelled. Your existing .env file was not modified.
        echo.
        pause
        exit /b 0
    )
    echo.
)

REM Bot token prompt
echo Step 1: Discord Bot Token
echo --------------------------
echo Enter your Discord bot token from the Discord Developer Portal.
echo See 02-Getting-Discord-Token.txt if you need help getting your token.
echo.
set /p BOT_TOKEN="Bot Token: "

REM Validate token not empty
if "%BOT_TOKEN%"=="" (
    echo.
    echo ERROR: Bot token cannot be empty.
    echo Please run this script again and enter your token.
    pause
    exit /b 1
)
echo.

REM Music folder prompt
echo Step 2: Music Folder Location
echo --------------------------
echo Where should the bot look for your music files?
echo.
echo Default location: music\
echo.
echo Options:
echo - Press Enter to use the default location
echo - Type a custom path (e.g., D:\Music\jill\)
echo - Type 'exit' to cancel setup
echo.
echo If the folder doesn't exist, this script will create it for you.
echo.
set /p MUSIC_PATH="Music folder path: "

REM Handle exit
if /i "%MUSIC_PATH%"=="exit" (
    echo.
    echo Setup cancelled.
    pause
    exit /b 0
)

REM Use default if empty
if "%MUSIC_PATH%"=="" set MUSIC_PATH=music\

REM Create music folder if it doesn't exist
if not exist "%MUSIC_PATH%" (
    echo.
    echo Music folder does not exist. Creating: %MUSIC_PATH%
    mkdir "%MUSIC_PATH%" 2>nul
    if errorlevel 1 (
        echo WARNING: Could not create music folder automatically.
        echo Please create it manually before running the bot.
    ) else (
        echo Music folder created successfully.
    )
) else (
    echo Music folder found: %MUSIC_PATH%
)
echo.

REM Optional conversion section
echo Step 3: Audio File Conversion (Optional)
echo --------------------------------------------
echo Do you want to convert audio files to .opus now?
echo.
echo If you already have .opus files, select No and add them to your music folder.
echo If you have MP3s, FLACs, or other audio files, we can convert them for you.
echo.
set /p CONVERT_FILES="Convert audio files now? (y/N): "
if /i "%CONVERT_FILES%"=="y" (
    echo.
    echo Checking for FFmpeg...
    ffmpeg -version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: FFmpeg is not installed or not in PATH.
        echo.
        echo Please install FFmpeg and add it to PATH, or follow the manual conversion guide:
        echo See 03-SETUP-Windows.txt and 04-Converting-To-Opus.txt
        echo.
        echo Press any key to continue without conversion...
        pause >nul
    ) else (
        echo FFmpeg found.
        echo.
        
        REM Ask for file format
        set /p FILE_FORMAT="What audio format are your files? (mp3/flac/wav/m4a/other): "
        if "%FILE_FORMAT%"=="" set FILE_FORMAT=mp3
        
        REM Ask for source folder
        echo.
        set /p SOURCE_FOLDER="Enter the path to your source music folder: "
        
        REM Validate source folder
        if exist "%SOURCE_FOLDER%\" (
            echo.
            echo Source folder found: %SOURCE_FOLDER%
            echo Conversion will preserve folder structure (subfolders = playlists).
            echo.
            echo Source: %SOURCE_FOLDER%
            echo Destination: %MUSIC_PATH%
            echo Format: %FILE_FORMAT% ^> .opus
            echo.
            set /p CONFIRM="Proceed with conversion? (Y/n): "
            if /i not "%CONFIRM%"=="n" (
                echo.
                echo Starting conversion...
                echo This may take a while depending on the number of files.
                echo.
                
                REM Convert files recursively
                set COUNT=0
                for /r "%SOURCE_FOLDER%" %%f in (*.%FILE_FORMAT%) do (
                    set /a COUNT+=1
                    ffmpeg -i "%%f" -c:a libopus -b:a 256k -ar 48000 -ac 2 -frame_duration 20 "%MUSIC_PATH%%%~pnf.opus" -loglevel error -n
                    if errorlevel 1 (
                        echo WARNING: Failed to convert: %%f
                    )
                )
                
                echo.
                echo Conversion complete! Processed %COUNT% files.
                echo.
                
                REM Ask about deleting originals
                set /p DELETE_ORIGINALS="Delete original files after conversion? (y/N): "
                if /i "%DELETE_ORIGINALS%"=="y" (
                    echo.
                    echo WARNING: This will permanently delete the original files from %SOURCE_FOLDER%
                    set /p DELETE_CONFIRM="Are you sure? Type 'yes' to confirm: "
                    if /i "%DELETE_CONFIRM%"=="yes" (
                        echo Deleting original files...
                        for /r "%SOURCE_FOLDER%" %%f in (*.%FILE_FORMAT%) do del "%%f" /f /q
                        echo Original files deleted.
                    ) else (
                        echo Original files kept.
                    )
                )
                echo.
            ) else (
                echo Conversion cancelled.
            )
        ) else (
            echo.
            echo ERROR: Source folder not found: %SOURCE_FOLDER%
            echo Please check the path and run the wizard again if needed.
            echo.
        )
    )
) else (
    echo Skipping conversion.
)

REM Create .env file
echo ========================================
echo Creating Configuration
echo ========================================
echo.

echo DISCORD_BOT_TOKEN=%BOT_TOKEN%> .env
echo MUSIC_FOLDER=%MUSIC_PATH%>> .env

REM Ask about deleting .env.example
if exist ".env.example" (
    echo.
    set /p DELETE_EXAMPLE="Delete .env.example (no longer needed)? (Y/n): "
    if /i not "%DELETE_EXAMPLE%"=="n" (
        del ".env.example" 2>nul
        echo .env.example deleted.
        echo.
    )
)

echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Configuration saved to .env
echo Music folder: %MUSIC_PATH%
echo.

if /i "%CONVERT_FILES%"=="y" (
    echo Your files have been converted and are ready to use!
) else (
    echo Next steps:
    echo 1. Add .opus music files to your music folder
    echo    See 04-Converting-To-Opus.txt for help converting audio files
    echo 2. Run scripts/win_run_bot.bat to start your bot
    echo.
)
echo.
echo.
echo For help, see the README folder or 06-troubleshooting.txt
echo.
pause

