# 🍸 Jill — A Cyberpunk Bartender Discord Music Bot

A simple, robust Discord music bot that plays local **.opus** files that supports
multiple playlists, auto-cleanup, song selection, spam protection, and more.

---

## About
Built in a neon-lit feedback loop between me and AI coding agents. I prompted,
stitched the pieces, and fine tuned behavior; the agents generated most of the
raw code. If it sings, credit the ensemble. If it glitches, that’s on me.

---

## Features
- Customization: rename commands, rewrite messages, flip features on or off, make it yours
- Multiple playlists: you're using subfolders? now it's a playlist!
- Spam protection: hammer it all you want, debounce, cooldowns, and limits keep it sane
- Smart: jill reads the room, pauses when alone, cleans up after herself
- Shuffle mode: toggle it on or off, she'll auto reshuffle as well!
- Quick search: just say the song name or track number (works on playlists too!)

---

## Quick Start
1. Download the bot
2. Get a Discord bot token → [02-Getting-Discord-Token.txt](../README/02-Getting-Discord-Token.txt)
3. Run the interactive setup:
   - **Windows:** [`win_setup.bat`](../scripts/win_setup.bat)
   - **Linux:** [`scripts/linux_setup.sh`](../scripts/linux_setup.sh)
4. Run the bot:
   - **Windows:** [`win_run_bot.bat`](../scripts/win_run_bot.bat)
   - **Linux:** [`./linux_run_bot.sh`](../scripts/linux_run_bot.sh)
5. Done. 

- **Full Linux setup guide:** [03-SETUP-Linux.txt](../README/03-SETUP-Linux.txt)
- **Full Windows setup guide:** [03-SETUP-Windows.txt](../README/03-SETUP-Windows.txt)

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
- **Overview:** [01-README.txt](../README/01-README.txt)
- **Files overview:** [05-Files.txt](../README/05-Files.txt)
- **Discord Token guide:** [02-Getting-Discord-Token.txt](../README/02-Getting-Discord-Token.txt)
- **Windows setup guide:** [03-SETUP-Windows.txt](../README/03-SETUP-Windows.txt)
- **Linux setup guide:** [03-SETUP-Linux.txt](../README/03-SETUP-Linux.txt)
- **Converting to Opus guide:** [04-Converting-To-Opus.txt](../README/04-Converting-To-Opus.txt)
- **Troubleshooting:** [06-troubleshooting.txt](../README/06-troubleshooting.txt)

---

## Notes
- Zero telemetry or spying
- Requires [Python 3.11+](https://www.python.org/downloads/) and [FFmpeg](https://ffmpeg.org/download.html)
- Built on the [Disnake](https://docs.disnake.dev) API
