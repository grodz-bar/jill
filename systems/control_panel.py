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
Control Panel Manager (Modern Mode Only)

Manages persistent control panel for Modern (/play) mode with:
- Auto-updating embeds showing current track and playback state
- Interactive buttons (play, pause, skip, previous, shuffle, stop)
- Throttled updates (2s default) to prevent rate limiting
- Message ID persistence (survives bot restart)

Only active when COMMAND_MODE='slash'. Created on first /play command.
All messages from config/slash/* - no hardcoded strings!
"""

import asyncio
import logging
import time
from typing import Dict, Optional
import disnake

from systems.voice_manager import PlaybackState
from config import (
    COMMAND_MODE,
    MESSAGES,
    UPDATE_THROTTLE_TIME,
    STARTUP_MESSAGE_DELAY,
    create_control_panel_embed,
    create_control_buttons,
)
from utils.persistence import (
    load_message_ids,
    save_message_ids,
    clear_message_ids,
)
from utils.discord_helpers import format_guild_log

logger = logging.getLogger(__name__)


class ControlPanelManager:
    """Manages control panel per guild."""

    def __init__(self, bot):
        self.bot = bot
        self.panels: Dict[int, Dict] = {}
        self.last_update_time: Dict[int, float] = {}
        self._init_task: Optional[asyncio.Task] = None

        # Initialize panels on startup
        if COMMAND_MODE == 'slash':
            self._init_task = asyncio.create_task(self._initialize_panels())
            self._init_task.add_done_callback(self._handle_init_error)

    def _handle_init_error(self, task: asyncio.Task):
        """Handle errors from initialization task."""
        try:
            task.result()
        except asyncio.CancelledError:
            logger.debug("Control panel initialization cancelled")
        except Exception as e:
            logger.error(f"Control panel initialization failed: {e}", exc_info=True)

    async def _initialize_panels(self):
        """Initialize panels from saved message IDs after bot startup."""
        await asyncio.sleep(STARTUP_MESSAGE_DELAY)

        logger.info("Initializing control panels from saved message IDs...")

        saved_messages = load_message_ids()

        for guild_id, message_info in saved_messages.items():
            try:
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    continue

                channel_id = message_info.get('channel_id')
                if not channel_id:
                    continue

                channel = guild.get_channel(channel_id)
                if not channel:
                    continue

                # Clean up old messages
                await self._cleanup_old_messages(channel, message_info)

                # Create new panel
                await self.create_panel(guild_id, channel)

                logger.debug(f"Initialized control panel for {format_guild_log(guild_id, self.bot)}")

            except Exception as e:
                logger.error(f"Failed to initialize panel for {format_guild_log(guild_id, self.bot)}: {e}")
                clear_message_ids(guild_id)

    async def _cleanup_old_messages(self, channel: disnake.TextChannel, message_info: Dict):
        """Try to delete old control panel messages."""
        # Control panel
        if 'control_panel_id' in message_info:
            try:
                msg = await channel.fetch_message(message_info['control_panel_id'])
                await msg.delete()
            except (disnake.NotFound, disnake.Forbidden):
                pass

    async def create_panel(self, guild_id: int, channel: disnake.TextChannel):
        """Create control panel for a guild."""
        if guild_id in self.panels:
            await self.delete_panel(guild_id)

        try:
            # Create control panel
            control_embed = create_control_panel_embed(
                is_playing=False,
                track_name=None,
                track_index=None,
                playlist_name=None,
                is_paused=False,
                upcoming_track_names=None,
                total_upcoming=0,
                shuffle_enabled=False,
                current_drink_emoji=None,
                last_track_name=None,
                last_drink_emoji=None,
                next_drink_emoji=None
            )
            control_components = create_control_buttons(is_playing=False, is_paused=False, shuffle_enabled=False)

            control_msg = await channel.send(
                embed=control_embed,
                components=control_components
            )

            # Store panel info
            self.panels[guild_id] = {
                'channel': channel,
                'control_panel': control_msg,
            }

            # Save message IDs
            save_message_ids(
                guild_id,
                control_panel_id=control_msg.id,
                channel_id=channel.id
            )

            logger.debug(f"Created control panel for {format_guild_log(guild_id, self.bot)}")

        except Exception as e:
            logger.error(f"Failed to create control panel for {format_guild_log(guild_id, self.bot)}: {e}")

    async def delete_panel(self, guild_id: int):
        """Delete control panel for a guild."""
        if guild_id not in self.panels:
            return

        panel_info = self.panels[guild_id]

        # Delete control panel message
        try:
            await panel_info['control_panel'].delete()
        except (disnake.NotFound, disnake.Forbidden):
            pass

        # Clean up
        del self.panels[guild_id]
        clear_message_ids(guild_id)

        logger.debug(f"Deleted control panel for {format_guild_log(guild_id, self.bot)}")

    async def update_panel(self, guild_id: int, player):
        """Update control panel based on player state."""
        # Throttle updates
        current_time = time.time()
        last_update = self.last_update_time.get(guild_id, 0)

        if current_time - last_update < UPDATE_THROTTLE_TIME:
            return

        self.last_update_time[guild_id] = current_time

        # Create panel if needed
        if guild_id not in self.panels:
            if player.text_channel:
                await self.create_panel(guild_id, player.text_channel)
            else:
                return

        panel_info = self.panels.get(guild_id)
        if not panel_info:
            return

        try:
            # Check if we need to move to new channel
            if player.text_channel and player.text_channel.id != panel_info['channel'].id:
                await self.delete_panel(guild_id)
                await self.create_panel(guild_id, player.text_channel)
                panel_info = self.panels.get(guild_id)
                if not panel_info:
                    return

            # Gather playback state
            state = player.voice_manager.get_playback_state()
            is_playing = (state == PlaybackState.PLAYING)
            is_paused = (state == PlaybackState.PAUSED)

            # Get current track info
            current_track = player.now_playing
            track_name = current_track.display_name if current_track else None
            track_index = (current_track.library_index + 1) if current_track else None

            # Get playlist info
            playlist_name = player.current_playlist.display_name if hasattr(player, 'current_playlist') and player.current_playlist else None

            # Get last track info (from played history)
            last_track_name = None
            if player.played and len(player.played) > 0:
                last_track_name = player.played[-1].display_name

            # Get drink emojis with offsets for Last/Now/Coming sections
            current_drink_emoji = player.get_drink_emoji(offset=0) if current_track else None
            last_drink_emoji = player.get_drink_emoji(offset=-1) if last_track_name else None
            next_drink_emoji = player.get_drink_emoji(offset=1) if current_track else None

            # Build upcoming tracks list
            upcoming_track_names = []
            if player.upcoming:
                upcoming_list = list(player.upcoming)
                upcoming_track_names = [track.display_name for track in upcoming_list[:3]]

            total_upcoming = len(player.upcoming) if player.upcoming else 0

            # Update control panel
            control_embed = create_control_panel_embed(
                is_playing=(is_playing or is_paused),
                track_name=track_name,
                track_index=track_index,
                playlist_name=playlist_name,
                is_paused=is_paused,
                upcoming_track_names=upcoming_track_names,
                total_upcoming=total_upcoming,
                shuffle_enabled=player.shuffle_enabled,
                current_drink_emoji=current_drink_emoji,
                last_track_name=last_track_name,
                last_drink_emoji=last_drink_emoji,
                next_drink_emoji=next_drink_emoji
            )
            control_components = create_control_buttons(
                is_playing=(is_playing or is_paused),
                is_paused=is_paused,
                shuffle_enabled=player.shuffle_enabled
            )

            await panel_info['control_panel'].edit(
                embed=control_embed,
                components=control_components
            )

        except Exception as e:
            logger.error(f"Failed to update control panel for {format_guild_log(guild_id, self.bot)}: {e}")
            if guild_id in self.panels:
                del self.panels[guild_id]

    async def shutdown(self):
        """Gracefully shutdown the control panel manager."""
        # Cancel initialization task if still running
        if self._init_task and not self._init_task.done():
            self._init_task.cancel()
            try:
                await self._init_task
            except asyncio.CancelledError:
                pass

        logger.debug("Control panel manager shutdown complete")


# Global instance
_control_panel_manager: Optional[ControlPanelManager] = None


def get_control_panel_manager(bot) -> Optional[ControlPanelManager]:
    """Get or create the global control panel manager."""
    global _control_panel_manager

    if COMMAND_MODE != 'slash':
        return None

    if _control_panel_manager is None:
        _control_panel_manager = ControlPanelManager(bot)

    return _control_panel_manager


__all__ = ['ControlPanelManager', 'get_control_panel_manager']
