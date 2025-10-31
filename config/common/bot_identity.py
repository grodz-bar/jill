# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

"""
Bot Identity Configuration - Shared Between All Modes

Bot appearance, theming, and identity settings.
"""

import os

# Bot display name
BOT_NAME = "Jill"

# Bot presence/activity text (what the bot shows it's "playing" or "doing")
# This is the text that appears under the bot's name in Discord
# Note: This is different from BOT_STATUS (online/dnd/idle) which is in core.py
#
# Examples:
#   "mixing drinks at VA-11 HALL-A" (default, themed)
#   "Playing music"
#   "Vibing to tunes"
#   "🎵 Music"
#
BOT_ACTIVITY_TEXT = os.getenv('BOT_ACTIVITY_TEXT', 'mixing drinks at VA-11 HALL-A')

# VA-11 HALL-A themed drink emojis (used in messages)
DRINK_EMOJIS = ['🍸', '🍹', '🍺', '🍻', '🥃', '🍷', '🍾', '🧉']

# Bot color scheme (for embeds in slash mode)
BOT_COLORS = {
    'primary': 0xE91E63,    # VA-11 HALL-A pink
    'success': 0x00E676,    # Green
    'warning': 0xFFD600,    # Yellow
    'error': 0xFF5252,      # Red
    'info': 0x2196F3,       # Blue
}

__all__ = [
    'BOT_NAME',
    'BOT_ACTIVITY_TEXT',
    'DRINK_EMOJIS',
    'BOT_COLORS',
]
