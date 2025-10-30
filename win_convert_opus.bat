@echo off
setlocal EnableExtensions EnableDelayedExpansion

echo ========================================
echo Jill Discord Bot - Opus Converter
echo ========================================
echo.
echo This tool converts audio files to .opus format for Jill.
echo You can press Ctrl+C at any time to exit.
echo.

REM ============================================
REM STEP 1: Determine DESTINATION folder
REM ============================================

set "JILL_MUSIC_FOLDER="
set "ENV_FILE_EXISTS=false"

if exist ".env" (
    set "ENV_FILE_EXISTS=true"

    REM Try to parse MUSIC_FOLDER from .env
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        if /i "%%a"=="MUSIC_FOLDER" (
            set "JILL_MUSIC_FOLDER=%%b"
        )
    )

    REM If not found in .env, use default
    if "!JILL_MUSIC_FOLDER!"=="" (
        set "JILL_MUSIC_FOLDER=music"
    )
)

REM Display appropriate prompt based on .env existence
if "%ENV_FILE_EXISTS%"=="false" (
    echo ========================================
    echo WARNING: No .env file detected
    echo ========================================
    echo.
    echo It looks like you haven't set up Jill yet.
    echo.
    echo We STRONGLY RECOMMEND running win_setup.bat first to:
    echo   - Set up your bot token
    echo   - Configure your music folder
    echo   - Convert your files in one go
    echo.
    echo However, if you've manually configured Jill or want to
    echo continue anyway, you can proceed.
    echo.
    set /p "CONTINUE_ANYWAY=Continue without setup? (y/N): "
    if /i not "!CONTINUE_ANYWAY!"=="y" (
        echo.
        echo Conversion cancelled. Please run win_setup.bat first.
        echo.
        pause
        exit /b 0
    )
    echo.
    echo Proceeding with conversion...
    echo.

    REM For users without .env, require explicit destination
    :ASK_DEST_NO_ENV
    set "DEST_PATH="
    echo Where should converted .opus files be saved?
    echo.
    set /p "DEST_PATH=Destination folder: "
    if "!DEST_PATH!"=="" (
        echo.
        echo ERROR: Destination folder is required.
        echo.
        goto ASK_DEST_NO_ENV
    )
) else (
    REM .env exists - offer to use Jill's music folder
    echo Your Jill bot is configured to use: !JILL_MUSIC_FOLDER!
    echo.
    echo Where should converted .opus files be saved?
    echo.
    echo Options:
    echo - Press Enter to use Jill's music folder (recommended)
    echo - Type a custom path
    echo.
    set /p "DEST_PATH=Destination folder [!JILL_MUSIC_FOLDER!]: "

    REM If empty, use Jill's folder
    if "!DEST_PATH!"=="" (
        set "DEST_PATH=!JILL_MUSIC_FOLDER!"
        echo.
        echo Using Jill's music folder: !DEST_PATH!
    )
)

REM Clean up path
set "DEST_PATH=!DEST_PATH:"=!"
if not "!DEST_PATH:~-1!"=="\" set "DEST_PATH=!DEST_PATH!\"

REM Create destination folder if needed
if not exist "!DEST_PATH!" (
    echo.
    echo Destination folder does not exist. Creating: !DEST_PATH!
    mkdir "!DEST_PATH!" 2>nul
    if errorlevel 1 (
        echo ERROR: Could not create destination folder.
        echo Please check the path and try again.
        pause
        exit /b 1
    )
    echo Folder created successfully.
    timeout /t 2 /nobreak >nul
)

echo.
timeout /t 1 /nobreak >nul

REM ============================================
REM STEP 2: Determine SOURCE folder
REM ============================================

echo ========================================
echo Source Folder Selection
echo ========================================
echo.
echo Where are your music files located?
echo (Subdirectories will be searched automatically)
echo.

:ASK_SOURCE
set "SOURCE_PATH="
set /p "SOURCE_PATH=Source folder: "

if "!SOURCE_PATH!"=="" (
    echo.
    echo ERROR: Source folder is required.
    echo.
    goto ASK_SOURCE
)

REM Clean up path
set "SOURCE_PATH=!SOURCE_PATH:"=!"
if not "!SOURCE_PATH:~-1!"=="\" set "SOURCE_PATH=!SOURCE_PATH!\"

REM Validate source folder
if not exist "!SOURCE_PATH!" (
    echo.
    echo ERROR: Folder does not exist: !SOURCE_PATH!
    echo Please check the path and try again.
    echo.
    goto ASK_SOURCE
)

echo.
echo Source folder: !SOURCE_PATH!
timeout /t 1 /nobreak >nul

REM ============================================
REM STEP 3: Scan for available formats
REM ============================================

echo.
echo Scanning for audio files...
echo.

REM Supported formats to scan for
set "SCAN_FORMATS=mp3 flac wav m4a ogg opus wma aac aiff ape"
set "FOUND_FORMATS="
set "FOUND_COUNTS="

for %%F in (%SCAN_FORMATS%) do (
    set "FORMAT=%%F"
    set "COUNT=0"

    for /f %%c in ('dir /s /b "!SOURCE_PATH!*.!FORMAT!" 2^>nul ^| find /c /v ""') do set "COUNT=%%c"

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
    echo ERROR: No audio files found in: !SOURCE_PATH!
    echo.
    echo Supported formats: %SCAN_FORMATS%
    echo.
    pause
    exit /b 1
)

REM ============================================
REM STEP 4: Format Selection
REM ============================================

echo.
echo ========================================
echo Audio Format Selection
echo ========================================
echo.
echo The bot supports MP3, FLAC, WAV, M4A, OGG, and OPUS formats.
echo.
echo HOWEVER, converting to .opus format is HIGHLY RECOMMENDED for:
echo   - Lower CPU usage (especially important on lower-end systems)
echo   - Best audio quality (Discord-native format, no double compression)
echo   - Guaranteed stability (zero transcoding overhead)
echo.
echo Other formats work but require real-time transcoding (higher CPU usage).
echo.
echo Which audio formats would you like to convert to .opus?
echo.
echo Available formats in your source folder: !FOUND_FORMATS!
echo.
echo Enter formats separated by spaces (e.g., flac mp3 wav)
echo Or type 'all' to convert all found formats
echo Or press Enter to cancel
echo.
set "USER_FORMATS="
set /p "USER_FORMATS=Formats to convert: "

REM Check if user wants to skip conversion
if "!USER_FORMATS!"=="" (
    echo.
    echo Conversion cancelled.
    pause
    exit /b 0
)

REM Handle 'all' option
if /i "!USER_FORMATS!"=="all" (
    set "USER_FORMATS=!FOUND_FORMATS!"
    echo.
    echo Converting all found formats: !FOUND_FORMATS!
)

REM ============================================
REM STEP 5: Check for FFmpeg
REM ============================================

echo.
echo Checking for FFmpeg...
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ERROR: FFmpeg is not installed or not in PATH.
    echo.
    echo Please install FFmpeg to use this converter:
    echo   1. Download from: https://ffmpeg.org/download.html
    echo   2. Add to Windows PATH
    echo   3. Restart this script
    echo.
    pause
    exit /b 1
)
echo FFmpeg found.
timeout /t 1 /nobreak >nul

REM Check FFmpeg capabilities
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

REM ============================================
REM STEP 6: Validate and prepare formats
REM ============================================

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
    pause
    exit /b 1
)

echo.
echo Will convert these !FORMAT_COUNT! format(s): !FORMATS_TO_CONVERT!
echo.
timeout /t 2 /nobreak >nul

REM ============================================
REM STEP 7: Conversion Process
REM ============================================

echo ========================================
echo Conversion Process
echo ========================================

REM Initialize tracking
set "MASTER_CONVERTED_LIST=%TEMP%\jill_converted_%RANDOM%.txt"
if exist "!MASTER_CONVERTED_LIST!" del "!MASTER_CONVERTED_LIST!" >nul 2>&1
set "TOTAL_CONVERTED_COUNT=0"
set "FORMATS_CONVERTED="

REM Process each format
for %%X in (!FORMATS_TO_CONVERT!) do (
    set "FILE_FORMAT=%%X"
    echo.
    echo ----------------------------------------
    echo Processing .!FILE_FORMAT! files
    echo ----------------------------------------
    call :CONVERT_FORMAT
)

REM After all formats processed
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

    REM Proceed to deletion phase
    call :DELETE_ORIGINALS
) else (
    echo.
    echo No files were converted.
    echo.
)

echo.
echo ========================================
echo Conversion Complete
echo ========================================
echo.
echo Your .opus files are in: !DEST_PATH!
echo.
if "%ENV_FILE_EXISTS%"=="true" (
    echo Jill is ready to play your music!
    echo Run start-jill.bat to start the bot.
) else (
    echo Next step: Run win_setup.bat to configure your bot.
)
echo.
pause
exit /b 0

REM ============================================
REM SUBROUTINE: Convert a single format
REM ============================================
:CONVERT_FORMAT
echo.

REM Count files
set "FILE_COUNT=0"
for /f %%c in ('dir /s /b "!SOURCE_PATH!*.!FILE_FORMAT!" 2^>nul ^| find /c /v ""') do set "FILE_COUNT=%%c"

if !FILE_COUNT! EQU 0 (
    echo No .!FILE_FORMAT! files found. Skipping.
    timeout /t 1 /nobreak >nul
    exit /b
)

echo Found !FILE_FORMAT! file(s) in !SOURCE_PATH! and subdirectories.
echo Starting conversion...
echo.

set "SOURCE_BASE=!SOURCE_PATH!"
set "SUCCESSFUL=0"
set "SKIPPED=0"
set "FAILED=0"
set "CURRENT_COUNT=0"

for /f "delims=" %%f in ('dir /s /b "!SOURCE_PATH!*.!FILE_FORMAT!" 2^>nul') do (
    set /a CURRENT_COUNT+=1
    set "CURRENT_FILE=%%f"
    set "REL_PATH=!CURRENT_FILE:%SOURCE_BASE%=!"
    set "DEST_FILE_PATH=!DEST_PATH!!REL_PATH!"
    for %%I in ("!DEST_FILE_PATH!") do set "DEST_DIR=%%~dpI"
    for %%I in ("!DEST_FILE_PATH!") do set "DEST_FILE=%%~dpnI"
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

        ffmpeg -i "%%f" !FFMPEG_ARGS! "!DEST_FILE!.opus" -loglevel error -n < nul
        if errorlevel 1 (
            echo     ERROR: Failed to convert this file
            set /a FAILED+=1
        ) else (
            set /a SUCCESSFUL+=1
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

REM ============================================
REM SUBROUTINE: Delete original files
REM ============================================
:DELETE_ORIGINALS
REM Check if we have files to delete
if !TOTAL_CONVERTED_COUNT! EQU 0 exit /b

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
echo The converted .opus files are safely in: !DEST_PATH!
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

REM Perform deletion
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

        del /f /q "!FILEPATH!"

        if exist "!FILEPATH!" (
            echo Failed to delete: !FILEPATH!
            set /a DELETED_FAIL+=1
        ) else (
            set /a DELETED_OK+=1
            set /a "PROGRESS_CHECK=!DELETED_OK! %% 10"
            if !PROGRESS_CHECK! EQU 0 echo Deleted !DELETED_OK! files so far...
        )
    ) else (
        echo Warning: File not found: !FILEPATH!
        set /a DELETED_FAIL+=1
    )
)

REM Clean up
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
