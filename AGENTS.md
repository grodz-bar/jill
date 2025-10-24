# AGENTS.md - (For AI Coding Agents)

Purpose: Instructions to run, check, and safely modify this repo.

## Setup / Run
- Python: 3.11+
- Install: `pip install -r requirements.txt`
- Env: `.env` with `DISCORD_BOT_TOKEN=<token>`, `MUSIC_FOLDER=./music` (folder of `.opus` files)
- Start: `python3 bot.py`

## Runtime files (not in git)
- .env — secrets/config
- last_channels.json — per-guild channel persistence
- bot.log — runtime logs
- music/ — user `.opus` library

## Quick Checks (no Discord required)
- Syntax: `python -m compileall .`
- Imports: `python - <<'PY'\nimport importlib; importlib.import_module('bot'); print('OK')\nPY`
- Files present: `test -f bot.py && test -f requirements.txt && echo OK`

## Repo Map (read-only contracts)
- `bot.py` — entry, events, presence, cleanup loops.
- `features.py` — feature flags. Do **not** change defaults silently.
- `timing.py` — authoritative constants (TTLs, intervals). Keep names/semantics.
- `messages.py` — user strings. Respect length & reuse.
- `paths.py` — runtime paths. Avoid new globals.
- `aliases.py` — command aliases. Keep backward compatible.
- Ops docs: `SETUP-*.txt`, `Converting-To-Opus.txt`, `troubleshooting.txt`.

## Voice / Media Requirements
- `disnake[voice] >= 2.9.0`, `PyNaCl >= 1.5.0`, FFmpeg + Opus on host.
- Accept only pre-encoded `.opus` from `MUSIC_FOLDER`.

## Safety & Guardrails (do-not-break)
1. **Dual cleanup systems** stay separate:
   - TTL loop → `_cleanup_messages()`
   - Channel sweep → `cleanup_channel_history()`
2. **Per-guild isolation**: no cross-guild global state.
3. **Async only** in event/callback paths; **never** blocking I/O.
4. **Spam protection**: keep layered checks (guild_only, perms, rate limits).
5. **Presence/AFK** timings: use constants from `timing.py` unchanged unless asked.
6. **Secrets**: never print tokens; `.env` stays out of git.
7. **Permissions**: require message_content, voice_states, members intents.
8. **Watchdog**: keep periodic watchdog loop & timeouts from `timing.py`; do not disable/block.

## Code Standards (concise)
- **Dependencies**: prefer stdlib; do not add deps unless necessary.
- **Typing**: add type hints for public funcs; use `collections.abc` (e.g., `Iterable`); avoid `Any`.
- **Imports**: stdlib → third‑party → local; no wildcard imports; module‑level constants in config files only.
- **Naming**: `snake_case` for vars/funcs, `UpperCamelCase` classes, `UPPER_SNAKE` constants.
- **Async rules**: never `time.sleep`; use `asyncio.sleep`. If unavoidable blocking I/O, wrap with `asyncio.to_thread(...)`.
- **Logging**: `logging.getLogger(__name__)`; no secrets; INFO for state, WARNING for recoverable, ERROR with exception context.
- **Errors**: validate cheap preconditions first; fail safe; avoid raising inside event handlers—catch/log and exit early.
- **Commands/Events**: keep permission/rate‑limit decorators; ensure `ctx.guild` present; keep messages short, pulled from `messages.py`.
- **Voice ops**: check `can_connect_to_channel`; cleanup/disconnect in `finally`; never spam reconnect attempts.
- **File/Path safety**: restrict to `.opus` under `MUSIC_FOLDER`; prevent path traversal (no `..` resolution outside base).

## Minimal Tasks Agents Can Do
- Small fixes in `bot.py` (typos, non‑blocking refactors).
- Update strings in `messages.py` (keep placeholders).
- Add a safe alias in `aliases.py` (no breaking changes).
- Adjust **documented** intervals in `timing.py` only if checks pass.

## Don’ts (hard rules)
- Don’t merge cleanup systems or alter their triggers.
- Don’t add synchronous network/file I/O in event handlers.
- Don’t change default features or intents silently.
- Don’t introduce external services, telemetry, or heavy deps.

## PR Rules (for agents)
- Diffs minimal & reversible; add rationale at top of patch.
- Must pass: compile check; clean startup (no new warnings).
- No secret leakage; no large files.

## Appendix: Critical Constants (names only)
# timing.py (authoritative)
TTL_CHECK_INTERVAL
USER_COMMAND_TTL
HISTORY_CLEANUP_INTERVAL
CLEANUP_SAFE_AGE_THRESHOLD
CLEANUP_HISTORY_LIMIT
CLEANUP_BATCH_SIZE
CLEANUP_BATCH_DELAY
SPAM_CLEANUP_DELAY
ALONE_PAUSE_DELAY
ALONE_DISCONNECT_DELAY
MAX_HISTORY
COMMAND_QUEUE_MAXSIZE
COMMAND_QUEUE_TIMEOUT
WATCHDOG_INTERVAL
WATCHDOG_TIMEOUT

--
Nearest-file wins: a subfolder's AGENTS.md overrides for that subtree.
