# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

"""
Spam Protection Configuration - Serial Queue (Layer 3)

This file contains the serial command queue settings used by BOTH prefix and slash modes.

The serial queue (Layer 3) ensures commands are processed one at a time to prevent
race conditions. This is critical for preventing simultaneous commands from corrupting
bot state (e.g., two !skip commands executing at the exact same time).

**BOTH MODES USE THIS:**
- Prefix mode: Uses Layers 1, 2 (in config/prefix/spam_protection.py) + Layer 3 (here)
- Slash mode: Uses only Layer 3 (Discord handles rate limiting via built-in API limits)

For mode-specific spam protection settings:
- Prefix mode settings: config/prefix/spam_protection.py (Layers 1, 2, command cooldowns)
- Slash mode settings: config/slash/timing.py (button cooldowns)
"""

# =========================================================================================================
# LAYER 3: SERIAL QUEUE - Race condition prevention (BOTH MODES)
# =========================================================================================================
# Ensures commands are processed one at a time to prevent race conditions.
# Critical for preventing simultaneous commands from corrupting bot state.
# Used by BOTH prefix and slash modes (essential protection layer).

COMMAND_QUEUE_TIMEOUT = 1.0  # Seconds to wait for queue slot
GUILD_MAX_QUEUE_SIZE = 30  # Maximum number of commands that can be queued
QUEUE_SIZE_WARNING_THRESHOLD = 0.9  # Warn when queue is 90% full
PRIORITY_COMMAND_TIMEOUT_MULTIPLIER = 0.5  # Critical commands wait half as long

# =========================================================================================================
# EXPORTS
# =========================================================================================================

__all__ = [
    'COMMAND_QUEUE_TIMEOUT',
    'GUILD_MAX_QUEUE_SIZE',
    'QUEUE_SIZE_WARNING_THRESHOLD',
    'PRIORITY_COMMAND_TIMEOUT_MULTIPLIER',
]
