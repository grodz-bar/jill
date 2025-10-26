#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

print_banner() {
  cat <<'BANNER'
========================================
Jill Discord Bot - Setup Wizard
========================================

This wizard will set up your bot in a few easy steps.
You can press Ctrl+C at any time to exit and run this again later.
BANNER
}

pause_message() {
  read -rp "Press Enter to continue..." _
}

sleep_two() {
  sleep 2
}

normalize_path_trailing_slash() {
  local path="$1"
  if [[ -z "$path" ]]; then
    printf '%s' ""
    return
  fi
  case "$path" in
    */) printf '%s' "$path" ;;
    *) printf '%s/' "$path" ;;
  esac
}

expand_path() {
  local p="$1"
  if [[ $p == ~* ]]; then
    printf '%s' "${p/#\~/$HOME}"
  else
    printf '%s' "$p"
  fi
}

print_banner

echo "Checking for Python..."
if ! command -v python3 >/dev/null 2>&1; then
  echo ""
  echo "ERROR: Python 3 was not found on your system."
  if command -v apt-get >/dev/null 2>&1; then
    read -rp "Install Python 3 using apt-get now? (Y/n): " INSTALL_PY
    if [[ ! "$INSTALL_PY" =~ ^[Nn]$ ]]; then
      echo "Installing Python 3..."
      if ! sudo apt-get update -qq || ! sudo apt-get install -y python3 python3-venv python3-pip; then
        echo "ERROR: Failed to install Python automatically."
        echo "Please install Python 3.11 or newer and rerun this setup."
        echo "See 03-SETUP-Linux.txt for instructions."
        pause_message
        exit 1
      fi
      echo "Python 3 installed successfully."
      sleep_two
    else
      echo "Please install Python 3.11 or newer and add it to PATH."
      echo "See 03-SETUP-Linux.txt for instructions."
      pause_message
      exit 1
    fi
  else
    echo "Please install Python 3.11 or newer and add it to PATH."
    echo "See 03-SETUP-Linux.txt for instructions."
    pause_message
    exit 1
  fi
fi

PYTHON_VERSION="$(python3 --version 2>/dev/null)"
echo "Found Python:"
echo "$PYTHON_VERSION"
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
read -rp "Do you want to continue? (Y/n): " CONTINUE
if [[ "$CONTINUE" =~ ^[Nn]$ ]]; then
  echo ""
  echo "Setup cancelled."
  pause_message
  exit 0
fi
echo ""

if [[ -d "venv" ]]; then
  echo "Virtual environment already exists, skipping creation..."
else
  echo "Creating virtual environment..."
  if ! python3 -m venv venv; then
    echo "ERROR: Failed to create virtual environment"
    pause_message
    exit 1
  fi
  echo "Virtual environment created successfully."
  sleep_two
fi
echo ""

if [[ ! -f "venv/bin/activate" ]]; then
  echo "ERROR: Virtual environment activation script not found."
  echo "Please delete the venv folder and rerun this setup."
  pause_message
  exit 1
fi

# shellcheck source=/dev/null
source "venv/bin/activate"

echo "Installing dependencies..."
if ! python3 -m pip install --upgrade pip --quiet; then
  echo "ERROR: Failed to upgrade pip"
  pause_message
  exit 1
fi
if ! python3 -m pip install -r requirements.txt; then
  echo "ERROR: Failed to install dependencies"
  pause_message
  exit 1
fi
echo "Dependencies installed successfully."
sleep_two
echo ""

echo "========================================"
echo "Configuration"
echo "========================================"
echo ""

if [[ -f .env ]]; then
  echo "WARNING: .env file already exists."
  read -rp "Do you want to overwrite it? (y/N): " OVERWRITE
  if [[ ! "$OVERWRITE" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Setup cancelled. Your existing .env file was not modified."
    pause_message
    exit 0
  fi
  echo ""
fi

echo "Step 1: Discord Bot Token"
echo "--------------------------"
echo "Enter your Discord bot token from the Discord Developer Portal."
echo "See 02-Getting-Discord-Token.txt if you need help getting your token."
echo ""
BOT_TOKEN=""
while [[ -z "$BOT_TOKEN" ]]; do
  read -rp "Bot Token: " BOT_TOKEN
  BOT_TOKEN="${BOT_TOKEN//$'\r'/}"
  if [[ -z "$BOT_TOKEN" ]]; then
    echo ""
    echo "ERROR: Bot token cannot be empty."
    echo "Please enter your token."
  fi
done
echo ""

echo "Step 2: Music Folder Location"
echo "--------------------------"
echo "Where should the bot look for your music files?"
echo ""
echo "Default location: music/ (inside bot folder, fully portable)"
echo ""
echo "Options:"
echo "- Press Enter to use the default location (recommended for portability)"
echo "- Type a custom path (e.g., /mnt/music/jill/)"
echo "- Type 'exit' to cancel setup"
echo ""
echo "If the folder doesn't exist, this script will create it for you."
echo ""
read -rp "Music folder path: " MUSIC_INPUT
if [[ "$MUSIC_INPUT" == "exit" ]]; then
  echo ""
  echo "Setup cancelled."
  pause_message
  exit 0
fi

DEFAULT_PATH=0
if [[ -z "$MUSIC_INPUT" ]]; then
  MUSIC_PATH="music/"
  DEFAULT_PATH=1
else
  MUSIC_PATH="$MUSIC_INPUT"
fi

MUSIC_PATH="$(normalize_path_trailing_slash "$MUSIC_PATH")"
MUSIC_PATH_EXPANDED="$(normalize_path_trailing_slash "$(expand_path "$MUSIC_PATH")")"

if [[ ! -d "$MUSIC_PATH_EXPANDED" ]]; then
  echo ""
  echo "Music folder does not exist. Creating: $MUSIC_PATH"
  if ! mkdir -p "$MUSIC_PATH_EXPANDED" 2>/dev/null; then
    echo "WARNING: Could not create music folder automatically."
    echo "Please create it manually before running the bot."
  else
    echo "Music folder created successfully."
    sleep_two
  fi
else
  echo "Music folder found: $MUSIC_PATH"
fi
echo ""

CONVERSION_SUCCESS=false
read -rp "Convert audio files now? (y/N): " CONVERT_FILES
if [[ "$CONVERT_FILES" =~ ^[Yy]$ ]]; then
  echo ""
  echo "Checking for FFmpeg..."
  if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "ERROR: FFmpeg is not installed or not in PATH."
    if command -v apt-get >/dev/null 2>&1; then
      read -rp "Install FFmpeg using apt-get now? (Y/n): " INSTALL_FFMPEG
      if [[ ! "$INSTALL_FFMPEG" =~ ^[Nn]$ ]]; then
        echo "Installing FFmpeg..."
        if sudo apt-get install -y ffmpeg; then
          echo "FFmpeg installed successfully."
          sleep_two
        else
          echo "WARNING: Failed to install FFmpeg automatically."
        fi
      fi
    fi
    echo "Please install FFmpeg or follow the manual conversion guide:"
    echo "See 03-SETUP-Linux.txt and 04-Converting-To-Opus.txt"
    pause_message
  else
    echo "FFmpeg found."
    sleep_two

    while true; do
      echo ""
      read -rp "What audio format are your files? (mp3/flac/wav/m4a/other): " FILE_FORMAT
      if [[ -z "$FILE_FORMAT" ]]; then
        FILE_FORMAT="mp3"
      fi
      echo ""
      read -rp "Enter the path to your source music folder: " SOURCE_FOLDER
      if [[ -z "$SOURCE_FOLDER" ]]; then
        echo ""
        echo "ERROR: Source folder cannot be empty."
        read -rp "Would you like to try again? (Y/n): " TRY_AGAIN
        if [[ "$TRY_AGAIN" =~ ^[Nn]$ ]]; then
          break
        fi
        continue
      fi
      SOURCE_FOLDER="$(normalize_path_trailing_slash "$SOURCE_FOLDER")"
      SOURCE_FOLDER_EXPANDED="$(normalize_path_trailing_slash "$(expand_path "$SOURCE_FOLDER")")"
      if [[ ! -d "$SOURCE_FOLDER_EXPANDED" ]]; then
        echo ""
        echo "ERROR: Source folder not found: $SOURCE_FOLDER"
        read -rp "Would you like to try again? (Y/n): " TRY_AGAIN
        if [[ "$TRY_AGAIN" =~ ^[Nn]$ ]]; then
          break
        fi
        continue
      fi

      echo ""
      echo "Source folder found: $SOURCE_FOLDER"
      echo "Conversion will preserve folder structure (subfolders = playlists)."
      echo ""
      echo "Source: $SOURCE_FOLDER"
      echo "Destination: $MUSIC_PATH"
      echo "Format: $FILE_FORMAT > .opus"
      echo ""
      read -rp "Proceed with conversion? (Y/n): " CONFIRM
      if [[ "$CONFIRM" =~ ^[Nn]$ ]]; then
        echo "Conversion cancelled."
        break
      fi

      mapfile -t FILE_LIST < <(find "$SOURCE_FOLDER_EXPANDED" -type f -iname "*.${FILE_FORMAT}" -print)
      FILE_COUNT=${#FILE_LIST[@]}
      if [[ "$FILE_COUNT" -eq 0 ]]; then
        echo ""
        echo "No ${FILE_FORMAT} files found in: $SOURCE_FOLDER"
        read -rp "Would you like to try again? (Y/n): " TRY_AGAIN
        if [[ "$TRY_AGAIN" =~ ^[Nn]$ ]]; then
          echo "Skipping conversion."
          break
        fi
        continue
      fi

      echo "Found $FILE_COUNT $FILE_FORMAT file(s)."
      echo "Starting conversion..."
      echo "This may take a while depending on the number of files."
      echo ""

      SUCCESSFUL=0
      while IFS= read -r -d '' file; do
        rel_path="${file#$SOURCE_FOLDER_EXPANDED}"
        rel_path="${rel_path#/}"
        rel_dir="${rel_path%/*}"
        if [[ "$rel_dir" == "$rel_path" ]]; then
          dest_dir="$MUSIC_PATH_EXPANDED"
        else
          dest_dir="$MUSIC_PATH_EXPANDED$rel_dir/"
        fi
        mkdir -p "$dest_dir"
        dest_file="$MUSIC_PATH_EXPANDED${rel_path%.*}.opus"
        if ffmpeg -i "$file" -c:a libopus -b:a 256k -ar 48000 -ac 2 -frame_duration 20 "$dest_file" -loglevel error -n; then
          SUCCESSFUL=$((SUCCESSFUL + 1))
        else
          echo "WARNING: Failed to convert: $(basename "$file")"
        fi
      done < <(find "$SOURCE_FOLDER_EXPANDED" -type f -iname "*.${FILE_FORMAT}" -print0)

      echo ""
      echo "Conversion complete! Processed $FILE_COUNT file(s)."
      echo "Successfully converted $SUCCESSFUL file(s)."
      sleep_two

      read -rp "Delete original files after conversion? (y/N): " DELETE_ORIGINALS
      if [[ "$DELETE_ORIGINALS" =~ ^[Yy]$ ]]; then
        echo ""
        echo "WARNING: This will permanently delete the original files from $SOURCE_FOLDER"
        read -rp "Are you sure? Type 'yes' to confirm: " DELETE_CONFIRM
        if [[ "$DELETE_CONFIRM" == "yes" ]]; then
          echo "Deleting original files..."
          find "$SOURCE_FOLDER_EXPANDED" -type f -iname "*.${FILE_FORMAT}" -delete
          echo "Original files deleted."
          sleep_two
        else
          echo "Original files kept."
        fi
      fi

      CONVERSION_SUCCESS=true
      break
    done
  fi
else
  echo "Skipping conversion."
fi

echo ""
echo "========================================"
echo "Creating Configuration"
echo "========================================"
echo ""

cat > .env <<ENV_FILE
DISCORD_BOT_TOKEN=$BOT_TOKEN
ENV_FILE
if [[ "$DEFAULT_PATH" -eq 0 ]]; then
  cat >> .env <<ENV_FILE
MUSIC_FOLDER=$MUSIC_PATH
ENV_FILE
else
  echo "Using default music folder: music/ (inside bot folder)"
  echo "This keeps your bot portable - you can move the entire bot folder anywhere."
fi

echo ""
if [[ -f .env.example ]]; then
  read -rp "Delete .env.example (no longer needed)? (Y/n): " DELETE_EXAMPLE
  if [[ ! "$DELETE_EXAMPLE" =~ ^[Nn]$ ]]; then
    rm -f .env.example
    echo ".env.example deleted."
    echo ""
  fi
fi

chmod +x "$SCRIPT_DIR/linux_run_bot.sh" 2>/dev/null || true

echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo ""
echo "Configuration saved to .env"
echo ""
if [[ "$DEFAULT_PATH" -eq 1 ]]; then
  echo "Music folder: music/ (inside bot folder - portable)"
  echo ""
  echo "IMPORTANT: Your bot folder is fully portable!"
  echo "- Virtual environment is in: venv/ (inside bot folder)"
  echo "- Music folder is in: music/ (inside bot folder)"
  echo "- Full path from here: $(pwd)/music/"
else
  echo "Music folder: $MUSIC_PATH"
  echo ""
  echo "NOTE: Custom music folder location - bot folder is portable but music folder stays at: $MUSIC_PATH"
fi

echo ""
if [[ "$CONVERSION_SUCCESS" == true ]]; then
  echo "Your files have been converted and are ready to use!"
else
  echo "Next steps:"
  echo "1. Add .opus music files to your music folder"
  echo "   See 04-Converting-To-Opus.txt for help converting audio files"
  echo "2. Run ./scripts/linux_run_bot.sh to start your bot"
fi

echo ""
echo "For help, see the README folder or 06-troubleshooting.txt"
echo ""
pause_message
exit 0