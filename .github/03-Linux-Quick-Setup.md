# Linux Quick Setup Guide (Using Wizard)
###### For manual setup instructions, see [Linux Manual Setup](03-Linux-Manual-Setup.md)
---
This guide works for:
- Debian/Ubuntu Linux
- Raspberry Pi OS

---

## Step 1: System Requirements

### Install Required Packages

1. **Update package list:**
   ```bash
   sudo apt update
   ```

2. **Install Python and dependencies:**
   ```bash
   sudo apt install -y python3 python3-pip python3-venv ffmpeg git
   ```

   > **Note:** On some distros (Debian 10, Ubuntu 18.04), the venv module is packaged separately. If you get "No module named venv", install it:
   > ```bash
   > sudo apt install -y python3.11-venv
   > ```
   > (Replace 3.11 with your Python version)

---

## Step 2: Get Discord Bot Token and Set Permissions

See [Getting a Discord Token](02-Getting-Discord-Token.md) for instructions on creating a Discord bot and getting your token. You will need this for the setup wizard.

---

## Step 3: Download Bot

Download the bot to your home directory:
> **Note:** Extract jill to any folder you want, but this guide assumes she's in `~/jill/`.
> 
> **Note:** Ensure files are in `~/jill/` (not `~/jill/jill/`)

#### Method 1 - Using Git

1. **Navigate to home directory:**
   ```bash
   cd ~
   ```

2. **Clone the repository:**
   ```bash
   git clone https://github.com/grodz-bar/jill.git jill
   ```

#### Method 2 - Download Release ZIP

1. Download the latest release ZIP from the releases page
2. Extract the zip file to `~/jill/`

---

## Step 4: Run Setup Wizard

The wizard will automatically:
- Create a virtual environment (`venv/`)
- Install required Python packages
- Generate your `.env` configuration file
- Create the music folder if it doesn't exist
- Optionally convert your audio files to `.opus`

### Running the Wizard

1. **Navigate to bot directory:**
   ```bash
   cd ~/jill
   ```

2. **Run the setup wizard:**
   ```bash
   ./linux_setup.sh
   ```

3. Follow the interactive prompts

**When done** → Continue to **Step 5**

### If Setup Fails

- Read the error message shown in the terminal
- See [Troubleshooting](06-troubleshooting.md) for common issues
- Try the manual setup guide: [Linux Manual Setup](03-Linux-Manual-Setup.md)

---

## Step 5: Convert Your Music

**If you skipped the optional conversion step during setup**, you can run the standalone converter anytime:

1. **Run the converter:**
   ```bash
   ./linux_convert_opus.sh
   ```

4. Follow the prompts to convert your music files

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

> **Note:** If you're using PLAYLISTS (subfolders inside your music folder), they should also use the same numeric naming format.

**Batch Renaming Tip:** On Linux, tools like `rename`, `mmv`, or `vidir` help batch-rename quickly.

---

## Step 7: Run the Bot

1. **Navigate to bot directory:**
   ```bash
   cd ~/jill
   ```

2. **Run the bot:**
   ```bash
   ./start-jill.sh
   ```

You should see:
- `"Bot connected as YourBot#1234"`
- `"Discovered X playlists with Y total songs"` (or `"Loaded X songs from music folder"`)

To stop the bot, press **Ctrl+C** in the terminal.

---

## Step 8: Auto-Start with systemd (Optional)

**Note:** Do this so bot will start automatically after a machine boot.


1. **Create systemd service file:**
   ```bash
   sudo nano /etc/systemd/system/jill.service
   ```

2. **Add the following configuration:**

   > **WARNING:** Before pasting, you MUST replace these placeholders:
   > - `YOUR-USERNAME` → your actual Linux username (appears 5 times below)
   > - `YOUR-BOT-TOKEN` → your Discord bot token (if using optional method)
   > - `/home/YOUR-USERNAME/jill/` → actual path if stored elsewhere

   ```ini
   [Unit]
   Description=Jill Discord Bot
   After=network-online.target
   Wants=network-online.target

   [Service]
   Type=simple
   User=YOUR-USERNAME
   WorkingDirectory=/home/YOUR-USERNAME/jill/
   ExecStart=/home/YOUR-USERNAME/jill/start-jill.sh
   StandardOutput=append:/home/YOUR-USERNAME/jill/bot.log
   StandardError=append:/home/YOUR-USERNAME/jill/bot.log
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

   **OPTIONAL:** If you don't want to use the `.env` file (from the default setup), you can place these lines under `[Service]` instead:
   ```ini
   Environment="DISCORD_BOT_TOKEN=YOUR-BOT-TOKEN"
   Environment="MUSIC_FOLDER=/home/YOUR-USERNAME/jill/music/"
   ```

3. **Save and exit** (Ctrl+X, Y, Enter in nano)

4. **Reload systemd configuration:**
   ```bash
   sudo systemctl daemon-reload
   ```

5. **Enable the service to start on boot:**
   ```bash
   sudo systemctl enable jill.service
   ```

6. **Start the service:**
   ```bash
   sudo systemctl start jill.service
   ```

7. **Check service status:**
   ```bash
   sudo systemctl status jill.service
   ```

---

## Customization

### How to Edit Config Files

Config files are just text files - edit them with nano:

1. ```bash
   cd ~/jill/config
   ```
2. ```bash
   ls
   ```
3. ```bash
   nano features.py
   ```
4. Make changes and save (Ctrl+X, Y, Enter)

### Config Files

Files in the `/config/` folder to customize:
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

Make sure to restart bot after changes:

```bash
sudo systemctl restart jill.service
```

For bot profile picture/banner/etc, change it on the developer portal:
https://discord.com/developers/applications

---

## Updating the Bot

To update to a new version:

```bash
cd ~/jill
git pull

# Restart the service
sudo systemctl restart jill.service

# Check logs to ensure it started correctly
tail -f ~/jill/bot.log
```
---

## Troubleshooting

For troubleshooting, see [Troubleshooting Guide](06-troubleshooting.md)

---

### Raspberry Pi Specific Notes

### Performance
- Tested on a Raspberry Pi 4, barely uses RAM and CPU.

#### Audio Quality
- `.opus` files means less CPU usage, plus Discord seems to like them A LOT better.

#### Storage
- SD card should be Class 10 or better (U1/U3 recommended)
- Huge libraries might benefit from a USB SSD

#### Networking
- Wired > WiFi
- If using WiFi, see if you drop packets when using Discord (not good)
- Discord voice uses ~96kbps upstream (opus 256kbps gets compressed)

