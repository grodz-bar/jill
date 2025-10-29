# 🍸 Jill — A Cyberpunk Bartender Discord Music Bot

A simple, robust Discord music bot that plays local audio files and supports multiple playlists, auto-cleanup, song selection, spam protection, and more.

---

## About
Built in a neon-lit feedback loop between me and AI coding agents. I prompted,
stitched the pieces, and fine-tuned behavior; the agents generated most of the
raw code. If it sings, credit the ensemble. If it glitches, that’s on me.

---

## Features
- **Customization**: Rename commands, rewrite messages, flip features on or off, make it yours.
- **Multiple playlists**: You're using subfolders? Now it's a playlist!
- **Spam protection**: Hammer it all you want, debounce, cooldowns, and limits keep it sane.
- **Smart**: Jill reads the room, pauses when alone, cleans up after herself.
- **Shuffle mode**: Toggle it on or off, she'll auto-reshuffle as well!
- **Quick search**: Just say the name or track number, works on playlists too!

---

## Quick Start
0. Install [Python 3.11+](https://www.python.org/downloads/) and [FFmpeg](https://www.ffmpeg.org/download.html)
1. Download the [latest release](https://github.com/grodz-bar/jill/releases/latest)
2. Get a Discord bot token → [Getting Discord Token](02-Getting-Discord-Token.md)
3. Run the interactive setup:
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

- [`config/messages.py`](../config/messages.py) — Customize bot responses.
- [`config/features.py`](../config/features.py) — Turn features on/off.
- [`config/aliases.py`](../config/aliases.py) — Change command aliases.

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
