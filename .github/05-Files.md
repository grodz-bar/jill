# Documentation Files

A comprehensive reference of the bot's directory structure and file descriptions.

---

## Directory Structure

```
/jill/
├── bot.py                            # Main bot file
├── requirements.txt                  # Python dependencies
├── /scripts/                         # Setup and launcher scripts
│   ├── win_setup.bat                 # Windows setup wizard
│   ├── linux_setup.sh                # Linux setup wizard
│   ├── win_run_bot.bat               # Windows launcher
│   └── linux_run_bot.sh              # Linux launcher
├── .env                              # Bot configuration (created during setup)
├── /config/                          # Configuration folder (USER CUSTOMIZATION)
│   ├── __init__.py                   # Python package marker
│   ├── aliases.py                    # Command aliases
│   ├── features.py                   # Feature toggles
│   ├── messages.py                   # Bot messages and responses
│   ├── timing.py                     # Timing and cooldown settings
│   └── paths.py                      # File paths configuration
├── /handlers/                        # Command handlers (implementation)
│   ├── __init__.py                   # Python package marker
│   └── commands.py                   # All bot commands
├── /venv/                            # Python virtual environment (created during setup)
├── .env                              # Bot configuration (created during setup)
├── last_channels.json                # Channel persistence (auto-created, managed)
├── last_playlists.json               # Playlist persistence (auto-created, managed)
├── /core/                            # Core music player (jill's code)
│   ├── __init__.py                   # Python package marker
│   ├── player.py                     # MusicPlayer class
│   ├── playback.py                   # Playback functions
│   └── track.py                      # Track class and library loading
├── /systems/                         # Specialized systems (jill's code)
│   ├── __init__.py                   # Python package marker
│   ├── spam_protection.py            # 5-layer spam protection
│   ├── cleanup.py                    # Message cleanup (TTL + history)
│   ├── voice_manager.py              # Voice operations & auto-pause
│   └── watchdog.py                   # Playback monitoring
├── /utils/                           # Utility helpers (jill's code)
│   ├── __init__.py                   # Python package marker
│   ├── discord_helpers.py            # Discord API helpers
│   ├── persistence.py                # Channel persistence
│   └── context_managers.py           # Context helpers
├── /README/                          # Documentation folder
│   ├── 01-README.txt                 # Main overview
│   ├── 02-Getting-Discord-Token.txt  # Bot token guide
│   ├── 03-SETUP-Windows.txt          # Windows setup guide
│   ├── 03-SETUP-Linux.txt            # Linux setup guide
│   ├── 04-Converting-To-Opus.txt     # Audio conversion guide
│   ├── 05-Files.txt                  # This file (reference)
│   └── 06-troubleshooting.txt        # Troubleshooting guide
└── /music/                           # Default music folder location
    ├── 01 - Track Name.opus
    ├── 02 - Track Name.opus
    └── ...
    │ # OR if you have multiple playlists:
    ├── 01 - Album Name/
    │   ├── 01 - Track Name.opus
    │   └── 02 - Track Name.opus
    ├── 02 - OST/
    │   └── 01 - Track Name.opus
    └── ...
```

---

## Files Description

### Documentation Files

#### `01-README.txt`
Main overview - start here! Quick feature list, commands, and basic info.

#### `02-Getting-Discord-Token.txt`
Quick guide for creating a Discord bot and getting your token.

#### `03-SETUP-Windows.txt`
Detailed setup guide for Windows.

#### `03-SETUP-Linux.txt`
Detailed setup guide for Linux/Pi.

#### `04-Converting-To-Opus.txt`
Instructions for converting your music to `.opus` format. (Windows/Linux)

> **Note:** The setup wizards can do this automatically for you.

#### `05-Files.txt`
This file - comprehensive reference of directory structure and file descriptions.

#### `06-troubleshooting.txt`
Troubleshooting guide for common issues.

---

### Setup Scripts

#### `scripts/win_setup.bat`
Interactive setup wizard for Windows. Creates venv inside bot folder, installs dependencies, configures bot token and music folder (default: `music/` subfolder), and optionally converts audio files. Bot folder is fully portable.

#### `scripts/linux_setup.sh`
Interactive setup wizard for Linux. Creates venv inside bot folder, installs dependencies, configures bot token and music folder (default: `music/` subfolder), and optionally converts audio files. Bot folder is fully portable.

#### `scripts/win_run_bot.bat`
Simple launcher script for Windows. Activates venv and runs the bot.

#### `scripts/linux_run_bot.sh`
Simple launcher script for Linux. Activates venv and runs the bot.

---

### Configuration Files

#### `.env.example`
Sample environment configuration file. Copy or rename to `.env` and fill in your bot token (music folder optional - uses default `music/` folder inside bot directory if not specified).

#### `requirements.txt`
Python package dependencies for easy installation.

Use with: `pip install -r requirements.txt`

---

### Config Folder

Configuration files for easy customization:

- **`config/aliases.py`** — Command aliases customization.
- **`config/features.py`** — Feature toggles (turn features on/off)
- **`config/messages.py`** — Customize responses, messages, and drink emojis.
- **`config/timing.py`** — Timing and cooldown settings. (Advanced)
- **`config/paths.py`** — File paths and storage location. (Advanced)

---

### Auto-Created Files

#### `last_channels.json`
Channel persistence storage file (auto-created). Stores the last used text channel per Discord server. Allows cleanup features to resume after bot restart. Automatically managed - do not edit manually.

#### `last_playlists.json`
Playlist persistence storage file (auto-created). Stores the last used playlist per Discord server. Allows the bot to remember which playlist each server was using after restart. Automatically managed - do not edit manually.

---

### Other Files

#### `.gitignore`
Tells git which files to ignore (logs, tokens, music, runtime state, caches, etc.) Prevents accidentally committing sensitive data and temporary files.

---

## Setup Order (Recommended)

1. Read [README](01-README.md) (get familiar with the bot)
2. Follow [Getting Discord Token](02-Getting-Discord-Token.md) (get your bot token)
3. Follow [Linux Setup](03-SETUP-Linux.md) or [Windows Setup](03-SETUP-Windows.md)
4. Run the bot
