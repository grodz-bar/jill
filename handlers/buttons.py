# Copyright (C) 2025 grodz
#
# This file is part of Jill.
#
# Jill is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Button Interaction Handler (Modern Mode Only)

Handles button clicks from control panel in Modern (/play) mode:
- 6 button types: play, pause, skip, previous, shuffle, stop
- Permission checking (VA-11 HALL-A themed)
- Ephemeral error responses
- Updates control panel after actions

Only active when COMMAND_MODE='slash'. All messages from config/slash/messages.py!
"""

import logging
import disnake
from disnake.ext import commands

from core.playback import _play_current, _play_next, _play_first
from utils.permission_checks import check_permission, check_voice_channel
from utils.discord_helpers import get_guild_player
from config import MESSAGES, PERMISSION_MESSAGES, COMMAND_MODE

logger = logging.getLogger(__name__)


class ButtonHandler(commands.Cog):
    """Handles button interactions."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction):
        """Handle button clicks."""

        if not inter.component.custom_id.startswith('music_'):
            return

        await inter.response.defer(ephemeral=True)

        command = inter.component.custom_id.replace('music_', '')

        # Check permissions
        if not check_permission(inter.author, command):
            from config import COMMAND_PERMISSIONS
            role = COMMAND_PERMISSIONS.get(command, 'everyone')
            await inter.followup.send(
                PERMISSION_MESSAGES['no_permission'].format(role=role),
                ephemeral=True
            )
            return

        # Check voice
        if not check_voice_channel(inter):
            await inter.followup.send(
                PERMISSION_MESSAGES['not_in_voice'],
                ephemeral=True
            )
            return

        player = await get_guild_player(inter, self.bot)

        try:
            response = await self.handle_button_action(command, player, inter)

            if response:
                await inter.followup.send(response, ephemeral=True)

            # Update panel
            from systems.control_panel import get_control_panel_manager
            panel_manager = get_control_panel_manager(self.bot)
            if panel_manager:
                await panel_manager.update_panel(inter.guild.id, player)

        except Exception as e:
            logger.error(f"Error handling button {command}: {e}", exc_info=True)
            await inter.followup.send(
                MESSAGES['ERROR_OCCURRED'],
                ephemeral=True
            )

    async def handle_button_action(self, command: str, player, inter) -> str:
        """Handle button action."""

        if command == 'play':
            if player.is_paused():
                player.resume()
                return MESSAGES['RESUMED']
            elif not player.is_playing() and player.library:
                if not player.voice_client:
                    if inter.author.voice and inter.author.voice.channel:
                        vc = await inter.author.voice.channel.connect(timeout=5.0, reconnect=True)
                        player.set_voice_client(vc)
                        player.set_text_channel(inter.channel)

                await _play_first(inter.guild.id, self.bot)
                return MESSAGES['STARTING_PLAYBACK']
            else:
                return MESSAGES['NO_TRACKS']

        elif command == 'pause':
            if player.is_playing():
                player.pause()
                return MESSAGES['PAUSED']
            else:
                return MESSAGES['BOT_NOT_PLAYING']

        elif command == 'skip':
            if player.is_playing() or player.is_paused():
                await _play_next(inter.guild.id, self.bot)
                return MESSAGES['SKIPPED']
            else:
                return MESSAGES['BOT_NOT_PLAYING']

        elif command == 'previous':
            if player.previous_track():
                await _play_current(inter.guild.id, self.bot)
                return MESSAGES['PREVIOUS']
            else:
                return MESSAGES['NO_PREVIOUS_TRACK']

        elif command == 'shuffle':
            player.toggle_shuffle()
            if player.shuffle_enabled:
                return MESSAGES['SHUFFLE_ON']
            else:
                return MESSAGES['SHUFFLE_OFF']

        elif command == 'stop':
            if player.voice_client:
                await player.voice_client.disconnect(force=True)

            player.reset_state()
            return MESSAGES['STOPPED']

        else:
            return MESSAGES['ERROR_OCCURRED']


def setup(bot):
    """Add cog to bot."""
    if COMMAND_MODE == 'slash':
        bot.add_cog(ButtonHandler(bot))
        logger.debug("Button handler registered")


__all__ = ['ButtonHandler', 'setup']
