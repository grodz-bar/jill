# AGENTS.md - Discord Music Bot

Quick start: `python3 bot.py` (needs `.env` with `DISCORD_BOT_TOKEN` + `JILL_COMMAND_MODE=prefix|slash`, Python 3.11+, `python -m pip install -r requirements.txt`)

Dual modes: Classic (`!play`) or Modern (`/play`). Set via `JILL_COMMAND_MODE` in `.env`. Mode-aware config loading in `config/__init__.py`.

Audio: MP3/FLAC/WAV/M4A/OGG/OPUS supported. Opus preferred (zero CPU). See `README/04-Converting-To-Opus.txt`.

## Agent Preferences

- Assume novice, <200 words, format: Answer→Why→How→Next
- Note risks. Prefer stdlib

## File Map

**Config** (`/config/`):
- `__init__.py` — detects JILL_COMMAND_MODE and loads mode-specific configs
- **Priority:** Python > .env > default. Helpers: `_get_config()`, `_str_to_bool()` (top of each file)
- **Common** (both): `basic_settings.py` (bot identity, music folder, feature toggles), `audio_settings.py` (FFmpeg, voice health monitoring), `advanced.py` (logging, watchdog intervals), `messages.py` (shared messages), `spam_protection.py` (Layer 3 serial queue only), `permissions.py`, `filename_patterns.py`
- **Prefix**: `features.py`, `messages.py` (prefix-specific messages only), `aliases.py`, `spam_protection.py` (Layers 1-2, command cooldowns), `cleanup.py` (TTL, history scanning, message lifetimes)
- **Slash**: `features.py`, `messages.py` (slash-specific messages only), `timing.py` (button cooldowns, update throttling, control panel settings), `embeds.py`, `buttons.py` (cooldown configs)
- **IMPORTANT**: Numbers/booleans → mode-specific `spam_protection.py`/`timing.py` or common `basic_settings.py`/`audio_settings.py`/`advanced.py` | User-facing text → `messages.py` | NEVER hardcode in implementation files

**Implementation:**
- `bot.py` — entry, gateway events (on_ready, on_resumed, on_disconnect), lifecycle, voice restoration
- **Handlers:**
  - `commands.py` — prefix (12 cmds, `@permission_check()`)
  - `slash_commands.py` — slash (11 cmds, ephemeral, control panel)
  - `buttons.py` — button interactions (Layer 4 cooldowns, stale interaction handling)
- **Core:** `player.py`, `playback.py` (FFmpeg, session-guarded), `track.py`
- **Systems:**
  - `spam_protection.py` — Layered protection (prefix: Layers 1-2-3, slash: Layer 3 only). Config split: `config/common/spam_protection.py` (Layer 3 serial queue), `config/prefix/spam_protection.py` (Layers 1-2 + command cooldowns), `config/slash/timing.py` (button cooldowns)
  - `cleanup.py` — TTL message cleanup (prefix only)
  - `control_panel.py` — ControlPanelManager (slash only)
  - `voice_manager.py` — auto-pause/disconnect when alone in channel
  - `watchdog.py` — FFmpeg hang detection + voice health monitoring (background tasks)
- **Utils:**
  - `discord_helpers.py` — 4 helpers (get_guild_player, ensure_voice_connected, send_player_message, spam_protected_execute) + voice health
  - `permission_checks.py`, `response_helper.py`, `persistence.py`

## Commands

**Prefix** (12): play, pause, skip, stop, previous, shuffle, queue, tracks, playlist, playlists, help, aliases. Context-aware (`!play` resumes/jumps). Aliases in `config/prefix/aliases.py`.

**Slash** (11): play, pause, skip, stop, previous, shuffle, queue, tracks, playlist, playlists, help. Ephemeral responses. Control panel updates.

**Buttons**: `music_*` custom_ids (play, pause, skip, stop, previous, shuffle). Permission-checked. Spam-protected (Layer 4 cooldowns, configurable per-button).

## Helper Functions (utils/discord_helpers.py)

Reduce boilerplate (~150 lines saved):

1. **`get_guild_player(context, bot)`** — Get MusicPlayer (prefix/slash compatible). 33 uses.

2. **`ensure_voice_connected(player, context, error_message=None)`** — Validate voice + error. Returns bool. 10 uses.

3. **`send_player_message(player, context, message_key, ttl_type, **format_kwargs)`** — Auto-sanitize + TTL cleanup. 20+ uses.

4. **`spam_protected_execute(player, ctx, bot, command_name, execute_func, cooldown)`** — 4-layer spam protection for prefix commands. Checks spam sessions (Discord drip-feed handling, Layer 1 filters first), circuit breaker (guild isolation, Layer 2 counts filtered commands), queues for serial execution, and enforces cooldowns. Circuit breaker counts commands AFTER spam session filtering, so single-user spam won't trip guild-wide lockouts. Used by 11 prefix commands (all except `play` which handles voice/resume/jump logic manually). Slash command invocations (`/play`) bypass Layers 1-2-4 since Discord provides built-in rate limiting, but control panel buttons use Layer 4 (cooldowns) to prevent spam-clicking. Both call playback functions directly which queue themselves via Layer 3 (serial queue).

## Where to Find...

**Voice Reconnection (2 systems):**
- **Health monitoring** (`utils/discord_helpers.py`) — fixes stuttering/latency during playback (watchdog-triggered)
- **Gateway recovery** (`bot.py`) — restores voice after network drops/VPN changes (event-triggered: on_ready, on_resumed)

**Playback:**
- Start/stop: `core/playback.py` (_play_current, _play_next)
- State: `core/player.py` (MusicPlayer class)
- Sessions: `core/playback.py` (PlaybackSession tokens prevent stale callbacks)

**Message Management:**
- Send: `utils/discord_helpers.py` (send_player_message)
- Cleanup: `systems/cleanup.py` (prefix only, TTL-based)
- Embeds: `config/slash/embeds.py` (create_*_embed functions)

**Spam Protection:**
- Implementation: `systems/spam_protection.py` (SpamProtector class)
- Wrapper: `utils/discord_helpers.py` (spam_protected_execute)
- Config: `config/common/spam_protection.py` (Layer 3 serial queue), `config/prefix/spam_protection.py` (Layers 1-2, command cooldowns), `config/slash/timing.py` (button cooldowns)

**Permissions:**
- Check: `utils/permission_checks.py` (permission_check decorator)
- Config: `config/common/permissions.py` (REQUIRE_ROLES, ALLOWED_ROLE_NAMES)

**State Persistence:**
- Save/load: `utils/persistence.py` (atomic writes, cache-based)
- Channel IDs: `last_channels.json` | Control panels: `last_message_ids.json`

## Critical Rules

**Lifecycle:** Configure in `on_ready()` (not `__main__`). Shutdown order: watchdogs→players→`flush_all_immediately()`→voice→bot.

**Persistence:** Cache = source of truth. Load once, flush from cache (never re-read). Atomic: tempfile + os.replace(). Ref: `utils/persistence.py`

**Atomic state:** Lock entire op: check→API→update. Pattern: `async with lock: if needs: await api(); state = new`. Ref: `discord_helpers.py:update_presence()`

**Cleanup:** Only used in prefix mode. (`CleanupManager = None` in slash mode). Slash mode uses ephemeral messages + button cooldowns instead.

**Control panel:** Throttled updates (2s). Persisted in `last_message_ids.json`. Created on first `/play`.

**Always:** `asyncio.sleep()` (not `time.sleep()`), `time.monotonic()` for elapsed, `python -m pip` (not `pip`), `from config import X` (never `from config.messages/timing/aliases`).

**Thread safety (FFmpeg):** Reads GIL-atomic safe. Writes: `bot.loop.call_soon_threadsafe()`. Coroutines: `asyncio.run_coroutine_threadsafe()`. Cancel sessions before manual actions.

**Voice health:** Auto-reconnects >250ms latency. 30s cooldown. Toggles: `VOICE_HEALTH_CHECK_ENABLED`, `VOICE_HEALTH_CHECK_IN_WATCHDOG`

**Never:** Blocking I/O (use `asyncio.to_thread()`), print secrets, skip slash permissions, discord.py API (we use disnake).

**Files:** Opus preferred (zero CPU). Others transcode. `ALLOW_TRANSCODING=False` for opus-only.

## Documentation

**AGENTS.md:** Update when changing architecture, file structure, command count, helper functions, or critical rules. Accuracy critical for agent handoffs.

**Code:** Keep Docstrings (purpose/args/return), inline comments (*why* not *what*), config comments (purpose/values/restart), .md's and .txt's updated as well.
