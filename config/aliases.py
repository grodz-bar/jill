"""
Command Aliases - Alternative command names

This file contains all command aliases and their validation.
Users can customize alternative command names here.

QUICK GUIDE:
- Add aliases to the COMMAND_ALIASES dictionary below
- Each alias can only be used ONCE across all commands
- Aliases work with all parameter combinations (e.g., !play and !play 5)
- Aliases are case-insensitive (!Play = !play = !PLAY)
- Restart bot after changes: sudo systemctl restart jill.service
- Avoid reserved names: 'help', disnake commands, anything starting with '_'

EXAMPLES:
- To add 'forward' to skip command: 'skip': ['next', 'ns', 'forward']
- To remove 'dc' from stop command: 'stop': ['leave', 'disconnect', 'bye']
"""

import logging

# Set up logging
logger = logging.getLogger(__name__)

# =========================================================================================================
# COMMAND ALIASES (Customize here!)
# =========================================================================================================
# Key = primary command, Value = list of aliases
# Each alias can only be used ONCE across all commands
# Aliases work with all parameter combinations (e.g., !play and !play 5)

COMMAND_ALIASES = {
    'queue': ['q', 'playing', 'name', 'song'],
    'library': ['fullqueue', 'songs', 'list', 'allsongs', 'playlist', 'fq', 'all'],
    'play': ['resume', 'unpause', 'start', 'join', 'skipto', 'jumpto'],
    'pause': ['break'],
    'skip': ['next', 'ns'],
    'stop': ['leave', 'disconnect', 'dc', 'bye'],
    'previous': ['prev', 'back', 'ps'],
    'shuffle': ['mess', 'scramble'],
    'unshuffle': ['fix', 'organize'],
    'help': ['commands', 'jill'],
}

def validate_command_aliases() -> None:
    """
    Validate that no alias is used for multiple commands.
    
    Raises:
        ValueError: If duplicate aliases are found
        
    Called on bot startup to catch configuration errors early.
    """
    # Track which command each alias belongs to
    alias_to_command = {}
    duplicates = []
    
    for command, aliases in COMMAND_ALIASES.items():
        for alias in aliases:
            if alias in alias_to_command:
                duplicates.append(
                    f"Alias '{alias}' is used by both '{alias_to_command[alias]}' and '{command}'"
                )
            else:
                alias_to_command[alias] = command
    
    if duplicates:
        error_msg = "COMMAND ALIAS CONFIGURATION ERROR:\n" + "\n".join(duplicates)
        logger.critical(error_msg)
        raise ValueError(error_msg)
    
    logger.info(f"Command aliases validated: {len(alias_to_command)} total aliases configured")

# Validate aliases on import (catches errors before bot starts)
validate_command_aliases()

