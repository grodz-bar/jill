# Linux Manual Setup Guide
#### For automated setup using the wizard, see [Linux Quick Setup](03-Linux-Quick-Setup.md)
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

3. **Verify Python version:**
   ```bash
   python3 --version
   ```

4. You should see **"Python 3.11.x"** or newer

> **Note:** If your version is too old, you may need to install a newer Python version.

---

## Step 2: Get Discord Bot Token and Set Permissions

See [Getting a Discord Token](02-Getting-Discord-Token.md) for instructions on creating a Discord bot and getting your token. You will need this in Step 4.

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

## Step 4: Manual Setup

1. **Navigate to bot directory:**
   ```bash
   cd ~/jill
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   ```

3. **Activate virtual environment:**
   ```bash
   source venv/bin/activate
   ```

4. **Upgrade pip and wheel (recommended):**
   ```bash
   python3 -m pip install -U pip wheel
   ```

5. **Install dependencies:**
   ```bash
   python3 -m pip install -r requirements.txt
   ```

6. **Create `.env` file** in the bot folder:
   - Run: `nano .env`
   - Add: `DISCORD_BOT_TOKEN=YOUR-BOT-TOKEN`
   - (Optional) Add: `MUSIC_FOLDER=path/to/music`
> Note: Not adding and changing this line will make Jill use her default music folder `/jill/music/`
   - Save and exit (Ctrl+X, Y, Enter)

7. **Deactivate venv:**
   ```bash
   deactivate
   ```

8. **Create start script** `start-jill.sh`:
   ```bash
   nano start-jill.sh
   ```

   Add these lines:
   ```bash
   #!/bin/bash
   # Jill Discord Bot Launcher

   # Activate virtual environment
   if [ -f "venv/bin/activate" ]; then
       source venv/bin/activate
   else
       echo "ERROR: Virtual environment not found."
       echo "Please run linux_setup.sh first to set up the bot."
       exit 1
   fi

   # Run the bot
   echo "Starting Jill Discord Bot..."
   exec python3 bot.py
   ```

   Save and exit (Ctrl+X, Y, Enter)

9. **Make the script executable:**
   ```bash
   chmod +x start-jill.sh
   ```

---

## Step 5: Convert Your Music

You can run the standalone converter anytime:

1. **Navigate to bot directory:**
   ```bash
   cd ~/jill
   ```

2. **Make converter executable (if not already):**
   ```bash
   chmod +x linux_convert_opus.sh
   ```

3. **Run the converter:**
   ```bash
   ./linux_convert_opus.sh
   ```

4. Follow the prompts to convert your music files

The bot supports MP3, FLAC, WAV, M4A, OGG, and OPUS formats. However, converting to `.opus` is **HIGHLY RECOMMENDED** for:
- **Way** fewer Discord audio bugs (for some reason)
- Lower CPU usage (especially important on Raspberry Pi)
- Best audio quality (Discord-native format, no double compression)
- Higher stability (zero transcoding overhead)

See [Converting to Opus](04-Converting-To-Opus.md) for detailed information about audio conversion.

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

1. **Make sure our run bot script is executable:**
   ```bash
   chmod +x ~/jill/start-jill.sh
   ```

2. **Create systemd service file:**
   ```bash
   sudo nano /etc/systemd/system/jill.service
   ```

3. **Add the following configuration:**

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

4. **Save and exit** (Ctrl+X, Y, Enter in nano)

5. **Reload systemd configuration:**
   ```bash
   sudo systemctl daemon-reload
   ```

6. **Enable the service to start on boot:**
   ```bash
   sudo systemctl enable jill.service
   ```

7. **Start the service:**
   ```bash
   sudo systemctl start jill.service
   ```

8. **Check service status:**
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
- `config/aliases.py` - Command aliases
- `config/features.py` - Turn features on/off
- `config/messages.py` - Bot text responses
- `config/timing.py` - Timing and cooldown settings
- `config/paths.py` - File paths

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

## Raspberry Pi Specific Notes

### Performance
- Tested on a Raspberry Pi 4, barely uses RAM and CPU.

### Audio Quality
- Using pre-encoded `.opus` files means less CPU usage, plus Discord seems to like it better, this is why the format requirements are strict.

### Storage
- SD card should be Class 10 or better (U1/U3 recommended)
- Huge libraries might benefit from a USB SSD

### Networking
- Wired > WiFi
- If using WiFi, see if you drop packets when using Discord (not good)
- Discord voice uses ~96kbps upstream (opus 256kbps gets compressed)

---

## Troubleshooting

For troubleshooting, see [Troubleshooting Guide](06-troubleshooting.md)
