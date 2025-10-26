# AGENTS.md - Discord Music Bot

Quick start: `python3 bot.py` (needs `.env` with `DISCORD_BOT_TOKEN`, Python 3.11+, `pip install -r requirements.txt`)

## File Map (Where to Look)

**Config** (`/config/` - user customization only):
- `features.py` — toggles (shuffle, queue, cleanup, auto-pause)
- `messages.py` — all user-facing text
- `aliases.py` — command aliases
- `paths.py` — file paths
- `timing.py` — all timing constants (TTLs, cooldowns, debounce). Message TTLs still
feed `systems.cleanup.CleanupManager` even when embeds update in place.

**Implementation:**
- `bot.py` — entry point, event handlers, watchdog setup
- `handlers/commands.py` — all commands
- `core/player.py` — MusicPlayer, queue, shuffle
- `core/playback.py` — _play_current, _play_next, FFmpeg callbacks (session-guarded playback tokens)
- `core/track.py` — Track class, library loading, playlist discovery
- `systems/spam_protection.py` — 5-layer spam protection
- `systems/cleanup.py` — dual cleanup (TTL + history scan)
- `systems/voice_manager.py` — auto-pause/disconnect/resume
- `systems/watchdog.py` — playback hang detection
- `utils/discord_helpers.py` — safe Discord wrappers
- `utils/persistence.py` — channel storage, playlist persistence
- `utils/context_managers.py` — suppress_callbacks (cancels playback session), reconnecting_state

## Command Structure

**Context-Aware Commands** (do different things based on arguments):
- `!tracks` → show tracks in current playlist
- `!tracks [name/number]` → switch to different playlist
- `!play` → start/resume playback
- `!play [number/name]` → jump to specific track
- `!shuffle` → toggle shuffle mode on/off

**View Commands:**
- `!queue` → show now playing + upcoming tracks
- `!playlists` → show all available playlists

**Control Commands:**
- `!pause`, `!skip`, `!stop`, `!previous` → playback controls

**Aliases:**
- All base commands have aliases in `config/aliases.py`
- Example: `!playlist`, `!library`, `!album` all map to `!tracks`
- Users can customize aliases without touching command implementations

## Critical Rules (DO NOT BREAK)

**Graceful shutdown:**
- Signal handlers (SIGINT, SIGTERM) trigger `shutdown_bot()` async sequence
- Shutdown order: watchdogs → players → voice → bot connection
- Never use blocking operations in shutdown sequence
- All subsystems must handle cancellation gracefully

**Never merge/disable dual cleanup systems:**
- TTL cleanup + history scan run independently (redundancy by design)

**Always use:**
- `asyncio.sleep()` not `time.sleep()`
- Constants from `timing.py` (don't hardcode timings)
- Messages from `messages.py` (don't hardcode user text)
- `python -m pip` not `pip` (reliability)

**Playback safety:**
- Cancel or replace the active playback session (`player.cancel_active_session()` or `suppress_callbacks`) before stopping/starting audio manually. This prevents stale callbacks from advancing the queue.

**Never:**
- Add blocking I/O in event handlers (use `asyncio.to_thread()`)
- Change feature defaults silently (breaks user expectations)
- Print tokens/secrets (security)
- Add heavy dependencies (prefer stdlib)
- Spam reconnect attempts (rate limit safety)

**File safety:** Only `.opus` files from `MUSIC_FOLDER`, prevent path traversal

**Version updates:** Remind and then ask user about updating the two version constants in `bot.py`

## Documentation

**Always document:**
- New functions/classes with docstrings (explain purpose, args, return)
- Complex logic with inline comments (explain *why*, not *what*)
- Update this AGENTS.md if you add new files or change architecture
- Update .txt's and .py's to reflect up to date behaviour after making changes, but only if needed.
