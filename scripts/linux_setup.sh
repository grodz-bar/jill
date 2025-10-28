#!/bin/bash
set -e

# Change to parent directory (project root)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.." || {
    echo "ERROR: Unable to locate project root."
    read -p "Press Enter to exit..."
    exit 1
}

if [ -f "scripts/linux_setup.sh" ]; then
    # Ensure we are really in project root by verifying requirements file
    if [ ! -f "requirements.txt" ]; then
        echo "ERROR: Could not find requirements.txt in project root."
        read -p "Press Enter to exit..."
        exit 1
    fi
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
echo ""

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

if [ ! -f "venv/bin/activate" ]; then
    echo "ERROR: Virtual environment activation script not found."
    echo "Please delete the venv folder and rerun this setup."
    read -p "Press Enter to exit..."
    exit 1
fi

source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment."
    read -p "Press Enter to exit..."
    exit 1
fi

# Verify virtual environment is active
VENV_PYTHON=$(python -c "import sys; print(sys.executable)" 2>/dev/null)
if [[ ! "$VENV_PYTHON" =~ "venv" ]]; then
    echo "WARNING: Virtual environment may not be activated properly."
    echo "Python is using: $VENV_PYTHON"
    echo "Expected path to contain 'venv'"
    echo ""
    echo "The virtual environment appears to be corrupted or wasn't created correctly."
    echo ""
    echo "WARNING: This will delete the existing venv folder."
    read -p "Type 'yes' to delete and recreate: " RECREATE_VENV
    if [[ "$RECREATE_VENV" == "yes" ]]; then
        echo ""
        echo "Removing corrupted virtual environment..."
        rm -rf venv
        echo "Creating fresh virtual environment..."
        if ! python3 -m venv venv; then
            echo ""
            echo "ERROR: Failed to create virtual environment"
            read -p "Press Enter to exit..."
            exit 1
        fi
        source venv/bin/activate
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to activate virtual environment."
            read -p "Press Enter to exit..."
            exit 1
        fi
        echo "Virtual environment recreated and activated successfully."
    else
        echo "Setup cancelled."
        read -p "Press Enter to exit..."
        exit 1
    fi
fi
echo "Virtual environment activated successfully."
sleep 1
echo ""

echo "Installing dependencies..."
if ! python -m pip install --upgrade pip --quiet; then
    echo ""
    echo "ERROR: Failed to upgrade pip"
    read -p "Press Enter to exit..."
    exit 1
fi

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

if [ -f ".env" ]; then
    echo "WARNING: .env file already exists."
    echo ""
    read -p "Do you want to overwrite it? (y/N): " OVERWRITE
    OVERWRITE=$(echo "$OVERWRITE" | xargs | cut -c1)
    if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Setup cancelled. Your existing .env file was not modified."
        echo ""
        read -p "Press Enter to exit..."
        exit 0
    fi
    echo ""
    echo "Overwriting existing .env file..."
    echo ""
    sleep 2
fi

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
    else
        # Validate token format (Discord tokens contain dots)
        if [[ ! "$BOT_TOKEN" == *.* ]]; then
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
    fi
done
echo ""
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
echo ""
echo "OPTIONAL STEP:"
echo "--------------------------"
CONVERSION_SUCCESS=false

# Function for conversion (defined before use)
run_conversion() {
    echo ""
    echo "Checking for FFmpeg..."
    if ! command -v ffmpeg &>/dev/null; then
        echo "ERROR: FFmpeg is not installed or not in PATH."
        echo "Please install FFmpeg, or follow the manual conversion guide:"
        echo "See 03-SETUP-Linux.txt and 04-Converting-To-Opus.txt"
        echo ""
        echo "Press any key to continue without conversion..."
        read -n 1 -s
        echo "Skipping conversion."
        sleep 2
        return
    fi

    echo "FFmpeg found."
    sleep 2

    echo "Checking FFmpeg capabilities..."

    # Check if FFmpeg has libopus encoder
    if ! ffmpeg -codecs 2>/dev/null | grep -q "libopus"; then
        echo ""
        echo "ERROR: FFmpeg does not have libopus encoder support."
        echo "Please install a version of FFmpeg with libopus support."
        echo "See 03-SETUP-Linux.txt for more information."
        echo ""
        echo "Press any key to continue without conversion..."
        read -n 1 -s
        echo "Skipping conversion."
        sleep 2
        return
    fi
    echo "FFmpeg has libopus encoder support."

    # Check if FFmpeg supports -frame_duration parameter
    SUPPORTS_FRAME_DURATION=false
    if ffmpeg -h encoder=libopus 2>/dev/null | grep -q "frame_duration"; then
        SUPPORTS_FRAME_DURATION=true
        echo "FFmpeg supports -frame_duration parameter (better Discord playback)."
    else
        echo "FFmpeg does not support -frame_duration parameter (will use defaults)."
    fi
    sleep 2

    while true; do
        echo ""
        echo "========================================"
        echo "Conversion Overview"
        echo "========================================"
        echo "We'll copy your audio into Jill's music folder so she can play it."
        echo "Destination (the folder you just configured): $MUSIC_PATH"
        echo "Folder structure is preserved (subfolders become playlists)."
        echo ""
        sleep 1

        echo ""
        echo "-------- Step 1: Choose the audio format --------"
        read -p "What audio format are your files? (mp3/flac/wav/m4a/other): " FILE_FORMAT
        if [ -z "$FILE_FORMAT" ]; then
            FILE_FORMAT="mp3"
        fi
        if [[ "$FILE_FORMAT" =~ ^[Oo]ther$ ]]; then
            read -p "Enter the file extension (without dot): " FILE_FORMAT
        fi
        # Trim whitespace
        FILE_FORMAT=$(echo "$FILE_FORMAT" | xargs)
        echo ""
        sleep 1

        echo "-------- Step 2: Tell us where the originals live --------"
        echo "This is the folder we will read from before writing to $MUSIC_PATH."
        echo ""
        echo "Enter the full folder path (for example: /home/user/Downloads/Albums/)."
        echo "or"
        echo "Press Enter to use Jill's music folder for both."
        echo ""
        read -p "Source folder path: " SOURCE_FOLDER

        if [ -z "$SOURCE_FOLDER" ]; then
            SOURCE_FOLDER="$MUSIC_PATH"
            echo ""
            echo "Using your Jill music folder as both the source and destination."
            sleep 1
        fi
        sleep 1

        # Remove surrounding quotes if present
        SOURCE_FOLDER="${SOURCE_FOLDER%\"}"
        SOURCE_FOLDER="${SOURCE_FOLDER#\"}"

        # Add trailing slash if not present
        if [[ ! "$SOURCE_FOLDER" =~ /$ ]]; then
            SOURCE_FOLDER="$SOURCE_FOLDER/"
        fi

        SOURCE_IS_DEST=false
        if [ "$SOURCE_FOLDER" = "$MUSIC_PATH" ]; then
            SOURCE_IS_DEST=true
        fi

        if [ ! -d "$SOURCE_FOLDER" ]; then
            echo ""
            echo "ERROR: Source folder not found: $SOURCE_FOLDER"
            echo "Please check the path and try again."
            echo ""
            read -p "Would you like to try again? (Y/n): " TRY_AGAIN
            if [[ "$TRY_AGAIN" =~ ^[Nn]$ ]]; then
                echo "Skipping conversion."
                sleep 2
                return
            fi
            continue
        fi

        echo "Destination: $MUSIC_PATH"
        echo "Format: $FILE_FORMAT > .opus"
        echo "Folder structure will be mirrored so playlists stay organized."
        echo ""

        # Check available disk space
        echo "Checking available disk space..."
        AVAILABLE_KB=$(df -P "$MUSIC_PATH" 2>/dev/null | awk 'NR==2 {print $4}')
        if [ -n "$AVAILABLE_KB" ]; then
            AVAILABLE_GB=$((AVAILABLE_KB / 1024 / 1024))
            echo "Available space at destination: ${AVAILABLE_GB}GB"
            if [ "$AVAILABLE_GB" -lt 1 ]; then
                echo "WARNING: Less than 1GB available. Conversion may fail if you run out of space."
                echo ""
                read -p "Continue anyway? (y/N): " CONTINUE_SPACE
                if [[ ! "$CONTINUE_SPACE" =~ ^[Yy]$ ]]; then
                    echo "Conversion cancelled."
                    sleep 2
                    return
                fi
            fi
        fi
        echo ""

        read -p "Proceed with conversion? (Y/n): " CONFIRM
        if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
            echo "Conversion cancelled."
            echo "Skipping conversion."
            sleep 2
            return
        fi

        # Count files
        FILE_COUNT=$(find "$SOURCE_FOLDER" -type f -iname "*.$FILE_FORMAT" 2>/dev/null | wc -l)

        if [ "$FILE_COUNT" -eq 0 ]; then
            echo ""
            echo "No $FILE_FORMAT files found in: $SOURCE_FOLDER"
            echo "Add your $FILE_FORMAT files to this folder and try again."
            read -p "Would you like to try again? (Y/n): " TRY_AGAIN
            if [[ "$TRY_AGAIN" =~ ^[Nn]$ ]]; then
                echo "Skipping conversion."
                sleep 2
                return
            fi
            continue
        fi
        break
    done

    echo "Found $FILE_COUNT $FILE_FORMAT file(s)."
    echo "Starting conversion..."
    echo "This may take a while depending on the number of files."
    echo ""
    echo "NOTE: Files already converted to .opus will be skipped automatically."
    echo "You can safely stop and resume conversion at any time."
    echo ""

    SUCCESSFUL=0
    SKIPPED=0
    FAILED=0
    CURRENT_COUNT=0
    SOURCE_BASE="$SOURCE_FOLDER"

    while IFS= read -r -d '' file; do
        ((CURRENT_COUNT++))
        CURRENT_FILE="$file"
        REL_PATH="${CURRENT_FILE#$SOURCE_BASE}"
        DEST_PATH="$MUSIC_PATH$REL_PATH"
        DEST_DIR="$(dirname "$DEST_PATH")"
        DEST_FILE="${DEST_PATH%.*}"
        BASENAME="$(basename "$file")"

        mkdir -p "$DEST_DIR" 2>/dev/null || true

        # Check if file already exists
        if [ -f "$DEST_FILE.opus" ]; then
            echo "[$CURRENT_COUNT/$FILE_COUNT] Skipping (already exists): $BASENAME"
            ((SKIPPED++))
            continue
        fi

        echo "[$CURRENT_COUNT/$FILE_COUNT] Converting: $BASENAME"

        # Set ffmpeg args (conditionally using -frame_duration for better Discord playback)
        if [[ "${FILE_FORMAT,,}" == "opus" ]]; then
            FFMPEG_ARGS="-c copy"
        else
            if [ "$SUPPORTS_FRAME_DURATION" = true ]; then
                FFMPEG_ARGS="-c:a libopus -b:a 256k -ar 48000 -ac 2 -frame_duration 20"
            else
                FFMPEG_ARGS="-c:a libopus -b:a 256k -ar 48000 -ac 2"
            fi
        fi

        # Prevent ffmpeg from consuming stdin
        if ffmpeg -i "$file" $FFMPEG_ARGS "$DEST_FILE.opus" -loglevel error -n < /dev/null 2>&1; then
            ((SUCCESSFUL++))
        else
            echo "    ERROR: Failed to convert this file"
            ((FAILED++))
        fi
    done < <(find "$SOURCE_FOLDER" -type f -iname "*.$FILE_FORMAT" -print0)

    echo ""
    echo "========================================"
    echo "Conversion Summary"
    echo "========================================"
    echo "Total files found: $FILE_COUNT"
    echo "Successfully converted: $SUCCESSFUL"
    if [ "$SKIPPED" -gt 0 ]; then
        echo "Skipped (already exists): $SKIPPED"
    fi
    if [ "$FAILED" -gt 0 ]; then
        echo "Failed: $FAILED"
    fi
    echo ""
    sleep 2

    read -p "Delete original files after conversion? (y/N): " DELETE_ORIGINALS
    if [[ "$DELETE_ORIGINALS" =~ ^[Yy]$ ]]; then
        if [[ "${FILE_FORMAT,,}" == "opus" ]] && [ "$SOURCE_IS_DEST" = true ]; then
            sleep 1
            echo ""
            echo "Skipping deletion: source and destination are the same folder and files are already .opus."
            sleep 2
        else
            echo ""
            echo "WARNING: This will permanently delete the original files from $SOURCE_FOLDER"
            echo ""
            read -p "Are you sure? Type 'yes' to confirm: " DELETE_CONFIRM
            if [[ "$DELETE_CONFIRM" == "yes" ]]; then
                sleep 1
                echo "Deleting original files..."
                while IFS= read -r -d '' file; do
                    CURRENT_FILE="$file"
                    REL_PATH="${CURRENT_FILE#$SOURCE_BASE}"
                    DEST_PATH="$MUSIC_PATH$REL_PATH"
                    DEST_FILE="${DEST_PATH%.*}"
                    # Only delete if corresponding .opus exists
                    if [ -f "$DEST_FILE.opus" ]; then
                        rm -f "$file"
                    fi
                done < <(find "$SOURCE_FOLDER" -type f -iname "*.$FILE_FORMAT" -print0)
                sleep 1
                echo "Original files deleted."
                sleep 2
            else
                echo "Original files kept."
                sleep 2
            fi
        fi
    fi

    CONVERSION_SUCCESS=true
}

# Prompt user for conversion
echo "Ready to convert and move your music files into $MUSIC_PATH as .opus files."
echo ""
echo "In this step, we'll:"
echo "1. Scan a folder for music files"
echo "2. Convert them to .opus"
echo "3. Make sure they're inside the music folder you set for Jill"
echo "4. Delete the pre-conversion music files (IF you want)"
echo "Note: The subfolder structure will stay the exact same"
echo ""
echo ""
read -p "Start the guided conversion now? (y/N): " CONVERT_FILES
if [[ "$CONVERT_FILES" =~ ^[Yy]$ ]]; then
    run_conversion
else
    echo "Skipping conversion."
    sleep 2
fi

sleep 1
echo ""
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

# Write .env file safely
{
    echo "DISCORD_BOT_TOKEN=$BOT_TOKEN"
    if [ "$DEFAULT_PATH" -eq 0 ]; then
        echo "MUSIC_FOLDER=$MUSIC_PATH"
    fi
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
    echo "Using default music folder: music/ (inside Jill's folder)"
    sleep 2
else
    echo "Music folder saved to .env: $MUSIC_PATH"
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

# Make the run bot script executable
echo ""
echo "Making run script executable..."
if chmod +x scripts/linux_run_bot.sh 2>/dev/null; then
    echo "scripts/linux_run_bot.sh is now executable."
else
    echo "WARNING: Could not make scripts/linux_run_bot.sh executable."
    echo "You may need to run: chmod +x scripts/linux_run_bot.sh"
fi
sleep 1

echo ""
sleep 1
echo "========================================"
echo "SETUP COMPLETED - SAFE TO CLOSE SCRIPT"
echo "========================================"
echo ""
echo "Configuration saved to .env file."
echo ""
if [ "$DEFAULT_PATH" -eq 1 ]; then
    echo "Music folder: music/ - inside Jill's folder"
    echo ""
    echo "  Your bot folder is fully portable:"
    echo "  - Virtual environment: venv/ - inside Jill's folder"
    echo "  - Music folder: music/ - inside Jill's folder"
else
    echo "Music folder: $MUSIC_PATH"
    echo ""
    echo "NOTE: Update .env file if you move the music folder somewhere else."
fi

if [ "$CONVERSION_SUCCESS" = true ]; then
    echo ""
    echo "Next step: Run scripts/linux_run_bot.sh to start your bot."
else
    echo ""
    echo "Next steps:"
    echo "  1. Add .opus music files to your music folder."
    echo "     See 04-Converting-To-Opus.txt for help converting audio files."
    echo "  2. Run scripts/linux_run_bot.sh to start your bot."
fi
echo ""
echo "For help, see the README folder or 06-troubleshooting.txt"
echo ""
read -p "Press Enter to exit..."