# AGENTS.md - Discord Music Bot

Quick start: `python3 bot.py` (needs `.env` with `DISCORD_BOT_TOKEN`, Python 3.11+, `pip install -r requirements.txt`)

## File Map (Where to Look)

**Config** (`/config/` - user customization only):
- `features.py` — toggles (shuffle, queue, cleanup, auto-pause)
- `timing.py` — all timing constants (TTLs, cooldowns, debounce)
- `messages.py` — all user-facing text
- `aliases.py` — command aliases
- `paths.py` — file paths

**Implementation:**
- `bot.py` — entry point, event handlers, watchdog setup
- `handlers/commands.py` — all 10 commands
- `core/player.py` — MusicPlayer, queue, shuffle
- `core/playback.py` — _play_current, _play_next, FFmpeg callbacks
- `core/track.py` — Track class, library loading
- `systems/spam_protection.py` — 5-layer spam protection
- `systems/cleanup.py` — dual cleanup (TTL + history scan)
- `systems/voice_manager.py` — auto-pause/disconnect/resume
- `systems/watchdog.py` — playback hang detection
- `utils/discord_helpers.py` — safe Discord wrappers
- `utils/persistence.py` — channel storage
- `utils/context_managers.py` — suppress_callbacks, reconnecting_state

## Critical Rules (DO NOT BREAK)

**Never merge/disable dual cleanup systems:**
- TTL cleanup + history scan run independently (redundancy by design)

**Always use:**
- `asyncio.sleep()` not `time.sleep()`
- Constants from `timing.py` (don't hardcode timings)
- Messages from `messages.py` (don't hardcode user text)
- `python -m pip` not `pip` (reliability)

**Never:**
- Add blocking I/O in event handlers (use `asyncio.to_thread()`)
- Change feature defaults silently (breaks user expectations)
- Print tokens/secrets (security)
- Add heavy dependencies (prefer stdlib)
- Spam reconnect attempts (rate limit safety)

**File safety:** Only `.opus` files from `MUSIC_FOLDER`, prevent path traversal

## Documentation

**Always document:**
- New functions/classes with docstrings (explain purpose, args, return)
- Complex logic with inline comments (explain *why*, not *what*)
- Update this AGENTS.md if you add new files or change architecture
