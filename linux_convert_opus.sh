#!/bin/bash
set -e

echo "========================================"
echo "Jill Discord Bot - Opus Converter"
echo "========================================"
echo ""
echo "This tool converts audio files to .opus format for Jill."
echo "You can press Ctrl+C at any time to exit."
echo ""

# ============================================
# STEP 1: Determine DESTINATION folder
# ============================================

JILL_MUSIC_FOLDER=""
ENV_FILE_EXISTS=false

if [ -f ".env" ]; then
    ENV_FILE_EXISTS=true

    # Try to parse MUSIC_FOLDER from .env
    if grep -q "^MUSIC_FOLDER=" .env 2>/dev/null; then
        JILL_MUSIC_FOLDER=$(grep "^MUSIC_FOLDER=" .env | cut -d'=' -f2-)
    fi

    # If not found in .env, use default
    if [ -z "$JILL_MUSIC_FOLDER" ]; then
        JILL_MUSIC_FOLDER="music"
    fi
fi

# Display appropriate prompt based on .env existence
if [ "$ENV_FILE_EXISTS" = false ]; then
    echo "========================================"
    echo "WARNING: No .env file detected"
    echo "========================================"
    echo ""
    echo "It looks like you haven't set up Jill yet."
    echo ""
    echo "We STRONGLY RECOMMEND running linux_setup.sh first to:"
    echo "  - Set up your bot token"
    echo "  - Configure your music folder"
    echo "  - Convert your files in one go"
    echo ""
    echo "However, if you've manually configured Jill or want to"
    echo "continue anyway, you can proceed."
    echo ""
    read -p "Continue without setup? (y/N): " CONTINUE_ANYWAY
    if [[ ! "$CONTINUE_ANYWAY" =~ ^[Yy]$ ]]; then
        echo ""
        echo "Conversion cancelled. Please run linux_setup.sh first."
        echo ""
        read -p "Press Enter to exit..."
        exit 0
    fi
    echo ""
    echo "Proceeding with conversion..."
    echo ""

    # For users without .env, require explicit destination
    while true; do
        echo "Where should converted .opus files be saved?"
        echo ""
        read -p "Destination folder: " DEST_PATH
        if [ -n "$DEST_PATH" ]; then
            break
        fi
        echo ""
        echo "ERROR: Destination folder is required."
        echo ""
    done
else
    # .env exists - offer to use Jill's music folder
    echo "Your Jill bot is configured to use: $JILL_MUSIC_FOLDER"
    echo ""
    echo "Where should converted .opus files be saved?"
    echo ""
    echo "Options:"
    echo "- Press Enter to use Jill's music folder (recommended)"
    echo "- Type a custom path"
    echo ""
    read -p "Destination folder [$JILL_MUSIC_FOLDER]: " DEST_PATH

    # If empty, use Jill's folder
    if [ -z "$DEST_PATH" ]; then
        DEST_PATH="$JILL_MUSIC_FOLDER"
        echo ""
        echo "Using Jill's music folder: $DEST_PATH"
    fi
fi

# Clean up path
DEST_PATH="${DEST_PATH%\"}"
DEST_PATH="${DEST_PATH#\"}"

# Add trailing slash if not present
if [[ ! "$DEST_PATH" =~ /$ ]]; then
    DEST_PATH="$DEST_PATH/"
fi

# Create destination folder if needed
if [ ! -d "$DEST_PATH" ]; then
    echo ""
    echo "Destination folder does not exist. Creating: $DEST_PATH"
    if ! mkdir -p "$DEST_PATH" 2>/dev/null; then
        echo "ERROR: Could not create destination folder."
        echo "Please check the path and try again."
        read -p "Press Enter to exit..."
        exit 1
    fi
    echo "Folder created successfully."
    sleep 2
fi

echo ""
sleep 1

# ============================================
# STEP 2: Determine SOURCE folder
# ============================================

echo "========================================"
echo "Source Folder Selection"
echo "========================================"
echo ""
echo "Where are your music files located?"
echo "(Subdirectories will be searched automatically)"
echo ""

while true; do
    read -p "Source folder: " SOURCE_PATH

    if [ -z "$SOURCE_PATH" ]; then
        echo ""
        echo "ERROR: Source folder is required."
        echo ""
        continue
    fi

    # Clean up path
    SOURCE_PATH="${SOURCE_PATH%\"}"
    SOURCE_PATH="${SOURCE_PATH#\"}"

    # Add trailing slash if not present
    if [[ ! "$SOURCE_PATH" =~ /$ ]]; then
        SOURCE_PATH="$SOURCE_PATH/"
    fi

    # Validate source folder
    if [ ! -d "$SOURCE_PATH" ]; then
        echo ""
        echo "ERROR: Folder does not exist: $SOURCE_PATH"
        echo "Please check the path and try again."
        echo ""
        continue
    fi

    break
done

# ============================================
# STEP 3: Scan for available formats
# ============================================

echo ""
echo "Scanning for audio files..."
echo ""

# Supported formats to scan for
SCAN_FORMATS="mp3 flac wav m4a ogg opus wma aac aiff ape"
FOUND_FORMATS=""
declare -A FOUND_COUNTS

for format in $SCAN_FORMATS; do
    count=$(find "$SOURCE_PATH" -type f -iname "*.$format" 2>/dev/null | wc -l)

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
    echo "ERROR: No audio files found in: $SOURCE_PATH"
    echo ""
    echo "Supported formats: $SCAN_FORMATS"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# ============================================
# STEP 4: Format Selection
# ============================================

echo ""
echo "========================================"
echo "Audio Format Selection"
echo "========================================"
echo ""
echo "Jill supports MP3, FLAC, WAV, M4A, OGG, and OPUS formats."
echo ""
echo "HOWEVER, converting to .opus format is HIGHLY RECOMMENDED!"
echo ""
echo "When using .opus, you will experience:"
echo "  - WAY fewer audio artifacts and warping issues (if any)"
echo "  - Lower CPU usage (important on lower-end systems)"
echo "  - Best audio quality (.opus is Discord's native format)"
echo "  - Often smaller file sizes"
echo ""
echo "Other formats will technically work, but are NOT recommended."
echo ""
echo "Which audio formats would you like to convert to .opus?"
echo ""
echo "Available formats in your source folder: $FOUND_FORMATS"
echo ""
echo "Enter formats separated by spaces (e.g., flac mp3 wav)"
echo "Or type 'all' to convert all found formats"
echo "Or press Enter to cancel"
echo ""
read -p "Formats to convert: " USER_FORMATS

# Check if user wants to cancel
if [ -z "$USER_FORMATS" ]; then
    echo ""
    echo "Conversion cancelled."
    read -p "Press Enter to exit..."
    exit 0
fi

# Handle 'all' option
if [[ "$USER_FORMATS" =~ ^[Aa][Ll][Ll]$ ]]; then
    USER_FORMATS="$FOUND_FORMATS"
    echo ""
    echo "Converting all found formats: $FOUND_FORMATS"
fi

# ============================================
# STEP 5: Check for FFmpeg
# ============================================

echo ""
echo "Checking for FFmpeg..."
if ! command -v ffmpeg &>/dev/null; then
    echo "ERROR: FFmpeg is not installed or not in PATH."
    echo ""
    echo "Please install FFmpeg to use this converter:"
    echo "  Debian/Ubuntu: sudo apt install ffmpeg"
    echo "  Fedora: sudo dnf install ffmpeg"
    echo "  Arch: sudo pacman -S ffmpeg"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi
echo "FFmpeg found."
sleep 1

# Check FFmpeg capabilities
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

# ============================================
# STEP 6: Validate and prepare formats
# ============================================

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
    read -p "Press Enter to exit..."
    exit 1
fi

echo ""
echo "Will convert these $FORMAT_COUNT format(s): $FORMATS_TO_CONVERT"
echo ""
sleep 2

# ============================================
# STEP 7: Conversion Process
# ============================================

echo "========================================"
echo "Conversion Process"
echo "========================================"

# Initialize tracking
MASTER_CONVERTED_LIST="/tmp/jill_converted_$$.txt"
rm -f "$MASTER_CONVERTED_LIST" 2>/dev/null
TOTAL_CONVERTED_COUNT=0
FORMATS_CONVERTED=""

# Convert format function
convert_format() {
    local FILE_FORMAT="$1"

    echo ""
    echo "----------------------------------------"
    echo "Processing .$FILE_FORMAT files"
    echo "----------------------------------------"
    echo ""

    # Count files
    FILE_COUNT=$(find "$SOURCE_PATH" -type f -iname "*.$FILE_FORMAT" 2>/dev/null | wc -l)

    if [ "$FILE_COUNT" -eq 0 ]; then
        echo "No .$FILE_FORMAT files found. Skipping."
        sleep 1
        return
    fi

    echo "Found $FILE_COUNT .$FILE_FORMAT file(s) in $SOURCE_PATH and subdirectories."
    echo "Starting conversion..."
    echo ""

    SOURCE_BASE="$SOURCE_PATH"
    SUCCESSFUL=0
    SKIPPED=0
    FAILED=0
    CURRENT_COUNT=0

    while IFS= read -r -d '' file; do
        ((CURRENT_COUNT++))
        CURRENT_FILE="$file"
        REL_PATH="${CURRENT_FILE#$SOURCE_BASE}"
        DEST_FILE_PATH="$DEST_PATH$REL_PATH"
        DEST_DIR="$(dirname "$DEST_FILE_PATH")"
        DEST_FILE="${DEST_FILE_PATH%.*}"
        BASENAME="$(basename "$file")"

        # Create destination directory if needed
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
                echo "\"$file\";$FILE_FORMAT" >> "$MASTER_CONVERTED_LIST"
                ((TOTAL_CONVERTED_COUNT++))
            else
                echo "    ERROR: Failed to convert this file"
                ((FAILED++))
            fi
        fi
    done < <(find "$SOURCE_PATH" -type f -iname "*.$FILE_FORMAT" -print0)

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

# Process each format
for FILE_FORMAT in $FORMATS_TO_CONVERT; do
    convert_format "$FILE_FORMAT"
done

# After all formats processed
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

    # Proceed to deletion phase
    delete_originals
else
    echo ""
    echo "No files were converted."
    echo ""
fi

# Delete originals function
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
    echo "The converted .opus files are safely in: $DEST_PATH"
    echo ""
    echo "Delete ALL $TOTAL_CONVERTED_COUNT original files to free up disk space?"
    echo ""

    read -p "Type YES (in capitals) to delete, or press Enter to keep them: " DELETE_CHOICE

    if [ "$DELETE_CHOICE" != "YES" ]; then
        echo ""
        echo "Original files will be kept."
        rm -f "$MASTER_CONVERTED_LIST" 2>/dev/null
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
        rm -f "$MASTER_CONVERTED_LIST" 2>/dev/null
        sleep 2
        return
    fi

    # Perform deletion
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

    # Clean up
    rm -f "$MASTER_CONVERTED_LIST" 2>/dev/null

    echo ""
    echo "========================================"
    echo "Deletion Complete"
    echo "========================================"
    [ "$DELETED_OK" -gt 0 ] && echo "Successfully deleted: $DELETED_OK files"
    [ "$DELETED_FAIL" -gt 0 ] && echo "Failed to delete: $DELETED_FAIL files"
    echo ""
    sleep 3
}

echo ""
echo "========================================"
echo "Conversion Complete"
echo "========================================"
echo ""
echo "Your .opus files are in: $DEST_PATH"
echo ""
if [ "$ENV_FILE_EXISTS" = true ]; then
    echo "Jill is ready to play your music!"
    echo "Run ./start-jill.sh to start the bot."
else
    echo "Next step: Run ./linux_setup.sh to configure your bot."
fi
echo ""
read -p "Press Enter to exit..."
