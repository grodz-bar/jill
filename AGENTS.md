# AGENTS.md - Discord Music Bot

Quick start: `python3 bot.py` (needs `.env` with `DISCORD_BOT_TOKEN`, Python 3.11+, `python -m pip install -r requirements.txt`)

Audio: MP3/FLAC/WAV/M4A/OGG/OPUS supported. Opus preferred (zero CPU). See `README/04-Converting-To-Opus.txt`.

## Agent Preferences

- Assume novice, <200 words, format: Answer→Why→How→Next
- Note risks. Prefer stdlib

## File Map

**Config** (`/config/` - user only):
- `features.py` — toggles (shuffle/queue/cleanup/auto-pause/transcoding/voice health), prefix, log level. Validates BOT_STATUS/COMMAND_PREFIX/LOG_LEVEL
- `messages.py` — user text | `aliases.py` — command aliases | `paths.py` — file paths
- `filename_patterns.py` — strip numeric prefixes from names
- `timing.py` — TTLs, cooldowns, debounce, voice health intervals

**Implementation:**
- `bot.py` — entry, events, watchdogs | `handlers/commands.py` — all commands
- `core/player.py` — MusicPlayer, queue, shuffle (`switch_playlist()` sync)
- `core/playback.py` — _play_current/_play_next, FFmpeg callbacks (session-guarded), voice health checks
- `core/track.py` — Track class, library load, playlist discovery, multi-format
- `systems/spam_protection.py` — 5-layer protection | `systems/cleanup.py` — dual cleanup (TTL + history)
- `systems/voice_manager.py` — auto-pause/disconnect/resume
- `systems/watchdog.py` — hang detection + adaptive voice health monitoring
- `utils/discord_helpers.py` — safe wrappers (atomic state pattern), voice health (VoiceHealthMonitor, check_voice_health_and_reconnect)
- `utils/persistence.py` — channel/playlist persist (persistence pattern) | `utils/context_managers.py` — suppress_callbacks, reconnecting_state

## Commands

All in `handlers/commands.py`. Context-aware (e.g., `!play` resumes/jumps). Aliases in `config/aliases.py`, prefix in `config/features.py` (default `!`).

Available: play, pause, skip, stop, previous, shuffle, queue, tracks, playlists, help, aliases

## Critical Rules

**Bot lifecycle:** `bot.run()` creates event loop. Configure in `on_ready()`, not `__main__`. Set exception handler in `on_ready()` where `bot.loop` exists.

**Shutdown:** Order: watchdogs→players→`flush_all_immediately()`→voice→bot. Signal handlers (SIGINT/SIGTERM) schedule `shutdown_bot()` on `bot.loop`. No blocking ops.

**Persistence pattern:** Cache = source of truth. Load once, flush from cache (never re-read). Why: corrupted file would wipe cache. Pattern: `if not _loaded: load(); data = _cache.copy(); write(data)`. Atomic: tempfile + os.replace(). Ref: `utils/persistence.py`

**Atomic state pattern:** Lock entire op: check→API→update on success. Prevents races + stale state. Pattern: `async with lock: if needs: await api(); state = new`. Ref: `discord_helpers.py:update_presence()`

**Dual cleanup:** TTL + history scan independent (redundancy). Never merge/disable.

**Always:**
- `asyncio.sleep()` not `time.sleep()` | `time.monotonic()` for elapsed time
- Constants from `timing.py`, messages from `messages.py` | `python -m pip` not `pip`

**Thread safety (FFmpeg audio thread):**
- Reads: GIL-atomic (bool/int/ref) safe | Writes: `bot.loop.call_soon_threadsafe(setattr, ...)` never direct
- Coroutines: `asyncio.run_coroutine_threadsafe(coro, bot.loop)`
- Sessions: Cancel (`player.cancel_active_session()`/`suppress_callbacks`) before manual stop/skip/switch

**Voice health:** Adaptive states (Normal/Suspicious/Post-Reconnect/Recovery). Auto-reconnects >250ms latency. 30s cooldown. Per-guild monitors in `_health_monitors`. In `_play_current()` + `playback_watchdog()`. Toggles: `VOICE_HEALTH_CHECK_ENABLED`, `VOICE_HEALTH_CHECK_IN_WATCHDOG`

**Never:** Blocking I/O in handlers (use `asyncio.to_thread()`), change defaults silently, print secrets, heavy deps, spam reconnects (30s enforced)

**Files:** Opus/MP3/FLAC/WAV/M4A/OGG from `MUSIC_FOLDER`. Opus preferred (passthrough=zero CPU, others transcode). `ALLOW_TRANSCODING=False` for opus-only. Prevent path traversal.

## Documentation

Always: docstrings (purpose/args/return), inline comments (*why* not *what*), update AGENTS.md for new files/architecture, update .txt/.py after changes (if applicable), config comments (purpose/values/restart)
