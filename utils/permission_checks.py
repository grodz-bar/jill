"""
Permission Checking Utilities

Provides permission checking for both prefix and slash commands.
"""

import logging
from typing import Union, List
from disnake.ext import commands
import disnake

from config import (
    PERMISSION_MODE,
    BARTENDER_ROLES,
    VIP_ROLES,
    BOSS_ROLES,
    COMMAND_PERMISSIONS,
    OWNER_BYPASS,
    PERMISSION_MESSAGES,
)

logger = logging.getLogger(__name__)


def has_role(member: disnake.Member, role_names: List[str]) -> bool:
    """Check if member has any of the specified roles."""
    if not member or not role_names:
        return False

    member_role_names = [role.name for role in member.roles]
    return any(role_name in member_role_names for role_name in role_names)


def check_permission(member: disnake.Member, command_name: str) -> bool:
    """Check if a member has permission to use a command."""
    # Permissions disabled = everyone can use
    if PERMISSION_MODE == 'none':
        return True

    # Owner bypass
    if OWNER_BYPASS and member.guild and member.id == member.guild.owner_id:
        return True

    # Get required level
    required_level = COMMAND_PERMISSIONS.get(command_name, 'everyone')

    if required_level == 'everyone':
        return True

    # Boss can do everything
    if has_role(member, BOSS_ROLES):
        return True

    # Check bartender
    if required_level == 'bartender':
        return has_role(member, BARTENDER_ROLES)

    # Check VIP
    if required_level == 'vip':
        return has_role(member, VIP_ROLES) or has_role(member, BARTENDER_ROLES)

    return False


def permission_check():
    """Decorator for command permission checking."""
    async def predicate(ctx: commands.Context) -> bool:
        command_name = ctx.command.name if ctx.command else 'unknown'
        has_perm = check_permission(ctx.author, command_name)

        if not has_perm:
            logger.debug(f"Permission denied: {ctx.author} for '{command_name}'")

            # Send error based on mode
            from config import COMMAND_MODE

            if COMMAND_MODE == 'prefix':
                player = ctx.bot.get_cog('MusicCommands').get_player(ctx)
                if player:
                    from config import USER_COMMAND_TTL
                    role = COMMAND_PERMISSIONS.get(command_name, 'everyone')
                    await player.cleanup_manager.send_with_ttl(
                        ctx.channel,
                        PERMISSION_MESSAGES['no_permission'].format(role=role),
                        USER_COMMAND_TTL
                    )

        return has_perm

    return commands.check(predicate)


def check_voice_channel(ctx_or_inter) -> bool:
    """Check if user is in same voice channel as bot."""
    if isinstance(ctx_or_inter, commands.Context):
        member = ctx_or_inter.author
        guild = ctx_or_inter.guild
    else:
        member = ctx_or_inter.author
        guild = ctx_or_inter.guild

    if not member or not guild:
        return False

    if not member.voice or not member.voice.channel:
        return False

    bot_voice = guild.me.voice if guild.me else None
    if not bot_voice or not bot_voice.channel:
        return True  # Bot not in voice, user can summon

    return member.voice.channel.id == bot_voice.channel.id


__all__ = [
    'has_role',
    'check_permission',
    'permission_check',
    'check_voice_channel',
]
