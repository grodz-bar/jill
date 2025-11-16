# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

r"""
========================================================================================================
JILL MUSIC BOT - BASIC SETTINGS
========================================================================================================

This file contains the most commonly customized settings for your bot.
These settings work in BOTH prefix mode (!play) and slash mode (/play).

Start here for your initial bot setup and day-to-day configuration changes.

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

FOR ADVANCED SETTINGS:
  - Audio/voice tweaking: See audio_settings.py
  - Internal constants: See advanced.py

========================================================================================================
"""

import os
from pathlib import Path

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
# BOT IDENTITY
# =========================================================================================================

# ----------------------------------------
# Bot Display Name
# ----------------------------------------
# What the bot calls itself in messages
#
BOT_NAME = "Jill"

# ----------------------------------------
# Bot Activity Text
# ----------------------------------------
# The text that appears under the bot's name in Discord (what it's "playing" or "doing")
#
# Examples:
#   "Mixing drinks and changing lives." (default, themed)
#   "Playing music"
#   "Vibing to tunes"
#   "🎵 Music"
#
BOT_ACTIVITY_TEXT = os.getenv('BOT_ACTIVITY_TEXT', 'Mixing drinks and changing lives.')

# =========================================================================================================
# BOT APPEARANCE
# =========================================================================================================

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
# BASIC CONFIGURATION
# =========================================================================================================

# ----------------------------------------
# Command Prefix
# ----------------------------------------
# What symbol users type before commands (prefix mode only)
#
# Examples:
#   '!' = !play, !skip, !queue (default)
#   '$' = $play, $skip, $queue
#   '?' = ?play, ?skip, ?queue
#   '!!' = !!play (multi-character works)
#   '🎵' = 🎵play (emoji works, but damn that's tacky)
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

# Resolve to absolute path if relative
if not Path(MUSIC_FOLDER).is_absolute():
    MUSIC_FOLDER = str(Path(MUSIC_FOLDER).resolve())

# =========================================================================================================
# FEATURE TOGGLES
# =========================================================================================================
#
# Enable or disable specific bot features.
# True = enabled, False = disabled
# These apply to both prefix and slash modes.

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
# Bot Features
# ----------------------------------------
# Control which commands/features are available (applies to both prefix and slash modes)
#
# SHUFFLE_MODE_ENABLED:
#   True = Users can toggle shuffle mode (!shuffle or /shuffle)
#   False = Shuffle feature is disabled
#
# QUEUE_DISPLAY_ENABLED:
#   True = Users can view upcoming tracks (!queue or /queue)
#   False = Queue display is disabled
#
# LIBRARY_DISPLAY_ENABLED:
#   True = Users can browse all tracks (!tracks or /tracks)
#   False = Track browsing is disabled
#
# PLAYLIST_SWITCHING_ENABLED:
#   True = Users can switch between playlists (!playlists or /playlists)
#   False = Playlist switching is disabled (single-playlist mode)
#
SHUFFLE_MODE_ENABLED = None  # Leave as None to use .env or default (True)
SHUFFLE_MODE_ENABLED = _get_config(SHUFFLE_MODE_ENABLED, 'SHUFFLE_MODE_ENABLED', True, _str_to_bool)

QUEUE_DISPLAY_ENABLED = None  # Leave as None to use .env or default (True)
QUEUE_DISPLAY_ENABLED = _get_config(QUEUE_DISPLAY_ENABLED, 'QUEUE_DISPLAY_ENABLED', True, _str_to_bool)

LIBRARY_DISPLAY_ENABLED = None  # Leave as None to use .env or default (True)
LIBRARY_DISPLAY_ENABLED = _get_config(LIBRARY_DISPLAY_ENABLED, 'LIBRARY_DISPLAY_ENABLED', True, _str_to_bool)

PLAYLIST_SWITCHING_ENABLED = None  # Leave as None to use .env or default (True)
PLAYLIST_SWITCHING_ENABLED = _get_config(PLAYLIST_SWITCHING_ENABLED, 'PLAYLIST_SWITCHING_ENABLED', True, _str_to_bool)

# =========================================================================================================
# DISPLAY SETTINGS
# =========================================================================================================
#
# Control how many items to display in lists (applies to both prefix and slash modes)

# ----------------------------------------
# Queue Display Count
# ----------------------------------------
# How many upcoming tracks to show in queue display
# Default: 10 (good balance for both text and embed formats)
#
QUEUE_DISPLAY_COUNT = None  # Leave as None to use .env or default (10)
QUEUE_DISPLAY_COUNT = _get_config(QUEUE_DISPLAY_COUNT, 'QUEUE_DISPLAY_COUNT', 10, int)

# ----------------------------------------
# Library Page Size
# ----------------------------------------
# How many tracks to show per page when browsing library
# Default: 20
#
LIBRARY_PAGE_SIZE = None  # Leave as None to use .env or default (20)
LIBRARY_PAGE_SIZE = _get_config(LIBRARY_PAGE_SIZE, 'LIBRARY_PAGE_SIZE', 20, int)

# ----------------------------------------
# Playlist Page Size
# ----------------------------------------
# How many playlists to show per page
# Default: 20
#
PLAYLIST_PAGE_SIZE = None  # Leave as None to use .env or default (20)
PLAYLIST_PAGE_SIZE = _get_config(PLAYLIST_PAGE_SIZE, 'PLAYLIST_PAGE_SIZE', 20, int)

# =========================================================================================================
# SPAM PROTECTION
# =========================================================================================================
#
# Prevents users from spamming commands (RECOMMENDED: Keep enabled)

# ----------------------------------------
# Spam Protection Enabled
# ----------------------------------------
# Should the bot ignore rapid command spam?
#
# True = Bot ignores rapid command spam (prevents API rate limits)
# False = NO PROTECTION - bot can crash from spam! (not recommended)
#
SPAM_PROTECTION_ENABLED = None  # Leave as None to use .env or default (True)
SPAM_PROTECTION_ENABLED = _get_config(SPAM_PROTECTION_ENABLED, 'SPAM_PROTECTION_ENABLED', True, _str_to_bool)

# ----------------------------------------
# Spam Warning Enabled
# ----------------------------------------
# Should the bot warn users when they're spamming?
#
# True = Bot warns users when they're spamming
# False = Silent (users won't know why commands are ignored)
#
SPAM_WARNING_ENABLED = None  # Leave as None to use .env or default (True)
SPAM_WARNING_ENABLED = _get_config(SPAM_WARNING_ENABLED, 'SPAM_WARNING_ENABLED', True, _str_to_bool)

# =========================================================================================================
# LOGGING SETTINGS
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
# Export Configuration
# =========================================================================================================

__all__ = [
    # Bot Identity
    'BOT_NAME',
    'BOT_ACTIVITY_TEXT',
    # Bot Appearance
    'BOT_STATUS',
    # Basic Configuration
    'COMMAND_PREFIX',
    'MUSIC_FOLDER',
    # Feature Toggles
    'AUTO_PAUSE_ENABLED',
    'AUTO_DISCONNECT_ENABLED',
    'SHUFFLE_MODE_ENABLED',
    'QUEUE_DISPLAY_ENABLED',
    'LIBRARY_DISPLAY_ENABLED',
    'PLAYLIST_SWITCHING_ENABLED',
    # Display Settings
    'QUEUE_DISPLAY_COUNT',
    'LIBRARY_PAGE_SIZE',
    'PLAYLIST_PAGE_SIZE',
    # Spam Protection
    'SPAM_PROTECTION_ENABLED',
    'SPAM_WARNING_ENABLED',
    # Logging
    'LOG_LEVEL',
    'SUPPRESS_LIBRARY_LOGS',
]
