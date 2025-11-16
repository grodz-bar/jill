# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

r"""
========================================================================================================
JILL MUSIC BOT - SLASH MODE CONFIGURATION
========================================================================================================

This file contains settings ONLY for slash mode (/play commands).
Prefix mode (!play commands) does NOT use this file.

SHARED SETTINGS:
  Most settings are in config/common/basic_settings.py, audio_settings.py, and advanced.py
  Go there first if you can't find what you're looking for!

SLASH-SPECIFIC SETTINGS:
  This file only contains features specific to slash commands:
  - Which commands are enabled (/shuffle, /queue, etc.)
  - Control panel settings (buttons, timeouts)
  - Embed appearance
  - Response behavior (ephemeral messages)

HOW TO CUSTOMIZE:
  1. Find the setting you want to change below
  2. Change 'None' to your desired value (True/False or a number)
  3. Save the file and restart the bot

  Example:
    EPHEMERAL_RESPONSES = None    ← Default (uses .env or True)
    EPHEMERAL_RESPONSES = False   ← Make responses visible to everyone

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
# 🎵 SLASH MODE NOTES
# =========================================================================================================
#
# LOOKING FOR SETTINGS?
#
# Most settings have been moved to config/common/ (basic_settings.py, audio_settings.py, advanced.py) because they apply to BOTH modes:
#   - Feature toggles (SHUFFLE_MODE_ENABLED, QUEUE_DISPLAY_ENABLED, etc.) - in basic_settings.py
#   - Display settings (QUEUE_DISPLAY_COUNT, LIBRARY_PAGE_SIZE, etc.) - in basic_settings.py
#   - Audio/voice settings, auto-pause - in audio_settings.py
#   - Logging, watchdog intervals - in advanced.py
#
# This file contains SLASH-MODE SPECIFIC settings:
#   - Ephemeral responses
#   - Control panel settings (timeout, update throttle)
#   - Startup delays
#
# If you're looking for a setting that used to be here, check config/common/basic_settings.py, audio_settings.py, or advanced.py!

# =========================================================================================================
# 💬 RESPONSE BEHAVIOR
# =========================================================================================================

# ----------------------------------------
# Ephemeral Responses
# ----------------------------------------
# Should slash command responses be visible only to you?
#
# True = Responses only visible to the person who used the command (recommended)
#        Example: You use /queue, only you see the track list
#
# False = Responses visible to everyone in the channel
#         Example: You use /queue, everyone sees the track list
#
# Note: Control panel (Now Playing message) is always visible to everyone
#
EPHEMERAL_RESPONSES = None
EPHEMERAL_RESPONSES = _get_config(EPHEMERAL_RESPONSES, 'EPHEMERAL_RESPONSES', True, _str_to_bool)

# =========================================================================================================
# 🎛️ CONTROL PANEL SETTINGS
# =========================================================================================================
#
# The control panel is the interactive "Now Playing" message with buttons
# (Play/Pause, Skip, Shuffle, etc.)

# ----------------------------------------
# Button Timeout
# ----------------------------------------
# How long should control panel buttons stay active?
#
# Examples:
#   300 = 5 minutes (default)
#   600 = 10 minutes
#   900 = 15 minutes
#   0 = Never timeout (buttons always work, but might cause issues)
#
# After timeout, buttons turn gray and stop working. A new /play creates fresh buttons.
#
CONTROL_PANEL_TIMEOUT = None
CONTROL_PANEL_TIMEOUT = _get_config(CONTROL_PANEL_TIMEOUT, 'CONTROL_PANEL_TIMEOUT', 300, int)

# ----------------------------------------
# Update Throttle Time
# ----------------------------------------
# Minimum seconds between control panel updates (prevents Discord rate limits)
#
# Examples:
#   2.0 = Wait 2 seconds between updates (default, recommended)
#   1.0 = Wait 1 second (faster updates, higher API usage)
#   5.0 = Wait 5 seconds (slower updates, lower API usage)
#
# Lower = More responsive but higher Discord API usage
# Higher = Less responsive but lower Discord API usage
#
UPDATE_THROTTLE_TIME = None
UPDATE_THROTTLE_TIME = _get_config(UPDATE_THROTTLE_TIME, 'UPDATE_THROTTLE_TIME', 2.0, float)

# =========================================================================================================
# 🚀 STARTUP SETTINGS
# =========================================================================================================

# ----------------------------------------
# Startup Message Delay
# ----------------------------------------
# How long to wait after bot starts before creating control panel messages
#
# Examples:
#   5.0 = Wait 5 seconds (default, gives Discord time to stabilize)
#   0.0 = No delay (might cause issues on slow connections)
#   10.0 = Wait 10 seconds (safer for unstable connections)
#
# This prevents errors when the bot restarts and tries to recreate messages too quickly.
#
STARTUP_MESSAGE_DELAY = None
STARTUP_MESSAGE_DELAY = _get_config(STARTUP_MESSAGE_DELAY, 'STARTUP_MESSAGE_DELAY', 5.0, float)

# =========================================================================================================
# 📝 NOTES FOR CUSTOMIZATION
# =========================================================================================================
#
# Looking for more settings? Check these files:
#
# config/common/basic_settings.py - Bot identity, feature toggles, spam protection, logging
# config/common/audio_settings.py - FFmpeg, voice health, auto-pause
# config/common/advanced.py - Watchdog intervals, persistence paths
# config/slash/messages.py - Customize slash command response text
# config/slash/embeds.py - Customize embed colors and appearance
# config/slash/buttons.py - Customize button labels and emojis
# config/slash/timing.py - Advanced: Timing values and cooldowns
#
# =========================================================================================================

# =========================================================================================================
# Export Configuration
# =========================================================================================================

__all__ = [
    'EPHEMERAL_RESPONSES',
    'CONTROL_PANEL_TIMEOUT',
    'UPDATE_THROTTLE_TIME',
    'STARTUP_MESSAGE_DELAY',
]
