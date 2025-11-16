# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

"""
========================================================================================================
JILL MUSIC BOT - ADVANCED SETTINGS
========================================================================================================

This file contains internal constants and technical settings.
These settings work in BOTH prefix mode (!play) and slash mode (/play).

⚠️ WARNING: Only change these if you know what you're doing or were told to by support.

Most users should never need to edit this file. These are low-level constants that affect
how the bot operates internally.

FOR OTHER SETTINGS:
  - Common settings: See basic_settings.py
  - Audio/voice: See audio_settings.py

========================================================================================================
"""

import os

# =========================================================================================================
# BOT TOKEN (DO NOT EDIT)
# =========================================================================================================
#
# Your Discord bot token - ALWAYS set this in .env file for security
# NEVER hardcode your token in this file!
#
BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN', '').strip()

# =========================================================================================================
# PERSISTENCE FILE PATHS
# =========================================================================================================
#
# File paths for storing bot state between restarts
# Don't change these unless you have a specific reason

# Storage files
CHANNEL_STORAGE_FILE = 'last_channels.json'  # Remembers which voice channels bot was in
PLAYLIST_STORAGE_FILE = 'last_playlists.json'  # Remembers active playlists
MESSAGE_PERSISTENCE_FILE = 'last_message_ids.json'  # Remembers control panel messages (slash mode only)

# =========================================================================================================
# INTERNAL CONSTANTS
# =========================================================================================================
#
# Low-level technical constants for bot operation
# DON'T CHANGE THESE unless specifically instructed by documentation/support

# ----------------------------------------
# Playback History
# ----------------------------------------
MAX_HISTORY = 100  # Maximum number of recently played tracks to remember

# ----------------------------------------
# Watchdog Monitoring
# ----------------------------------------
# The watchdog monitors playback health and detects stuck/hung playback
WATCHDOG_CHECK_INTERVAL = 30.0  # Seconds between playback health checks
WATCHDOG_HANG_THRESHOLD = 90.0  # Seconds before declaring playback "stuck"
WATCHDOG_INTERVAL = 600  # Check for stuck playback every 10 minutes
WATCHDOG_TIMEOUT = 660  # Consider playback stuck after 11 minutes

# ----------------------------------------
# Voice Channel Auto-Pause/Disconnect Timing
# ----------------------------------------
# When the bot is alone in a voice channel
# Note: AUTO_PAUSE_WHEN_ALONE is created in __init__.py as an alias to AUTO_PAUSE_ENABLED
PAUSE_ON_EMPTY_DELAY = 30.0  # Seconds to wait before pausing when alone
ALONE_PAUSE_DELAY = 10  # Seconds to wait before pausing music when alone
ALONE_DISCONNECT_DELAY = 600  # Seconds to wait before leaving channel when alone (10 minutes)
ALONE_WATCHDOG_INTERVAL = 10  # Check if alone in voice channel every 10 seconds

# =========================================================================================================
# Export Configuration
# =========================================================================================================

__all__ = [
    # Bot Token
    'BOT_TOKEN',
    # Persistence Files
    'CHANNEL_STORAGE_FILE',
    'PLAYLIST_STORAGE_FILE',
    'MESSAGE_PERSISTENCE_FILE',
    # Internal Constants
    'MAX_HISTORY',
    'WATCHDOG_CHECK_INTERVAL',
    'WATCHDOG_HANG_THRESHOLD',
    'WATCHDOG_INTERVAL',
    'WATCHDOG_TIMEOUT',
    'PAUSE_ON_EMPTY_DELAY',
    'ALONE_PAUSE_DELAY',
    'ALONE_DISCONNECT_DELAY',
    'ALONE_WATCHDOG_INTERVAL',
]
