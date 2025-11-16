# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

r"""
========================================================================================================
JILL MUSIC BOT - PREFIX MODE CONFIGURATION
========================================================================================================

This file contains settings ONLY for prefix mode (!play commands).
Slash mode (/play commands) does NOT use this file.

SHARED SETTINGS:
  Most settings are in config/common/basic_settings.py, audio_settings.py, and advanced.py
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
#  PREFIX MODE SETTINGS
# =========================================================================================================
#
# LOOKING FOR SETTINGS?
#
# Most settings have been moved to config/common/ (basic_settings.py, audio_settings.py, advanced.py) because they apply to BOTH modes:
#   - Feature toggles (SHUFFLE_MODE_ENABLED, QUEUE_DISPLAY_ENABLED, etc.) - in basic_settings.py
#   - Display settings (QUEUE_DISPLAY_COUNT, LIBRARY_PAGE_SIZE, etc.) - in basic_settings.py
#   - Audio/voice settings - in audio_settings.py
#   - Logging, watchdog intervals - in advanced.py
#
# Other prefix-specific settings are in:
#   - config/prefix/aliases.py - Command shortcuts
#   - config/prefix/messages.py - Message templates
#   - config/prefix/cleanup.py - Cleanup timing and toggles
#   - config/prefix/spam_protection.py - Spam protection layers 1-2

# ----------------------------------------
# Smart Message Management (Prefix Only)
# ----------------------------------------
# Edit existing "now playing" messages instead of sending new ones
#
# True = Edits existing messages when not buried (cleaner, recommended)
# False = Always sends new message (more chat clutter)
#
# NOTE: Slash mode always edits control panels, so this setting doesn't apply there.
#
SMART_MESSAGE_MANAGEMENT = None  # Leave as None to use .env or default (True)
SMART_MESSAGE_MANAGEMENT = _get_config(SMART_MESSAGE_MANAGEMENT, 'SMART_MESSAGE_MANAGEMENT', True, _str_to_bool)

# =========================================================================================================
#  NOTES FOR CUSTOMIZATION
# =========================================================================================================
#
# Looking for more settings? Check these files:
#
# config/common/basic_settings.py - Bot identity, command prefix, feature toggles, logging
# config/common/audio_settings.py - FFmpeg, voice health monitoring
# config/common/advanced.py - Watchdog intervals, persistence paths
# config/prefix/messages.py - Customize message text and wording
# config/prefix/aliases.py - Add custom command shortcuts (!p for !play, etc.)
# config/prefix/cleanup.py - Message cleanup timing and TTLs
#
# =========================================================================================================

# =========================================================================================================
# Export Configuration
# =========================================================================================================

__all__ = [
    'SMART_MESSAGE_MANAGEMENT',
]
