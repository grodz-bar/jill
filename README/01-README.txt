================================================================================
                    JILL - A CYBERPUNK BARTENDER MUSIC BOT
================================================================================

A simple, robust Discord music bot that plays local audio files and supports
multiple playlists, auto-cleanup, song selection, spam protection, and more.

================================================================================
ABOUT
================================================================================
Built in a neon-lit feedback loop between me and AI coding agents. I prompted,
stitched the pieces, and fine-tuned behavior; the agents generated most of the
raw code. If it sings, credit the ensemble. If it glitches, that's on me.

================================================================================
FEATURES
================================================================================
- Customization: Rename commands, rewrite messages, flip features on or off,
  make it yours
- Multiple playlists: You're using subfolders. Now it's a playlist.
- Spam protection: Hammer it all you want, debounce, cooldowns, and limits
  keep it sane
- Smart: Jill reads the room, pauses when alone, cleans up after herself
- Shuffle mode: Toggle it on or off, she'll auto-reshuffle as well.
- Quick search: Just say the song name or track number (works on playlists too)

================================================================================
QUICK START
================================================================================
0. Install Python 3.11+ from: https://www.python.org/downloads/
   Install FFmpeg from: https://www.ffmpeg.org/download.html
1. Download the latest release from:
   https://github.com/grodz-bar/jill/releases/latest
2. Get a Discord bot token - see 02-Getting-Discord-Token.txt
3. Run the interactive setup:
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
!help             # show help

================================================================================
CONFIG
================================================================================
- config/messages.py - Customize bot responses
- config/features.py - Turn features on/off
- config/aliases.py - Change command aliases

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
