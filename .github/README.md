# 🍸 Jill — Cyberpunk Bartender Discord Music Bot

Self-hosted, customizable Discord music bot for your local song library.

---

## Features
- Direct playback of local **.opus** files (no re-encoding)
- Super customizable: change responses, commands, features, etc
- Multiple playlists (organize music in subfolders, switch between them)
- Protection against command spam with debounce + cooldowns
- Easy to use queue, previous, skip, playlist switching, shuffle, etc
- Smart message cleanup system to keep text channels tidy

---

## Quick Start
1. Download the bot
2. Run the interactive setup:
   - **Windows:** Double-click [`scripts/win_setup.bat`](../scripts/win_setup.bat)
   - **Linux:** `chmod +x scripts/linux_setup.sh && ./scripts/linux_setup.sh` → [view script](../scripts/linux_setup.sh)
3. Run the bot:
   - **Windows:** Double-click [`scripts/win_run_bot.bat`](../scripts/win_run_bot.bat)
   - **Linux:** `./scripts/linux_run_bot.sh` → [view script](../scripts/linux_run_bot.sh)

## Docs
- **Overview:** [01-README.txt](../README/01-README.txt)
- **Get a Discord token:** [02-Getting-Discord-Token.txt](../README/02-Getting-Discord-Token.txt)
- **Windows setup:** [03-SETUP-Windows.txt](../README/03-SETUP-Windows.txt)
- **Linux setup:** [03-SETUP-Linux.txt](../README/03-SETUP-Linux.txt)
- **Convert audio to Opus:** [04-Converting-To-Opus.txt](../README/04-Converting-To-Opus.txt)
- **Files overview:** [05-Files.txt](../README/05-Files.txt)
- **Troubleshooting:** [06-troubleshooting.txt](../README/06-troubleshooting.txt)

---

## Commands (core)
```
!play [n]         # join/resume; or jump to track n
!pause            # pause
!skip             # next track
!previous         # previous track
!stop             # disconnect/reset
!queue            # show last/now/next
!list [page]      # browse song list
!playlists [page] # browse playlist library
!playlist [name]  # switch to playlist
!shuffle          # toggle shuffle
!unshuffle        # back to order
!help             # show help
```

---

## Config references
- [`aliases.py`](../config/aliases.py) — command aliases
- [`messages.py`](../config/messages.py) — messages
- [`features.py`](../config/features.py) — features
- [`timing.py`](../config/timing.py) — cooldowns/TTLs

> See the setup docs above for environment variables and service examples.

---

## Notes
- No telemetry whatsoever; playback is local.
- Requires [Python 3.11+](https://www.python.org/downloads/) and [FFmpeg](https://ffmpeg.org/download.html).
