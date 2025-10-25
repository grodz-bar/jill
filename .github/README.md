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

## Docs
- **Windows setup:** [SETUP-Windows.txt](../README/SETUP-Windows.txt)
- **Linux setup:** [SETUP-Linux.txt](../README/SETUP-Linux.txt)
- **Get a Discord token:** [Getting-Discord-Token.txt](../README/Getting-Discord-Token.txt)
- **Convert audio to Opus:** [Converting-To-Opus.txt](../README/Converting-To-Opus.txt)
- **Files overview:** [Files.txt](../README/Files.txt)
- **Troubleshooting:** [troubleshooting.txt](../README/troubleshooting.txt)
- **Reference README:** [README.txt](../README/README.txt)

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
- Requires Python 3.11+ and FFmpeg.
