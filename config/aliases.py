# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

"""
Command Aliases

Users can customize alternative command names here.

QUICK GUIDE:
- Add aliases to the COMMAND_ALIASES dictionary below
- Each alias can only be used ONCE across all commands
- Aliases work with all parameter combinations (e.g., !play and !play 5)
- Aliases are case-insensitive (!Play = !play = !PLAY)
- Restart bot after changes: sudo systemctl restart jill.service (Linux)
- Avoid reserved names: 'help', disnake commands, anything starting with '_'

WARNING:
- DO NOT change the dictionary keys (queue, play, pause, skip, stop, etc.) as these are the base command names used internally. Only modify the alias lists inside the brackets [].

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

COMMAND_ALIASES = {
    'queue': ['q', 'playing', 'name', 'song'],
    'play': ['resume', 'unpause', 'start', 'join', 'skipto', 'jumpto'],
    'pause': ['break'],
    'skip': ['next', 'ns'],
    'stop': ['leave', 'disconnect', 'dc', 'bye'],
    'previous': ['prev', 'back', 'ps'],
    'shuffle': ['mess', 'scramble', 'fix', 'organize'],
    'tracks': ['playlist', 'album', 'library', 'songs', 'list', 'allsongs', 'fq', 'all', 'fullqueue', 'switch', 'useplaylist'],
    'playlists': ['libraries', 'albums', 'lists', 'collections'],
    'help': ['commands', 'jill'],
}

def validate_command_aliases() -> None:
    """
    Validate that no alias is used for multiple commands.
    
    Raises:
        ValueError: If duplicate aliases are found
        
    Called on bot startup to catch configuration errors early.
    """
    # Track which command each alias belongs to (case-insensitive)
    alias_to_command = {}
    duplicates = []
    
    for command, aliases in COMMAND_ALIASES.items():
        for alias in aliases:
            alias_lower = alias.lower()
            if alias_lower in alias_to_command:
                duplicates.append(
                    f"Alias '{alias}' is used by both '{alias_to_command[alias_lower]}' and '{command}'"
                )
            else:
                alias_to_command[alias_lower] = command
    
    if duplicates:
        error_msg = "COMMAND ALIAS CONFIGURATION ERROR:\n" + "\n".join(duplicates)
        logger.critical(error_msg)
        raise ValueError(error_msg)
    
    logger.info(f"Command aliases validated: {len(alias_to_command)} total aliases configured")

# Validate aliases on import (catches errors before bot starts)
validate_command_aliases()

