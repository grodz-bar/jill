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
Modern Mode Commands (Slash Commands)

All 11 bot commands for Modern (/play) mode with:
- Discord native slash commands (type / to see all)
- Ephemeral responses (only command user sees them)
- Interactive button controls via control panel
- Auto-updating embeds with live playback status
- Permission checks (VA-11 HALL-A themed)

Only loaded when COMMAND_MODE='slash'. Discord handles rate limiting
and command caching automatically for slash commands.
"""

import logging
from typing import Optional
import disnake
from disnake.ext import commands

logger = logging.getLogger(__name__)

# Import from our modules
from core.playback import _play_current, _play_next, _play_first
from core.track import has_playlist_structure, discover_playlists
from config import (
    COMMAND_MODE, MESSAGES, COMMAND_DESCRIPTIONS,
    create_queue_embed, create_tracks_embed, create_playlists_embed,
    create_help_embed, LIBRARY_PAGE_SIZE, PLAYLIST_PAGE_SIZE
)
from utils.response_helper import send_response
from utils.discord_helpers import can_connect_to_channel, get_guild_player, ensure_voice_connected
from systems.control_panel import get_control_panel_manager


def setup(bot):
    """Register slash commands with the bot."""

    if COMMAND_MODE != 'slash':
        logger.info("Slash commands disabled (prefix mode)")
        return

    logger.info("Registering slash commands...")

    # =========================================================================
    # SLASH COMMANDS
    # =========================================================================

    @bot.slash_command(
        name='play',
        description=COMMAND_DESCRIPTIONS['play']
    )
    async def play_slash(
        inter: disnake.ApplicationCommandInteraction,
        track: str = disnake.Option(description="Track name or number", required=False, default=None)
    ):
        """Start playback or jump to a specific track."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        # Check voice
        if not inter.author.voice:
            await send_response(inter, MESSAGES['USER_NOT_IN_VOICE'])
            return

        channel = inter.author.voice.channel

        # Connect if needed
        if not player.voice_client or not player.voice_client.is_connected():
            if not can_connect_to_channel(channel):
                await send_response(inter, MESSAGES['CANNOT_CONNECT'])
                return

            try:
                vc = await channel.connect(timeout=5.0, reconnect=True)
                player.set_voice_client(vc)
                player.set_text_channel(inter.channel)
            except Exception as e:
                await send_response(inter, MESSAGES['CANNOT_CONNECT'])
                logger.error(f"Guild {inter.guild.id}: Connection failed: {e}")
                return

        # If no track specified, just resume/start
        if not track:
            if player.is_paused():
                player.resume()
                await send_response(inter, MESSAGES['RESUMED'])
            elif not player.is_playing():
                await _play_first(inter.guild.id, bot)
                await send_response(inter, MESSAGES['STARTING_PLAYBACK'])
            else:
                await send_response(inter, MESSAGES['STARTING_PLAYBACK'])
        else:
            # Jump to track
            try:
                track_num = int(track) - 1
                if 0 <= track_num < len(player.library):
                    player.jump_to_track(track_num)
                    await _play_current(inter.guild.id, bot)
                    track_name = player.library[track_num].display_name
                    await send_response(inter, MESSAGES['JUMPED_TO_TRACK'].format(
                        number=track_num + 1,
                        name=track_name
                    ))
                else:
                    await send_response(inter, MESSAGES['TRACK_NOT_FOUND'].format(query=track))
            except ValueError:
                # Search by name
                found = False
                for idx, t in enumerate(player.library):
                    if track.lower() in t.display_name.lower():
                        player.jump_to_track(idx)
                        await _play_current(inter.guild.id, bot)
                        await send_response(inter, MESSAGES['JUMPED_TO_TRACK'].format(
                            number=idx + 1,
                            name=t.display_name
                        ))
                        found = True
                        break

                if not found:
                    await send_response(inter, MESSAGES['TRACK_NOT_FOUND'].format(query=track))

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)


    @bot.slash_command(
        name='pause',
        description=COMMAND_DESCRIPTIONS['pause']
    )
    async def pause_slash(inter: disnake.ApplicationCommandInteraction):
        """Pause the current track."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        if not player.is_playing():
            await send_response(inter, MESSAGES['BOT_NOT_PLAYING'])
            return

        if player.is_paused():
            player.resume()
            await send_response(inter, MESSAGES['RESUMED'])
        else:
            player.pause()
            await send_response(inter, MESSAGES['PAUSED'])

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)


    @bot.slash_command(
        name='skip',
        description=COMMAND_DESCRIPTIONS['skip']
    )
    async def skip_slash(inter: disnake.ApplicationCommandInteraction):
        """Skip to the next track."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        if not player.is_playing():
            await send_response(inter, MESSAGES['BOT_NOT_PLAYING'])
            return

        await _play_next(inter.guild.id, bot)
        await send_response(inter, MESSAGES['SKIPPED'])

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)


    @bot.slash_command(
        name='stop',
        description=COMMAND_DESCRIPTIONS['stop']
    )
    async def stop_slash(inter: disnake.ApplicationCommandInteraction):
        """Stop playback and disconnect."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        if player.voice_client:
            await player.voice_client.disconnect(force=True)

        player.reset_state()
        await send_response(inter, MESSAGES['STOPPED'])

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)


    @bot.slash_command(
        name='previous',
        description=COMMAND_DESCRIPTIONS['previous']
    )
    async def previous_slash(inter: disnake.ApplicationCommandInteraction):
        """Go back to the previous track."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        if player.previous_track():
            await _play_current(inter.guild.id, bot)
            await send_response(inter, MESSAGES['PREVIOUS'])
        else:
            await send_response(inter, MESSAGES['NO_PREVIOUS_TRACK'])

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)


    @bot.slash_command(
        name='shuffle',
        description=COMMAND_DESCRIPTIONS['shuffle']
    )
    async def shuffle_slash(inter: disnake.ApplicationCommandInteraction):
        """Toggle shuffle mode."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        player.toggle_shuffle()

        if player.shuffle_enabled:
            await send_response(inter, MESSAGES['SHUFFLE_ON'])
        else:
            await send_response(inter, MESSAGES['SHUFFLE_OFF'])

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)


    @bot.slash_command(
        name='queue',
        description=COMMAND_DESCRIPTIONS['queue']
    )
    async def queue_slash(inter: disnake.ApplicationCommandInteraction):
        """Show the current queue."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        current_track = None
        if player.current_track_index is not None and player.library:
            current_track = player.library[player.current_track_index].display_name

        upcoming = []
        if player.queue:
            upcoming = [player.library[idx].display_name for idx in player.queue[:10]]

        embed = create_queue_embed(current_track, upcoming, player.shuffle_enabled)
        await send_response(inter, "", embed=embed)


    @bot.slash_command(
        name='tracks',
        description=COMMAND_DESCRIPTIONS['tracks']
    )
    async def tracks_slash(
        inter: disnake.ApplicationCommandInteraction,
        page: int = disnake.Option(description="Page number", required=False, default=1)
    ):
        """List all available tracks."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        if not player.library:
            await send_response(inter, MESSAGES['NO_TRACKS'])
            return

        # Pagination
        total_pages = (len(player.library) + LIBRARY_PAGE_SIZE - 1) // LIBRARY_PAGE_SIZE
        page = max(1, min(page, total_pages))

        start_idx = (page - 1) * LIBRARY_PAGE_SIZE
        end_idx = min(start_idx + LIBRARY_PAGE_SIZE, len(player.library))

        track_list = []
        for i in range(start_idx, end_idx):
            track = player.library[i]
            track_list.append(f"{i+1}. {track.display_name}")

        embed = create_tracks_embed(track_list, page, total_pages, player.current_playlist)
        await send_response(inter, "", embed=embed)


    @bot.slash_command(
        name='playlist',
        description=COMMAND_DESCRIPTIONS['playlist']
    )
    async def playlist_slash(
        inter: disnake.ApplicationCommandInteraction,
        name: str = disnake.Option(description="Playlist name", required=True)
    ):
        """Switch to a different playlist."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        if not has_playlist_structure():
            await send_response(inter, MESSAGES['NO_PLAYLISTS'])
            return

        playlists = discover_playlists(inter.guild.id)
        found = None

        for pl in playlists:
            if pl.name.lower() == name.lower():
                found = pl
                break

        if not found:
            await send_response(inter, MESSAGES['PLAYLIST_NOT_FOUND'].format(name=name))
            return

        player.switch_playlist(found.name)
        await send_response(inter, MESSAGES['PLAYLIST_SWITCHED'].format(playlist=found.name))

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)


    @bot.slash_command(
        name='playlists',
        description=COMMAND_DESCRIPTIONS['playlists']
    )
    async def playlists_slash(inter: disnake.ApplicationCommandInteraction):
        """Show all available playlists."""
        await inter.response.defer(ephemeral=True)

        if not has_playlist_structure():
            await send_response(inter, MESSAGES['NO_PLAYLISTS'])
            return

        playlists = discover_playlists(inter.guild.id)

        if not playlists:
            await send_response(inter, MESSAGES['NO_PLAYLISTS'])
            return

        playlist_names = [f"{pl.name} ({pl.track_count} tracks)" for pl in playlists]
        embed = create_playlists_embed(playlist_names)
        await send_response(inter, "", embed=embed)


    @bot.slash_command(
        name='help',
        description=COMMAND_DESCRIPTIONS['help']
    )
    async def help_slash(inter: disnake.ApplicationCommandInteraction):
        """Show help information."""
        await inter.response.defer(ephemeral=True)

        embed = create_help_embed()
        await send_response(inter, "", embed=embed)

    logger.info("Slash commands registered successfully")
