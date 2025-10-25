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
- **Windows setup:** [`SETUP-Windows.txt`](../SETUP-Windows.txt)
- **Linux setup:** [`SETUP-Linux.txt`](../SETUP-Linux.txt)
- **Get a Discord token:** [`Getting-Discord-Token.txt`](../Getting-Discord-Token.txt)
- **Convert audio to Opus:** [`Converting-To-Opus.txt`](../Converting-To-Opus.txt)
- **Troubleshooting:** [`troubleshooting.txt`](../troubleshooting.txt)
- **Files overview:** [`Files.txt`](../Files.txt)
- **Reference README:** [`README.txt`](../README.txt)

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
- [`paths.py`](../paths.py) — library & storage paths
- [`features.py`](../features.py) — feature flags
- [`messages.py`](../messages.py) — bot text
- [`timing.py`](../timing.py) — cooldowns/TTLs
- [`aliases.py`](../aliases.py) — optional aliases

> See the setup docs above for environment variables and service examples.

---

## Notes
- No telemetry; playback is local.
- Requires Python 3.11+ and FFmpeg.
