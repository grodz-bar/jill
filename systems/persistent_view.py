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
Persistent Button View (Modern Mode Only)

Provides persistent button controls that survive bot restarts.
Uses disnake.ui.View with timeout=None and custom_id registration.

Registered in bot.on_ready() with flag protection (disnake lacks setup_hook method).
"""

import logging
import disnake
from utils.permission_checks import check_permission, check_voice_channel
from utils.discord_helpers import get_guild_player, format_guild_log
from config import MESSAGES, PERMISSION_MESSAGES

logger = logging.getLogger(__name__)


class MusicControlView(disnake.ui.View):
    """
    Persistent view for music control buttons.

    Buttons survive bot restarts using timeout=None and custom_id registration.
    Delegates to handlers.buttons.ButtonHandler for business logic.
    """

    def __init__(self, bot):
        super().__init__(timeout=None)  # Never expire
        self.bot = bot

    async def _handle_interaction(self, inter: disnake.MessageInteraction, command: str):
        """
        Common interaction handling logic for all buttons.

        Delegates to ButtonHandler.handle_button_action for business logic.
        """
        # Handle stale/duplicate interactions
        if inter.response.is_done():
            logger.debug(
                f"{format_guild_log(inter.guild.id, self.bot)}: "
                f"Duplicate button event ignored: {inter.component.custom_id}"
            )
            return

        # Defer the interaction
        try:
            await inter.response.defer(ephemeral=True)
        except (disnake.NotFound, disnake.HTTPException):
            logger.debug(
                f"{format_guild_log(inter.guild.id, self.bot)}: "
                f"Button interaction already handled/expired: {inter.component.custom_id}"
            )
            return

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
            # Delegate to ButtonHandler for business logic
            from handlers.buttons import ButtonHandler
            handler = ButtonHandler(self.bot)
            response = await handler.handle_button_action(command, player, inter)

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

    @disnake.ui.button(
        style=disnake.ButtonStyle.secondary,
        emoji="⏮️",
        custom_id="music_previous"
    )
    async def previous_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        """Previous track button."""
        await self._handle_interaction(inter, 'previous')

    @disnake.ui.button(
        style=disnake.ButtonStyle.secondary,
        emoji="⏸️",
        custom_id="music_pause"
    )
    async def pause_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        """Pause button."""
        await self._handle_interaction(inter, 'pause')

    @disnake.ui.button(
        style=disnake.ButtonStyle.success,
        emoji="▶️",
        custom_id="music_play"
    )
    async def play_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        """Play button."""
        await self._handle_interaction(inter, 'play')

    @disnake.ui.button(
        style=disnake.ButtonStyle.secondary,
        emoji="⏭️",
        custom_id="music_skip"
    )
    async def skip_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        """Skip track button."""
        await self._handle_interaction(inter, 'skip')

    @disnake.ui.button(
        style=disnake.ButtonStyle.secondary,
        emoji="🔀",
        custom_id="music_shuffle"
    )
    async def shuffle_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        """Shuffle toggle button."""
        await self._handle_interaction(inter, 'shuffle')

    @disnake.ui.button(
        style=disnake.ButtonStyle.danger,
        emoji="⏹️",
        custom_id="music_stop"
    )
    async def stop_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        """Stop button."""
        await self._handle_interaction(inter, 'stop')


__all__ = ['MusicControlView']
