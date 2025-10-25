# 🍸 Jill — Cyberpunk Bartender Discord Music Bot

Self-hosted, customizable Discord music bot for your local library.

---

## What it does
- Direct playback of local **.opus** files (no re-encoding)
- Simple, predictable queue with optional shuffle
- Resilient under command spam (debounce + cooldowns)
- Low-noise chat output; auto-pause/leave when idle

---

## Docs
- **Windows setup:** [SETUP-Windows.txt](../README/SETUP-Windows.txt)
- **Linux setup:** [SETUP-Linux.txt](../README/SETUP-Linux.txt)
- **Get a Discord token:** [Getting-Discord-Token.txt](../README/Getting-Discord-Token.txt)
- **Convert audio to Opus:** [Converting-To-Opus.txt](../README/Converting-To-Opus.txt)
- **Troubleshooting:** [troubleshooting.txt](../README/troubleshooting.txt)
- **Files overview:** [Files.txt](../README/Files.txt)
- **Reference README:** [README.txt](../README/README.txt)

---

## Commands (core)
```
!play [n]        # join/resume; or jump to track n
!pause           # pause
!skip            # next track
!previous        # previous track
!stop            # disconnect/reset
!queue           # show last/now/next
!library [page]  # browse library
!shuffle         # toggle shuffle
!unshuffle       # back to order
!help            # show help
```

---

## Config references
- [`.env.example`](../.env.example)
- [`aliases.py`](../config/aliases.py) — aliases
- [`messages.py`](../config/messages.py) — messages
- [`features.py`](../config/features.py) — features
- [`timing.py`](../config/timing.py) — cooldowns/TTLs

> See the setup docs above for environment variables and service examples.

---

## Notes
- No telemetry; playback is local.
- Requires Python 3.11+ and FFmpeg.
