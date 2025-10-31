"""
Permission Configuration - Shared Between All Modes

VA-11 HALL-A themed permission system.
Default: All commands available to everyone (PERMISSION_MODE='none')
"""

import os

# Permission mode: 'none' (no restrictions) or 'role' (role-based)
PERMISSION_MODE = os.getenv('PERMISSION_MODE', 'none').lower()

# VA-11 HALL-A themed role tiers
BARTENDER_ROLES = os.getenv('BARTENDER_ROLES', 'Bartender,DJ').split(',')
BARTENDER_ROLES = [r.strip() for r in BARTENDER_ROLES if r.strip()]

VIP_ROLES = os.getenv('VIP_ROLES', 'VIP,Regular').split(',')
VIP_ROLES = [r.strip() for r in VIP_ROLES if r.strip()]

BOSS_ROLES = os.getenv('BOSS_ROLES', 'Boss,Admin,Administrator').split(',')
BOSS_ROLES = [r.strip() for r in BOSS_ROLES if r.strip()]

# Command permissions
# Values: 'everyone', 'vip', 'bartender', 'boss'
COMMAND_PERMISSIONS = {
    'play': 'everyone',
    'pause': 'everyone',
    'skip': 'everyone',
    'stop': 'everyone',
    'previous': 'everyone',
    'shuffle': 'everyone',
    'queue': 'everyone',
    'tracks': 'everyone',
    'playlist': 'everyone',
    'playlists': 'everyone',
    'help': 'everyone',
    'aliases': 'everyone',
}

# Server owner bypass
OWNER_BYPASS = True

# Permission denied messages
PERMISSION_MESSAGES = {
    'no_permission': "❌ You need the **{role}** role to use this command.",
    'not_in_voice': "❌ You need to be in a voice channel.",
    'wrong_channel': "❌ You need to be in the same voice channel as the bot.",
}

__all__ = [
    'PERMISSION_MODE',
    'BARTENDER_ROLES',
    'VIP_ROLES',
    'BOSS_ROLES',
    'COMMAND_PERMISSIONS',
    'OWNER_BYPASS',
    'PERMISSION_MESSAGES',
]
