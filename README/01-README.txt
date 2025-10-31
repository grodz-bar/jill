================================================================================
                    JILL - A CYBERPUNK BARTENDER MUSIC BOT
================================================================================

A simple, robust Discord music bot that plays local audio files and supports
multiple playlists, auto-cleanup, song selection, spam protection, and more.

Choose your command style:
- Classic Mode (!play): Text commands with automatic message cleanup
- Modern Mode (/play): Slash commands with interactive buttons and live panels

================================================================================
ABOUT
================================================================================
Built in a neon-lit feedback loop between me and AI coding agents. I prompted,
stitched the pieces, and fine-tuned behavior; the agents generated most of the
raw code. If it sings, credit the ensemble. If it glitches, that's on me.

================================================================================
FEATURES
================================================================================
- Dual Command Modes: Choose Classic (!play) or Modern (/play) during setup
- Multiple playlists: You're using subfolders. Now it's a playlist.
- Spam protection: Hammer it all you want, debounce, cooldowns, and limits
  keep it sane
- Smart: Jill reads the room, pauses when alone, manages herself
- Auto-fix stuttering: Adaptive voice health monitoring detects degraded
  connections and auto-reconnects to fix audio stuttering (no user action needed)
- Shuffle mode: Toggle it on or off, she'll auto-reshuffle as well.
- Quick search: Just say the song name or track number (works on playlists too)
- Flexible naming: Multiple file naming patterns supported (01 - Track.opus,
  01_Track.mp3, 01. Track.flac, etc.)
- Configurable logging: Debug mode for troubleshooting, quiet mode for production

CLASSIC MODE (!play):
- Text-based commands with customizable prefix
- Automatic message cleanup after 15 seconds
- Rename commands, change prefix, full customization
- Traditional Discord bot experience

MODERN MODE (/play):
- Discord's native slash commands (type / to see all)
- Interactive button controls (pause, skip, shuffle, etc.)
- Auto-updating control panel with live playback status
- Ephemeral messages (only you see command responses)
- Discord handles rate limiting and permissions

================================================================================
QUICK START
================================================================================
0. Install Python 3.11+ from: https://www.python.org/downloads/
   Install FFmpeg from: https://www.ffmpeg.org/download.html
1. Download the latest release from:
   https://github.com/grodz-bar/jill/releases/latest
2. Get a Discord bot token - see 02-Getting-Discord-Token.txt
3. Run the interactive setup (choose command mode during setup):
   - Linux: ./linux_setup.sh
   - Windows: win_setup.bat
4. Run the bot:
   - Linux: ./start-jill.sh (created during setup)
   - Windows: start-jill.bat (created during setup)
5. Done.

SETUP GUIDES:
- Linux (Quick): 03-Linux-Quick-Setup.txt - Using the wizard
- Linux (Manual): 03-Linux-Manual-Setup.txt - Step-by-step commands
- Windows (Quick): 03-Windows-Quick-Setup.txt - Using the wizard
- Windows (Manual): 03-Windows-Manual-Setup.txt - Step-by-step commands

NOTE: Supports OPUS, MP3, FLAC, WAV, M4A, and OGG files.

Since .opus is HIGHLY RECOMMENDED for the best experience, I've included a
very nice converter script.

================================================================================
COMMANDS
================================================================================
CLASSIC MODE (!play):
  !play             # start/resume playback
  !play [track]     # jump by number or name (!play 5 or !play lonely job)
  !pause            # pause
  !skip             # next track
  !previous         # previous track
  !stop             # disconnect/reset
  !queue            # show the current queue
  !tracks           # show tracks in the current playlist
  !playlist [name]  # switch to a playlist (!playlist dome keeper)
  !playlists        # show all available playlists
  !shuffle          # toggle shuffle
  !aliases          # show all command aliases (or !aliases [command] for specific)
  !help             # show help

  NOTE: The command prefix (!) is configurable via config/prefix/features.py

MODERN MODE (/play):
  /play             # start/resume playback
  /play [track]     # jump by number or name (/play track:lonely job)
  /pause            # pause
  /skip             # next track
  /previous         # previous track
  /stop             # disconnect/reset
  /queue            # show the current queue
  /tracks           # show tracks in the current playlist
  /playlist [name]  # switch to a playlist (/playlist name:dome keeper)
  /playlists        # show all available playlists
  /shuffle          # toggle shuffle
  /help             # show help

  PLUS: Interactive button controls on the control panel
  - Buttons appear after first /play command
  - Click to control: play, pause, skip, previous, shuffle, stop
  - Control panel updates automatically with current track info

  NOTE: Type / in Discord to see all slash commands with descriptions

================================================================================
CONFIG
================================================================================
COMMAND MODE:
- .env - Set JILL_COMMAND_MODE to 'prefix' or 'slash'

COMMON (Both Modes):
- config/common/core.py - Bot token, music folder, logging, voice health
- config/common/permissions.py - VA-11 HALL-A themed permission system
- config/common/filename_patterns.py - File naming patterns
- config/common/paths.py - Path configuration
- config/common/bot_identity.py - Bot name and avatar

CLASSIC MODE (prefix):
- config/prefix/features.py - Command prefix, feature toggles
- config/prefix/messages.py - Bot response text
- config/prefix/aliases.py - Command aliases
- config/prefix/timing.py - Cooldowns, debounce, cleanup timing

MODERN MODE (slash):
- config/slash/features.py - Feature toggles
- config/slash/messages.py - Bot response text and button labels
- config/slash/timing.py - Update throttling, interaction delays
- config/slash/embeds.py - Rich embed formatting functions
- config/slash/buttons.py - Button component builders

================================================================================
DOCS
================================================================================
- This file: 01-README.txt
- Files overview: 05-Files.txt
- Discord Token guide: 02-Getting-Discord-Token.txt
- Setup guides:
  - 03-Windows-Quick-Setup.txt (Recommended)
  - 03-Windows-Manual-Setup.txt (Manual setup)
  - 03-Linux-Quick-Setup.txt (Recommended)
  - 03-Linux-Manual-Setup.txt (Manual setup)
- Converting to Opus guide: 04-Converting-To-Opus.txt
- Troubleshooting: 06-troubleshooting.txt

================================================================================
NOTES
================================================================================
- Zero telemetry or spying
- Requires Python 3.11+ (https://www.python.org/downloads/)
  and FFmpeg (https://ffmpeg.org/download.html)
- Built on the Disnake API (https://docs.disnake.dev)
