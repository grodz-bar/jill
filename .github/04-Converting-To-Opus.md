# How to Manually Convert Music to Opus Format

Linux and Windows guide for converting audio to `.opus` format.

> **Important:** The bot supports multiple audio formats (MP3, FLAC, WAV, M4A, OGG, OPUS). However, converting to .opus is **HIGHLY recommended** for:
> - **Way** fewer Discord audio bugs (for some reason)
> - Lower CPU usage (especially important on Raspberry Pi)
> - Best audio quality (Discord-native format, no double compression)
> - Higher stability (zero transcoding overhead)
>
> Other formats work but require real-time transcoding, which increases CPU usage.


> **NOTE:** The **EASIEST** way to convert your music is to use the standalone converter scripts:
> - **Windows:** Double-click `win_convert_opus.bat` in the bot folder
> - **Linux:** Run `./linux_convert_opus.sh` in the bot folder

---

## Recommended Format Specifications

The recommended `.opus` specifications are:
- **48kHz** sample rate
- **Stereo** (2 channels)
- **256kbps VBR** (Variable Bit Rate)
- **20ms** frame duration

### Why these specifications?

Using the correct format ensures:
- Minimal CPU overhead (native passthrough)
- Better jitter or warping prevention
- Less Discord weirdness

---

## Linux / Raspberry Pi

### Install FFmpeg

1. **Update package list:**
   ```bash
   sudo apt update
   ```

2. **Install ffmpeg:**
   ```bash
   sudo apt install ffmpeg
   ```

### Batch Convert All Files

Convert ALL audio files in a folder to `.opus`:

1. **Navigate to where your music files are stored:**
   ```bash
   cd /path/to/your/music/files
   ```

2. **IMPORTANT:** Change BOTH variables to match your use case:
   - `.mp3` → `.YOURFORMAT`
> **Note:** You need to change TWO variables below:

   ```bash
   for file in *.mp3; do
       ffmpeg -i "$file" -c:a libopus -b:a 256k -ar 48000 -ac 2 -frame_duration 20 "${file%.mp3}.opus"
   done
   ```
   

### Cleanup (Optional)

Remove original files after successful conversion:

1. **Check what file types you have:**
   ```bash
   ls *.mp3 *.flac *.wav *.m4a 2>/dev/null
   ```

2. **Remove files (replace `*.mp3` with YOUR FORMAT):**
   ```bash
   rm *.mp3
   ```

> **WARNING:** This permanently deletes files. Test your `.opus` files first!
> 
> **Note:** The bot accepts `.opus` files with any case (`.opus`, `.OPUS`, `.Opus`).

---

## Windows

### Install FFmpeg

1. Download from: [ffmpeg.org/download.html](https://ffmpeg.org/download.html) and extract to `C:\ffmpeg`

2. **Add to PATH:**
   - Right-click **"This PC"** → Properties
   - **Advanced system settings** → **Environment Variables**
   - Under **System Variables**, find **"Path"** → **Edit**
   - Click **"New"** and add: `C:\ffmpeg\bin`
   - Click **OK** on all windows

3. **Open Command Prompt** (Windows key + R, type `cmd`, press Enter) to test:
   ```cmd
   ffmpeg -version
   ```

### Batch Convert All Files

Convert ALL audio files in a folder to `.opus`:

1. **Open Command Prompt**

2. **Navigate to where your music files are stored:**
   ```cmd
   cd /d "C:\path\to\your\music\files"
   ```

3. **IMPORTANT:** Change BOTH variables to match your use case:
> **Note:** You need to change TWO variables below:
   ```cmd
   for %f in (*.mp3) do ffmpeg -i "%f" -c:a libopus -b:a 256k -ar 48000 -ac 2 -frame_duration 20 "%~nf.opus"
   ```
   
### Cleanup (Optional)

Remove original files after successful conversion:

1. Open **File Explorer** and navigate to your music folder
2. Sort by **"Type"** to group files by extension
3. Select all files of the original format (e.g., all `.mp3` files) and delete them

> **WARNING:** This permanently deletes files. Test your `.opus` files first!
> 
> **Note:** The bot accepts `.opus` files with any case (`.opus`, `.OPUS`, `.Opus`).

---

## Quality Notes

### Source Quality

- **Garbage in, garbage out**
- Use quality sources (320kbps MP3 or FLAC)
- Avoid low-quality YouTube rips

### Opus Bitrate

- **256kbps** is overkill for most music (sounds great)
- Discord compresses to **~96kbps** anyway
- You can use **128kbps** for smaller files: `-b:a 128k`
- Don't go below **96kbps** (noticeable quality loss)

### File Sizes

- 256kbps opus ≈ **1.9 MB per minute**
- 128kbps opus ≈ **0.95 MB per minute**
- Average song ≈ **~5 MB** at 256kbps

> **Note:** It is unclear if bots playing on boosted servers that have their voice channel manually set higher than 96kbps actually benefit from it.

---

## Troubleshooting

For troubleshooting audio conversion issues, see [Troubleshooting](06-troubleshooting.md)
