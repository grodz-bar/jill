# Setup Script Portability Logic

## How the Bot Finds Music

From `config/paths.py` line 29:
```python
MUSIC_FOLDER = os.getenv('MUSIC_FOLDER') or str(_BOT_ROOT / 'music')
```

**3-tier fallback system:**
1. Check .env file for `MUSIC_FOLDER`
2. Check system environment variable `MUSIC_FOLDER`
3. **Default to `bot_root/music/` (relative path anchored to bot location)**

The bot uses `_BOT_ROOT` which is calculated as:
```python
_BOT_ROOT = Path(__file__).resolve().parent.parent
```

This means the bot ALWAYS knows where it is, and resolves `music/` relative to its own location.

---

## Setup Script Portability Rules

### Rule 1: Default Path = No .env Entry (PORTABLE)

**When user presses Enter (empty input):**
- Set `MUSIC_PATH="music\"` (Windows) or `"music/"` (Linux)
- **DO NOT write `MUSIC_FOLDER` to .env file**
- Bot uses fallback: `_BOT_ROOT / 'music'` (anchored to bot directory)
- Result: **Fully portable** - entire bot folder can be moved anywhere

### Rule 2: Custom Path = Write to .env (NON-PORTABLE)

**When user enters custom path:**
- Set `MUSIC_PATH=[custom path]`
- **WRITE `MUSIC_FOLDER=[custom path]` to .env file**
- Bot reads from .env and uses absolute path
- Result: **Bot folder portable, music folder stays at custom location**

### Rule 3: Relative Paths Stay Relative

- Default music folder is always `music\` or `music/` (relative)
- Script creates folder relative to project root
- Bot resolves relative path from its own location (`_BOT_ROOT`)
- Works regardless of where user runs bot from

---

## What Makes It Portable

### Portable Setup (user presses Enter)

```
local-jill/
├── venv/           ← Virtual environment (local to folder)
├── music/          ← Music folder (relative path)
│   ├── 01 - Album/
│   │   └── *.opus
│   └── 02 - Album/
│       └── *.opus
├── .env            ← Contains ONLY: DISCORD_BOT_TOKEN=xxx
├── bot.py
├── config/
│   └── paths.py    ← Resolves music/ relative to bot location
└── last_channels.json
```

**User can:**
- Move entire `local-jill/` folder to different drive (C: → D:)
- Rename parent directories
- Run bot from any location
- Zip and send to another computer
- Bot always finds `music/` relative to its own location

**Why it works:**
- No `MUSIC_FOLDER` in .env → bot uses fallback
- Fallback is `_BOT_ROOT / 'music'` → always relative to bot
- All paths anchored to bot location, not system paths

---

### Non-Portable Setup (user enters custom path)

```
local-jill/
├── venv/           ← Virtual environment (local to folder)
├── .env            ← Contains: DISCORD_BOT_TOKEN=xxx
│                      AND: MUSIC_FOLDER=D:\Music\jill\
├── bot.py
├── config/
│   └── paths.py
└── last_channels.json

D:\Music\jill\      ← Music folder (absolute path, separate location)
├── 01 - Album/
│   └── *.opus
└── 02 - Album/
    └── *.opus
```

**User can:**
- Move `local-jill/` folder (bot folder is portable)
- But music stays at `D:\Music\jill\`
- If music folder moves, must update .env

**Why it's not fully portable:**
- `MUSIC_FOLDER=D:\Music\jill\` in .env → absolute path
- Bot reads absolute path from .env
- Moving bot folder works, but music location is fixed

---

## Setup Script Logic Summary

### When user input is EMPTY (presses Enter)

**Script behavior:**
1. Set `MUSIC_PATH` to relative path: `"music\"` (Windows) or `"music/"` (Linux)
2. Create `music/` folder in project root if it doesn't exist
3. Write .env with ONLY `DISCORD_BOT_TOKEN`
4. **DO NOT write MUSIC_FOLDER to .env**
5. Display: "Using default music folder: music\ (inside bot folder)"
6. Display: "This keeps your bot portable - you can move the entire bot folder anywhere."

**Windows example:**
```batch
if "%MUSIC_PATH%"=="" set MUSIC_PATH=music\
REM Create folder
mkdir "%MUSIC_PATH%" 2>nul
REM Write .env
echo DISCORD_BOT_TOKEN=%BOT_TOKEN%> .env
REM DO NOT write MUSIC_FOLDER
```

**Linux example:**
```bash
if [ -z "$MUSIC_PATH" ]; then
    MUSIC_PATH="music/"
fi
# Create folder
mkdir -p "$MUSIC_PATH" 2>/dev/null
# Write .env
cat > .env << EOF
DISCORD_BOT_TOKEN=$BOT_TOKEN
EOF
# DO NOT write MUSIC_FOLDER
```

---

### When user input is NOT EMPTY (custom path)

**Script behavior:**
1. Set `MUSIC_PATH` to user's entered path
2. Create folder at that path if it doesn't exist
3. Write .env with `DISCORD_BOT_TOKEN` AND `MUSIC_FOLDER=[custom path]`
4. Display: "Music folder: [custom path]"
5. Display: "NOTE: Custom music folder location - bot folder is portable but music folder stays at: [custom path]"

**Windows example:**
```batch
REM User entered: D:\Music\jill\
set MUSIC_PATH=D:\Music\jill\
REM Create folder
mkdir "%MUSIC_PATH%" 2>nul
REM Write .env with BOTH values
echo DISCORD_BOT_TOKEN=%BOT_TOKEN%> .env
echo MUSIC_FOLDER=%MUSIC_PATH%>> .env
```

**Linux example:**
```bash
# User entered: /mnt/music/jill/
MUSIC_PATH="/mnt/music/jill/"
# Create folder
mkdir -p "$MUSIC_PATH" 2>/dev/null
# Write .env with BOTH values
cat > .env << EOF
DISCORD_BOT_TOKEN=$BOT_TOKEN
MUSIC_FOLDER=$MUSIC_PATH
EOF
```

---

## Critical Takeaway

**The absence of `MUSIC_FOLDER` in .env triggers the bot's fallback to `bot_root/music/`, which is what makes it fully portable.**

This is the key to ensuring "slam Enter" users get a portable setup by default.

When the bot starts:
```python
# config/paths.py
MUSIC_FOLDER = os.getenv('MUSIC_FOLDER') or str(_BOT_ROOT / 'music')
#                        ↑                      ↑
#                        Returns None           Uses this fallback
#                        if not in .env         (portable!)
```

---

## Testing Portability

### Test 1: Default Setup (Should be portable)
1. Run setup script
2. Press Enter for music folder (use default)
3. Check .env file - should ONLY have `DISCORD_BOT_TOKEN`
4. Move entire bot folder to different location
5. Run bot - should work without changes

### Test 2: Custom Path (Should be non-portable)
1. Run setup script
2. Enter custom path like `D:\Music\jill\`
3. Check .env file - should have BOTH `DISCORD_BOT_TOKEN` and `MUSIC_FOLDER`
4. Move bot folder to different location
5. Run bot - should still work (reads absolute path from .env)
6. Move music folder - bot will fail (absolute path no longer valid)

---

## Common Mistakes to Avoid

❌ **WRONG:** Always write `MUSIC_FOLDER` to .env
```batch
echo MUSIC_FOLDER=%MUSIC_PATH%>> .env
```
This breaks portability even for default setup.

✅ **CORRECT:** Only write `MUSIC_FOLDER` for custom paths
```batch
if %DEFAULT_PATH%==0 (
    echo MUSIC_FOLDER=%MUSIC_PATH%>> .env
)
```

❌ **WRONG:** Use absolute path for default
```batch
set MUSIC_PATH=%CD%\music\
echo MUSIC_FOLDER=%MUSIC_PATH%>> .env
```
This makes it non-portable.

✅ **CORRECT:** Use relative path and omit from .env
```batch
set MUSIC_PATH=music\
REM Don't write MUSIC_FOLDER to .env
```

