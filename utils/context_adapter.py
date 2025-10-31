"""
Context Adapter

Unified interface for both command types.
"""

import logging
from typing import Optional
import disnake
from disnake.ext import commands

logger = logging.getLogger(__name__)


class UnifiedContext:
    """Wrapper providing unified interface."""

    def __init__(self, ctx_or_inter):
        self._inner = ctx_or_inter
        self.is_slash = isinstance(ctx_or_inter, disnake.ApplicationCommandInteraction)

    @property
    def author(self) -> disnake.Member:
        return self._inner.author

    @property
    def guild(self) -> disnake.Guild:
        return self._inner.guild

    @property
    def channel(self) -> disnake.TextChannel:
        return self._inner.channel

    @property
    def bot(self):
        return self._inner.bot

    @property
    def voice_client(self) -> Optional[disnake.VoiceClient]:
        if self.guild:
            return self.guild.voice_client
        return None

    async def send(self, content=None, *, embed=None, ephemeral=None, components=None):
        """Send response based on type."""
        if self.is_slash:
            if ephemeral is None:
                ephemeral = True

            if not self._inner.response.is_done():
                await self._inner.response.send_message(
                    content=content,
                    embed=embed,
                    ephemeral=ephemeral,
                    components=components
                )
            else:
                await self._inner.followup.send(
                    content=content,
                    embed=embed,
                    ephemeral=ephemeral,
                    components=components
                )
            return None
        else:
            return await self._inner.send(content=content, embed=embed, components=components)

    async def defer(self, ephemeral=True):
        """Defer response (slash only)."""
        if self.is_slash and not self._inner.response.is_done():
            await self._inner.response.defer(ephemeral=ephemeral)

    @property
    def command_name(self) -> str:
        if self.is_slash:
            return self._inner.data.name
        return self._inner.command.name if self._inner.command else 'unknown'


def create_unified_context(ctx_or_inter):
    """Create unified context."""
    return UnifiedContext(ctx_or_inter)


__all__ = ['UnifiedContext', 'create_unified_context']
