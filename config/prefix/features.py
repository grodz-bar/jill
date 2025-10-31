# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

r"""
========================================================================================================
JILL MUSIC BOT - PREFIX MODE CONFIGURATION
========================================================================================================

This file contains settings ONLY for prefix mode (!play commands).
Slash mode (/play commands) does NOT use this file.

SHARED SETTINGS:
  Most settings (command prefix, auto-pause, cleanup, etc.) are in config/common/core.py
  Go there first if you can't find what you're looking for!

PREFIX-SPECIFIC SETTINGS:
  This file only contains features specific to text-based commands:
  - Which commands are enabled (!shuffle, !queue, !tracks, etc.)
  - How many items to show in lists
  - Prefix-mode only features

HOW TO CUSTOMIZE:
  1. Find the setting you want to change below
  2. Change 'None' to your desired value (True/False or a number)
  3. Save the file and restart the bot

  Example:
    SHUFFLE_MODE_ENABLED = None    ← Default (uses .env or True)
    SHUFFLE_MODE_ENABLED = False   ← Disable !shuffle command

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

# Internal helper functions (scroll down to skip to settings)
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
# 🎵 PLAYBACK FEATURES
# =========================================================================================================
#
# Control which commands are available to users.
# Disabled features won't show up in the !help menu.

# ----------------------------------------
# Shuffle Mode
# ----------------------------------------
# Enable the !shuffle command (toggles random track order)
#
# True = Users can type !shuffle to enable/disable shuffle
# False = !shuffle command is disabled (responds with "feature disabled")
#
SHUFFLE_MODE_ENABLED = None
SHUFFLE_MODE_ENABLED = _get_config(SHUFFLE_MODE_ENABLED, 'SHUFFLE_MODE_ENABLED', True, _str_to_bool)

# ----------------------------------------
# Queue Display
# ----------------------------------------
# Enable the !queue command (shows upcoming tracks)
#
# True = Users can see what's coming up next
# False = !queue command is disabled
#
QUEUE_DISPLAY_ENABLED = None
QUEUE_DISPLAY_ENABLED = _get_config(QUEUE_DISPLAY_ENABLED, 'QUEUE_DISPLAY_ENABLED', True, _str_to_bool)

# ----------------------------------------
# Queue Display Count
# ----------------------------------------
# How many upcoming tracks to show in !queue
#
# Examples:
#   3 = Show next 3 tracks (default, keeps message short)
#   5 = Show next 5 tracks
#   10 = Show next 10 tracks (longer message)
#
QUEUE_DISPLAY_COUNT = None
QUEUE_DISPLAY_COUNT = _get_config(QUEUE_DISPLAY_COUNT, 'QUEUE_DISPLAY_COUNT', 3, int)

# ----------------------------------------
# Library Display
# ----------------------------------------
# Enable the !tracks command (lists all songs in current playlist)
#
# True = Users can browse the entire music library
# False = !tracks command is disabled
#
LIBRARY_DISPLAY_ENABLED = None
LIBRARY_DISPLAY_ENABLED = _get_config(LIBRARY_DISPLAY_ENABLED, 'LIBRARY_DISPLAY_ENABLED', True, _str_to_bool)

# ----------------------------------------
# Library Page Size
# ----------------------------------------
# How many tracks to show per page in !tracks
#
# Examples:
#   20 = Show 20 tracks per page (default)
#   50 = Show 50 tracks per page (good for large libraries)
#   10 = Show 10 tracks per page (better for mobile)
#
LIBRARY_PAGE_SIZE = None
LIBRARY_PAGE_SIZE = _get_config(LIBRARY_PAGE_SIZE, 'LIBRARY_PAGE_SIZE', 20, int)

# ----------------------------------------
# Playlist Switching
# ----------------------------------------
# Enable the !playlists and !tracks [name] commands (multi-playlist mode)
#
# True = Users can switch between playlists
# False = Commands disabled (single-playlist mode)
#
# NOTE: Only works if you have music organized in subfolders
# Example folder structure:
#   music/
#     ├── Rock/
#     ├── Jazz/
#     └── Electronic/
#
PLAYLIST_SWITCHING_ENABLED = None
PLAYLIST_SWITCHING_ENABLED = _get_config(PLAYLIST_SWITCHING_ENABLED, 'PLAYLIST_SWITCHING_ENABLED', True, _str_to_bool)

# ----------------------------------------
# Playlist Page Size
# ----------------------------------------
# How many playlists to show per page in !playlists
#
# Examples:
#   20 = Show 20 playlists per page (default)
#   10 = Show 10 playlists per page
#   50 = Show 50 playlists per page (if you have many playlists)
#
PLAYLIST_PAGE_SIZE = None
PLAYLIST_PAGE_SIZE = _get_config(PLAYLIST_PAGE_SIZE, 'PLAYLIST_PAGE_SIZE', 20, int)

# =========================================================================================================
# 🔧 ADVANCED FEATURES
# =========================================================================================================
#
# Technical features that most users won't need to change.

# ----------------------------------------
# Voice Reconnect
# ----------------------------------------
# Auto-reconnect to voice channel if connection drops
#
# True = Bot automatically rejoins if disconnected (recommended)
# False = Requires manual !play to reconnect
#
VOICE_RECONNECT_ENABLED = None
VOICE_RECONNECT_ENABLED = _get_config(VOICE_RECONNECT_ENABLED, 'VOICE_RECONNECT_ENABLED', True, _str_to_bool)

# =========================================================================================================
# 📝 NOTES FOR CUSTOMIZATION
# =========================================================================================================
#
# Looking for more settings? Check these files:
#
# config/common/core.py - Shared settings (prefix, status, cleanup, spam protection)
# config/prefix/messages.py - Customize message text and wording
# config/prefix/aliases.py - Add custom command shortcuts (!p for !play, etc.)
# config/prefix/timing.py - Advanced: Timing values, cooldowns, TTLs
#
# =========================================================================================================

# =========================================================================================================
# Export Configuration
# =========================================================================================================

__all__ = [
    'SHUFFLE_MODE_ENABLED',
    'QUEUE_DISPLAY_ENABLED',
    'QUEUE_DISPLAY_COUNT',
    'LIBRARY_DISPLAY_ENABLED',
    'LIBRARY_PAGE_SIZE',
    'PLAYLIST_SWITCHING_ENABLED',
    'PLAYLIST_PAGE_SIZE',
    'VOICE_RECONNECT_ENABLED',
]
