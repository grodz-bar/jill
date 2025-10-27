# AGENTS.md - Discord Music Bot

Quick start: `python3 bot.py` (needs `.env` with `DISCORD_BOT_TOKEN`, Python 3.11+, `python -m pip install -r requirements.txt`)

## Agent Interaction Preferences

- Assume novice audience, keep responses under 200 words
- Format: Answer → Why → How → Next steps
- Note risks/side-effects. Prefer stdlib over dependencies

## File Map (Where to Look)

**Config** (`/config/` - user customization only):
- `features.py` — toggles (shuffle, queue, cleanup, auto-pause). Validates BOT_STATUS at import.
- `messages.py` — all user-facing text
- `aliases.py` — command aliases
- `paths.py` — file paths
- `timing.py` — all timing constants (TTLs, cooldowns, debounce). TTLs still schedule cleanup even when smart message management edits in place.

**Implementation:**
- `bot.py` — entry point, event handlers, watchdog setup
- `handlers/commands.py` — all commands
- `core/player.py` — MusicPlayer, queue, shuffle. `switch_playlist()` is currently synchronous (no await).
- `core/playback.py` — _play_current, _play_next, FFmpeg callbacks (session-guarded playback tokens)
- `core/track.py` — Track class, library loading, playlist discovery
- `systems/spam_protection.py` — 5-layer spam protection
- `systems/cleanup.py` — dual cleanup (TTL + history scan). Protects now-playing and pinned messages.
- `systems/voice_manager.py` — auto-pause/disconnect/resume
- `systems/watchdog.py` — playback hang detection
- `utils/discord_helpers.py` — safe Discord wrappers
- `utils/persistence.py` — channel/playlist persistence. Reference for safe pattern. See module docstring.
- `utils/context_managers.py` — suppress_callbacks (cancels playback session), reconnecting_state

## Commands

All user commands implemented in `handlers/commands.py`. Context-aware (e.g., `!play` resumes OR jumps to track). Aliases in `config/aliases.py`.

## Critical Rules (DO NOT BREAK)

**Graceful shutdown:**
- Signal handlers (SIGINT, SIGTERM) trigger `shutdown_bot()` async sequence
- Shutdown order: watchdogs → players → persistence flush → voice → bot connection
- Persistence: `flush_all_immediately()` ensures no data loss on shutdown
- Never use blocking operations in shutdown sequence
- All subsystems must handle cancellation gracefully

**Persistence safety pattern (CRITICAL):**
- In-memory cache is source of truth, not disk files
- Load from disk ONLY when cache is empty (on first access)
- During flush/save: serialize from cache, NEVER re-read from disk
- Why: If file corrupts between startup and flush, re-reading wipes cache and loses all data
- Pattern for new persistence: `if not _cache_loaded: load(); data = _cache.copy(); write(data)`
- See `utils/persistence.py` for reference implementation (channels/playlists)
- Atomic writes: use tempfile + os.replace() to prevent partial writes

**Never merge/disable dual cleanup systems:**
- TTL cleanup + history scan run independently (redundancy by design)

**Always use:**
- `asyncio.sleep()` not `time.sleep()`
- `time.monotonic()` for elapsed time tracking (immune to system clock changes)
- Constants from `timing.py` (don't hardcode timings)
- Messages from `messages.py` (don't hardcode user text)
- `python -m pip` not `pip` (reliability)

**Playback safety:**
- Cancel or replace the active playback session (`player.cancel_active_session()` or `suppress_callbacks`) before stopping/starting audio manually. This prevents stale callbacks from advancing the queue.
- FFmpeg callbacks run in audio thread: use `bot.loop.call_soon_threadsafe()` for player mutations, never direct assignment

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
- Update .txts and .pys to reflect up-to-date behavior after making changes, but only if applicable.
