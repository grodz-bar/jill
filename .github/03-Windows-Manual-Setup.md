# Windows Manual Setup Guide (Step-by-Step Commands)

This guide will help you set up jill on Windows 10/11 manually using command-line instructions.
#### For automated setup using the wizard, see [Windows Quick Setup](03-Windows-Quick-Setup.md) (Recommended)

---

## Step 1: Install Python and FFmpeg (Manual Method)

### Install Python

1. Download Python from: [python.org/downloads](https://www.python.org/downloads/)
2. Run the installer
3. **IMPORTANT:** CHECK **"Add Python to PATH"** on the first screen
4. Click **"Install Now"**
5. Wait for installation to complete
6. Click **"Close"**

### Adding Python to PATH Manually (if you forgot to check the box)

1. Find your Python installation directory (usually `C:\Users\YourName\AppData\Local\Programs\Python\Python3XX\`)
2. Press Windows key, search **"Environment Variables"**
3. Click **"Edit the system environment variables"**
4. Click **"Environment Variables"** button
5. Under "System variables", find and select **"Path"**, then click **"Edit"**
6. Click **"New"** and add your Python directory path
7. Click **"New"** again and add your Python Scripts directory (same path but add `\Scripts` at the end)
8. Click **OK** on all windows
9. **Restart your computer** for changes to take effect

### Verify Python Installation

1. Press **Windows key + R**
2. Type `cmd` and press Enter
3. Type: `python --version`
4. You should see **"Python 3.11+"** (e.g., 3.12.x/3.13.x/3.14.x)
5. Type: `python -m pip --version`
6. You should see "pip" with a version number
7. Close the Command Prompt window

**If `python --version` doesn't work:**
- Restart your computer (PATH change might need a reboot)
- Reinstall Python and choose **"Add to PATH"** if prompted
- Try: `python3 --version`
- Or see [Troubleshooting](06-troubleshooting.md) for manual PATH configuration

### Install FFmpeg

1. Download FFmpeg from: [ffmpeg.org/download.html](https://ffmpeg.org/download.html#build-windows)
   (Click "Windows builds from gyan.dev" or similar trusted source)
2. Download the "ffmpeg-release-essentials.zip" file
3. Extract the zip file to `C:\ffmpeg`
   (You should have `C:\ffmpeg\bin\ffmpeg.exe` when done)
4. **Add FFmpeg to PATH:**
   - Press Windows key, search **"Environment Variables"**
   - Click **"Edit the system environment variables"**
   - Click **"Environment Variables"** button
   - Under "System variables", find and select **"Path"**, then click **"Edit"**
   - Click **"New"** and add: `C:\ffmpeg\bin`
   - Click **OK** on all windows
5. **Restart your computer** for changes to take effect

### Verify FFmpeg Installation

1. Press **Windows key + R**
2. Type `cmd` and press Enter
3. Type: `ffmpeg -version`
4. You should see FFmpeg version information
5. Close the Command Prompt window

**If `ffmpeg -version` doesn't work:**
- Restart your computer (PATH change might need a reboot)
- Verify `C:\ffmpeg\bin\ffmpeg.exe` exists
- Or see [Troubleshooting](06-troubleshooting.md) for more help

---

## Step 2: Get Discord Bot Token

See [Getting a Discord Token](02-Getting-Discord-Token.md) for instructions on creating a Discord bot and getting your token. You will need this in Step 4.

---

## Step 3: Download Bot

Download the bot to your system:

### Download Release ZIP

1. Go to the project's releases page
2. Download the latest release ZIP file
3. Extract the zip file to `C:\jill\`

> **Note:** Ensure files are in `C:\jill\` (not `C:\jill\jill\`)
>
> **Note:** Extract jill to any folder you want, but this guide assumes she's in `C:\jill\`.

---

## Step 4: Manual Setup


1. **Open CMD and navigate to bot directory:**
   ```cmd
   cd C:\jill
   ```

2. **Create virtual environment:**
   ```cmd
   python -m venv venv
   ```

3. **Activate virtual environment:**
   ```cmd
   venv\Scripts\activate
   ```

4. **Install dependencies:**
   ```cmd
   python -m pip install -r requirements.txt
   ```

5. **Create `.env` file** in `C:\jill\`:
   - Create a file named `.env` (including the dot)
   - Add: `DISCORD_BOT_TOKEN=YOUR-BOT-TOKEN`
   - (Optional) Add: `MUSIC_FOLDER=C:\jill\music\`
> Note: Not adding and changing this line will make Jill use her default music folder `\jill\music\` (keeps her portable)

6. **Create start script** `start-jill.bat` in `C:\jill\`:
   - Create a file named `start-jill.bat`
   - Add these lines:
     ```batch
     @echo off
     if not exist "venv\Scripts\activate.bat" (
         echo ERROR: Virtual environment not found.
         echo Please run win_setup.bat first to set up the bot.
         pause
         exit /b 1
     )
     call venv\Scripts\activate
     echo Starting Jill Discord Bot...
     python bot.py
     pause
     ```

---

## Step 5: Convert Your Music

You can run the standalone converter anytime:

1. Navigate to `C:\jill\` in File Explorer
2. Double-click **"win_convert_opus.bat"**
3. Follow the prompts to convert your music files

The bot supports MP3, FLAC, WAV, M4A, OGG, and OPUS formats. However, converting to `.opus` is **HIGHLY RECOMMENDED** for:
- **Way** fewer Discord audio bugs
- Lower CPU usage
- Best audio quality

See [Converting to Opus](04-Converting-To-Opus.md) for information about audio conversion and steps to do it manually.

---

## Step 6: File Naming Format

**IMPORTANT:** Your music files MUST follow this naming format for proper playback!

Files MUST start with numbers for proper sorting. The bot expects:

```
01 - Track Name.opus
02 - Track Name.opus
03 - Track Name.opus
...
10 - Track Name.opus
```

### Format Rules

- Start with digits (01, 02, 03... or 1, 2, 3...)
- Follow with space, dash, space: `" - "`
- Then your track name
- End with `.opus` extension (or other supported format)

### Examples

**Good names:**
- ✓ `01 - Hopes and Dreams.opus`
- ✓ `02 - Every Day Is Night.opus`
- ✓ `10 - Drive Me Wild.opus`

**Bad names:**
- ✗ `Hopes and Dreams.opus` (no number - won't sort correctly)
- ✗ `Track 01.opus` (number not at start)
- ✗ `Song_01.opus` (number not at start)

> **Note:** If you're using **PLAYLISTS** (subfolders inside your music folder), they should also use the same numeric naming format.

**Batch Renaming Tip:** PowerRename from Microsoft PowerToys can batch-rename files easily on Windows.

---

## Step 7: Run the Bot

1. Navigate to `C:\jill\` in File Explorer
2. Double-click **"start-jill.bat"**

You should see:
- `"Bot connected as YourBot#1234"`
- `"Discovered X playlists with Y total songs"` (or `"Loaded X songs from music folder"`)

To stop the bot, press **Ctrl+C** in the console window.

---

## Step 8: Auto-Start on Boot (Optional)

**Note:** Do this so bot will start automatically after Windows starts.

### Create a Windows Task Scheduler task:

1. Open **Task Scheduler** (search "Task Scheduler" in Start menu)
2. Click **"Create Basic Task"**
3. Name: **"Jill Discord Bot"**
4. Trigger: **"When the computer starts"**
5. Action: **"Start a program"**
6. Program: `C:\jill\start-jill.bat`
7. Finish

---

## Updating the Bot

### To update the bot:

1. Stop the bot (Ctrl+C if running manually, or disable Task Scheduler task)
2. Download [latest release](https://github.com/grodz-bar/jill/releases/latest)
3. Replace files
> Make sure to keep your your `.env` file and `music` folder.
4. Restart the bot

### To update dependencies:

1. Open Command Prompt
2. Navigate to bot directory:
   ```cmd
   cd C:\jill
   ```
3. Activate virtual environment:
   ```cmd
   C:\jill\venv\Scripts\activate
   ```
4. Update packages:
   ```cmd
   python -m pip install -r requirements.txt --upgrade
   ```

---

## Customization

### How to Edit Config Files

Config files are just text files - edit them with Notepad:
1. Right-click any `.py` file in `C:\jill\config\`
2. Select **"Open with"** → **"Notepad"**
3. Make changes and save (Ctrl+S)

### Config Files

Edit files in the `config/` folder to customize:
- `config/common/basic_settings.py` - Bot identity, music folder, feature toggles, logging
- `config/common/audio_settings.py` - FFmpeg options, voice health monitoring
- `config/common/advanced.py` - Bot token, persistence paths, watchdog intervals
- `config/common/messages.py` - Shared messages (both modes)
- `config/common/spam_protection.py` - Spam protection (Layer 3 serial queue, both modes)
- `config/prefix/features.py` - Turn features on/off (prefix mode)
- `config/prefix/messages.py` - Prefix-specific bot text responses
- `config/prefix/aliases.py` - Command aliases (prefix mode only)
- `config/prefix/spam_protection.py` - Command cooldowns (Layers 1-2, prefix mode)
- `config/prefix/cleanup.py` - Message cleanup timing and TTL settings (prefix mode)
- `config/slash/features.py` - Turn features on/off (slash mode)
- `config/slash/messages.py` - Slash-specific bot text responses, button labels
- `config/slash/timing.py` - Update throttling, interaction delays, button cooldowns (slash mode)

Make sure to restart bot after changes.

For bot profile picture/banner/etc, just change it on the developer portal:
https://discord.com/developers/applications

---

## Troubleshooting

For troubleshooting, see [Troubleshooting Guide](06-troubleshooting.md)
