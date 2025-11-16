@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Ensure we are in project root by verifying requirements file
if not exist requirements.txt (
    echo ERROR: Could not find requirements.txt in project root.
    echo Please run this script from your Jill bot's root directory.
    pause
    exit /b 1
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

REM Parse Python version and enforce >= 3.11
for /f "tokens=2 delims= " %%v in ('python -V 2^>^&1') do set "PY_VER=%%v"
for /f "tokens=1-3 delims=." %%a in ("%PY_VER%") do (
  set "PY_MAJ=%%a"
  set "PY_MIN=%%b"
)
set /a PY_NUM=100*%PY_MAJ%+%PY_MIN%
if %PY_NUM% LSS 311 (
  echo.
  echo ERROR: Python %PY_VER% detected. Please use Python 3.11+.
  pause
  exit /b 1
)
echo Found Python: %PY_VER%
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

if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment activation script not found.
    echo Please delete the venv folder and rerun this setup.
    pause
    exit /b 1
)
call "venv\Scripts\activate.bat"
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment.
    pause
    exit /b 1
)

REM Verify virtual environment is active
for /f "tokens=*" %%p in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "VENV_PYTHON=%%p"
echo !VENV_PYTHON! | findstr /i "venv" >nul
if errorlevel 1 (
    echo WARNING: Virtual environment may not be activated properly.
    echo Python is using: !VENV_PYTHON!
    echo Expected path to contain 'venv'
    echo.
    echo The virtual environment appears to be corrupted or wasn't created correctly.
    echo.
    echo WARNING: This will delete the existing venv folder.
    set /p "RECREATE_VENV=Type 'yes' to delete and recreate: "
    if /i "!RECREATE_VENV!"=="yes" (
        echo.
        echo Removing corrupted virtual environment...
        rmdir /s /q venv
        echo Creating fresh virtual environment...
        python -m venv venv
        if errorlevel 1 (
            echo.
            echo ERROR: Failed to create virtual environment
            pause
            exit /b 1
        )
        call venv\Scripts\activate
        if errorlevel 1 (
            echo ERROR: Failed to activate virtual environment.
            pause
            exit /b 1
        )
        echo Virtual environment recreated and activated successfully.
    ) else (
        echo Setup cancelled.
        pause
        exit /b 1
    )
)
echo Virtual environment activated successfully.
timeout /t 1 /nobreak >nul
echo.

echo Installing dependencies (this may take a moment)...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo.
    echo ERROR: Failed to upgrade pip
    pause
    exit /b 1
)
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo ERROR: Failed to install dependencies
    echo Please check your internet connection and try again.
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
    echo You already have a .env configuration file.
    echo.
    set /p "OVERWRITE=Do you want to reconfigure it? (y/N): "
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
    echo Updating .env file with new configuration...
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

REM Validate token length (Discord tokens are typically 59+ characters)
set "TOKEN_LEN=0"
set "TOKEN_COPY=%BOT_TOKEN%"
:COUNT_LOOP
if defined TOKEN_COPY (
    set "TOKEN_COPY=%TOKEN_COPY:~1%"
    set /a TOKEN_LEN+=1
    goto COUNT_LOOP
)

REM Validate token format (Discord tokens contain dots)
echo %BOT_TOKEN% | findstr /C:"." >nul
if errorlevel 1 (
    echo.
    echo WARNING: Token doesn't appear to be a valid Discord bot token.
    echo Discord tokens typically contain dots ^(periods^).
    echo.
    set /p "CONTINUE_TOKEN=Continue anyway? (y/N): "
    if /i not "!CONTINUE_TOKEN!"=="y" (
        echo.
        goto ASK_TOKEN
    )
)

if %TOKEN_LEN% LSS 50 (
    echo.
    echo WARNING: Token seems unusually short ^(%TOKEN_LEN% characters^).
    echo Discord bot tokens are typically 59+ characters long.
    echo.
    set /p "CONTINUE_TOKEN=Continue anyway? (y/N): "
    if /i not "!CONTINUE_TOKEN!"=="y" (
        echo.
        goto ASK_TOKEN
    )
)
echo.
timeout /t 1 /nobreak >nul

REM Command Mode Selection
echo.
echo =========================================
echo Choose command style:
echo 1) Classic (^^!play) - Text commands with auto message cleanup
echo 2) Modern (/play) - Slash commands with buttons
echo.
echo Classic Mode: Traditional text commands (e.g., ^^!play, ^^!skip)
echo   - Bot messages auto-delete after a short time
echo   - Great for keeping your music channel clean
echo.
echo Modern Mode: Slash commands with a persistent control panel
echo   - Interactive buttons for play/pause/skip
echo   - Control panel updates in place (no message spam)
echo =========================================
echo.
set /p command_choice="Choice (1 or 2) [default: 1]: "

if "%command_choice%"=="2" (
    set COMMAND_MODE=slash
    echo Using modern slash commands mode
) else (
    set COMMAND_MODE=prefix
    echo Using classic prefix commands mode
)
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
echo.
echo If the folder doesn't exist, this script will create it for you.
echo.
set "DEFAULT_PATH=0"
set /p "MUSIC_PATH=Music folder path: "
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

REM Test write permissions
echo Testing write permissions...
echo test > "%MUSIC_PATH%.write_test" 2>nul
if errorlevel 1 (
    echo WARNING: Cannot write to music folder: %MUSIC_PATH%
    echo Please check folder permissions.
    timeout /t 3 /nobreak >nul
) else (
    del "%MUSIC_PATH%.write_test" 2>nul
    echo Write permissions OK.
    timeout /t 1 /nobreak >nul
)

echo.
timeout /t 1 /nobreak >nul

echo ========================================
echo Configuration Summary
echo ========================================
echo.
echo The following settings will be saved to .env:
echo.
REM Show masked token (first 10 and last 5 characters)
set "TOKEN_START=%BOT_TOKEN:~0,10%"
set "TOKEN_END=%BOT_TOKEN:~-5%"
echo Bot Token: %TOKEN_START%...%TOKEN_END% ^(partially hidden for security^)
if "%DEFAULT_PATH%"=="1" (
    echo Music Folder: music\ ^(default - inside Jill's folder^)
) else (
    echo Music Folder: %MUSIC_PATH%
)
echo.
choice /c YN /d Y /t 30 /m "Is this correct"
if errorlevel 2 (
    echo.
    echo Configuration cancelled. Please run the setup script again.
    pause
    exit /b 0
)

echo.
timeout /t 1 /nobreak >nul
echo ========================================
echo Creating Configuration
echo ========================================
echo.

REM Create .env file using simple echo commands
(
    echo DISCORD_BOT_TOKEN=%BOT_TOKEN%
) > .env

if errorlevel 1 (
    echo.
    echo ERROR: Failed to create .env file.
    pause
    exit /b 1
)

REM Add MUSIC_FOLDER line only if using custom path
if "%DEFAULT_PATH%"=="0" (
    echo MUSIC_FOLDER=%MUSIC_PATH%>> .env
    if errorlevel 1 (
        echo.
        echo ERROR: Failed to write MUSIC_FOLDER to .env file.
        pause
        exit /b 1
    )
)

REM Add command mode
echo JILL_COMMAND_MODE=%COMMAND_MODE%>> .env

if not exist ".env" (
    echo.
    echo ERROR: .env file was not created successfully.
    pause
    exit /b 1
)

if "%DEFAULT_PATH%"=="1" (
    echo Configuration saved. Using default music folder: music\
    timeout /t 2 /nobreak >nul
) else (
    echo Configuration saved. Music folder: %MUSIC_PATH%
    timeout /t 2 /nobreak >nul
)

echo.
if exist ".env.example" (
    choice /c YN /d Y /t 10 /m "Delete .env.example (no longer needed)"
    if not errorlevel 2 (
        del ".env.example" 2>nul
        echo .env.example deleted.
        timeout /t 2 /nobreak >nul
        echo.
    )
)

REM Create start-jill.bat script
echo.
echo Creating start script...
(
    echo @echo off
    echo REM Jill Discord Bot Launcher
    echo.
    echo REM Activate virtual environment
    echo if not exist "venv\Scripts\activate.bat" ^(
    echo     echo ERROR: Virtual environment not found.
    echo     echo Please run win_setup.bat first to set up the bot.
    echo     pause
    echo     exit /b 1
    echo ^)
    echo.
    echo call venv\Scripts\activate
    echo.
    echo REM Run the bot
    echo echo Starting Jill Discord Bot...
    echo python bot.py
    echo pause
) > start-jill.bat

if exist "start-jill.bat" (
    echo start-jill.bat created successfully.
) else (
    echo WARNING: Could not create start-jill.bat
)
timeout /t 1 /nobreak >nul

echo.
echo ========================================
echo OPTIONAL: Audio Conversion
echo ========================================
set "CONVERSION_SUCCESS=false"
echo.
echo Jill supports MP3, FLAC, WAV, M4A, OGG, and OPUS formats.
echo.
echo HOWEVER, converting to .opus format is HIGHLY RECOMMENDED!
echo.
echo When using .opus, you will experience:
echo   - WAY fewer audio artifacts and warping issues (if any)
echo   - Lower CPU usage (important on lower-end systems)
echo   - Best audio quality (.opus is Discord's native format)
echo   - Often smaller file sizes
echo.
echo Other formats will technically work, but are NOT recommended.
echo.
echo If you choose to use this conversion tool, we'll:
echo 1. Scan a folder for music files
echo 2. Convert them to .opus (with recommended flags)
echo 3. Make sure they're inside Jill's music folder
echo 4. Optionally delete the pre-conversion music files
echo Note: The subfolder structure will stay the exact same
echo.
echo.
set /p "CONVERT_FILES=Start the guided conversion now? (y/N): "
if /i "%CONVERT_FILES%"=="y" (
    call :RUN_CONVERSION
) else (
    echo.
    echo Skipping conversion.
    echo.
    timeout /t 2 /nobreak >nul
)

REM Jump to completion message
goto AFTER_CONVERSION

:RUN_CONVERSION
REM Initialize master conversion tracking
set "MASTER_CONVERTED_LIST=%TEMP%\jill_all_converted_%RANDOM%.txt"
if exist "!MASTER_CONVERTED_LIST!" del "!MASTER_CONVERTED_LIST!" >nul 2>&1
set "TOTAL_CONVERTED_COUNT=0"
set "FORMATS_CONVERTED="
set "CONVERSION_SUCCESS=false"

echo.
echo ========================================
echo Source Folder Selection
echo ========================================
echo.
echo Where are your music files located?
echo (Subdirectories will be searched automatically)
echo.

:ASK_CONVERSION_SOURCE
set "SOURCE_FOLDER="
set /p "SOURCE_FOLDER=Source folder: "

if "!SOURCE_FOLDER!"=="" (
    echo.
    echo Skipping conversion.
    timeout /t 2 /nobreak >nul
    goto AFTER_CONVERSION
)

REM Clean up path
set "SOURCE_FOLDER=!SOURCE_FOLDER:"=!"
if not "!SOURCE_FOLDER:~-1!"=="\" set "SOURCE_FOLDER=!SOURCE_FOLDER!\"

REM Validate source folder
if not exist "!SOURCE_FOLDER!" (
    echo.
    echo ERROR: Folder does not exist: !SOURCE_FOLDER!
    echo Please check the path and try again.
    echo.
    goto ASK_CONVERSION_SOURCE
)

REM Scan for available formats
echo.
echo Scanning for audio files...
echo.

set "SCAN_FORMATS=mp3 flac wav m4a ogg opus wma aac aiff ape"
set "FOUND_FORMATS="
set "FOUND_COUNTS="

for %%F in (%SCAN_FORMATS%) do (
    set "FORMAT=%%F"
    set "COUNT=0"

    for /f %%c in ('dir /s /b "!SOURCE_FOLDER!*.!FORMAT!" 2^>nul ^| find /c /v ""') do set "COUNT=%%c"

    if !COUNT! GTR 0 (
        if "!FOUND_FORMATS!"=="" (
            set "FOUND_FORMATS=!FORMAT!"
            set "FOUND_COUNTS=!COUNT!"
        ) else (
            set "FOUND_FORMATS=!FOUND_FORMATS! !FORMAT!"
            set "FOUND_COUNTS=!FOUND_COUNTS! !COUNT!"
        )
        echo Found !COUNT! .!FORMAT! file(s)
    )
)

if "!FOUND_FORMATS!"=="" (
    echo.
    echo ERROR: No audio files found in: !SOURCE_FOLDER!
    echo.
    echo Supported formats: %SCAN_FORMATS%
    echo.
    echo Press any key to continue without conversion...
    pause >nul
    goto AFTER_CONVERSION
)

echo.
echo ========================================
echo Audio Format Selection
echo ========================================
echo.
echo Which audio formats would you like to convert to .opus?
echo.
echo Available formats in your source folder: !FOUND_FORMATS!
echo.
echo Enter formats separated by spaces (e.g., flac mp3 wav)
echo Or type 'all' to convert all found formats
echo Or press Enter to skip conversion
echo.
set "USER_FORMATS="
set /p "USER_FORMATS=Formats to convert: "

REM Check if user wants to skip conversion
if "!USER_FORMATS!"=="" (
    echo.
    echo Skipping conversion.
    timeout /t 2 /nobreak >nul
    goto AFTER_CONVERSION
)

REM Handle 'all' option
if /i "!USER_FORMATS!"=="all" (
    set "USER_FORMATS=!FOUND_FORMATS!"
    echo.
    echo Converting all found formats: !FOUND_FORMATS!
)

REM Check for FFmpeg once before starting
echo.
echo Checking for FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ERROR: FFmpeg is not installed or not in PATH.
    echo Please install FFmpeg and add it to PATH, or follow the manual conversion guide.
    echo.
    echo Press any key to continue without conversion...
    pause >nul
    echo Skipping conversion.
    timeout /t 2 /nobreak >nul
    goto AFTER_CONVERSION
)
echo FFmpeg found.
timeout /t 1 /nobreak >nul

REM Check FFmpeg capabilities once
echo Checking FFmpeg capabilities...
set "SUPPORTS_FRAME_DURATION=false"
ffmpeg -codecs 2>nul | findstr /i "libopus" >nul 2>&1
if errorlevel 1 (
    echo WARNING: FFmpeg doesn't have libopus support. Will try alternative method.
    timeout /t 2 /nobreak >nul
) else (
    ffmpeg -h encoder=libopus 2>nul | findstr /i "frame_duration" >nul 2>&1
    if not errorlevel 1 set "SUPPORTS_FRAME_DURATION=true"
)

REM Clean up and validate formats
set "FORMATS_TO_CONVERT="
set "FORMAT_COUNT=0"
for %%F in (!USER_FORMATS!) do (
    set "CLEAN_FORMAT=%%F"
    REM Remove dots if present
    set "CLEAN_FORMAT=!CLEAN_FORMAT:.=!"

    REM Check if this format was actually found
    echo !FOUND_FORMATS! | findstr /i "\<!CLEAN_FORMAT!\>" >nul 2>&1
    if not errorlevel 1 (
        REM Add to list if not already there
        echo !FORMATS_TO_CONVERT! | findstr /i "\<!CLEAN_FORMAT!\>" >nul 2>&1
        if errorlevel 1 (
            if "!FORMATS_TO_CONVERT!"=="" (
                set "FORMATS_TO_CONVERT=!CLEAN_FORMAT!"
            ) else (
                set "FORMATS_TO_CONVERT=!FORMATS_TO_CONVERT! !CLEAN_FORMAT!"
            )
            set /a FORMAT_COUNT+=1
        )
    ) else (
        echo Warning: Format '!CLEAN_FORMAT!' not found in source folder, skipping.
    )
)

if "!FORMATS_TO_CONVERT!"=="" (
    echo.
    echo ERROR: None of the selected formats were found in the source folder.
    echo.
    echo Press any key to continue without conversion...
    pause >nul
    goto AFTER_CONVERSION
)

echo.
echo Will convert these !FORMAT_COUNT! format(s): !FORMATS_TO_CONVERT!
echo.
timeout /t 2 /nobreak >nul

echo ========================================
echo Conversion Process
echo ========================================

REM Process each format the user selected
for %%X in (!FORMATS_TO_CONVERT!) do (
    set "FILE_FORMAT=%%X"
    echo.
    echo ----------------------------------------
    echo Processing .!FILE_FORMAT! files
    echo ----------------------------------------
    call :CONVERT_FORMAT
)

REM After all formats are processed
echo.
echo ========================================
echo All Conversions Complete
echo ========================================

if !TOTAL_CONVERTED_COUNT! GTR 0 (
    echo.
    echo Successfully processed formats: !FORMATS_CONVERTED!
    echo Total files converted: !TOTAL_CONVERTED_COUNT!
    echo.
    timeout /t 2 /nobreak >nul
    set "CONVERSION_SUCCESS=true"
    
    REM Now proceed to deletion phase
    call :DELETE_ORIGINALS
) else (
    echo.
    echo No files were converted.
    echo.
    timeout /t 2 /nobreak >nul
)

exit /b

REM ===== SUBROUTINE: Convert a single format =====
:CONVERT_FORMAT
echo.

REM Count files (including in subdirectories)
set "FILE_COUNT=0"
for /f %%c in ('dir /s /b "!SOURCE_FOLDER!*.!FILE_FORMAT!" 2^>nul ^| find /c /v ""') do set "FILE_COUNT=%%c"

if !FILE_COUNT! EQU 0 (
    echo No .!FILE_FORMAT! files found. Skipping.
    timeout /t 1 /nobreak >nul
    exit /b
)

echo Found !FILE_COUNT! .!FILE_FORMAT! file(s) in !SOURCE_FOLDER! and subdirectories.
echo Starting conversion...
echo.

set "SOURCE_BASE=!SOURCE_FOLDER!"
set "SUCCESSFUL=0"
set "SKIPPED=0"
set "FAILED=0"
set "CURRENT_COUNT=0"

for /f "delims=" %%f in ('dir /s /b "!SOURCE_FOLDER!*.!FILE_FORMAT!" 2^>nul') do (
    set /a CURRENT_COUNT+=1
    set "CURRENT_FILE=%%f"
    set "REL_PATH=!CURRENT_FILE:%SOURCE_BASE%=!"
    set "DEST_PATH=!MUSIC_PATH!!REL_PATH!"
    for %%I in ("!DEST_PATH!") do set "DEST_DIR=%%~dpI"
    for %%I in ("!DEST_PATH!") do set "DEST_FILE=%%~dpnI"
    set "BASENAME=%%~nxf"

    if not exist "!DEST_DIR!" mkdir "!DEST_DIR!" >nul 2>&1

    REM Check if file already exists
    if exist "!DEST_FILE!.opus" (
        echo [!CURRENT_COUNT!/!FILE_COUNT!] Skipping ^(already exists^): !BASENAME!
        set /a SKIPPED+=1
    ) else (
        echo [!CURRENT_COUNT!/!FILE_COUNT!] Converting: !BASENAME!

        REM Set FFmpeg args
        if /i "!FILE_FORMAT!"=="opus" (
            set "FFMPEG_ARGS=-c copy"
        ) else (
            if "!SUPPORTS_FRAME_DURATION!"=="true" (
                set "FFMPEG_ARGS=-c:a libopus -b:a 256k -ar 48000 -ac 2 -frame_duration 20"
            ) else (
                set "FFMPEG_ARGS=-c:a libopus -b:a 256k -ar 48000 -ac 2"
            )
        )

        ffmpeg -nostdin -i "%%f" !FFMPEG_ARGS! "!DEST_FILE!.opus" -loglevel error -n
        if errorlevel 1 (
            echo     ERROR: Failed to convert this file
            set /a FAILED+=1
        ) else (
            set /a SUCCESSFUL+=1
            REM Add to master list immediately after successful conversion (with quotes for safety)
            echo "%%f";!FILE_FORMAT!>>"!MASTER_CONVERTED_LIST!"
            set /a TOTAL_CONVERTED_COUNT+=1
        )
    )
)

echo.
echo Format Summary: !FILE_FORMAT!
echo - Converted: !SUCCESSFUL!
if !SKIPPED! GTR 0 echo - Skipped: !SKIPPED!
if !FAILED! GTR 0 echo - Failed: !FAILED!
timeout /t 1 /nobreak >nul

REM Track which formats we've successfully converted
if !SUCCESSFUL! GTR 0 (
    if "!FORMATS_CONVERTED!"=="" (
        set "FORMATS_CONVERTED=!FILE_FORMAT!"
    ) else (
        set "FORMATS_CONVERTED=!FORMATS_CONVERTED!, !FILE_FORMAT!"
    )
)

exit /b

REM ===== SUBROUTINE: Delete original files =====
:DELETE_ORIGINALS
REM Check if we have files to delete
if !TOTAL_CONVERTED_COUNT! EQU 0 (
    exit /b
)

if not exist "!MASTER_CONVERTED_LIST!" (
    echo No conversion tracking file found.
    exit /b
)

echo.
echo ========================================
echo Original Files Deletion
echo ========================================
echo.
echo You have successfully converted files in these formats: !FORMATS_CONVERTED!
echo Total original files that can be deleted: !TOTAL_CONVERTED_COUNT!
echo.
echo The converted .opus files are safely in: !MUSIC_PATH!
echo.
echo Delete ALL !TOTAL_CONVERTED_COUNT! original files to free up disk space?
echo.

set "DELETE_CHOICE="
set /p "DELETE_CHOICE=Type YES (in capitals) to delete, or press Enter to keep them: "

if not "!DELETE_CHOICE!"=="YES" (
    echo.
    echo Original files will be kept.
    if exist "!MASTER_CONVERTED_LIST!" del "!MASTER_CONVERTED_LIST!" >nul 2>&1
    timeout /t 2 /nobreak >nul
    exit /b
)

REM Final safety confirmation
echo.
echo ============================================
echo FINAL CONFIRMATION REQUIRED
echo ============================================
echo You are about to permanently DELETE:
echo   - !TOTAL_CONVERTED_COUNT! original files
echo   - In formats: !FORMATS_CONVERTED!
echo.
echo This action CANNOT be undone!
echo.
set "FINAL_CONFIRM="
set /p "FINAL_CONFIRM=Type DELETE (in capitals) to proceed, or press Enter to cancel: "

if not "!FINAL_CONFIRM!"=="DELETE" (
    echo.
    echo Deletion cancelled. Original files kept.
    if exist "!MASTER_CONVERTED_LIST!" del "!MASTER_CONVERTED_LIST!" >nul 2>&1
    timeout /t 2 /nobreak >nul
    exit /b
)

REM Perform the actual deletion
echo.
echo Deleting original files...
set "DELETED_OK=0"
set "DELETED_FAIL=0"
set "CURRENT_FORMAT="

for /f "usebackq tokens=1,2 delims=;" %%F in ("!MASTER_CONVERTED_LIST!") do (
    set "FILEPATH=%%~F"
    set "FILEFORMAT=%%G"
    
    if exist "!FILEPATH!" (
        REM Show format changes
        if not "!FILEFORMAT!"=="!CURRENT_FORMAT!" (
            set "CURRENT_FORMAT=!FILEFORMAT!"
            echo Processing .!CURRENT_FORMAT! files...
        )
        
        REM Delete the file
        del /f /q "!FILEPATH!"
        
        REM Verify deletion
        if exist "!FILEPATH!" (
            echo Failed to delete: !FILEPATH!
            set /a DELETED_FAIL+=1
        ) else (
            set /a DELETED_OK+=1
            set /a "PROGRESS_CHECK=!DELETED_OK! %% 10"
            if !PROGRESS_CHECK! EQU 0 echo Deleted !DELETED_OK! files so far...
        )
    ) else (
        echo Warning: File not found for deletion: !FILEPATH!
        set /a DELETED_FAIL+=1
    )
)

REM Clean up master list
if exist "!MASTER_CONVERTED_LIST!" del "!MASTER_CONVERTED_LIST!" >nul 2>&1

echo.
echo ========================================
echo Deletion Complete
echo ========================================
if !DELETED_OK! GTR 0 echo Successfully deleted: !DELETED_OK! files
if !DELETED_FAIL! GTR 0 echo Failed to delete: !DELETED_FAIL! files
echo.
timeout /t 3 /nobreak >nul

exit /b

:AFTER_CONVERSION

echo.
echo.
echo.
echo ========================================
echo ========================================
echo    SETUP COMPLETED SUCCESSFULLY!
echo ========================================
echo ========================================
echo.
echo Your bartender is now fully configured!
echo.
if "%DEFAULT_PATH%"=="1" (
    echo Your bot folder is fully portable:
    echo   - Virtual environment: venv\ - inside Jill's folder
    echo   - Music folder: music\ - inside Jill's folder
) else (
    echo Music folder: %MUSIC_PATH%
    echo NOTE: Update .env file if you move the music folder somewhere else.
)

if "%CONVERSION_SUCCESS%"=="true" (
    echo.
    echo Songs converted: !TOTAL_CONVERTED_COUNT!
    echo.
    echo NEXT STEPS:
    echo   1. Run start-jill.bat to start your bot
    echo   2. To convert MORE files later, run: win_convert_opus.bat
) else (
    echo.
    echo NEXT STEPS:
    echo   1. CONVERT YOUR MUSIC: Run win_convert_opus.bat
    echo      ^(Converts MP3/FLAC/WAV/etc to .opus format - HIGHLY RECOMMENDED^)
    echo.
    echo   2. START YOUR BOT: Run start-jill.bat
    echo.
    echo   Note: You can also manually add .opus files to your music folder.
)
echo.
echo For help, see the README folder or 06-troubleshooting.txt
echo.
echo ========================================
if "%COMMAND_MODE%"=="slash" (
    echo.
    echo =========================================
    echo SLASH COMMAND NOTES:
    echo - Commands may take up to 1 hour to appear
    echo - Control panel creates on first /play
    echo - Consider restricting bot to one channel
    echo =========================================
)
echo.
pause
echo.
echo Exiting setup...
