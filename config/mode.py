"""
Command Mode Configuration

Determines whether the bot uses prefix commands (!play) or slash commands (/play).
"""

import os

# Command mode: 'prefix' (classic) or 'slash' (modern)
COMMAND_MODE = os.getenv('JILL_COMMAND_MODE', 'prefix').lower()

# Validate
if COMMAND_MODE not in ['prefix', 'slash']:
    print(f"Warning: Invalid JILL_COMMAND_MODE '{COMMAND_MODE}'. Using 'prefix'.")
    COMMAND_MODE = 'prefix'

__all__ = ['COMMAND_MODE']
