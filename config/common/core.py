# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

r"""
========================================================================================================
JILL MUSIC BOT - CORE CONFIGURATION
========================================================================================================

This file contains settings that work in BOTH prefix mode (!play) and slash mode (/play).

HOW TO CUSTOMIZE:
  1. Find the setting you want to change below
  2. Change 'None' to your desired value (see examples in comments)
  3. Save the file and restart the bot

  Example:
    COMMAND_PREFIX = None        ← Default (uses .env or '!')
    COMMAND_PREFIX = '?'         ← Override to use '?' instead

DOCKER USERS:
  Leave settings as 'None' and create a .env file instead (see .env.example)

PRIORITY:
  Python setting (if not None) > .env file > built-in default

RESTART REQUIRED:
  All changes require restarting the bot to take effect.
  - Linux: sudo systemctl restart jill.service
  - Windows: Stop bot (Ctrl+C) and restart

========================================================================================================
"""

import os

# =========================================================================================================
# Internal helper functions (used by settings below - scroll down to skip to settings)
# =========================================================================================================

def _str_to_bool(value):
    """Convert string to boolean (for environment variables)."""
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('true', '1', 'yes', 'on')

def _get_config(python_value, env_name, default, converter=None):
    """Get configuration value using priority system (Python > .env > default)."""
    if python_value is not None:
        return python_value
    env_value = os.getenv(env_name)
    if env_value is not None:
        return converter(env_value) if converter else env_value
    return default

# =========================================================================================================
# 🎵 BASIC SETTINGS (MOST COMMON)
# =========================================================================================================
#
# These are the settings you'll most likely want to customize when first setting up your bot.

# ----------------------------------------
# Command Prefix
# ----------------------------------------
# What symbol users type before commands (prefix mode only)
#
# Examples:
#   '!' = !play, !skip, !queue (default)
#   '$' = $play, $skip, $queue
#   '?' = ?play, ?skip, ?queue
#   '!!' = !!play (multi-character works!)
#   '🎵' = 🎵play (emoji works!)
#
# Note: Slash mode (/play) ignores this setting
# Note: Don't use '/', '@', or '#' (reserved by Discord)
#
COMMAND_PREFIX = None  # Leave as None to use .env or default ('!')
COMMAND_PREFIX = _get_config(COMMAND_PREFIX, 'COMMAND_PREFIX', '!')

# Validation
if not COMMAND_PREFIX or len(COMMAND_PREFIX) > 5:
    raise ValueError(f"Invalid COMMAND_PREFIX '{COMMAND_PREFIX}'. Must be 1-5 characters.")
if COMMAND_PREFIX in ['/', '@', '#']:
    raise ValueError(f"COMMAND_PREFIX '{COMMAND_PREFIX}' is reserved by Discord. Choose a different prefix.")

# ----------------------------------------
# Music Folder
# ----------------------------------------
# Where your music files are stored
#
# Examples:
#   'music' = ./music folder (default)
#   '/home/user/Music' = absolute path
#   'C:\\Music' = Windows path
#
MUSIC_FOLDER = None  # Leave as None to use .env or default ('music')
MUSIC_FOLDER = _get_config(MUSIC_FOLDER, 'MUSIC_FOLDER', 'music')

# ----------------------------------------
# Bot Status Indicator
# ----------------------------------------
# The colored dot next to bot's name in Discord
#
# Options:
#   'online' = Green dot (bot is available)
#   'dnd' = Red dot (do not disturb) - default
#   'idle' = Yellow dot (away)
#   'invisible' = Gray dot (appears offline but still works)
#
BOT_STATUS = None  # Leave as None to use .env or default ('dnd')
BOT_STATUS = _get_config(BOT_STATUS, 'BOT_DISCORD_STATUS', 'dnd')

# Validation
if BOT_STATUS not in ['online', 'dnd', 'idle', 'invisible']:
    raise ValueError(f"Invalid BOT_STATUS '{BOT_STATUS}'. Must be: online, dnd, idle, or invisible")

# =========================================================================================================
# ⚙️ FEATURE TOGGLES (CUSTOMIZE BEHAVIOR)
# =========================================================================================================
#
# Enable or disable specific bot features.
# True = enabled, False = disabled

# ----------------------------------------
# Auto-Pause When Alone
# ----------------------------------------
# Should the bot pause music when everyone leaves the voice channel?
#
# True = Pauses after 30 seconds alone (saves CPU, prevents playing to empty channel)
# False = Keeps playing even when alone
#
AUTO_PAUSE_ENABLED = None  # Leave as None to use .env or default (True)
AUTO_PAUSE_ENABLED = _get_config(AUTO_PAUSE_ENABLED, 'AUTO_PAUSE_ENABLED', True, _str_to_bool)

# ----------------------------------------
# Auto-Disconnect When Alone
# ----------------------------------------
# Should the bot disconnect after being alone for a long time?
#
# True = Disconnects after 10 minutes alone (frees up voice connection)
# False = Stays connected forever (even when paused and alone)
#
AUTO_DISCONNECT_ENABLED = None  # Leave as None to use .env or default (True)
AUTO_DISCONNECT_ENABLED = _get_config(AUTO_DISCONNECT_ENABLED, 'AUTO_DISCONNECT_ENABLED', True, _str_to_bool)

# ----------------------------------------
# Message Cleanup
# ----------------------------------------
# Should the bot automatically clean up old messages in chat?
#
# AUTO_CLEANUP_ENABLED:
#   True = Bot runs background cleanup (keeps chat tidy)
#   False = Messages stay forever (chat gets cluttered)
#
# DELETE_OTHER_BOTS:
#   True = Also delete other bots' messages during cleanup
#   False = Only delete Jill's messages and user commands (safer default)
#
AUTO_CLEANUP_ENABLED = None  # Leave as None to use .env or default (True)
AUTO_CLEANUP_ENABLED = _get_config(AUTO_CLEANUP_ENABLED, 'AUTO_CLEANUP_ENABLED', True, _str_to_bool)

DELETE_OTHER_BOTS = None  # Leave as None to use .env or default (False)
DELETE_OTHER_BOTS = _get_config(DELETE_OTHER_BOTS, 'DELETE_OTHER_BOTS', False, _str_to_bool)

# ----------------------------------------
# Spam Protection
# ----------------------------------------
# Prevents users from spamming commands (RECOMMENDED: Keep enabled)
#
# SPAM_PROTECTION_ENABLED:
#   True = Bot ignores rapid command spam (prevents API rate limits)
#   False = NO PROTECTION - bot can crash from spam! (not recommended)
#
# SPAM_WARNING_ENABLED:
#   True = Bot warns users when they're spamming
#   False = Silent (users won't know why commands are ignored)
#
SPAM_PROTECTION_ENABLED = None  # Leave as None to use .env or default (True)
SPAM_PROTECTION_ENABLED = _get_config(SPAM_PROTECTION_ENABLED, 'SPAM_PROTECTION_ENABLED', True, _str_to_bool)

SPAM_WARNING_ENABLED = None  # Leave as None to use .env or default (True)
SPAM_WARNING_ENABLED = _get_config(SPAM_WARNING_ENABLED, 'SPAM_WARNING_ENABLED', True, _str_to_bool)

# =========================================================================================================
# 🎼 AUDIO SETTINGS
# =========================================================================================================

# ----------------------------------------
# Audio Format Support
# ----------------------------------------
# What audio formats can the bot play?
#
# ALLOW_TRANSCODING:
#   True = Play MP3, FLAC, WAV, M4A, OGG, OPUS (uses more CPU)
#   False = Only play .opus files (best performance, Discord's native format)
#
# RECOMMENDATION: Convert your music to .opus format for best results
# See README/04-Converting-To-Opus.txt for instructions
#
ALLOW_TRANSCODING = None  # Leave as None to use .env or default (True)
ALLOW_TRANSCODING = _get_config(ALLOW_TRANSCODING, 'ALLOW_TRANSCODING', True, _str_to_bool)

# Supported formats (in preference order - .opus is always preferred)
# Don't change this unless you know what you're doing
SUPPORTED_AUDIO_FORMATS = ['.opus', '.mp3', '.flac', '.wav', '.m4a', '.ogg']

# =========================================================================================================
# 📊 LOGGING SETTINGS
# =========================================================================================================

# ----------------------------------------
# Log Level
# ----------------------------------------
# How much information should the bot print to console/terminal?
#
# Options (from most verbose to least):
#   'DEBUG' = Everything (very noisy, use for troubleshooting)
#   'INFO' = Normal operation (recommended for most users)
#   'WARNING' = Only warnings and errors (quiet mode)
#   'ERROR' = Only errors (very quiet)
#   'CRITICAL' = Only critical failures (almost silent)
#
LOG_LEVEL = None  # Leave as None to use .env or default ('INFO')
LOG_LEVEL = _get_config(LOG_LEVEL, 'LOG_LEVEL', 'INFO', str.upper)

# Validation
if LOG_LEVEL not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
    raise ValueError(f"Invalid LOG_LEVEL '{LOG_LEVEL}'. Must be: DEBUG, INFO, WARNING, ERROR, or CRITICAL")

# ----------------------------------------
# Suppress Library Logs
# ----------------------------------------
# Should we reduce noise from the Discord library (disnake)?
#
# True = Disnake only shows warnings/errors (cleaner console, recommended)
# False = Disnake shows everything at LOG_LEVEL (very noisy)
#
SUPPRESS_LIBRARY_LOGS = None  # Leave as None to use .env or default (True)
SUPPRESS_LIBRARY_LOGS = _get_config(SUPPRESS_LIBRARY_LOGS, 'SUPPRESS_LIBRARY_LOGS', True, _str_to_bool)

# =========================================================================================================
# 🔧 ADVANCED SETTINGS (RARELY CHANGED)
# =========================================================================================================
#
# These are technical settings that most users won't need to touch.
# Only change these if you know what you're doing or were told to by support.

# ----------------------------------------
# Voice Connection Health Monitoring
# ----------------------------------------
# Auto-fix stuttering audio from network issues
#
# The bot checks voice connection health and reconnects if needed
# This fixes stuttering caused by high latency or dead WebSocket connections
#
VOICE_HEALTH_CHECK_ENABLED = None  # Leave as None to use .env or default (True)
VOICE_HEALTH_CHECK_ENABLED = _get_config(VOICE_HEALTH_CHECK_ENABLED, 'VOICE_HEALTH_CHECK', True, _str_to_bool)

# Technical constants for voice health monitoring
# (Don't change unless you're experiencing specific issues)
VOICE_HEALTH_CHECK_IN_WATCHDOG = True  # Monitor during playback
VOICE_HEALTH_LATENCY_THRESHOLD = 250.0  # Milliseconds before reconnect
VOICE_HEALTH_CHECK_INTERVAL = 10.0  # Seconds between checks
VOICE_HEALTH_RECONNECT_COOLDOWN = 30.0  # Seconds before retry

# ----------------------------------------
# Smart Message Management
# ----------------------------------------
# Edit existing messages instead of sending new ones (reduces API calls)
#
# True = Edits "now playing" messages (cleaner, recommended)
# False = Sends new message each time (more chat clutter)
#
SMART_MESSAGE_MANAGEMENT = None  # Leave as None to use .env or default (True)
SMART_MESSAGE_MANAGEMENT = _get_config(SMART_MESSAGE_MANAGEMENT, 'SMART_MESSAGE_MANAGEMENT', True, _str_to_bool)

# ----------------------------------------
# Message Cleanup Methods
# ----------------------------------------
# Technical settings for how messages are cleaned up
#
# TTL_CLEANUP_ENABLED:
#   True = Messages expire after set time (like TTL in databases)
#   False = Messages never auto-delete
#
# BATCH_DELETE_ENABLED:
#   True = Delete multiple messages at once (faster, recommended)
#   False = Delete one at a time (slower)
#
TTL_CLEANUP_ENABLED = None  # Leave as None to use .env or default (True)
TTL_CLEANUP_ENABLED = _get_config(TTL_CLEANUP_ENABLED, 'TTL_CLEANUP_ENABLED', True, _str_to_bool)

BATCH_DELETE_ENABLED = None  # Leave as None to use .env or default (True)
BATCH_DELETE_ENABLED = _get_config(BATCH_DELETE_ENABLED, 'BATCH_DELETE_ENABLED', True, _str_to_bool)

# ----------------------------------------
# Internal Constants
# ----------------------------------------
# Low-level technical constants
# DON'T CHANGE THESE unless specifically instructed by documentation/support

AUTO_PAUSE_WHEN_ALONE = AUTO_PAUSE_ENABLED  # Alias for compatibility
PAUSE_ON_EMPTY_DELAY = 30.0  # Seconds to wait before pausing when alone
MAX_HISTORY = 100  # Maximum number of recently played tracks to remember
WATCHDOG_CHECK_INTERVAL = 30.0  # Seconds between playback health checks
WATCHDOG_HANG_THRESHOLD = 90.0  # Seconds before declaring playback "stuck"

# ----------------------------------------
# Bot Token (DO NOT EDIT)
# ----------------------------------------
# Your Discord bot token - ALWAYS set this in .env file for security
# NEVER hardcode your token in Python files (it could leak on GitHub!)
#
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN', '').strip()

# =========================================================================================================
# Export Configuration
# =========================================================================================================
# (This list tells Python which settings to make available to the rest of the bot)

__all__ = [
    'BOT_TOKEN',
    'LOG_LEVEL',
    'SUPPRESS_LIBRARY_LOGS',
    'COMMAND_PREFIX',
    'MUSIC_FOLDER',
    'MAX_HISTORY',
    'WATCHDOG_CHECK_INTERVAL',
    'WATCHDOG_HANG_THRESHOLD',
    'ALLOW_TRANSCODING',
    'SUPPORTED_AUDIO_FORMATS',
    'VOICE_HEALTH_CHECK_ENABLED',
    'VOICE_HEALTH_CHECK_IN_WATCHDOG',
    'VOICE_HEALTH_LATENCY_THRESHOLD',
    'VOICE_HEALTH_CHECK_INTERVAL',
    'VOICE_HEALTH_RECONNECT_COOLDOWN',
    'AUTO_PAUSE_WHEN_ALONE',
    'AUTO_PAUSE_ENABLED',
    'AUTO_DISCONNECT_ENABLED',
    'PAUSE_ON_EMPTY_DELAY',
    'BOT_STATUS',
    'SPAM_PROTECTION_ENABLED',
    'SPAM_WARNING_ENABLED',
    'AUTO_CLEANUP_ENABLED',
    'TTL_CLEANUP_ENABLED',
    'BATCH_DELETE_ENABLED',
    'DELETE_OTHER_BOTS',
    'SMART_MESSAGE_MANAGEMENT',
]
