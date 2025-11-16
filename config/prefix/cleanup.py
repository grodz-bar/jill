# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

"""
Cleanup Configuration - Automatic Message Cleanup System (PREFIX MODE ONLY)

The cleanup system automatically removes old bot messages to keep Discord channels clean.

NOTE: This is PREFIX MODE ONLY. Slash mode doesn't need cleanup because:
- Slash responses are ephemeral (auto-deleted by Discord)
- Control panels are edited in place (no message spam)

Features:
- Auto-deletes user commands (!play, !skip, etc.) and bot responses
- Periodic channel history scanning
- Smart "now playing" message management
- TTL-based message expiration
"""

import os

# Internal helper functions
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
# CLEANUP FEATURE TOGGLES (PREFIX MODE ONLY)
# =========================================================================================================
# Control whether cleanup runs at all. Slash mode doesn't use these.

# ----------------------------------------
# Auto Cleanup Enabled
# ----------------------------------------
# Should the bot automatically clean up old messages in chat?
#
# True = Bot runs background cleanup (keeps chat tidy)
# False = Messages stay forever (chat gets cluttered)
#
AUTO_CLEANUP_ENABLED = None  # Leave as None to use .env or default (True)
AUTO_CLEANUP_ENABLED = _get_config(AUTO_CLEANUP_ENABLED, 'AUTO_CLEANUP_ENABLED', True, _str_to_bool)

# ----------------------------------------
# Delete Other Bots
# ----------------------------------------
# Should cleanup also remove other bots' messages?
#
# True = Also delete other bots' messages during cleanup
# False = Only delete Jill's messages and user commands (safer default)
#
DELETE_OTHER_BOTS = None  # Leave as None to use .env or default (False)
DELETE_OTHER_BOTS = _get_config(DELETE_OTHER_BOTS, 'DELETE_OTHER_BOTS', False, _str_to_bool)

# ----------------------------------------
# TTL Cleanup Enabled
# ----------------------------------------
# Should messages expire after set time (like TTL in databases)?
#
# True = Messages expire after set time (configured below)
# False = Messages never auto-delete based on age
#
TTL_CLEANUP_ENABLED = None  # Leave as None to use .env or default (True)
TTL_CLEANUP_ENABLED = _get_config(TTL_CLEANUP_ENABLED, 'TTL_CLEANUP_ENABLED', True, _str_to_bool)

# ----------------------------------------
# Batch Delete Enabled
# ----------------------------------------
# Should we delete multiple messages at once (faster)?
#
# True = Delete multiple messages at once (faster, recommended)
# False = Delete one at a time (slower)
#
BATCH_DELETE_ENABLED = None  # Leave as None to use .env or default (True)
BATCH_DELETE_ENABLED = _get_config(BATCH_DELETE_ENABLED, 'BATCH_DELETE_ENABLED', True, _str_to_bool)

# =========================================================================================================
# TTL CLEANUP - Auto-delete messages after time-to-live expires
# =========================================================================================================
# The bot tracks messages and deletes them after a set lifetime.

USER_COMMAND_TTL = 8.0  # How long to keep user commands visible (!play, !skip, etc.)
TTL_CHECK_INTERVAL = 1.0  # How often to check for expired messages (seconds)

# =========================================================================================================
# HISTORY CLEANUP - Periodic channel scanning
# =========================================================================================================
# Background worker that periodically scans channel history to remove old bot messages.

HISTORY_CLEANUP_INTERVAL = 180  # How often to scan channel history (seconds - 3 minutes)
CLEANUP_HISTORY_LIMIT = 50  # How many recent messages to check during scan
USER_COMMAND_MAX_LENGTH = 2000  # Maximum length for user commands (Discord's limit)

# =========================================================================================================
# SPAM CLEANUP - Remove spam warnings and related messages
# =========================================================================================================
# After spam is detected, the bot displays warnings and then cleans them up.

SPAM_CLEANUP_DELAY = 15  # How long to keep spam warning messages visible (seconds)
CLEANUP_SAFE_AGE_THRESHOLD = 120  # Only delete messages older than this (seconds - 2 minutes)

# =========================================================================================================
# BATCH DELETE - Bulk message deletion settings
# =========================================================================================================
# When deleting multiple messages at once (like during spam cleanup).
# Discord allows up to 100 messages per batch, with rate limiting.

CLEANUP_BATCH_SIZE = 95  # Messages per batch (near Discord's 100 limit for efficiency)
CLEANUP_BATCH_DELAY = 1.2  # Delay between batches (seconds - respects Discord's rate limit)

# =========================================================================================================
# NOW PLAYING MANAGEMENT - Smart message handling
# =========================================================================================================
# The bot manages "now playing" messages intelligently.
# If the message gets buried by chat, send a new one instead of editing the old one.

MESSAGE_BURIAL_CHECK_LIMIT = 40  # How many messages to check when detecting burial
MESSAGE_BURIAL_THRESHOLD = 4  # If 4+ messages after "now playing", send new message

# =========================================================================================================
# MESSAGE LIFETIMES - Time-to-live for different message types
# =========================================================================================================
# How long different types of bot messages stay visible before auto-deletion.

MESSAGE_TTL = {
    'now_serving': 600,    # 10 minutes - current track info
    'pause': 10,           # Quick confirmation messages
    'resume': 10,
    'stop': 20,
    'queue': 30,           # 30 seconds - queue list
    'tracks': 90,          # 90 seconds - track list (longer to read)
    'playlists': 90,       # 90 seconds - playlist list
    'help': 120,           # 2 minutes - help text
    'shuffle': 30,         # 30 seconds - shuffle toggle
    'error_quick': 10,     # Quick errors
    'error': 15,           # Standard errors
}

# =========================================================================================================
# EXPORTS
# =========================================================================================================

__all__ = [
    # Feature Toggles
    'AUTO_CLEANUP_ENABLED',
    'DELETE_OTHER_BOTS',
    'TTL_CLEANUP_ENABLED',
    'BATCH_DELETE_ENABLED',
    # TTL Cleanup
    'USER_COMMAND_TTL',
    'TTL_CHECK_INTERVAL',
    # History Cleanup
    'HISTORY_CLEANUP_INTERVAL',
    'CLEANUP_HISTORY_LIMIT',
    'USER_COMMAND_MAX_LENGTH',
    # Spam Cleanup
    'SPAM_CLEANUP_DELAY',
    'CLEANUP_SAFE_AGE_THRESHOLD',
    # Batch Delete
    'CLEANUP_BATCH_SIZE',
    'CLEANUP_BATCH_DELAY',
    # Now Playing Management
    'MESSAGE_BURIAL_CHECK_LIMIT',
    'MESSAGE_BURIAL_THRESHOLD',
    # Message Lifetimes
    'MESSAGE_TTL',
]
