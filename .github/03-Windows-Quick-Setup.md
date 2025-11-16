# Windows Quick Setup Guide (Using Wizard)

This guide will help you set up jill on Windows 10/11.

###### For manual setup instructions, see [Windows Manual Setup](03-Windows-Manual-Setup.md)

---

## Step 1: Install Python and FFmpeg

### THE EASY WAY (Recommended)

1. Press the Windows key
2. Type **"PowerShell"** and press Enter
3. Copy and paste this command, then press Enter:
   ```powershell
   winget install Python.Python.3.13 && winget install Gyan.FFmpeg
   ```
4. Wait for it to finish (you'll see "Successfully installed" messages)
5. Close PowerShell
6. **Restart your computer**
7. Done. Both Python and FFmpeg are installed with PATH set automatically

> #### Verify it worked
>
> 1. Press **Windows key**, type **"cmd"** and press Enter
> 2. Type `python --version`
> 3. Type `ffmpeg -version`
> 4. If both show version numbers, you're good.

### If the Easy Way Doesn't Work

If you can't use winget (older Windows versions or it's not installed), see the manual installation instructions in [Windows Manual Setup](03-Windows-Manual-Setup.md) under "Step 1: Install Python and FFmpeg (Manual Method)".

---

## Step 2: Get Discord Bot Token

See [Getting a Discord Token](02-Getting-Discord-Token.md) for instructions on creating a Discord bot and getting your token. You will need this for the setup wizard.

---

## Step 3: Download Bot

Download the bot to your system:

### Download Release ZIP

1. Go to the project's releases page
2. Download the latest release ZIP file
3. Extract the zip file to `C:\jill\`

> **Note:** Ensure files are in `C:\jill\` (not `C:\jill\jill\`)
>
> **Note:** You can extract jill into any folder you want, but this guide assumes you've placed her in `C:\jill\`.

---

## Step 4: Run Setup Wizard

1. Navigate to `C:\jill\` in File Explorer
2. Double-click **"win_setup.bat"**
3. Follow the interactive prompts

**When done** → Continue to **Step 5**

### If Setup Fails

- Read the error message shown in the console
- See [Troubleshooting](06-troubleshooting.md) for common issues
- Verify Python 3.11+ is installed: `python --version`
- Try the manual setup guide: [Windows Manual Setup](03-Windows-Manual-Setup.md)

---

## Step 5: Convert Your Music

**If you skipped the optional conversion step during setup**, you can run the standalone converter anytime:

1. Navigate to `C:\jill\` in File Explorer
2. Double-click **"win_convert_opus.bat"**
3. Follow the prompts to convert your music files

The bot supports MP3, FLAC, WAV, M4A, OGG, and OPUS formats. However, converting to `.opus` is **HIGHLY RECOMMENDED** for:
- **Way** fewer Discord audio bugs
- Lower CPU usage
- Best audio quality

See [Converting to Opus](04-Converting-To-Opus.md) for information about audio conversion.
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

> **Note:** If you're using PLAYLISTS (subfolders inside your music folder), they should also use the same numeric naming format.

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
3. Replace files (keep your `.env` file)
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
