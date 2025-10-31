#!/bin/bash
set -e

# Ensure we are in project root by verifying requirements file
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: Could not find requirements.txt in project root."
    echo "Please run this script from your Jill bot's root directory."
    read -p "Press Enter to exit..."
    exit 1
fi

echo "========================================"
echo "Jill Discord Bot - Setup Wizard"
echo "========================================"
echo ""
echo "This wizard will set up Jill in a few easy steps."
echo "You can press Ctrl+C at any time to exit and run this again later."
echo ""

# STEP 0: PYTHON CHECK
echo "Checking for Python..."
if ! command -v python3 &>/dev/null; then
    echo ""
    echo "ERROR: Python not found"
    echo "Please install Python 3.11 or newer."
    echo "See 03-SETUP-Linux.txt for instructions."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "Found Python:"
echo "$PYTHON_VERSION"
echo ""

# Enforce Python >= 3.11
if ! python3 -c "import sys; sys.exit(0 if sys.version_info[:2] >= (3,11) else 1)" 2>/dev/null; then
    echo "ERROR: Python 3.11 or newer is required. Found: $PYTHON_VERSION"
    echo "Please upgrade Python and try again."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo "========================================"
echo "What This Setup Will Do"
echo "========================================"
echo ""
echo "- Create a Python virtual environment (venv)"
echo "- Install required dependencies (disnake, PyNaCl, python-dotenv)"
echo "- Ask you to configure your bot token and music folder"
echo "- Optionally convert audio files to .opus format"
echo "- Create a .env configuration file"
echo ""
read -p "Do you want to continue? (Y/n): " CONTINUE
if [[ "$CONTINUE" =~ ^[Nn]$ ]]; then
    echo ""
    echo "Setup cancelled."
    read -p "Press Enter to exit..."
    exit 0
fi
echo ""

# STEP 1: VIRTUAL ENVIRONMENT
if [ -d "venv" ]; then
    echo "Virtual environment already exists, skipping creation..."
else
    echo "Creating virtual environment..."
    if ! python3 -m venv venv; then
        echo ""
        echo "ERROR: Failed to create virtual environment"
        read -p "Press Enter to exit..."
        exit 1
    fi
    echo "Virtual environment created successfully."
    sleep 2
fi
echo ""

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "ERROR: Virtual environment activation script not found."
    echo "Please delete the venv folder and rerun this setup."
    read -p "Press Enter to exit..."
    exit 1
fi

# Verify virtual environment is active
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "WARNING: Virtual environment may not be activated properly."
    echo "The script will continue, but you may encounter issues."
    sleep 3
else
    echo "Virtual environment activated successfully."
    sleep 1
fi
echo ""

echo "Installing dependencies..."
# Upgrade pip first (quietly)
python -m pip install --upgrade pip --quiet
# Install requirements
if ! python -m pip install -r requirements.txt; then
    echo ""
    echo "ERROR: Failed to install dependencies"
    read -p "Press Enter to exit..."
    exit 1
fi
echo "Dependencies installed successfully."
sleep 2
echo ""

echo "========================================"
echo "Configuration"
echo "========================================"
echo ""

# STEP 2: DISCORD BOT TOKEN
echo "Step 1: Discord Bot Token"
echo "--------------------------"
echo "Enter your Discord bot token from the Discord Developer Portal."
echo "See 02-Getting-Discord-Token.txt if you need help getting your token."
echo ""

while true; do
    read -p "Bot Token: " BOT_TOKEN
    if [ -z "$BOT_TOKEN" ]; then
        echo ""
        echo "ERROR: Bot token cannot be empty."
        echo "Please enter your token."
        continue
    fi
    
    # Basic validation - check if token contains dots (Discord tokens do)
    if [[ ! "$BOT_TOKEN" == *"."* ]]; then
        echo ""
        echo "WARNING: Token doesn't appear to be a valid Discord bot token."
        echo "Discord tokens typically contain dots (periods)."
        echo ""
        read -p "Continue anyway? (y/N): " CONTINUE_TOKEN
        if [[ ! "$CONTINUE_TOKEN" =~ ^[Yy]$ ]]; then
            echo ""
            continue
        fi
    fi
    
    # Validate token length (Discord tokens are typically 59+ characters)
    if [ ${#BOT_TOKEN} -lt 50 ]; then
        echo ""
        echo "WARNING: Token seems unusually short (${#BOT_TOKEN} characters)."
        echo "Discord bot tokens are typically 59+ characters long."
        echo ""
        read -p "Continue anyway? (y/N): " CONTINUE_TOKEN
        if [[ ! "$CONTINUE_TOKEN" =~ ^[Yy]$ ]]; then
            echo ""
            continue
        fi
    fi
    break
done
echo ""
sleep 1

# Command Mode Selection
echo ""
echo "========================================="
echo "Choose command style:"
echo "1) Classic (!play) - Text commands with auto-cleanup"
echo "2) Modern (/play) - Slash commands with buttons"
echo "========================================="
echo ""
read -p "Choice (1 or 2) [default: 1]: " command_choice

case "$command_choice" in
    2)
        COMMAND_MODE="slash"
        echo "✓ Using modern slash commands mode"
        ;;
    *)
        COMMAND_MODE="prefix"
        echo "✓ Using classic prefix commands mode"
        ;;
esac
sleep 1

echo ""
echo "Step 2: Music Folder Location"
echo "--------------------------"
echo "Where should Jill look for your music files?"
echo ""
echo "Default location: music/ - inside Jill's folder"
echo ""
echo "Options:"
echo "- Press Enter to use the default location (recommended for portability)"
echo "- Type a custom path (e.g., /home/user/Music/jill/)"
echo "- Type 'exit' to cancel setup"
echo ""
echo "If the folder doesn't exist, this script will create it for you."
echo ""

DEFAULT_PATH=0
read -p "Music folder path: " MUSIC_PATH
if [[ "$MUSIC_PATH" == "exit" ]]; then
    echo ""
    echo "Setup cancelled."
    read -p "Press Enter to exit..."
    exit 0
fi

if [ -z "$MUSIC_PATH" ]; then
    MUSIC_PATH="music"
    DEFAULT_PATH=1
else
    # Remove surrounding quotes if present
    MUSIC_PATH="${MUSIC_PATH%\"}"
    MUSIC_PATH="${MUSIC_PATH#\"}"
fi

# Add trailing slash if not present
if [[ ! "$MUSIC_PATH" =~ /$ ]]; then
    MUSIC_PATH="$MUSIC_PATH/"
fi

if [ ! -d "$MUSIC_PATH" ]; then
    echo ""
    echo "Music folder does not exist. Creating: $MUSIC_PATH"
    if ! mkdir -p "$MUSIC_PATH" 2>/dev/null; then
        echo "WARNING: Could not create music folder automatically."
        echo "Please create it manually before running the bot."
    else
        echo "Music folder created successfully."
        sleep 2
    fi
else
    sleep 1
    echo "Music folder found: $MUSIC_PATH"
fi

# Test write permissions
echo "Testing write permissions..."
if touch "$MUSIC_PATH.write_test" 2>/dev/null; then
    rm -f "$MUSIC_PATH.write_test" 2>/dev/null
    echo "Write permissions OK."
    sleep 1
else
    echo "WARNING: Cannot write to music folder: $MUSIC_PATH"
    echo "Please check folder permissions."
    sleep 3
fi

echo ""
sleep 1

echo "========================================"
echo "Configuration Summary"
echo "========================================"
echo ""
echo "The following settings will be saved to .env:"
echo ""
# Show masked token (first 10 and last 5 characters)
TOKEN_START="${BOT_TOKEN:0:10}"
TOKEN_END="${BOT_TOKEN: -5}"
echo "Bot Token: ${TOKEN_START}...${TOKEN_END} (partially hidden for security)"
if [ "$DEFAULT_PATH" -eq 1 ]; then
    echo "Music Folder: music/ (default - inside Jill's folder)"
else
    echo "Music Folder: $MUSIC_PATH"
fi
echo ""
read -p "Is this correct? (Y/n): " CONFIRM_CONFIG
if [[ "$CONFIRM_CONFIG" =~ ^[Nn]$ ]]; then
    echo ""
    echo "Configuration cancelled. Please run the setup script again."
    read -p "Press Enter to exit..."
    exit 0
fi

sleep 1
echo ""
echo "========================================"
echo "Creating Configuration"
echo "========================================"
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo "You already have a .env configuration file."
    echo ""
    read -p "Do you want to reconfigure it? (y/N): " OVERWRITE
    if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Setup cancelled. Your existing .env file was not modified."
        echo ""
        read -p "Press Enter to exit..."
        exit 0
    fi
    echo ""
    echo "Updating .env file with new configuration..."
    sleep 2
    echo ""
fi

# Write .env file safely
{
    echo "DISCORD_BOT_TOKEN=$BOT_TOKEN"
    if [ "$DEFAULT_PATH" -eq 0 ]; then
        echo "MUSIC_FOLDER=$MUSIC_PATH"
    fi
    echo "JILL_COMMAND_MODE=$COMMAND_MODE"
} > .env

# Verify .env was created successfully
if [ ! -f ".env" ]; then
    echo ""
    echo "ERROR: Failed to create .env file."
    read -p "Press Enter to exit..."
    exit 1
fi

# Set secure permissions on .env file (readable only by owner)
chmod 600 .env 2>/dev/null || {
    echo "WARNING: Could not set secure permissions on .env file."
    echo "You may want to run: chmod 600 .env"
}

if [ "$DEFAULT_PATH" -eq 1 ]; then
    echo "Configuration saved. Using default music folder: music/"
    sleep 2
else
    echo "Configuration saved. Music folder: $MUSIC_PATH"
    sleep 2
fi

echo ""
if [ -f ".env.example" ]; then
    read -p "Delete .env.example (no longer needed)? (Y/n): " DELETE_EXAMPLE
    if [[ ! "$DELETE_EXAMPLE" =~ ^[Nn]$ ]]; then
        rm -f .env.example 2>/dev/null || true
        echo ".env.example deleted."
        sleep 2
        echo ""
    fi
fi

echo ""
echo "========================================"
echo "OPTIONAL: Audio Conversion"
echo "========================================"
CONVERSION_SUCCESS=false

# Multi-format conversion function
run_conversion() {
    # Initialize master conversion tracking
    MASTER_CONVERTED_LIST="/tmp/jill_all_converted_$$.txt"
    rm -f "$MASTER_CONVERTED_LIST" 2>/dev/null
    TOTAL_CONVERTED_COUNT=0
    FORMATS_CONVERTED=""
    CONVERSION_SUCCESS=false

    echo ""
    echo "========================================"
    echo "Source Folder Selection"
    echo "========================================"
    echo ""
    echo "Where are your music files located?"
    echo "(Subdirectories will be searched automatically)"
    echo ""

    while true; do
        read -p "Source folder: " SOURCE_FOLDER

        if [ -z "$SOURCE_FOLDER" ]; then
            echo ""
            echo "Skipping conversion."
            sleep 2
            return
        fi

        # Clean up path
        SOURCE_FOLDER="${SOURCE_FOLDER%\"}"
        SOURCE_FOLDER="${SOURCE_FOLDER#\"}"

        # Add trailing slash if not present
        if [[ ! "$SOURCE_FOLDER" =~ /$ ]]; then
            SOURCE_FOLDER="$SOURCE_FOLDER/"
        fi

        # Validate source folder
        if [ ! -d "$SOURCE_FOLDER" ]; then
            echo ""
            echo "ERROR: Folder does not exist: $SOURCE_FOLDER"
            echo "Please check the path and try again."
            echo ""
            continue
        fi

        break
    done

    echo ""
    echo "Source folder: $SOURCE_FOLDER"
    sleep 1

    # Scan for available formats
    echo ""
    echo "Scanning for audio files..."
    echo ""

    SCAN_FORMATS="mp3 flac wav m4a ogg opus wma aac aiff ape"
    FOUND_FORMATS=""
    declare -A FOUND_COUNTS

    for format in $SCAN_FORMATS; do
        count=$(find "$SOURCE_FOLDER" -type f -iname "*.$format" 2>/dev/null | wc -l)

        if [ "$count" -gt 0 ]; then
            if [ -z "$FOUND_FORMATS" ]; then
                FOUND_FORMATS="$format"
            else
                FOUND_FORMATS="$FOUND_FORMATS $format"
            fi
            FOUND_COUNTS[$format]=$count
            echo "Found $count .$format file(s)"
        fi
    done

    if [ -z "$FOUND_FORMATS" ]; then
        echo ""
        echo "ERROR: No audio files found in: $SOURCE_FOLDER"
        echo ""
        echo "Supported formats: $SCAN_FORMATS"
        echo ""
        echo "Press any key to continue without conversion..."
        read -n 1 -s
        return
    fi

    echo ""
    echo "========================================"
    echo "Audio Format Selection"
    echo "========================================"
    echo ""
    echo "Which audio formats would you like to convert to .opus?"
    echo ""
    echo "Available formats in your source folder: $FOUND_FORMATS"
    echo ""
    echo "Enter formats separated by spaces (e.g., flac mp3 wav)"
    echo "Or type 'all' to convert all found formats"
    echo "Or press Enter to skip conversion"
    echo ""
    read -p "Formats to convert: " USER_FORMATS

    # Check if user wants to skip conversion
    if [ -z "$USER_FORMATS" ]; then
        echo ""
        echo "Skipping conversion."
        sleep 2
        return
    fi

    # Handle 'all' option
    if [[ "$USER_FORMATS" =~ ^[Aa][Ll][Ll]$ ]]; then
        USER_FORMATS="$FOUND_FORMATS"
        echo ""
        echo "Converting all found formats: $FOUND_FORMATS"
    fi

    # Check for FFmpeg once before starting
    echo ""
    echo "Checking for FFmpeg..."
    if ! command -v ffmpeg &>/dev/null; then
        echo "ERROR: FFmpeg is not installed or not in PATH."
        echo "Please install FFmpeg and add it to PATH, or follow the manual conversion guide."
        echo ""
        echo "Press any key to continue without conversion..."
        read -n 1 -s
        echo "Skipping conversion."
        sleep 2
        return
    fi
    echo "FFmpeg found."
    sleep 1

    # Check FFmpeg capabilities once
    echo "Checking FFmpeg capabilities..."
    SUPPORTS_FRAME_DURATION=false
    if ffmpeg -codecs 2>/dev/null | grep -q "libopus"; then
        if ffmpeg -h encoder=libopus 2>/dev/null | grep -q "frame_duration"; then
            SUPPORTS_FRAME_DURATION=true
            echo "FFmpeg supports -frame_duration parameter (better Discord playback)."
        else
            echo "FFmpeg does not support -frame_duration parameter (will use defaults)."
        fi
    else
        echo "WARNING: FFmpeg doesn't have libopus support. Will try alternative method."
        sleep 2
    fi

    # Clean up and validate formats
    FORMATS_TO_CONVERT=""
    FORMAT_COUNT=0
    for format in $USER_FORMATS; do
        # Remove dots if present
        CLEAN_FORMAT="${format#.}"
        CLEAN_FORMAT=$(echo "$CLEAN_FORMAT" | tr '[:upper:]' '[:lower:]')

        # Check if this format was actually found
        if [[ " $FOUND_FORMATS " =~ " $CLEAN_FORMAT " ]]; then
            # Add to list if not already there
            if [[ ! " $FORMATS_TO_CONVERT " =~ " $CLEAN_FORMAT " ]]; then
                if [ -z "$FORMATS_TO_CONVERT" ]; then
                    FORMATS_TO_CONVERT="$CLEAN_FORMAT"
                else
                    FORMATS_TO_CONVERT="$FORMATS_TO_CONVERT $CLEAN_FORMAT"
                fi
                ((FORMAT_COUNT++))
            fi
        else
            echo "Warning: Format '$CLEAN_FORMAT' not found in source folder, skipping."
        fi
    done

    if [ -z "$FORMATS_TO_CONVERT" ]; then
        echo ""
        echo "ERROR: None of the selected formats were found in the source folder."
        echo ""
        echo "Press any key to continue without conversion..."
        read -n 1 -s
        return
    fi

    echo ""
    echo "Will convert these $FORMAT_COUNT format(s): $FORMATS_TO_CONVERT"
    echo ""
    sleep 2

    echo "========================================"
    echo "Conversion Process"
    echo "========================================"

    # Process each format the user selected
    for FILE_FORMAT in $FORMATS_TO_CONVERT; do
        echo ""
        echo "----------------------------------------"
        echo "Processing .$FILE_FORMAT files"
        echo "----------------------------------------"

        convert_format "$FILE_FORMAT"
    done
    
    # After all formats are processed
    echo ""
    echo "========================================"
    echo "All Conversions Complete"
    echo "========================================"
    
    if [ "$TOTAL_CONVERTED_COUNT" -gt 0 ]; then
        echo ""
        echo "Successfully processed formats: $FORMATS_CONVERTED"
        echo "Total files converted: $TOTAL_CONVERTED_COUNT"
        echo ""
        sleep 2
        CONVERSION_SUCCESS=true
        
        # Now proceed to deletion phase
        delete_originals
    else
        echo ""
        echo "No files were converted."
        echo ""
        sleep 2
    fi
    
    # Clean up temp file
    rm -f "$MASTER_CONVERTED_LIST" 2>/dev/null
}

# Subroutine: Convert a single format
convert_format() {
    local FILE_FORMAT="$1"

    echo ""

    # Count files
    FILE_COUNT=$(find "$SOURCE_FOLDER" -type f -iname "*.$FILE_FORMAT" 2>/dev/null | wc -l)

    if [ "$FILE_COUNT" -eq 0 ]; then
        echo "No .$FILE_FORMAT files found. Skipping."
        sleep 1
        return
    fi
    
    echo "Found $FILE_COUNT .$FILE_FORMAT file(s) in $SOURCE_FOLDER and subdirectories."
    echo "Starting conversion..."
    echo ""
    
    SOURCE_BASE="$SOURCE_FOLDER"
    SUCCESSFUL=0
    SKIPPED=0
    FAILED=0
    CURRENT_COUNT=0
    
    while IFS= read -r -d '' file; do
        ((CURRENT_COUNT++))
        CURRENT_FILE="$file"
        REL_PATH="${CURRENT_FILE#$SOURCE_BASE}"
        DEST_PATH="$MUSIC_PATH$REL_PATH"
        DEST_DIR="$(dirname "$DEST_PATH")"
        DEST_FILE="${DEST_PATH%.*}"
        BASENAME="$(basename "$file")"
        
        # Create destination directory if it doesn't exist
        mkdir -p "$DEST_DIR" 2>/dev/null
        
        # Check if file already exists
        if [ -f "$DEST_FILE.opus" ]; then
            echo "[$CURRENT_COUNT/$FILE_COUNT] Skipping (already exists): $BASENAME"
            ((SKIPPED++))
        else
            echo "[$CURRENT_COUNT/$FILE_COUNT] Converting: $BASENAME"
            
            # Set FFmpeg args
            if [[ "${FILE_FORMAT,,}" == "opus" ]]; then
                FFMPEG_ARGS="-c copy"
            else
                if [ "$SUPPORTS_FRAME_DURATION" = true ]; then
                    FFMPEG_ARGS="-c:a libopus -b:a 256k -ar 48000 -ac 2 -frame_duration 20"
                else
                    FFMPEG_ARGS="-c:a libopus -b:a 256k -ar 48000 -ac 2"
                fi
            fi
            
            if ffmpeg -i "$file" $FFMPEG_ARGS "$DEST_FILE.opus" -loglevel error -n < /dev/null 2>&1; then
                ((SUCCESSFUL++))
                # Add to master list immediately after successful conversion
                echo "\"$file\";$FILE_FORMAT" >> "$MASTER_CONVERTED_LIST"
                ((TOTAL_CONVERTED_COUNT++))
            else
                echo "    ERROR: Failed to convert this file"
                ((FAILED++))
            fi
        fi
    done < <(find "$SOURCE_FOLDER" -type f -iname "*.$FILE_FORMAT" -print0)
    
    echo ""
    echo "Format Summary: $FILE_FORMAT"
    echo "- Converted: $SUCCESSFUL"
    [ "$SKIPPED" -gt 0 ] && echo "- Skipped: $SKIPPED"
    [ "$FAILED" -gt 0 ] && echo "- Failed: $FAILED"
    sleep 1
    
    # Track which formats we've successfully converted
    if [ "$SUCCESSFUL" -gt 0 ]; then
        if [ -z "$FORMATS_CONVERTED" ]; then
            FORMATS_CONVERTED="$FILE_FORMAT"
        else
            FORMATS_CONVERTED="$FORMATS_CONVERTED, $FILE_FORMAT"
        fi
    fi
}

# Subroutine: Delete original files
delete_originals() {
    # Check if we have files to delete
    if [ "$TOTAL_CONVERTED_COUNT" -eq 0 ]; then
        return
    fi
    
    if [ ! -f "$MASTER_CONVERTED_LIST" ]; then
        echo "No conversion tracking file found."
        return
    fi
    
    echo ""
    echo "========================================"
    echo "Original Files Deletion"
    echo "========================================"
    echo ""
    echo "You have successfully converted files in these formats: $FORMATS_CONVERTED"
    echo "Total original files that can be deleted: $TOTAL_CONVERTED_COUNT"
    echo ""
    echo "The converted .opus files are safely in: $MUSIC_PATH"
    echo ""
    echo "Delete ALL $TOTAL_CONVERTED_COUNT original files to free up disk space?"
    echo ""
    
    read -p "Type YES (in capitals) to delete, or press Enter to keep them: " DELETE_CHOICE
    
    if [ "$DELETE_CHOICE" != "YES" ]; then
        echo ""
        echo "Original files will be kept."
        sleep 2
        return
    fi
    
    # Final safety confirmation
    echo ""
    echo "============================================"
    echo "FINAL CONFIRMATION REQUIRED"
    echo "============================================"
    echo "You are about to permanently DELETE:"
    echo "  - $TOTAL_CONVERTED_COUNT original files"
    echo "  - In formats: $FORMATS_CONVERTED"
    echo ""
    echo "This action CANNOT be undone!"
    echo ""
    read -p "Type DELETE (in capitals) to proceed, or press Enter to cancel: " FINAL_CONFIRM
    
    if [ "$FINAL_CONFIRM" != "DELETE" ]; then
        echo ""
        echo "Deletion cancelled. Original files kept."
        sleep 2
        return
    fi
    
    # Perform the actual deletion
    echo ""
    echo "Deleting original files..."
    DELETED_OK=0
    DELETED_FAIL=0
    CURRENT_FORMAT=""
    
    while IFS=';' read -r quoted_filepath format; do
        # Remove surrounding quotes if present
        filepath="${quoted_filepath%\"}"
        filepath="${filepath#\"}"
        
        if [ -f "$filepath" ]; then
            # Show format changes
            if [ "$format" != "$CURRENT_FORMAT" ]; then
                CURRENT_FORMAT="$format"
                echo "Processing .$CURRENT_FORMAT files..."
            fi
            
            if rm -f "$filepath" 2>/dev/null; then
                ((DELETED_OK++))
                if [ $((DELETED_OK % 10)) -eq 0 ]; then
                    echo "Deleted $DELETED_OK files so far..."
                fi
            else
                echo "Failed to delete: $(basename "$filepath")"
                ((DELETED_FAIL++))
            fi
        fi
    done < "$MASTER_CONVERTED_LIST"
    
    echo ""
    echo "========================================"
    echo "Deletion Complete"
    echo "========================================"
    [ "$DELETED_OK" -gt 0 ] && echo "Successfully deleted: $DELETED_OK files"
    [ "$DELETED_FAIL" -gt 0 ] && echo "Failed to delete: $DELETED_FAIL files"
    echo ""
    sleep 3
}

# Prompt user for conversion
echo "Ready to convert and move your music files into $MUSIC_PATH as .opus files."
echo ""
echo "In this step, we'll:"
echo "1. Ask which formats you want to convert (all at once)"
echo "2. Convert each format to .opus"
echo "3. Organize them in your music folder"
echo "4. Optionally delete the original files (with confirmation)"
echo "Note: The subfolder structure will stay the exact same"
echo ""
echo ""
read -p "Start the guided conversion now? (y/N): " CONVERT_FILES
if [[ "$CONVERT_FILES" =~ ^[Yy]$ ]]; then
    run_conversion
else
    echo ""
    echo "Skipping conversion."
    echo ""
    sleep 2
fi

# Create start-jill.sh script
echo ""
echo "Creating start script..."
cat > start-jill.sh << 'EOF'
#!/bin/bash
# Jill Discord Bot Launcher

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "ERROR: Virtual environment not found."
    echo "Please run linux_setup.sh first to set up the bot."
    exit 1
fi

# Run the bot
echo "Starting Jill Discord Bot..."
exec python3 bot.py
EOF

# Make the start script executable
if chmod +x start-jill.sh 2>/dev/null; then
    echo "start-jill.sh created and made executable."
else
    echo "WARNING: Could not make start-jill.sh executable."
    echo "You may need to run: chmod +x start-jill.sh"
fi
sleep 1

echo ""
echo ""
echo ""
echo "========================================"
echo "========================================"
echo "   SETUP COMPLETED SUCCESSFULLY!"
echo "========================================"
echo "========================================"
echo ""
echo "Your bartender is now fully configured!"
echo ""
if [ "$DEFAULT_PATH" -eq 1 ]; then
    echo "Your bot folder is fully portable:"
    echo "  - Virtual environment: venv/ - inside Jill's folder"
    echo "  - Music folder: music/ - inside Jill's folder"
else
    echo "Music folder: $MUSIC_PATH"
    echo "NOTE: Update .env file if you move the music folder somewhere else."
fi

if [ "$CONVERSION_SUCCESS" = true ]; then
    echo ""
    echo "Songs converted: $TOTAL_CONVERTED_COUNT"
    echo ""
    echo "NEXT STEPS:"
    echo "  1. Run ./start-jill.sh to start your bot"
    echo "  2. To convert MORE files later, run: ./linux_convert_opus.sh"
else
    echo ""
    echo "NEXT STEPS:"
    echo "  1. CONVERT YOUR MUSIC: Run ./linux_convert_opus.sh"
    echo "     (Converts MP3/FLAC/WAV/etc to .opus format - HIGHLY RECOMMENDED)"
    echo ""
    echo "  2. START YOUR BOT: Run ./start-jill.sh"
    echo ""
    echo "  Note: You can also manually add .opus files to your music folder."
fi
echo ""
echo "For help, see the README folder or 06-troubleshooting.txt"
echo ""
echo "========================================"
if [ "$COMMAND_MODE" = "slash" ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📝 SLASH COMMAND NOTES:"
    echo "• Commands may take up to 1 hour to appear"
    echo "• Control panel creates on first /play"
    echo "• Consider restricting bot to one channel"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
echo ""
read -p "Press Enter to exit..."
echo ""
echo "Exiting setup..."
