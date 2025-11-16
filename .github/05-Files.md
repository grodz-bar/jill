# Documentation Files

A comprehensive reference of the bot's directory structure and file descriptions.

---

## Directory Structure

```
/jill/
├── bot.py                            # Main bot file
├── requirements.txt                  # Python dependencies
├── win_setup.bat                     # Windows setup wizard
├── linux_setup.sh                    # Linux setup wizard
├── win_convert_opus.bat              # Windows standalone opus converter
├── linux_convert_opus.sh             # Linux standalone opus converter
├── start-jill.bat                    # Windows launcher (created by setup)
├── start-jill.sh                     # Linux launcher (created by setup)
├── .env                              # Bot configuration (created during setup)
├── /config/                          # Configuration folder (USER CUSTOMIZATION)
│   ├── __init__.py                   # Mode-aware config loader (detects JILL_COMMAND_MODE)
│   ├── /common/                      # Shared configuration (both modes)
│   │   ├── basic_settings.py         # Bot identity, music folder, feature toggles, logging
│   │   ├── audio_settings.py         # FFmpeg options, voice health monitoring
│   │   ├── advanced.py               # Bot token, persistence paths, watchdog intervals
│   │   ├── messages.py               # Shared messages
│   │   ├── spam_protection.py        # Spam protection (Layer 3 serial queue)
│   │   ├── permissions.py            # VA-11 HALL-A themed permission system
│   │   └── filename_patterns.py      # File naming patterns
│   ├── /prefix/                      # Classic mode (!play) configuration
│   │   ├── features.py               # Command prefix, feature toggles
│   │   ├── messages.py               # Prefix-specific bot response text
│   │   ├── aliases.py                # Command aliases
│   │   ├── spam_protection.py        # Command cooldowns (Layers 1-2)
│   │   └── cleanup.py                # Message cleanup timing and TTL settings
│   └── /slash/                       # Modern mode (/play) configuration
│       ├── features.py               # Feature toggles
│       ├── messages.py               # Slash-specific bot response text, button labels
│       ├── timing.py                 # Update throttling, interaction delays, button cooldowns
│       ├── embeds.py                 # Rich embed formatting functions
│       └── buttons.py                # Button component builders
├── /handlers/                        # Command handlers (implementation)
│   ├── __init__.py                   # Python package marker
│   ├── commands.py                   # Classic mode commands (!play)
│   ├── slash_commands.py             # Modern mode commands (/play)
│   └── buttons.py                    # Button interaction handler
├── /venv/                            # Python virtual environment (created during setup)
├── .env                              # Bot configuration (created during setup)
├── last_channels.json                # Channel persistence (prefix mode, auto-created)
├── last_playlists.json               # Playlist persistence (auto-created, managed)
├── last_message_ids.json             # Control panel message IDs (slash mode, auto-created)
├── /core/                            # Core music player (jill's code)
│   ├── __init__.py                   # Python package marker
│   ├── player.py                     # MusicPlayer class
│   ├── playback.py                   # Playback functions
│   └── track.py                      # Track class and library loading
├── /systems/                         # Specialized systems (jill's code)
│   ├── __init__.py                   # Python package marker
│   ├── spam_protection.py            # 4-layer spam protection with guild isolation
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
│   ├── 03-Windows-Quick-Setup.txt    # Windows quick setup guide (wizard)
│   ├── 03-Windows-Manual-Setup.txt   # Windows manual setup guide (step-by-step)
│   ├── 03-Linux-Quick-Setup.txt      # Linux quick setup guide (wizard)
│   ├── 03-Linux-Manual-Setup.txt     # Linux manual setup guide (step-by-step)
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

#### `03-Windows-Quick-Setup.txt`
Windows setup guide using the automated setup wizard (`win_setup.bat`).

#### `03-Windows-Manual-Setup.txt`
Windows setup guide with step-by-step manual commands.

#### `03-Linux-Quick-Setup.txt`
Linux setup guide using the automated setup wizard (`linux_setup.sh`).

#### `03-Linux-Manual-Setup.txt`
Linux setup guide with step-by-step manual commands for Linux/Raspberry Pi.

#### `04-Converting-To-Opus.txt`
Instructions for converting your music to `.opus` format. (Windows/Linux)

> **Note:** The setup wizards can do this automatically for you.

#### `05-Files.txt`
This file - comprehensive reference of directory structure and file descriptions.

#### `06-troubleshooting.txt`
Troubleshooting guide for common issues.

---

### Setup and Launcher Scripts

#### `win_setup.bat`
Interactive setup wizard for Windows. Creates venv inside bot folder, installs dependencies, configures bot token and music folder (default: `music/` subfolder), and optionally converts audio files. Bot folder is fully portable.

#### `linux_setup.sh`
Interactive setup wizard for Linux. Creates venv inside bot folder, installs dependencies, configures bot token and music folder (default: `music/` subfolder), and optionally converts audio files. Bot folder is fully portable.

#### `win_convert_opus.bat`
Standalone opus converter for Windows. Intelligently detects your music folder from `.env` and converts all audio files to `.opus` format recursively. Can be run anytime after setup.

#### `linux_convert_opus.sh`
Standalone opus converter for Linux. Intelligently detects your music folder from `.env` and converts all audio files to `.opus` format recursively. Can be run anytime after setup.

#### `start-jill.bat`
Launcher script for Windows (created during setup). Activates venv and runs the bot.

#### `start-jill.sh`
Launcher script for Linux (created during setup). Activates venv and runs the bot.

---

### Configuration Files

#### `.env.example`
Sample environment configuration file. Copy or rename to `.env` and fill in your bot token (music folder optional - uses default `music/` folder inside bot directory if not specified).

#### `requirements.txt`
Python package dependencies for easy installation.

Use with: `pip install -r requirements.txt`

---

### Config Folder

Configuration files for easy customization. The bot uses a **mode-aware configuration system** with separate settings for prefix mode (`!play`) and slash mode (`/play`):

#### Common Configuration (Shared by Both Modes)
- **`config/common/basic_settings.py`** — Bot identity, music folder path, command prefix, feature toggles (shuffle, queue, etc.), spam protection, logging level, bot status.
- **`config/common/audio_settings.py`** — FFmpeg options, audio format support, voice connection timing, playback timing, voice health monitoring.
- **`config/common/advanced.py`** — Bot token, persistence file paths, watchdog intervals, debug settings (rarely changed).
- **`config/common/messages.py`** — Shared messages used by both prefix and slash modes.
- **`config/common/spam_protection.py`** — Spam protection settings: Layer 3 serial queue (prevents command overlap).
- **`config/common/permissions.py`** — Permission system configuration.
- **`config/common/filename_patterns.py`** — Regex patterns for music file parsing.

#### Prefix Mode Configuration (`!play` commands)
- **`config/prefix/aliases.py`** — Command aliases (e.g., `!p` for `!play`).
- **`config/prefix/features.py`** — Feature toggles specific to prefix mode.
- **`config/prefix/messages.py`** — Prefix-specific bot text responses (chatty announcements and UI).
- **`config/prefix/spam_protection.py`** — Command cooldowns (Layers 1-2: user sessions and circuit breaker).
- **`config/prefix/cleanup.py`** — Message cleanup timing and TTL settings (prefix mode only).

#### Slash Mode Configuration (`/play` commands)
- **`config/slash/features.py`** — Feature toggles specific to slash mode.
- **`config/slash/messages.py`** — Slash-specific bot text responses (silent mode - UI and error text only).
- **`config/slash/embeds.py`** — Discord embed styling and formatting.
- **`config/slash/buttons.py`** — Button labels and emoji configuration.
- **`config/slash/timing.py`** — Control panel update throttling, interaction timeouts, button cooldowns.

---

### Auto-Created Files

#### `last_channels.json`
Channel persistence storage file (auto-created, prefix mode only). Stores the last used text channel per Discord server. Allows cleanup features to resume after bot restart. Automatically managed - do not edit manually.

#### `last_playlists.json`
Playlist persistence storage file (auto-created). Stores the last used playlist per Discord server. Allows the bot to remember which playlist each server was using after restart. Automatically managed - do not edit manually.

#### `last_message_ids.json`
Control panel message IDs (auto-created, slash mode only). Stores the control panel message ID per Discord server. Allows control panels to persist and update after bot restart. Automatically managed - do not edit manually.

---

### Other Files

#### `.gitignore`
Tells git which files to ignore (logs, tokens, music, runtime state, caches, etc.) Prevents accidentally committing sensitive data and temporary files.

---

## Setup Order (Recommended)

1. Read [README](01-README.txt) (get familiar with the bot)
2. Follow [Getting Discord Token](02-Getting-Discord-Token.txt) (get your bot token)
3. Follow one of the setup guides:
   - [Windows Quick Setup](03-Windows-Quick-Setup.txt) (recommended - uses wizard)
   - [Windows Manual Setup](03-Windows-Manual-Setup.txt) (step-by-step commands)
   - [Linux Quick Setup](03-Linux-Quick-Setup.txt) (recommended - uses wizard)
   - [Linux Manual Setup](03-Linux-Manual-Setup.txt) (step-by-step commands)
4. Run the bot with `start-jill.bat` (Windows) or `./start-jill.sh` (Linux)
