# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

r"""
Feature Toggles

This file contains feature switches and adjustments for the major bot behaviors.

QUICK GUIDE:
- True = feature enabled, False = feature disabled
- Restart bot after changes:
  * Linux: sudo systemctl restart jill.service
  * Windows: Stop bot (Ctrl+C) and restart it / Restart your Task Scheduler task/process
- Most features work independently (no dependencies)
- WARNING: Keep SPAM_PROTECTION_ENABLED = True (prevents API rate limits)

To change the bot profile picture/banner/etc, do it on the developer portal:
https://discord.com/developers/applications

"""

# =========================================================================================================
# MESSAGE CLEANUP FEATURES
# =========================================================================================================

# CLEANUP SYSTEMS EXPLAINED:
# --------------------------
# SCHEDULED CLEANUP (TTL-based): Messages get "expiration dates" and are deleted when time is up
# CHANNEL SWEEP (History scan): Scans channel history periodically + when spam detected and smartly
# cleans up left over bot messages and left over user commands (!play, !queue, etc)
#
# Why both? SCHEDULED CLEANUP is fast for known messages, CHANNEL SWEEP catches missed ones.
# Together they ensure a clean chat with redundancy.
#
# CHANNEL PERSISTENCE:
# The bot remembers which text channel to clean up per server. Any command (not just !play)
# updates the active channel. On bot restart, cleanup workers automatically resume on the
# saved channel. Channel data is stored in last_channels.json and managed transparently.

DELETE_OTHER_BOTS = False          # Delete other bots' messages as well during cleanup
                                   # False = only delete jill's messages (and user !commands)
                                   # Set to False by default just in case, but I find it useful

AUTO_CLEANUP_ENABLED = True        # Enable automatic message cleanup (background worker)
                                   # False = manual cleanup only (chat gets cluttered)

TTL_CLEANUP_ENABLED = True         # Auto-delete messages after TTL expires
                                   # False = messages stay forever

# =========================================================================================================
# ANTI-SPAM FEATURES
# =========================================================================================================

# SPAM PROTECTION EXPLAINED:
# --------------------------
# The bot automatically prevents spam and abuse in multiple ways:
# - Bot ignores commands sent too quickly (prevents spam)
# - Bot checks permissions before doing expensive operations (fast errors)
# - Bot limits how many commands can run at once (protects Discord API)
# - Bot waits for spam to stop before executing commands (prevents flooding)
# - Bot processes commands one at a time (prevents conflicts)
# - Bot adds cooldowns after commands finish (prevents rapid re-execution)
#
# This keeps the bot stable and prevents abuse.

SPAM_PROTECTION_ENABLED = True     # CRITICAL: Prevents API rate limits
                                   # False = NO PROTECTION (can break bot!)

SPAM_WARNING_ENABLED = True        # Show spam warning responses when users spam commands
                                   # False = silent (users won't know why commands don't work)

# =========================================================================================================
# AUTO-PAUSE FEATURES
# =========================================================================================================

AUTO_PAUSE_ENABLED = True          # Auto-pause when alone in voice channel (default: 10s)
                                   # False = keeps playing to empty channel

AUTO_DISCONNECT_ENABLED = True     # Auto-disconnect when alone too long (default: 10min)
                                   # False = stays connected forever

# =========================================================================================================
# PLAYBACK FEATURES
# =========================================================================================================

# NOTE: Disabled features won't show up in the !help menu to prevent confusion.

SHUFFLE_MODE_ENABLED = True        # Enable !shuffle command (toggles shuffle mode)
                                   # False = command returns "feature disabled"

QUEUE_DISPLAY_ENABLED = True       # Enable !queue command (shows upcoming tracks)
                                   # False = command returns "feature disabled"

QUEUE_DISPLAY_COUNT = 3            # Number of upcoming tracks to show in !queue
                                   # Higher = more tracks shown (longer messages)

LIBRARY_DISPLAY_ENABLED = True     # Enable !tracks command (shows all tracks in current playlist)
                                   # False = command returns "feature disabled"

LIBRARY_PAGE_SIZE = 20             # Number of tracks per page in !tracks
                                   # Higher = more tracks per page (longer messages)

PLAYLIST_SWITCHING_ENABLED = True  # Enable !playlists and !tracks [name] commands (multi-playlist mode)
                                   # False = commands return "feature disabled"
                                   # Note: Only works if you have playlists (music in subfolders)

PLAYLIST_PAGE_SIZE = 20            # Number of playlists per page in !playlists
                                   # Higher = more playlists per page (longer messages)

# =========================================================================================================
# AUDIO FORMAT FEATURES
# =========================================================================================================

# AUDIO TRANSCODING EXPLAINED:
# -----------------------------
# By default, the bot supports multiple audio formats (MP3, FLAC, WAV, M4A, OGG, OPUS).
# OPUS files are ALWAYS preferred when available (zero CPU overhead, best quality).
# Other formats are transcoded in real-time (uses CPU during playback).
#
# RECOMMENDATION: Convert your music to .opus format using the setup scripts for:
# - Lower CPU usage (especially on Raspberry Pi)
# - Guaranteed stability (Discord-native format)
# - Best audio quality (no double-compression)
#
# See README/04-Converting-To-Opus.txt for conversion instructions.

ALLOW_TRANSCODING = True           # Enable playback of non-opus formats (MP3, FLAC, etc)
                                   # False = opus-only mode (highest performance, guaranteed stability)
                                   # True = supports multiple formats (convenience, higher CPU usage)

# Supported audio formats (in preference order - opus is always first)
# DO NOT MODIFY unless you know what you're doing
SUPPORTED_AUDIO_FORMATS = ['.opus', '.mp3', '.flac', '.wav', '.m4a', '.ogg']

# =========================================================================================================
# ADVANCED FEATURES
# =========================================================================================================

SMART_MESSAGE_MANAGEMENT = True    # Edit "now serving" messages instead of sending new ones
                                   # False = more messages in chat (uses more API calls)

BATCH_DELETE_ENABLED = True        # Delete messages in batches (faster cleanup)
                                   # False = slower cleanup (more API calls)

VOICE_RECONNECT_ENABLED = True     # Auto-reconnect on voice errors
                                   # False = manual reconnection required

# Voice Health Monitoring - Auto-fix stuttering from network issues
# This feature detects degraded voice connections (high latency, dead WebSocket)
# and automatically reconnects to fix stuttering audio
VOICE_HEALTH_CHECK_ENABLED = True  # Check voice health before each track
VOICE_HEALTH_CHECK_IN_WATCHDOG = True  # Also monitor during playback (recommended!)

# =========================================================================================================
# BOT APPEARANCE
# =========================================================================================================

# Bot Status (online indicator color)
# Options: 'online' (green), 'dnd' (red), 'idle' (yellow), 'invisible' (gray/offline)
# Note: 'invisible' makes bot appear offline but still functional

BOT_STATUS = 'dnd'

# Validate BOT_STATUS at import time to catch typos early
ALLOWED_BOT_STATUSES = {'online', 'dnd', 'idle', 'invisible'}
if BOT_STATUS not in ALLOWED_BOT_STATUSES:
    raise ValueError(f"Invalid BOT_STATUS '{BOT_STATUS}'. Allowed: {sorted(ALLOWED_BOT_STATUSES)}")

# =========================================================================================================
# COMMAND PREFIX
# =========================================================================================================

# Command Prefix (what users type before commands)
# This is for "prefix commands" (traditional text-based Discord commands)
#
# Examples:
#   '!' = !play, !skip, !queue (default)
#   '$' = $play, $skip, $queue
#   '?' = ?play, ?skip, ?queue
#   '!!' = !!play, !!skip, !!queue (multi-character works!)
#   '🎵' = 🎵play, 🎵skip, 🎵queue (emoji works!)
#
# Note: This does NOT affect Discord slash commands (/play), only text commands
# Note: All aliases automatically work with your chosen prefix
# Note: If you change this, consider updating config/messages.py to match
#       (search for '!' and replace with your new prefix in command examples)
#
# Restart required after changing this setting
COMMAND_PREFIX = '!'

# Validation (prevents common mistakes)
if not COMMAND_PREFIX or len(COMMAND_PREFIX) > 5:
    raise ValueError(f"Invalid COMMAND_PREFIX '{COMMAND_PREFIX}'. Must be 1-5 characters.")

# Reserved prefixes that conflict with Discord features
if COMMAND_PREFIX in ['/', '@', '#']:
    raise ValueError(
        f"COMMAND_PREFIX '{COMMAND_PREFIX}' conflicts with Discord features. "
        f"Choose a different prefix (/, @, # are reserved by Discord)."
    )

# =========================================================================================================
# LOGGING CONFIGURATION
# =========================================================================================================

# Logging Level - Controls how much the bot logs to console/terminal
# This affects how verbose the bot's output is when running
#
# Levels (from most verbose to least):
#   'DEBUG'    - Everything including diagnostic info (very noisy, use for debugging)
#   'INFO'     - Normal operation messages (recommended for most users)
#   'WARNING'  - Only warnings and errors (quiet mode)
#   'ERROR'    - Only errors and critical issues (very quiet)
#   'CRITICAL' - Only critical failures that might crash the bot (silent unless dying)
#
# When to use each level:
#   - DEBUG: When troubleshooting issues or tracking down bugs
#   - INFO: Normal everyday use (default, recommended)
#   - WARNING: Production environments where you only care about problems
#   - ERROR: When you only want to see actual failures
#   - CRITICAL: Extreme cases (rarely useful)
#
# Restart required after changing this setting
LOG_LEVEL = 'INFO'

# Suppress Library Logs - Reduce noise from Discord library (disnake)
# The Discord library (disnake) can be very chatty with INFO messages
# This setting keeps disnake at WARNING level even when LOG_LEVEL is DEBUG/INFO
#
# True  = Disnake only logs warnings/errors (recommended, much cleaner)
# False = Disnake logs at the same level as LOG_LEVEL (very noisy)
#
# Restart required after changing this setting
SUPPRESS_LIBRARY_LOGS = True

# Validation (prevents typos)
ALLOWED_LOG_LEVELS = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
if LOG_LEVEL not in ALLOWED_LOG_LEVELS:
    raise ValueError(f"Invalid LOG_LEVEL '{LOG_LEVEL}'. Allowed: {sorted(ALLOWED_LOG_LEVELS)}")

# =========================================================================================================
# FUTURE FEATURES (WIP)
# =========================================================================================================

#FULL_SHUFFLE_ENABLED = False       # Shuffles every song of every playlist together
#CROSS_SERVER_SYNC_ENABLED = False  # Enable cross-server synchronization
#VOLUME_CONTROL_ENABLED = False     # Enable volume control commands

# NOTE: Volume control unlikely to be implemented since it causes so many freaking issues,
# but maybe I'll add the feature as a toggle for the people that wanna risk it.


