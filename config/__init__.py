"""
Configuration Package - Mode-Aware Configuration Loader

Loads configuration based on JILL_COMMAND_MODE environment variable:
- 'prefix' (Classic Mode): Loads prefix/* config (command prefix, aliases, cleanup timing)
- 'slash' (Modern Mode): Loads slash/* config (embeds, buttons, throttling)

Common configuration (common/*) is always loaded for both modes.

Structure:
  common/ - Shared config (bot token, music folder, permissions, logging)
  prefix/ - Classic mode specific (features, messages, aliases, timing)
  slash/  - Modern mode specific (features, messages, embeds, buttons, timing)
"""

# First, determine command mode
from .mode import COMMAND_MODE

# Always load common configuration
from .common.core import *
from .common.paths import *
from .common.permissions import *
from .common.bot_identity import *
from .common.filename_patterns import *

# Load mode-specific configuration
if COMMAND_MODE == 'prefix':
    # Prefix mode configuration
    from .prefix.features import *
    from .prefix.messages import *
    from .prefix.aliases import *
    from .prefix.timing import *

elif COMMAND_MODE == 'slash':
    # Slash mode configuration
    from .slash.features import *
    from .slash.messages import *
    from .slash.embeds import *
    from .slash.buttons import *
    from .slash.timing import *

    # Create empty aliases dict for compatibility
    COMMAND_ALIASES = {}

    # Import help text from messages
    HELP_TEXT = MESSAGES.get('HELP_DESCRIPTION', 'Music bot commands')

# Export mode for checking
__all__ = ['COMMAND_MODE']
