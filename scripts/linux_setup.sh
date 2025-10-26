#!/bin/bash
# Navigate to parent directory (project root)
cd "$(dirname "$0")/.."

echo "========================================"
echo "Jill Discord Bot - Setup Wizard"
echo "========================================"
echo ""
echo "This wizard will set up your bot in a few easy steps."
echo "You can press Ctrl+C at any time to exit and run this again later."
echo ""

# Check Python first
if ! command -v python3 &> /dev/null; then
    echo "Python 3 not found"
    echo ""
    echo "Would you like to install Python 3 now?"
    echo "NOTE: You will be asked for your password to install system packages."
    read -p "Install Python 3? (Y/n): " INSTALL_PYTHON
    if [[ ! "$INSTALL_PYTHON" =~ ^[Nn]$ ]]; then
        echo "Installing Python 3..."
        sudo apt update -qq
        sudo apt install -y python3 python3-pip python3-venv
        if [ $? -ne 0 ]; then
            echo "ERROR: Failed to install Python 3"
            echo "Please install Python 3.11 or newer manually."
            echo "See 03-SETUP-Linux.txt for instructions."
            exit 1
        fi
        echo "Python 3 installed successfully!"
        echo ""
    else
        echo "Please install Python 3.11 or newer first."
        echo "See 03-SETUP-Linux.txt for instructions."
        exit 1
    fi
fi

echo "Found Python:"
python3 --version
echo ""

# Check for FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg not found (needed for audio conversion feature)"
    echo ""
    echo "Would you like to install FFmpeg now?"
    echo "NOTE: You will be asked for your password to install system packages."
    read -p "Install FFmpeg? (Y/n): " INSTALL_FFMPEG
    if [[ ! "$INSTALL_FFMPEG" =~ ^[Nn]$ ]]; then
        echo "Installing FFmpeg..."
        sudo apt install -y ffmpeg
        if [ $? -ne 0 ]; then
            echo "WARNING: Failed to install FFmpeg"
            echo "You can still use the bot without audio conversion."
            echo "See 04-Converting-To-Opus.txt for manual conversion."
        else
            echo "FFmpeg installed successfully!"
        fi
        echo ""
    else
        echo "You can install FFmpeg later if needed for audio conversion."
        echo ""
    fi
fi

echo "========================================"
echo "What This Setup Will Do"
echo "========================================"
echo ""
echo "- Create a Python virtual environment at ~/jill-env/"
echo "- Install required dependencies (disnake, PyNaCl, python-dotenv)"
echo "- Ask you to configure your bot token and music folder"
echo "- Optionally convert audio files to .opus format"
echo "- Create a .env configuration file"
echo ""
read -p "Do you want to continue? (Y/n): " CONTINUE
if [[ "$CONTINUE" =~ ^[Nn]$ ]]; then
    echo ""
    echo "Setup cancelled."
    exit 0
fi
echo ""

# Create venv (idempotent - skip if exists)
if [ -d "$HOME/jill-env" ]; then
    echo "Virtual environment already exists, skipping creation..."
else
    echo "Creating virtual environment..."
    python3 -m venv ~/jill-env
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment"
        exit 1
    fi
    echo "Virtual environment created successfully."
fi
echo ""

# Activate venv
source ~/jill-env/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
python3 -m pip install --upgrade pip --quiet
python3 -m pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi
echo "Dependencies installed successfully."
echo ""

# Configuration section
echo "========================================"
echo "Configuration"
echo "========================================"
echo ""

# Check if .env already exists
if [ -f ".env" ]; then
    echo "WARNING: .env file already exists."
    read -p "Do you want to overwrite it? (y/N): " OVERWRITE
    if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Setup cancelled. Your existing .env file was not modified."
        echo ""
        exit 0
    fi
    echo ""
fi

# Bot token prompt
echo "Step 1: Discord Bot Token"
echo "--------------------------"
echo "Enter your Discord bot token from the Discord Developer Portal."
echo "See 02-Getting-Discord-Token.txt if you need help getting your token."
echo ""
read -p "Bot Token: " BOT_TOKEN

# Validate token not empty
if [ -z "$BOT_TOKEN" ]; then
    echo ""
    echo "ERROR: Bot token cannot be empty."
    echo "Please run this script again and enter your token."
    exit 1
fi
echo ""

# Music folder prompt
echo "Step 2: Music Folder Location"
echo "--------------------------"
echo "Where should the bot look for your music files?"
echo ""
echo "Default location: ~/jill/music/"
echo ""
echo "Options:"
echo "- Press Enter to use the default location"
echo "- Type a custom path (e.g., /mnt/music/jill/)"
echo "- Type 'exit' to cancel setup"
echo ""
echo "If the folder doesn't exist, this script will create it for you."
echo ""
read -p "Music folder path: " MUSIC_PATH

# Handle exit
if [ "$MUSIC_PATH" = "exit" ]; then
    echo ""
    echo "Setup cancelled."
    exit 0
fi

# Use default if empty
if [ -z "$MUSIC_PATH" ]; then
    MUSIC_PATH="~/jill/music/"
fi

# Expand tilde for operations
MUSIC_PATH_EXPANDED="${MUSIC_PATH/#\~/$HOME}"

# Create music folder if it doesn't exist
if [ ! -d "$MUSIC_PATH_EXPANDED" ]; then
    echo ""
    echo "Music folder does not exist. Creating: $MUSIC_PATH"
    mkdir -p "$MUSIC_PATH_EXPANDED" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "WARNING: Could not create music folder automatically."
        echo "Please create it manually before running the bot."
    else
        echo "Music folder created successfully."
    fi
else
    echo "Music folder found: $MUSIC_PATH"
fi
echo ""

# Optional conversion section
echo "Step 3: Audio File Conversion (Optional)"
echo "-------------------------------------------"
echo "Do you want to convert audio files to .opus now?"
echo ""
echo "If you already have .opus files, select No and add them to your music folder."
echo "If you have MP3s, FLACs, or other audio files, we can convert them for you."
echo ""
read -p "Convert audio files now? (y/N): " CONVERT_FILES

if [[ "$CONVERT_FILES" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Checking for FFmpeg..."
    
    if ! command -v ffmpeg &> /dev/null; then
        echo "ERROR: FFmpeg is not installed or not in PATH."
        echo ""
        echo "Please install FFmpeg:"
        echo "  sudo apt update && sudo apt install ffmpeg"
        echo ""
        echo "Or follow the manual conversion guide:"
        echo "See 03-SETUP-Linux.txt and 04-Converting-To-Opus.txt"
        echo ""
        echo "Press Enter to continue without conversion..."
        read
    else
        echo "FFmpeg found."
        echo ""
        
        # Ask for file format
        read -p "What audio format are your files? (mp3/flac/wav/m4a/other): " FILE_FORMAT
        if [ -z "$FILE_FORMAT" ]; then
            FILE_FORMAT="mp3"
        fi
        
        # Ask for source folder
        echo ""
        read -p "Enter the path to your source music folder: " SOURCE_FOLDER
        
        # Expand tilde in source folder
        SOURCE_FOLDER_EXPANDED="${SOURCE_FOLDER/#\~/$HOME}"
        
        # Validate source folder
        if [ -d "$SOURCE_FOLDER_EXPANDED" ]; then
            echo ""
            echo "Source folder found: $SOURCE_FOLDER"
            echo "Conversion will preserve folder structure (subfolders = playlists)."
            echo ""
            echo "Source: $SOURCE_FOLDER"
            echo "Destination: $MUSIC_PATH"
            echo "Format: $FILE_FORMAT > .opus"
            echo ""
            read -p "Proceed with conversion? (Y/n): " CONFIRM
            
            if [[ ! "$CONFIRM" =~ ^[Nn]$ ]]; then
                echo ""
                echo "Starting conversion..."
                echo "This may take a while depending on the number of files."
                echo ""
                
                # Convert files recursively
                COUNT=0
                find "$SOURCE_FOLDER_EXPANDED" -type f -name "*.$FILE_FORMAT" | while IFS= read -r file; do
                    # Get relative path from source folder
                    rel_path="${file#$SOURCE_FOLDER_EXPANDED/}"
                    # Create destination path preserving directory structure
                    dest_file="$MUSIC_PATH_EXPANDED/$rel_path"
                    dest_dir="$(dirname "$dest_file")"
                    
                    # Create directory if needed
                    mkdir -p "$dest_dir"
                    
                    # Convert file
                    ffmpeg -i "$file" -c:a libopus -b:a 256k -ar 48000 -ac 2 -frame_duration 20 "${dest_file%.$FILE_FORMAT}.opus" -loglevel error -n
                    if [ $? -eq 0 ]; then
                        COUNT=$((COUNT + 1))
                        echo "Converted: $(basename "$file")"
                    fi
                done
                
                echo ""
                echo "Conversion complete! Processed files."
                echo ""
                
                # Ask about deleting originals
                read -p "Delete original files after conversion? (y/N): " DELETE_ORIGINALS
                if [[ "$DELETE_ORIGINALS" =~ ^[Yy]$ ]]; then
                    echo ""
                    echo "WARNING: This will permanently delete the original files from $SOURCE_FOLDER"
                    read -p "Are you sure? Type 'yes' to confirm: " DELETE_CONFIRM
                    if [ "$DELETE_CONFIRM" = "yes" ]; then
                        echo "Deleting original files..."
                        find "$SOURCE_FOLDER_EXPANDED" -type f -name "*.$FILE_FORMAT" -delete
                        echo "Original files deleted."
                    else
                        echo "Original files kept."
                    fi
                fi
                echo ""
            else
                echo "Conversion cancelled."
            fi
        else
            echo ""
            echo "ERROR: Source folder not found: $SOURCE_FOLDER"
            echo "Please check the path and run the wizard again if needed."
            echo ""
        fi
    fi
else
    echo "Skipping conversion."
fi

# Create .env file (keep tilde notation for portability)
echo ""
echo "========================================"
echo "Creating Configuration"
echo "========================================"
echo ""

cat > .env << EOF
DISCORD_BOT_TOKEN=$BOT_TOKEN
MUSIC_FOLDER=$MUSIC_PATH
EOF

# Ask about deleting .env.example
if [ -f ".env.example" ]; then
    echo ""
    read -p "Delete .env.example (no longer needed)? (Y/n): " DELETE_EXAMPLE
    if [[ ! "$DELETE_EXAMPLE" =~ ^[Nn]$ ]]; then
        rm ".env.example" 2>/dev/null
        echo ".env.example deleted."
    fi
fi

# Make run script executable
chmod +x scripts/linux_run_bot.sh 2>/dev/null

echo ""
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Configuration saved to .env"
echo "Music folder: $MUSIC_PATH"
echo ""

if [[ "$CONVERT_FILES" =~ ^[Yy]$ ]]; then
    echo "Your files have been converted and are ready to use!"
else
    echo "Next steps:"
    echo "1. Add .opus music files to your music folder"
    echo "   See 04-Converting-To-Opus.txt for help converting audio files"
    echo "2. Run ./scripts/linux_run_bot.sh to start your bot"
    echo ""
fi
echo ""
echo ""
echo "For help, see the README folder or 06-troubleshooting.txt"
echo ""

