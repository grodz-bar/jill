# AGENTS.md - Discord Music Bot

Quick start: `python3 bot.py` (needs `.env` with `DISCORD_BOT_TOKEN`, Python 3.11+, `python -m pip install -r requirements.txt`)

**Audio formats:** Supports MP3, FLAC, WAV, M4A, OGG, OPUS. Opus recommended for best performance (see `README/04-Converting-To-Opus.txt`).

## Agent Interaction Preferences

- Assume novice audience, keep responses under 200 words
- Format: Answer → Why → How → Next steps
- Note risks/side-effects. Prefer stdlib over dependencies

## File Map (Where to Look)

**Config** (`/config/` - user customization only):
- `features.py` — toggles (shuffle, queue, cleanup, auto-pause, transcoding). Validates BOT_STATUS at import.
- `messages.py` — all user-facing text
- `aliases.py` — command aliases
- `paths.py` — file paths
- `timing.py` — all timing constants (TTLs, cooldowns, debounce). TTLs still schedule cleanup even when smart message management edits in place.

**Implementation:**
- `bot.py` — entry point, event handlers, watchdog setup
- `handlers/commands.py` — all commands
- `core/player.py` — MusicPlayer, queue, shuffle. `switch_playlist()` is synchronous.
- `core/playback.py` — _play_current, _play_next, FFmpeg callbacks (session-guarded)
- `core/track.py` — Track class, library loading, playlist discovery, multi-format support
- `systems/spam_protection.py` — 5-layer spam protection
- `systems/cleanup.py` — dual cleanup (TTL + history scan)
- `systems/voice_manager.py` — auto-pause/disconnect/resume
- `systems/watchdog.py` — playback hang detection
- `utils/discord_helpers.py` — safe Discord wrappers (see atomic state pattern)
- `utils/persistence.py` — channel/playlist persistence (see persistence pattern)
- `utils/context_managers.py` — suppress_callbacks, reconnecting_state

## Commands

All user commands implemented in `handlers/commands.py`. Context-aware (e.g., `!play` resumes OR jumps to track). Aliases in `config/aliases.py`.

## Critical Rules (DO NOT BREAK)

**Bot lifecycle:**
- `bot.run()` creates its own event loop. Configure in `on_ready()`, not `__main__`
- Example: set exception handler in `on_ready()` where `bot.loop` exists

**Shutdown:**
- Order: watchdogs → players → `flush_all_immediately()` → voice → bot
- Signal handlers (SIGINT/SIGTERM) schedule `shutdown_bot()` on `bot.loop`
- No blocking ops, all subsystems handle cancellation

**Persistence pattern (CRITICAL):**
- Cache is source of truth. Load once, flush from cache (never re-read during flush)
- Why: corrupted file between startup/flush would wipe cache
- Pattern: `if not _loaded: load(); data = _cache.copy(); write(data)`
- Atomic writes: tempfile + os.replace(). Ref: `utils/persistence.py`

**Atomic state pattern (API + local state):**
- Lock entire operation: check → API call → update state on success only
- Why: prevents races (concurrent calls) + stale state (failed calls blocking retries)
- Pattern: `async with lock: if needs: await api(); state = new; return True`
- Ref: `discord_helpers.py:update_presence()`

**Never merge/disable dual cleanup systems:**
- TTL cleanup + history scan run independently (redundancy by design)

**Always use:**
- `asyncio.sleep()` not `time.sleep()`
- `time.monotonic()` for elapsed time tracking (immune to system clock changes)
- Constants from `timing.py` (don't hardcode timings)
- Messages from `messages.py` (don't hardcode user text)
- `python -m pip` not `pip` (reliability)

**Thread safety (FFmpeg callbacks run in audio thread):**
- **Reads:** GIL-atomic (booleans/ints/refs) - safe for early-exit guards
- **Writes:** `bot.loop.call_soon_threadsafe(setattr, player, 'attr', val)` - never direct
- **Coroutines:** `asyncio.run_coroutine_threadsafe(coro, bot.loop)`
- **Sessions:** Cancel session (`player.cancel_active_session()` or `suppress_callbacks`) before manual stop/skip/switch to prevent stale callbacks advancing queue

**Never:**
- Add blocking I/O in event handlers (use `asyncio.to_thread()`)
- Change feature defaults silently (breaks user expectations)
- Print tokens/secrets (security)
- Add heavy dependencies (prefer stdlib)
- Spam reconnect attempts (rate limit safety)

**File safety:**
- Supports `.opus`, `.mp3`, `.flac`, `.wav`, `.m4a`, `.ogg` files from `MUSIC_FOLDER`
- Always prefers `.opus` format when multiple versions exist (best performance)
- Opus uses passthrough (zero CPU), other formats transcode (higher CPU usage)
- Set `ALLOW_TRANSCODING = False` in `config/features.py` for opus-only mode
- Prevent path traversal attacks

## Documentation

**Always document:**
- New functions/classes with docstrings (explain purpose, args, return)
- Complex logic with inline comments (explain *why*, not *what*)
- Update this AGENTS.md if you add new files or change architecture
- Update .txts and .pys to reflect up-to-date behavior after making changes, but only if applicable.
