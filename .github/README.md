# 🍸 Jill — A Cyberpunk Bartender Discord Music Bot

A simple, robust Discord music bot that plays local audio files and supports multiple playlists, auto-cleanup, song selection, spam protection, and more.

**Choose your command style:**
- **Classic Mode** (`!play`): Text commands with automatic message cleanup
- **Modern Mode** (`/play`): Slash commands with interactive buttons and live panels

---

## About
Built in a neon-lit feedback loop between me and AI coding agents. I prompted,
stitched the pieces, and fine-tuned behavior; the agents generated most of the
raw code. If it sings, credit the ensemble. If it glitches, that’s on me.

---

## Features
- **Dual Command Modes**: Choose Classic (`!play`) or Modern (`/play`) during setup
- **Multiple playlists**: You're using subfolders? Now it's a playlist!
- **Spam protection**: Hammer it all you want, spam sessions, cooldowns, and guild isolation keep it sane.
- **Smart**: Jill reads the room, pauses when alone, manages herself.
- **Shuffle mode**: Toggle it on or off, she'll auto-reshuffle as well!
- **Quick search**: Just say the name or track number, works on playlists too!

**Classic Mode** (`!play`):
- Text-based commands with customizable prefix
- Automatic message cleanup after 15 seconds
- Rename commands, change prefix, full customization
- Traditional Discord bot experience

**Modern Mode** (`/play`):
- Discord's native slash commands (type `/` to see all)
- Interactive button controls (pause, skip, shuffle, etc.)
- Auto-updating control panel with live playback status
- Ephemeral messages (only you see command responses)
- Discord handles rate limiting and permissions

---

## Quick Start
0. Install [Python 3.11+](https://www.python.org/downloads/) and [FFmpeg](https://www.ffmpeg.org/download.html)
1. Download the [latest release](https://github.com/grodz-bar/jill/releases/latest)
2. Get a Discord bot token → [Getting Discord Token](02-Getting-Discord-Token.md)
3. Run the interactive setup (choose command mode during setup):
   - **Linux:** [`./linux_setup.sh`](../linux_setup.sh)
   - **Windows:** [`win_setup.bat`](../win_setup.bat)
5. Run the bot:
   - **Linux:** [`./start-jill.sh`](../start-jill.sh) (created during setup)
   - **Windows:** [`start-jill.bat`](../start-jill.bat) (created during setup)
6. Done.

**Setup guides:**
  - [Windows Quick Setup](03-Windows-Quick-Setup.md) - Recommended.
  - [Windows Manual Setup](03-Windows-Manual-Setup.md) - Manual setup.
  - [Linux Quick Setup](03-Linux-Quick-Setup.md) - Recommended.
  - [Linux Manual Setup](03-Linux-Manual-Setup.md) - Manual setup.

---
> Supports OPUS, MP3, FLAC, WAV, M4A, and OGG files.
>
> Since .opus is **HIGHLY RECOMMENDED** for the best experience, I've included a very nice converter script.
---
## Commands

**Classic Mode** (`!play`):
```text
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
!aliases          # show all command aliases
!help             # show help
```
> **Note:** Command prefix (`!`) is configurable via `config/prefix/features.py`

**Modern Mode** (`/play`):
```text
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
```
**Plus:** Interactive button controls on the control panel
- Buttons appear after first `/play` command
- Click to control: play, pause, skip, previous, shuffle, stop
- Control panel updates automatically with current track info

> **Note:** Type `/` in Discord to see all slash commands with descriptions

---

## Config

**Command Mode:**
- [`.env`](../.env) — Set `JILL_COMMAND_MODE` to `prefix` or `slash`

**Common (Both Modes):**
- [`config/common/basic_settings.py`](../config/common/basic_settings.py) — Bot identity, music folder, feature toggles, logging
- [`config/common/audio_settings.py`](../config/common/audio_settings.py) — FFmpeg options, voice health monitoring
- [`config/common/advanced.py`](../config/common/advanced.py) — Bot token, persistence paths, watchdog intervals
- [`config/common/messages.py`](../config/common/messages.py) — Shared messages
- [`config/common/spam_protection.py`](../config/common/spam_protection.py) — Spam protection (Layer 3 serial queue)
- [`config/common/permissions.py`](../config/common/permissions.py) — VA-11 HALL-A themed permissions
- [`config/common/filename_patterns.py`](../config/common/filename_patterns.py) — File naming patterns

**Classic Mode (prefix):**
- [`config/prefix/features.py`](../config/prefix/features.py) — Command prefix, feature toggles
- [`config/prefix/messages.py`](../config/prefix/messages.py) — Prefix-specific bot response text
- [`config/prefix/aliases.py`](../config/prefix/aliases.py) — Command aliases
- [`config/prefix/spam_protection.py`](../config/prefix/spam_protection.py) — Command cooldowns (Layers 1-2)
- [`config/prefix/cleanup.py`](../config/prefix/cleanup.py) — Message cleanup timing and TTL settings

**Modern Mode (slash):**
- [`config/slash/features.py`](../config/slash/features.py) — Feature toggles
- [`config/slash/messages.py`](../config/slash/messages.py) — Slash-specific bot response text, button labels
- [`config/slash/timing.py`](../config/slash/timing.py) — Update throttling, button cooldowns
- [`config/slash/embeds.py`](../config/slash/embeds.py) — Rich embed formatting
- [`config/slash/buttons.py`](../config/slash/buttons.py) — Button components

---

## Docs
- **This file:** [README](01-README.md)
- **Files overview:** [Files Reference](05-Files.md)
- **Discord Token guide:** [Getting Discord Token](02-Getting-Discord-Token.md)
- **Setup guides:**
  - [Windows Quick Setup](03-Windows-Quick-Setup.md)
  - [Windows Manual Setup](03-Windows-Manual-Setup.md)
  - [Linux Quick Setup](03-Linux-Quick-Setup.md)
  - [Linux Manual Setup](03-Linux-Manual-Setup.md)
- **Converting to Opus guide:** [Converting to Opus](04-Converting-To-Opus.md)
- **Troubleshooting:** [Troubleshooting](06-troubleshooting.md)

---

## Notes
- Zero telemetry or spying.
- Requires [Python 3.11+](https://www.python.org/downloads/) and [FFmpeg](https://ffmpeg.org/download.html).
- Built on the [Disnake](https://docs.disnake.dev) API.
