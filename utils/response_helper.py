"""
Response Helper

Unified message sending for both modes.
"""

import logging
from typing import Optional
import disnake
from disnake.ext import commands
from config import COMMAND_MODE

logger = logging.getLogger(__name__)


async def send_response(
    ctx,
    content: str,
    ttl: Optional[float] = None,
    embed: Optional[disnake.Embed] = None,
    ephemeral: bool = None,
    player=None
) -> Optional[disnake.Message]:
    """Send response based on mode."""

    if COMMAND_MODE == 'slash':
        if ephemeral is None:
            ephemeral = True

        if isinstance(ctx, disnake.ApplicationCommandInteraction):
            if not ctx.response.is_done():
                await ctx.response.send_message(
                    content=content,
                    embed=embed,
                    ephemeral=ephemeral
                )
            else:
                await ctx.followup.send(
                    content=content,
                    embed=embed,
                    ephemeral=ephemeral
                )
        else:
            await ctx.send(content=content, embed=embed, ephemeral=ephemeral)

        return None

    else:
        # Prefix mode - use cleanup manager
        if player and hasattr(player, 'cleanup_manager') and ttl is not None:
            return await player.cleanup_manager.send_with_ttl(
                ctx.channel,
                content,
                ttl
            )
        else:
            return await ctx.send(content=content, embed=embed)


__all__ = ['send_response']
