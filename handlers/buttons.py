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
- Permission checking (role-based)
- Ephemeral error responses
- Updates control panel after actions

Only active when COMMAND_MODE='slash'. All messages from config/slash/messages.py!
"""

import logging
import disnake
from disnake.ext import commands

from core.playback import _play_current, _play_next, _play_first
from systems.voice_manager import PlaybackState
from utils.permission_checks import check_permission, check_voice_channel
from utils.discord_helpers import get_guild_player, format_guild_log
from config import (
    MESSAGES,
    PERMISSION_MESSAGES,
    COMMAND_MODE,
    BUTTON_PLAY_PAUSE_COOLDOWN,
    BUTTON_SKIP_COOLDOWN,
    BUTTON_PREVIOUS_COOLDOWN,
    BUTTON_SHUFFLE_COOLDOWN,
    BUTTON_STOP_COOLDOWN,
    BUTTON_SHOW_COOLDOWN_MESSAGE,
)

logger = logging.getLogger(__name__)

# Button command to cooldown mapping (spam protection Layer 4)
BUTTON_COOLDOWNS = {
    'play': BUTTON_PLAY_PAUSE_COOLDOWN,
    'pause': BUTTON_PLAY_PAUSE_COOLDOWN,
    'skip': BUTTON_SKIP_COOLDOWN,
    'previous': BUTTON_PREVIOUS_COOLDOWN,
    'shuffle': BUTTON_SHUFFLE_COOLDOWN,
    'stop': BUTTON_STOP_COOLDOWN,
}


class ButtonHandler(commands.Cog):
    """Handles button interactions."""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_button_click(self, inter: disnake.MessageInteraction):
        """Handle button clicks."""

        if not inter.component.custom_id.startswith('music_'):
            return

        # Handle stale/duplicate interactions
        # Discord can send duplicate button events for the same interaction
        if inter.response.is_done():
            logger.debug(
                f"{format_guild_log(inter.guild.id, self.bot)}: "
                f"Duplicate button event ignored: {inter.component.custom_id}"
            )
            return

        # Defer the interaction (with fallback for edge cases)
        # Discord interactions expire after 15 minutes
        try:
            await inter.response.defer(ephemeral=True)
        except (disnake.NotFound, disnake.HTTPException):
            logger.debug(
                f"{format_guild_log(inter.guild.id, self.bot)}: "
                f"Button interaction already handled/expired: {inter.component.custom_id}"
            )
            return

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
                MESSAGES['error_occurred'],
                ephemeral=True
            )

    async def handle_button_action(self, command: str, player, inter) -> str:
        """
        Handle button action with spam protection (Layer 4 cooldowns).

        Returns error message string to show user, or None for silent success.
        """

        # Spam protection: Check cooldown (Layer 4)
        # Layer 3 (serial queue) already handled by playback functions
        cooldown = BUTTON_COOLDOWNS.get(command, 1.0)
        allow, reason = player.spam_protector.check_cooldown(
            f"button_{command}",
            cooldown
        )

        if not allow:
            # User clicking too fast - silently ignore or show message based on config
            if BUTTON_SHOW_COOLDOWN_MESSAGE:
                return MESSAGES['button_on_cooldown']
            else:
                return None  # Silent failure (recommended)

        if command == 'play':
            state = player.voice_manager.get_playback_state()
            logger.debug(
                f"{format_guild_log(inter.guild.id, self.bot)}: Play button clicked - "
                f"state={state}, library_size={len(player.library)}, "
                f"has_voice_client={player.voice_client is not None}"
            )

            if state == PlaybackState.PAUSED:
                # Resume paused playback
                player.voice_client.resume()
                player.state = PlaybackState.PLAYING
                player.spam_protector.record_execution(f"button_{command}")
                return None  # Control panel shows play state

            elif state == PlaybackState.PLAYING:
                # Already playing - silently ignore
                return None

            elif player.library:
                # Start playback from beginning
                if not player.voice_client:
                    if inter.author.voice and inter.author.voice.channel:
                        vc = await inter.author.voice.channel.connect(timeout=5.0, reconnect=True)
                        player.set_voice_client(vc)
                        player.set_text_channel(inter.channel)

                await _play_first(inter.guild.id, self.bot)
                player.spam_protector.record_execution(f"button_{command}")
                return None  # Control panel updates

            else:
                # No tracks in library
                logger.warning(
                    f"{format_guild_log(inter.guild.id, self.bot)}: Play button failed - "
                    f"no tracks in library"
                )
                return MESSAGES['error_no_tracks']

        elif command == 'pause':
            state = player.voice_manager.get_playback_state()
            if state == PlaybackState.PLAYING:
                player.voice_client.pause()
                player.state = PlaybackState.PAUSED
                player.spam_protector.record_execution(f"button_{command}")
                return None  # Control panel shows pause state
            else:
                return MESSAGES['error_not_playing']

        elif command == 'skip':
            state = player.voice_manager.get_playback_state()
            if state == PlaybackState.PLAYING or state == PlaybackState.PAUSED:
                await _play_next(inter.guild.id, self.bot)
                player.spam_protector.record_execution(f"button_{command}")
                return None  # "Now playing" updates
            else:
                return MESSAGES['error_not_playing']

        elif command == 'previous':
            if player.go_to_previous():
                await _play_current(inter.guild.id, self.bot, going_backward=True)
                player.spam_protector.record_execution(f"button_{command}")
                return None  # "Now playing" updates
            else:
                return MESSAGES['error_no_previous']

        elif command == 'shuffle':
            player.shuffle_enabled = not player.shuffle_enabled
            player.spam_protector.record_execution(f"button_{command}")
            return None  # Shuffle button changes color

        elif command == 'stop':
            # Stop button handling (if it exists)
            state = player.voice_manager.get_playback_state()
            if state != PlaybackState.IDLE:
                # Stop logic would go here
                player.spam_protector.record_execution(f"button_{command}")
                return None
            else:
                return MESSAGES['error_not_playing']

        else:
            return MESSAGES['error_occurred']


def setup(bot):
    """Add cog to bot."""
    if COMMAND_MODE == 'slash':
        bot.add_cog(ButtonHandler(bot))
        logger.debug("Button handler registered")


__all__ = ['ButtonHandler', 'setup']
