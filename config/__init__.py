"""
Configuration Package - Mode-Aware Configuration Loader

Loads configuration based on JILL_COMMAND_MODE environment variable:
- 'prefix' (Classic Mode): Loads prefix/* config (features, messages, aliases, spam protection, cleanup)
- 'slash' (Modern Mode): Loads slash/* config (features, messages, embeds, buttons, timing)

Common configuration (common/*) is always loaded for both modes.

Structure:
  common/ - Shared config (basic settings, audio settings, advanced settings, spam protection, permissions, etc.)
  prefix/ - Classic mode specific (features, messages, aliases, spam protection, cleanup)
  slash/  - Modern mode specific (features, messages, embeds, buttons, timing)
"""

import os

# =========================================================================================================
# Determine Command Mode
# =========================================================================================================
# Command mode: 'prefix' (classic) or 'slash' (modern)
COMMAND_MODE = os.getenv('JILL_COMMAND_MODE', 'prefix').lower()

# Validate
if COMMAND_MODE not in ['prefix', 'slash']:
    print(f"Warning: Invalid JILL_COMMAND_MODE '{COMMAND_MODE}'. Using 'prefix'.")
    COMMAND_MODE = 'prefix'

# =========================================================================================================
# Load Common Configuration (Shared by Both Modes)
# =========================================================================================================
from .common.basic_settings import *
from .common.audio_settings import *
from .common.advanced import *
from .common.spam_protection import *
from .common.permissions import *
from .common.filename_patterns import *
from .common.messages import COMMON_MESSAGES, DRINK_EMOJIS

# Create compatibility alias (AUTO_PAUSE_WHEN_ALONE -> AUTO_PAUSE_ENABLED)
AUTO_PAUSE_WHEN_ALONE = AUTO_PAUSE_ENABLED

# =========================================================================================================
# Load Mode-Specific Configuration
# =========================================================================================================
if COMMAND_MODE == 'prefix':
    # Prefix mode configuration
    from .prefix.features import *
    from .prefix.messages import MESSAGES as MODE_MESSAGES, HELP_TEXT
    from .prefix.aliases import *
    from .prefix.spam_protection import *
    from .prefix.cleanup import *

    # Merge common and mode-specific messages
    # Mode-specific messages can override common ones if needed
    MESSAGES = {**COMMON_MESSAGES, **MODE_MESSAGES}

elif COMMAND_MODE == 'slash':
    # Slash mode configuration
    from .slash.features import *
    from .slash.messages import (
        MESSAGES as MODE_MESSAGES,
        BUTTON_LABELS,
        COMMAND_DESCRIPTIONS,
        FALLBACK_PLAYLIST_NAME,
        BOT_COLORS,
    )
    from .slash.embeds import *
    from .slash.buttons import *
    from .slash.timing import *

    # Merge common and mode-specific messages
    # Mode-specific messages can override common ones if needed
    MESSAGES = {**COMMON_MESSAGES, **MODE_MESSAGES}

    # Create empty aliases dict for compatibility
    COMMAND_ALIASES = {}

    # Import help text from messages
    HELP_TEXT = MESSAGES.get('HELP_DESCRIPTION', 'Music bot commands')

# Export mode for checking
__all__ = ['COMMAND_MODE']
