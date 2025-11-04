# AGENTS.md - Discord Music Bot

Quick start: `python3 bot.py` (needs `.env` with `DISCORD_BOT_TOKEN` + `JILL_COMMAND_MODE=prefix|slash`, Python 3.11+, `python -m pip install -r requirements.txt`)

Dual modes: Classic (`!play`) or Modern (`/play`). Set via `JILL_COMMAND_MODE` in `.env`. Mode-aware config loading in `config/__init__.py`.

Audio: MP3/FLAC/WAV/M4A/OGG/OPUS supported. Opus preferred (zero CPU). See `README/04-Converting-To-Opus.txt`.

## Agent Preferences

- Assume novice, <200 words, format: Answer→Why→How→Next
- Note risks. Prefer stdlib

## File Map

**Config** (`/config/`):
- `mode.py` — detects JILL_COMMAND_MODE | `__init__.py` — mode loader
- **Priority:** Python > .env > default. Helpers: `_get_config()`, `_str_to_bool()` (top of each file)
- **Common** (both): `core.py` (token, music folder, logging, voice), `permissions.py`, `filename_patterns.py`, `paths.py`, `bot_identity.py`
- **Prefix**: `features.py`, `messages.py`, `aliases.py`, `timing.py`
- **Slash**: `features.py`, `messages.py`, `timing.py`, `embeds.py`, `buttons.py`

**Implementation:**
- `bot.py` — entry, events, mode setup
- **Handlers:**
  - `commands.py` — prefix (12 cmds, `@permission_check()`)
  - `slash_commands.py` — slash (11 cmds, ephemeral, control panel)
  - `buttons.py` — button interactions
- **Core:** `player.py`, `playback.py` (FFmpeg, session-guarded), `track.py`
- **Systems:**
  - `spam_protection.py` — 4-layer (spam sessions, circuit breaker, serial queue, cooldowns)
  - `cleanup.py` — TTL cleanup (prefix only)
  - `control_panel.py` — ControlPanelManager (slash only)
  - `voice_manager.py` — auto-pause | `watchdog.py` — hang detection
- **Utils:**
  - `discord_helpers.py` — 4 helpers (get_guild_player, ensure_voice_connected, send_player_message, spam_protected_execute) + voice health
  - `permission_checks.py`, `context_adapter.py`, `response_helper.py`, `persistence.py`

## Commands

**Prefix** (12): play, pause, skip, stop, previous, shuffle, queue, tracks, playlist, playlists, help, aliases. Context-aware (`!play` resumes/jumps). Aliases in `config/prefix/aliases.py`.

**Slash** (11): play, pause, skip, stop, previous, shuffle, queue, tracks, playlist, playlists, help. Ephemeral responses. Control panel updates.

**Buttons**: `music_*` custom_ids (play, pause, skip, stop, previous, shuffle). Permission-checked.

## Helper Functions (utils/discord_helpers.py)

Reduce boilerplate (~150 lines saved):

1. **`get_guild_player(context, bot)`** — Get MusicPlayer (prefix/slash compatible). 33 uses.

2. **`ensure_voice_connected(player, context, error_message=None)`** — Validate voice + error. Returns bool. 10 uses.

3. **`send_player_message(player, context, message_key, ttl_type, **format_kwargs)`** — Auto-sanitize + TTL cleanup. 20+ uses.

4. **`spam_protected_execute(player, ctx, bot, command_name, execute_func, cooldown)`** — 4-layer spam protection for prefix commands. Checks spam sessions (Discord drip-feed handling, Layer 1 filters first), circuit breaker (guild isolation, Layer 2 counts filtered commands), queues for serial execution, and enforces cooldowns. Circuit breaker counts commands AFTER spam session filtering, so single-user spam won't trip guild-wide lockouts. Used by 11 prefix commands (all except `play` which handles voice/resume/jump logic manually). Slash commands bypass this—they call playback functions directly since Discord provides built-in protection.

## Critical Rules

**Lifecycle:** Configure in `on_ready()` (not `__main__`). Shutdown order: watchdogs→players→`flush_all_immediately()`→voice→bot.

**Persistence:** Cache = source of truth. Load once, flush from cache (never re-read). Atomic: tempfile + os.replace(). Ref: `utils/persistence.py`

**Atomic state:** Lock entire op: check→API→update. Pattern: `async with lock: if needs: await api(); state = new`. Ref: `discord_helpers.py:update_presence()`

**Cleanup:** Prefix only (`self.enabled = (COMMAND_MODE == 'prefix')`). Slash uses ephemeral.

**Control panel:** Throttled updates (2s). Persisted in `message_ids.json`. Created on first `/play`.

**Always:** `asyncio.sleep()` (not `time.sleep()`), `time.monotonic()` for elapsed, `python -m pip` (not `pip`), `from config import X` (never `from config.messages/timing/aliases`).

**Thread safety (FFmpeg):** Reads GIL-atomic safe. Writes: `bot.loop.call_soon_threadsafe()`. Coroutines: `asyncio.run_coroutine_threadsafe()`. Cancel sessions before manual actions.

**Voice health:** Auto-reconnects >250ms latency. 30s cooldown. Toggles: `VOICE_HEALTH_CHECK_ENABLED`, `VOICE_HEALTH_CHECK_IN_WATCHDOG`

**Never:** Blocking I/O (use `asyncio.to_thread()`), print secrets, skip slash permissions, discord.py API (we use disnake).

**Files:** Opus preferred (zero CPU). Others transcode. `ALLOW_TRANSCODING=False` for opus-only.

## Documentation

**AGENTS.md:** Update when changing architecture, file structure, command count, helper functions, or critical rules. Accuracy critical for agent handoffs.

**Code:** Keep Docstrings (purpose/args/return), inline comments (*why* not *what*), config comments (purpose/values/restart), .md's and .txt's updated as well.
