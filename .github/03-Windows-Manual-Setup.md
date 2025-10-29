# Windows Manual Setup Guide (Step-by-Step Commands)

This guide will help you set up jill on Windows 10/11 manually using command-line instructions.
#### For automated setup using the wizard, see [Windows Quick Setup](03-Windows-Quick-Setup.md) (Recommended)

---

## Step 1: Install Python

Download and install Python from: [python.org/downloads](https://www.python.org/downloads/)

### Important Installation Notes

- When installing, **CHECK "Add Python to PATH"** on the first screen
- Python's New "Python Install Manager" should do this automatically
- This is critical for the bot to work

### Adding Python to PATH Manually (if needed)

1. Find your Python installation directory (usually `C:\Users\YourName\AppData\Local\Programs\Python\Python3XX\`)
2. Press Windows key, search **"Environment Variables"**
3. Click **"Edit the system environment variables"**
4. Click **"Environment Variables"** button
5. Under "System variables", find and select **"Path"**, then click **"Edit"**
6. Click **"New"** and add your Python directory path
7. Click **"New"** again and add your Python Scripts directory (same path but add `\Scripts` at the end)
8. Click **OK** on all windows

### Verify Installation

1. Press **Windows key + R**
2. Type `cmd` and press Enter
3. Type `python --version` and press Enter
4. You should see **"Python 3.11+"** (e.g., 3.12.x/3.13.x/3.14.x)
5. Type `python -m pip --version` and press Enter
6. You should see "pip" with a version number
7. Close the Command Prompt window

### If `python --version` doesn't work:

- Restart your computer (**PATH change might need a reboot**)
- Reinstall Python and choose **"Add to PATH"** if prompted
- Try: `python3 --version`
- Or see [Troubleshooting](06-troubleshooting.md)

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
- `config/aliases.py` - Command aliases
- `config/messages.py` - Bot text responses
- `config/features.py` - Turn features on/off
- `config/timing.py` - Timing and cooldown settings (advanced)
- `config/paths.py` - File paths (advanced)

Make sure to restart bot after changes.

For bot profile picture/banner/etc, just change it on the developer portal:
https://discord.com/developers/applications

---

## Troubleshooting

For troubleshooting, see [Troubleshooting Guide](06-troubleshooting.md)
