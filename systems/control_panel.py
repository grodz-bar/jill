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

logger = logging.getLogger(__name__)


class ControlPanelManager:
    """Manages control panel and now playing messages per guild."""

    def __init__(self, bot):
        self.bot = bot
        self.panels: Dict[int, Dict] = {}
        self.last_update_time: Dict[int, float] = {}

        # Initialize panels on startup
        if COMMAND_MODE == 'slash':
            asyncio.create_task(self._initialize_panels())

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

                logger.debug(f"Initialized control panel for guild {guild_id}")

            except Exception as e:
                logger.error(f"Failed to initialize panel for guild {guild_id}: {e}")
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

        # Now playing message
        if 'now_playing_id' in message_info:
            try:
                msg = await channel.fetch_message(message_info['now_playing_id'])
                await msg.delete()
            except (disnake.NotFound, disnake.Forbidden):
                pass

    async def create_panel(self, guild_id: int, channel: disnake.TextChannel):
        """Create control panel and now playing messages."""
        if guild_id in self.panels:
            await self.delete_panel(guild_id)

        try:
            # Create control panel
            control_embed = create_control_panel_embed(is_playing=False)
            control_components = create_control_buttons(is_playing=False, is_paused=False)

            control_msg = await channel.send(
                embed=control_embed,
                components=control_components
            )

            # Create now playing message
            now_playing_content = self._format_now_playing(None, None)
            now_playing_msg = await channel.send(content=now_playing_content)

            # Store panel info
            self.panels[guild_id] = {
                'channel': channel,
                'control_panel': control_msg,
                'now_playing': now_playing_msg,
            }

            # Save message IDs
            save_message_ids(
                guild_id,
                control_panel_id=control_msg.id,
                now_playing_id=now_playing_msg.id,
                channel_id=channel.id
            )

            logger.debug(f"Created control panel for guild {guild_id}")

        except Exception as e:
            logger.error(f"Failed to create control panel for guild {guild_id}: {e}")

    async def delete_panel(self, guild_id: int):
        """Delete control panel messages for a guild."""
        if guild_id not in self.panels:
            return

        panel_info = self.panels[guild_id]

        # Delete messages
        try:
            await panel_info['control_panel'].delete()
        except (disnake.NotFound, disnake.Forbidden):
            pass

        try:
            await panel_info['now_playing'].delete()
        except (disnake.NotFound, disnake.Forbidden):
            pass

        # Clean up
        del self.panels[guild_id]
        clear_message_ids(guild_id)

        logger.debug(f"Deleted control panel for guild {guild_id}")

    def _format_now_playing(self, player, track) -> str:
        """Format the now playing message text."""
        if not track:
            return f"{MESSAGES['NOW_PLAYING_TITLE']}\n{MESSAGES['NOTHING_PLAYING']}\n{MESSAGES['QUEUE_EMPTY_MESSAGE']}"

        # Basic track info
        lines = [
            MESSAGES['NOW_PLAYING_TITLE'],
            MESSAGES['TRACK_INFO'].format(
                index=player.current_track_index + 1 if player else 1,
                name=track.display_name
            )
        ]

        # Playlist info
        if player and hasattr(player, 'current_playlist') and player.current_playlist:
            lines.append(MESSAGES['PLAYLIST_INFO'].format(name=player.current_playlist))

        # Status
        if player:
            if player.is_paused():
                lines.append(MESSAGES['STATUS_PAUSED'])
            elif player.is_playing():
                lines.append(MESSAGES['STATUS_PLAYING'])

        # Queue preview
        if player and hasattr(player, 'queue') and player.queue:
            lines.append("")
            lines.append(MESSAGES['UP_NEXT'])

            for i in range(min(3, len(player.queue))):
                idx = player.queue[i]
                if idx < len(player.library):
                    lines.append(f"  {i+1}. {player.library[idx].display_name}")

            if len(player.queue) > 3:
                lines.append(f"  {MESSAGES['AND_MORE'].format(count=len(player.queue) - 3)}")

        return "\n".join(lines)

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

            # Update control panel
            is_playing = player.is_playing()
            is_paused = player.is_paused()

            control_embed = create_control_panel_embed(is_playing=(is_playing or is_paused))
            control_components = create_control_buttons(
                is_playing=(is_playing or is_paused),
                is_paused=is_paused
            )

            await panel_info['control_panel'].edit(
                embed=control_embed,
                components=control_components
            )

            # Update now playing message
            current_track = None
            if player.current_track_index is not None and player.library:
                current_track = player.library[player.current_track_index]

            now_playing_content = self._format_now_playing(player, current_track)
            await panel_info['now_playing'].edit(content=now_playing_content)

        except Exception as e:
            logger.error(f"Failed to update control panel for guild {guild_id}: {e}")
            if guild_id in self.panels:
                del self.panels[guild_id]


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
