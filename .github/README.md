# 🍸 Jill — A Cyberpunk Bartender Discord Music Bot

A simple, robust Discord music bot that plays local **.opus** files and supports
multiple playlists, auto-cleanup, song selection, spam protection, and more.

---

## About
Built in a neon-lit feedback loop between me and AI coding agents. I prompted,
stitched the pieces, and fine-tuned behavior; the agents generated most of the
raw code. If it sings, credit the ensemble. If it glitches, that’s on me.

---

## Features
- Customization: rename commands, rewrite messages, flip features on or off, make it yours
- Multiple playlists: you're using subfolders? Now it's a playlist!
- Spam protection: hammer it all you want, debounce, cooldowns, and limits keep it sane
- Smart: jill reads the room, pauses when alone, cleans up after herself
- Shuffle mode: toggle it on or off, she'll auto-reshuffle as well!
- Quick search: just say the song name or track number (works on playlists too!)

---

## Quick Start
0. Install [Python 3.11+](https://www.python.org/downloads/) and [FFmpeg](https://www.ffmpeg.org/download.html)
1. Download the [latest release](https://github.com/grodz-bar/jill/releases/latest)
2. Get a Discord bot token → [Getting Discord Token](02-Getting-Discord-Token.md)
3. Run the interactive setup:
   - **Windows:** [`/scripts/win_setup.bat`](../scripts/win_setup.bat)
   - **Linux:** [`./scripts/linux_setup.sh`](../scripts/linux_setup.sh)
4. Run the bot:
   - **Windows:** [`/scripts/win_run_bot.bat`](../scripts/win_run_bot.bat)
   - **Linux:** [`./scripts/linux_run_bot.sh`](../scripts/linux_run_bot.sh)
5. Done. 

- **Full Linux setup guide:** [Linux Setup Guide](03-SETUP-Linux.md)
- **Full Windows setup guide:** [Windows Setup Guide](03-SETUP-Windows.md)

## Commands
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
!help             # show help
```

---

## Config

- [`config/messages.py`](../config/messages.py) — Customize bot responses
- [`config/features.py`](../config/features.py) — Turn features on/off
- [`config/aliases.py`](../config/aliases.py) — Change command aliases

---

## Docs
- **This file:** [README](01-README.md)
- **Files overview:** [Files Reference](05-Files.md)
- **Discord Token guide:** [Getting Discord Token](02-Getting-Discord-Token.md)
- **Windows setup guide:** [Windows Setup](03-SETUP-Windows.md)
- **Linux setup guide:** [Linux Setup](03-SETUP-Linux.md)
- **Converting to Opus guide:** [Converting to Opus](04-Converting-To-Opus.md)
- **Troubleshooting:** [Troubleshooting](06-troubleshooting.md)

---

## Notes
- Zero telemetry or spying
- Requires [Python 3.11+](https://www.python.org/downloads/) and [FFmpeg](https://ffmpeg.org/download.html)
- Built on the [Disnake](https://docs.disnake.dev) API
