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

SPAM PROTECTION:
Slash commands bypass most spam protection layers (Layers 1, 2, 4) because
Discord provides built-in protection (rate limiting, cooldowns, ephemeral responses).
They only use Layer 3 (Serial Queue) by calling playback functions directly
(e.g., _play_next(), _play_current()) which queue operations internally.

This is different from prefix commands (!skip) which go through all 4 layers
via spam_protected_execute() helper. See systems/spam_protection.py for details.

Only loaded when COMMAND_MODE='slash'. Discord handles rate limiting
and command caching automatically for slash commands.
"""

import logging
from typing import Optional
import disnake
from disnake.ext import commands

logger = logging.getLogger(__name__)
user_logger = logging.getLogger('jill')

# Import from our modules
from core.playback import _play_current, _play_next, _play_first
from core.track import has_playlist_structure, discover_playlists
from systems.voice_manager import PlaybackState
from config import (
    COMMAND_MODE, MESSAGES, COMMAND_DESCRIPTIONS,
    create_queue_embed, create_tracks_embed, create_playlists_embed,
    create_help_embed, QUEUE_DISPLAY_COUNT, LIBRARY_PAGE_SIZE, PLAYLIST_PAGE_SIZE
)
from utils.response_helper import send_response
from utils.discord_helpers import can_connect_to_channel, get_guild_player, ensure_voice_connected, format_guild_log, format_user_log, fuzzy_match
from systems.control_panel import get_control_panel_manager


def setup(bot):
    """Register slash commands with the bot."""

    if COMMAND_MODE != 'slash':
        logger.debug("Slash commands disabled (prefix mode)")
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
        track: str = commands.Param(description="Track name or number", default=None)
    ):
        """Start playback or jump to a specific track."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        # Check voice
        if not inter.author.voice:
            await send_response(inter, MESSAGES['error_not_in_voice'])
            return

        channel = inter.author.voice.channel

        # Connect if needed
        if not player.voice_client or not player.voice_client.is_connected():
            if not can_connect_to_channel(channel):
                await send_response(inter, MESSAGES['error_cant_connect'].format(error="Permission denied"))
                return

            try:
                vc = await channel.connect(timeout=5.0, reconnect=True)
                player.set_voice_client(vc)
                player.set_text_channel(inter.channel)
            except Exception as e:
                await send_response(inter, MESSAGES['error_cant_connect'].format(error=str(e)))
                logger.error(f"{format_guild_log(inter.guild.id, bot)}: Connection failed: {e}")
                return

        # If no track specified, just resume/start
        if not track:
            state = player.voice_manager.get_playback_state()
            if state == PlaybackState.PAUSED:
                player.voice_client.resume()
                player.state = PlaybackState.PLAYING
                # No message - control panel shows play state
            elif state != PlaybackState.PLAYING:
                await _play_first(inter.guild.id, bot)
                # No message - control panel updates
            # If already playing, do nothing
        else:
            # Jump to track using fuzzy matching
            found = fuzzy_match(
                track,
                player.library,
                lambda t: t.display_name,
                lambda t: t.library_index
            )

            if found:
                player.jump_to_track(found.library_index)
                await _play_current(inter.guild.id, bot)
                # No message - "now playing" updates
            else:
                await send_response(inter, MESSAGES['error_track_not_found'].format(query=track))
                return

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)

        # Delete deferred response (silent mode)
        await inter.delete_original_response()


    @bot.slash_command(
        name='pause',
        description=COMMAND_DESCRIPTIONS['pause']
    )
    async def pause_slash(inter: disnake.ApplicationCommandInteraction):
        """Pause the current track."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        state = player.voice_manager.get_playback_state()
        if state != PlaybackState.PLAYING and state != PlaybackState.PAUSED:
            await send_response(inter, MESSAGES['error_not_playing'])
            return

        if state == PlaybackState.PAUSED:
            player.voice_client.resume()
            player.state = PlaybackState.PLAYING
            # No message - control panel shows play state
        else:
            player.voice_client.pause()
            player.state = PlaybackState.PAUSED
            # No message - control panel shows pause state

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)

        # Delete deferred response (silent mode)
        await inter.delete_original_response()


    @bot.slash_command(
        name='skip',
        description=COMMAND_DESCRIPTIONS['skip']
    )
    async def skip_slash(inter: disnake.ApplicationCommandInteraction):
        """Skip to the next track."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        state = player.voice_manager.get_playback_state()
        if state != PlaybackState.PLAYING and state != PlaybackState.PAUSED:
            await send_response(inter, MESSAGES['error_not_playing'])
            return

        await _play_next(inter.guild.id, bot)
        # No message - "now playing" updates

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)

        # Delete deferred response (silent mode)
        await inter.delete_original_response()


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

        # Log stop command
        user_logger.info(f"{format_guild_log(inter.guild.id, bot)}－{format_user_log(inter.author, bot)} stopped jill")

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)

        # Delete deferred response (silent mode)
        await inter.delete_original_response()


    @bot.slash_command(
        name='previous',
        description=COMMAND_DESCRIPTIONS['previous']
    )
    async def previous_slash(inter: disnake.ApplicationCommandInteraction):
        """Go back to the previous track."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        if player.go_to_previous():
            await _play_current(inter.guild.id, bot, going_backward=True)
            # No message - "now playing" updates

            # Update control panel
            panel_manager = get_control_panel_manager(bot)
            if panel_manager:
                await panel_manager.update_panel(inter.guild.id, player)

            # Delete deferred response (silent mode)
            await inter.delete_original_response()
        else:
            await send_response(inter, MESSAGES['error_no_previous'])


    @bot.slash_command(
        name='shuffle',
        description=COMMAND_DESCRIPTIONS['shuffle']
    )
    async def shuffle_slash(inter: disnake.ApplicationCommandInteraction):
        """Toggle shuffle mode."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        player.shuffle_enabled = not player.shuffle_enabled
        # No message - shuffle button changes color

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)

        # Delete deferred response (silent mode)
        await inter.delete_original_response()


    @bot.slash_command(
        name='queue',
        description=COMMAND_DESCRIPTIONS['queue']
    )
    async def queue_slash(inter: disnake.ApplicationCommandInteraction):
        """Show the current queue."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        current_track = None
        if player.now_playing:
            current_track = player.now_playing.display_name

        upcoming = []
        if player.upcoming:
            upcoming = [track.display_name for track in list(player.upcoming)[:QUEUE_DISPLAY_COUNT]]

        last_played = None
        if player.played:
            last_played = player.played[-1].display_name

        embed = create_queue_embed(current_track, upcoming, player.shuffle_enabled, last_played)
        await send_response(inter, "", embed=embed)


    @bot.slash_command(
        name='tracks',
        description=COMMAND_DESCRIPTIONS['tracks']
    )
    async def tracks_slash(
        inter: disnake.ApplicationCommandInteraction,
        page: int = commands.Param(description="Page number", default=1)
    ):
        """List all available tracks."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        if not player.library:
            await send_response(inter, MESSAGES['error_no_tracks'])
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

        embed = create_tracks_embed(track_list, page, total_pages, player.current_playlist.display_name if player.current_playlist else None)
        await send_response(inter, "", embed=embed)


    @bot.slash_command(
        name='playlist',
        description=COMMAND_DESCRIPTIONS['playlist']
    )
    async def playlist_slash(
        inter: disnake.ApplicationCommandInteraction,
        name: str = commands.Param(description="Playlist name", default=...)
    ):
        """Switch to a different playlist."""
        await inter.response.defer(ephemeral=True)

        player = await get_guild_player(inter, bot)

        if not has_playlist_structure():
            await send_response(inter, MESSAGES['error_no_playlists'])
            return

        playlists = discover_playlists(inter.guild.id)

        found = fuzzy_match(
            name,
            playlists,
            lambda p: p.display_name
        )

        if not found:
            await send_response(inter, MESSAGES['error_playlist_not_found'].format(name=name))
            return

        player.switch_playlist(found.display_name)
        # No message - control panel updates

        # Update control panel
        panel_manager = get_control_panel_manager(bot)
        if panel_manager:
            await panel_manager.update_panel(inter.guild.id, player)

        # Delete deferred response (silent mode)
        await inter.delete_original_response()


    @bot.slash_command(
        name='playlists',
        description=COMMAND_DESCRIPTIONS['playlists']
    )
    async def playlists_slash(inter: disnake.ApplicationCommandInteraction):
        """Show all available playlists."""
        await inter.response.defer(ephemeral=True)

        if not has_playlist_structure():
            await send_response(inter, MESSAGES['error_no_playlists'])
            return

        playlists = discover_playlists(inter.guild.id)

        if not playlists:
            await send_response(inter, MESSAGES['error_no_playlists'])
            return

        playlist_names = [f"{pl.display_name} ({pl.track_count} tracks)" for pl in playlists]
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
