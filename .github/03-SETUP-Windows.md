# Windows Setup Guide

This guide will help you set up jill on Windows 10/11.

---

## Step 1: Install Python

Download and install Python from: [python.org/downloads](https://www.python.org/downloads/)

### Verify Installation

1. Press **Windows key + R**
2. Type `cmd` and press Enter
3. Type `python --version` and press Enter
4. You should see **"Python 3.11+"** (e.g., 3.12.x/3.13.x/3.14.x)
5. Type `python -m pip --version` and press Enter
6. You should see "pip" with a version number
7. Close the Command Prompt window

### If `python --version` doesn't work:

- Restart your computer (PATH change might need a reboot)
- Reinstall Python and choose **"Add to PATH"** if prompted
- Try: `python3 --version`
- Or see [Troubleshooting](06-troubleshooting.md) for manual PATH configuration

---

## Step 2: Get Discord Bot Token

See [Getting Discord Token](02-Getting-Discord-Token.md) for instructions on creating a Discord bot and getting your token. You will need this later.

---

## Step 3: Download Bot

Download the bot to your system:

### Method 1 - Download Release ZIP

1. Go to the project's releases page
2. Download the latest release ZIP file
3. Extract the zip file to `C:\jill\`

> **Note:** Ensure files are in `C:\jill\` (not `C:\jill\jill\`)

### Method 2 - Using Git

1. Open Command Prompt
2. Navigate to `C:\`:
   ```cmd
   cd C:\
   ```
3. Clone the repository:
   ```cmd
   git clone https://github.com/grodz-bar/jill.git jill
   ```

> **Note:** You can extract jill into any folder you want, but this guide assumes you've placed it in `C:\jill\`, change instructions to fit your use case.

---

## Step 4: Run Setup Wizard (Recommended)

The wizard will automatically:
- Create a virtual environment (`venv\`)
- Install required Python packages
- Generate your `.env` configuration file
- Create the music folder if it doesn't exist
- Optionally convert your audio files to `.opus`

### Prerequisites

- Discord bot token (from Step 2)
- Python 3.11 or newer installed and added to PATH
- FFmpeg (only needed if converting audio to `.opus`) - See [Converting to Opus](04-Converting-To-Opus.md) for installation guide

### Running the Wizard

1. Navigate to `C:\jill\scripts\` in File Explorer
2. Double-click **"win_setup.bat"**
3. Follow the interactive prompts
4. Setup completed successfully when you see:
   ```
   ========================================
   SETUP COMPLETED - SAFE TO CLOSE SCRIPT
   ========================================
   ```

**If successful** → Continue to **Step 5**

### If Setup Fails

- Read the error message shown in the console
- See [Troubleshooting](06-troubleshooting.md) for common issues
- Verify Python 3.11+ is installed: `python --version`
- Try **Alternative Step 4 (Manual Setup)** below

---

## Alternative Step 4: Manual Setup

If you prefer to set up manually, follow these steps:

1. **Open Command Prompt**

2. **Navigate to bot directory:**
   ```cmd
   cd C:\jill
   ```

3. **Create virtual environment:**
   ```cmd
   python -m venv venv
   ```

4. **Activate virtual environment:**
   ```cmd
   C:\jill\venv\Scripts\activate
   ```

5. **Install dependencies:**
   ```cmd
   python -m pip install -r requirements.txt
   ```

6. **Create .env file in `C:\jill\`:**
   - Create a file named `.env` (including the dot)
   - Add: `DISCORD_BOT_TOKEN=YOUR-BOT-TOKEN`
   - (Optional) Add: `MUSIC_FOLDER=C:\jill\music\` (leave blank to use default: `music\` folder)

7. Proceed to **Step 5** of this setup guide

---

## Step 5: Add Your Music Files (If Needed)

Convert your files to `.opus` by following the [Converting to Opus](04-Converting-To-Opus.md) guide.

**EVEN** if you used the WIZARD (`win_setup.bat`) you need to make sure your `.opus` music files follow the naming format described below.

> **Note:** This step only covers music files, but if you're using **PLAYLISTS** (as in, subfolders inside your jill music folder), it is HIGHLY recommended that they use the same naming format described below.

### File Naming Format

Files MUST start with numbers for proper sorting. The bot expects:

```
01 - Track Name.opus
02 - Track Name.opus
03 - Track Name.opus
...
10 - Track Name.opus
```

**Format rules:**
- Start with digits (01, 02, 03... or 1, 2, 3...)
- Follow with space, dash, space: `" - "`
- Then your track name
- End with `.opus` extension

**Example good names:**
- ✅ `01 - Hopes and Dreams.opus`
- ✅ `02 - Every Day Is Night.opus`
- ✅ `10 - Drive Me Wild.opus`

**Example bad names:**
- ❌ `Hopes and Dreams.opus` (no number - won't sort correctly)
- ❌ `Track 01.opus` (number not at start)
- ❌ `Song_01.opus` (number not at start)

> **Note:** PowerRename from Microsoft PowerToys can batch‑rename files.

---

## Step 6: Run the Bot

1. Navigate to `C:\jill\` in File Explorer
2. Double-click `scripts\win_run_bot.bat`

You should see:
- "Bot connected as YourBot#1234"
- "Music folder found: C:\jill\music"

**To stop the bot**, press `Ctrl+C` in the console window.

---

## Step 7: Auto-Start on Boot (Optional)

> **Note:** Do this so bot will start automatically after Windows starts.

### Create a Windows Task Scheduler task:

1. Open **Task Scheduler** (search "Task Scheduler" in Start menu)
2. Click **"Create Basic Task"**
3. Name: `Jill Discord Bot`
4. Trigger: **"When the computer starts"**
5. Action: **"Start a program"**
6. Program: `C:\jill\scripts\win_run_bot.bat`
7. **Finish**

---

## Updating the Bot

### To update the bot:

1. Stop the bot (Ctrl+C if running manually, or disable Task Scheduler task)
2. Download new version
3. Replace files (keep your `.env` file)
4. Restart the bot

### To update dependencies:

1. **Open Command Prompt**

2. **Navigate to bot directory:**
   ```cmd
   cd C:\jill
   ```

3. **Activate virtual environment:**
   ```cmd
   C:\jill\venv\Scripts\activate
   ```

4. **Update packages:**
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

### Edit files in the `config/` folder to customize:

- `config/aliases.py` - Command aliases
- `config/messages.py` - Bot text responses
- `config/features.py` - Turn features on/off
- `config/timing.py` - Timing and cooldown settings (advanced)
- `config/paths.py` - File paths (advanced)

**Make sure to restart bot after changes.**

For bot profile picture/banner/etc, just change it on the [Developer Portal](https://discord.com/developers/applications).

---

## Troubleshooting

For troubleshooting, see [Troubleshooting](06-troubleshooting.md)
