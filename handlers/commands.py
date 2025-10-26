# Copyright (C) 2025 grodz-bar
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
All Bot Commands

Comprehensive command implementations using the refactored architecture.
All commands include spam protection and proper error handling.

WARNING: USE THE "aliases.py" INSIDE THE "config" FOLDER TO CHANGE/ADD/REMOVE YOUR OWN
COMMAND ALIASES, NOT THIS FILE!
"""

import asyncio
import logging
import random
import disnake
from collections import deque
from difflib import SequenceMatcher
from typing import Optional
from disnake.ext import commands

logger = logging.getLogger(__name__)

# Import from our modules
from core.player import get_player, players
from core.playback import _play_current, _play_next, _play_first
from core.track import has_playlist_structure
from config.aliases import COMMAND_ALIASES
from config.timing import (
    PAUSE_DEBOUNCE_WINDOW, PAUSE_COOLDOWN, PAUSE_SPAM_THRESHOLD,
    SKIP_DEBOUNCE_WINDOW, SKIP_COOLDOWN, SKIP_SPAM_THRESHOLD,
    STOP_DEBOUNCE_WINDOW, STOP_COOLDOWN, STOP_SPAM_THRESHOLD,
    PREVIOUS_DEBOUNCE_WINDOW, PREVIOUS_COOLDOWN, PREVIOUS_SPAM_THRESHOLD,
    SHUFFLE_DEBOUNCE_WINDOW, SHUFFLE_COOLDOWN, SHUFFLE_SPAM_THRESHOLD,
    QUEUE_DEBOUNCE_WINDOW, QUEUE_COOLDOWN, QUEUE_SPAM_THRESHOLD,
    TRACKS_DEBOUNCE_WINDOW, TRACKS_COOLDOWN, TRACKS_SPAM_THRESHOLD,
    PLAYLISTS_DEBOUNCE_WINDOW, PLAYLISTS_COOLDOWN, PLAYLISTS_SPAM_THRESHOLD,
    HELP_DEBOUNCE_WINDOW, HELP_COOLDOWN, HELP_SPAM_THRESHOLD,
    PLAY_JUMP_DEBOUNCE_WINDOW, PLAY_JUMP_COOLDOWN, PLAY_JUMP_SPAM_THRESHOLD,
    VOICE_CONNECT_DELAY, USER_COMMAND_TTL,
)
from config.features import (
    SHUFFLE_MODE_ENABLED,
    QUEUE_DISPLAY_ENABLED,
    LIBRARY_DISPLAY_ENABLED,
    PLAYLIST_SWITCHING_ENABLED,
    QUEUE_DISPLAY_COUNT,
    LIBRARY_PAGE_SIZE,
    PLAYLIST_PAGE_SIZE,
)
from config.messages import MESSAGES, HELP_TEXT
from utils.discord_helpers import can_connect_to_channel, safe_disconnect, update_presence, sanitize_for_format
from systems.voice_manager import PlaybackState
from utils.context_managers import suppress_callbacks


def setup(bot):
    """Register all commands with the bot."""

    # =========================================================================
    # HELPER FUNCTIONS
    # =========================================================================

    def resolve_track_identifier(player, identifier: str) -> Optional[int]:
        """
        Resolve track identifier (number or name) to track index using fuzzy matching.

        Args:
            player: MusicPlayer instance
            identifier: Either a number (1-based) or name substring

        Returns:
            Track index (0-based) or None if not found

        Matching Algorithm:
            1. Try parsing as number (exact match)
            2. Find all tracks containing the search term (case-insensitive)
            3. Score each match by similarity ratio
            4. Return best match (highest score, then first in library order)

        Examples:
            resolve_track_identifier(player, "5") → 4 (track #5)
            resolve_track_identifier(player, "dawn") → index of "Dawn of" (best match)
            resolve_track_identifier(player, "dawn of men") → index of "Dawn of Men 1" (first of equal matches)
        """
        # Try parsing as number (1-based index)
        try:
            track_number = int(identifier)
            track_index = track_number - 1
            if 0 <= track_index < len(player.library):
                return track_index
            else:
                return None  # Out of range
        except ValueError:
            pass

        # Fuzzy name matching with similarity scoring
        identifier_lower = identifier.lower()
        matches = []

        # Find all tracks that contain the search term
        for track in player.library:
            track_name_lower = track.display_name.lower()
            if identifier_lower in track_name_lower:
                # Calculate similarity ratio (0.0 to 1.0)
                similarity = SequenceMatcher(None, identifier_lower, track_name_lower).ratio()
                matches.append((similarity, track.library_index, track))

        if not matches:
            return None

        # Sort by: similarity (descending), then library_index (ascending)
        # This ensures: best match first, ties broken by playlist order
        matches.sort(key=lambda x: (-x[0], x[1]))

        # Return the best match
        best_match = matches[0]
        logger.debug(
            f"Guild {player.guild_id}: Fuzzy match '{identifier}' → '{best_match[2].display_name}' "
            f"(similarity: {best_match[0]:.2f})"
        )
        return best_match[1]

    # =========================================================================
    # PLAYBACK COMMANDS
    # =========================================================================

    @bot.command(name='play', aliases=COMMAND_ALIASES['play'])
    @commands.guild_only()
    async def play_command(ctx, *, track_arg: str = None):
        """Play, resume, or jump to track by number or name."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        # Layer 0: User spam check
        if await player.spam_protector.check_user_spam(ctx.author.id, "play"):
            return

        # Set text channel early so validation errors can be sent
        if not player.text_channel:
            player.set_text_channel(ctx.channel)

        # Validation: User must be in voice
        if not ctx.author.voice:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel,
                MESSAGES['error_not_in_voice'],
                'error',
                ctx.message
            )
            return

        # Layer 2: Global rate limit
        if player.spam_protector.check_global_rate_limit():
            return

        # Connect to voice if needed
        if not player.voice_client or not player.voice_client.is_connected():
            channel = ctx.author.voice.channel
            if not can_connect_to_channel(channel):
                await player.cleanup_manager.send_with_ttl(
                    player.text_channel,
                    MESSAGES['error_no_permission'].format(channel=channel.name),
                    'error',
                    ctx.message
                )
                return

            try:
                vc = await channel.connect()
                player.set_voice_client(vc)
                await asyncio.sleep(VOICE_CONNECT_DELAY)
            except (disnake.HTTPException, disnake.ClientException) as e:
                await player.cleanup_manager.send_with_ttl(
                    player.text_channel,
                    MESSAGES['error_cant_connect'].format(error=str(e)),
                    'error',
                    ctx.message
                )
                return
            except Exception as e:
                logger.exception("Guild %s: Unexpected connect error", ctx.guild.id)
                await player.cleanup_manager.send_with_ttl(
                    player.text_channel,
                    MESSAGES['error_cant_connect'].format(error="unexpected error"),
                    'error',
                    ctx.message
                )
                return

        # Handle track jumping (by number or name)
        if track_arg is not None:
            await player.spam_protector.debounce_command(
                "play_jump",
                lambda: _execute_play_jump(ctx, track_arg, bot),
                PLAY_JUMP_DEBOUNCE_WINDOW,
                PLAY_JUMP_COOLDOWN,
                PLAY_JUMP_SPAM_THRESHOLD,
                MESSAGES.get('spam_play_jump')
            )
            return

        # Handle resume
        current_state = player.voice_manager.get_playback_state()
        if current_state == PlaybackState.PAUSED:
            player.voice_client.resume()
            player.state = PlaybackState.PLAYING
            if player.now_playing:
                await player.cleanup_manager.send_with_ttl(
                    player.text_channel,
                    MESSAGES['resume'].format(track=sanitize_for_format(player.now_playing.display_name)),
                    'resume',
                    ctx.message
                )
            return

        # Handle start playback
        if current_state == PlaybackState.IDLE:
            await player.spam_protector.queue_command(
                lambda: _play_first(ctx.guild.id, bot, players)
            )

    async def _execute_play_jump(ctx, track_arg: str, bot):
        """Execute track jump command (by number or name)."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        # Resolve identifier to track index
        track_index = resolve_track_identifier(player, track_arg)

        if track_index is None:
            # Check if it was a number (out of range) or name (not found)
            try:
                track_number = int(track_arg)
                # Was a number but out of range
                await player.cleanup_manager.send_with_ttl(
                    player.text_channel,
                    MESSAGES['error_invalid_track'].format(
                        number=track_number,
                        total=len(player.library)
                    ),
                    'error',
                    ctx.message
                )
            except ValueError:
                # Was a name but not found
                await player.cleanup_manager.send_with_ttl(
                    player.text_channel,
                    MESSAGES['error_track_not_found'].format(query=sanitize_for_format(track_arg)),
                    'error',
                    ctx.message
                )
            return

        player.jump_to_track(track_index)
        await player.spam_protector.queue_command(
            lambda: _play_current(ctx.guild.id, bot, players)
        )

    @bot.command(name='pause', aliases=COMMAND_ALIASES['pause'])
    @commands.guild_only()
    async def pause_command(ctx):
        """Pause playback."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if await player.spam_protector.check_user_spam(ctx.author.id, "pause"):
            return

        if player.spam_protector.check_global_rate_limit():
            return

        await player.spam_protector.debounce_command(
            "pause",
            lambda: _execute_pause(ctx, bot),
            PAUSE_DEBOUNCE_WINDOW,
            PAUSE_COOLDOWN,
            PAUSE_SPAM_THRESHOLD,
            MESSAGES.get('spam_pause')
        )

    async def _execute_pause(ctx, bot):
        """Execute pause command."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if not player.voice_client or not player.voice_client.is_connected():
            return

        state = player.voice_manager.get_playback_state()
        if state == PlaybackState.PLAYING:
            player.voice_client.pause()
            player.state = PlaybackState.PAUSED
            await player.cleanup_manager.send_with_ttl(
                player.text_channel,
                MESSAGES['pause'],
                'pause',
                ctx.message
            )

    @bot.command(name='skip', aliases=COMMAND_ALIASES['skip'])
    @commands.guild_only()
    async def skip_command(ctx):
        """Skip to next track."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if await player.spam_protector.check_user_spam(ctx.author.id, "skip"):
            return

        if player.spam_protector.check_global_rate_limit():
            return

        await player.spam_protector.debounce_command(
            "skip",
            lambda: _execute_skip(ctx, bot),
            SKIP_DEBOUNCE_WINDOW,
            SKIP_COOLDOWN,
            SKIP_SPAM_THRESHOLD,
            MESSAGES.get('spam_skip')
        )

    async def _execute_skip(ctx, bot):
        """Execute skip command."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if not player.voice_client or not player.voice_client.is_connected():
            await player.cleanup_manager.send_with_ttl(
                player.text_channel,
                MESSAGES['skip_no_disc'],
                'error'
            )
            return

        state = player.voice_manager.get_playback_state()
        if state in [PlaybackState.PLAYING, PlaybackState.PAUSED]:
            if state == PlaybackState.PLAYING:
                player.voice_client.pause()
                await asyncio.sleep(0.02)
            with suppress_callbacks(player):
                player.voice_client.stop()
            await player.spam_protector.queue_command(
                lambda: _play_next(ctx.guild.id, bot, players)
            )
            await player.cleanup_manager.schedule_message_deletion(ctx.message, USER_COMMAND_TTL)

    @bot.command(name='stop', aliases=COMMAND_ALIASES['stop'])
    @commands.guild_only()
    async def stop_command(ctx):
        """Stop and disconnect."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if await player.spam_protector.check_user_spam(ctx.author.id, "stop"):
            return

        if player.spam_protector.check_global_rate_limit():
            return

        await player.spam_protector.debounce_command(
            "stop",
            lambda: _execute_stop(ctx, bot),
            STOP_DEBOUNCE_WINDOW,
            STOP_COOLDOWN,
            STOP_SPAM_THRESHOLD,
            MESSAGES.get('spam_stop')
        )

    async def _execute_stop(ctx, bot):
        """Execute stop command."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if player.voice_client:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel,
                MESSAGES['stop'],
                'stop',
                ctx.message
            )
            await safe_disconnect(player.voice_client, force=True)
            player.reset_state()
            await update_presence(bot, None)

    @bot.command(name='previous', aliases=COMMAND_ALIASES['previous'])
    @commands.guild_only()
    async def previous_command(ctx):
        """Go to previous track."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if await player.spam_protector.check_user_spam(ctx.author.id, "previous"):
            return

        if player.spam_protector.check_global_rate_limit():
            return

        await player.spam_protector.debounce_command(
            "previous",
            lambda: _execute_previous(ctx, bot),
            PREVIOUS_DEBOUNCE_WINDOW,
            PREVIOUS_COOLDOWN,
            PREVIOUS_SPAM_THRESHOLD,
            MESSAGES.get('spam_previous')
        )

    async def _execute_previous(ctx, bot):
        """Execute previous command."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        prev_track = player.go_to_previous()
        if prev_track:
            await _play_current(ctx.guild.id, bot, players)
        else:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel,
                MESSAGES['previous_at_start'],
                'error',
                ctx.message
            )

    # =========================================================================
    # SHUFFLE COMMANDS
    # =========================================================================

    @bot.command(name='shuffle', aliases=COMMAND_ALIASES['shuffle'])
    @commands.guild_only()
    async def shuffle_command(ctx):
        """Toggle shuffle mode."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if not SHUFFLE_MODE_ENABLED:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                MESSAGES['feature_shuffle_disabled'],
                'error',
                ctx.message
            )
            return

        if await player.spam_protector.check_user_spam(ctx.author.id, "shuffle"):
            return

        if player.spam_protector.check_global_rate_limit():
            return

        await player.spam_protector.debounce_command(
            "shuffle",
            lambda: _execute_shuffle(ctx, bot),
            SHUFFLE_DEBOUNCE_WINDOW,
            SHUFFLE_COOLDOWN,
            SHUFFLE_SPAM_THRESHOLD,
            MESSAGES.get('spam_shuffle')
        )

    async def _execute_shuffle(ctx, bot):
        """Execute shuffle command (toggle)."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        # Toggle shuffle mode
        player.shuffle_enabled = not player.shuffle_enabled

        # Apply shuffle/unshuffle to current queue immediately
        if player.shuffle_enabled:
            # Shuffle the upcoming queue
            if player.upcoming:
                upcoming_list = list(player.upcoming)
                random.shuffle(upcoming_list)
                player.upcoming = deque(upcoming_list)
        else:
            # Un-shuffle: sort upcoming queue back to library order
            if player.upcoming:
                upcoming_list = list(player.upcoming)
                upcoming_list.sort(key=lambda track: track.library_index)
                player.upcoming = deque(upcoming_list)

        msg_key = 'shuffle_on' if player.shuffle_enabled else 'shuffle_off'
        await player.cleanup_manager.send_with_ttl(
            player.text_channel or ctx.channel,
            MESSAGES[msg_key],
            'shuffle',
            ctx.message
        )

    # =========================================================================
    # QUEUE & TRACKS COMMANDS
    # =========================================================================

    @bot.command(name='queue', aliases=COMMAND_ALIASES['queue'])
    @commands.guild_only()
    async def queue_command(ctx):
        """Show current queue."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if not QUEUE_DISPLAY_ENABLED:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                MESSAGES['feature_queue_disabled'],
                'error',
                ctx.message
            )
            return

        if await player.spam_protector.check_user_spam(ctx.author.id, "queue"):
            return

        if player.spam_protector.check_global_rate_limit():
            return

        await player.spam_protector.debounce_command(
            "queue",
            lambda: _execute_queue(ctx, bot),
            QUEUE_DEBOUNCE_WINDOW,
            QUEUE_COOLDOWN,
            QUEUE_SPAM_THRESHOLD,
            None
        )

    async def _execute_queue(ctx, bot):
        """
        Execute queue command.
        
        PARTIAL QUEUE MESSAGE CUSTOMIZATION:
        - Upcoming tracks indentation: Modify line ~549 below, the f-string with spaces before bullet that looks like this:
        - msg += f"            • {track.display_name}\n"     <- (Example, real one is below, just look for it)
        - You can change what's inside the quotes, but don't touch "{track.display_name}\n"
        - WARNING: BE CAREFUL, changing the wrong thing in here will break things. Maybe backup commands.py before changing anything?
        """
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if not player.now_playing:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                MESSAGES['nothing_playing'],
                'error',
                ctx.message
            )
            return

        msg = f"{MESSAGES['queue_header']}\n"
        
        if player.played:
            track = player.played[-1]
            msg += f"{MESSAGES['queue_last_played']} {track.display_name}\n"
        
        msg += f"{MESSAGES['queue_now_playing']} {player.now_playing.display_name}\n"

        if player.upcoming:
            msg += f"{MESSAGES['queue_up_next']}\n"
            for track in list(player.upcoming)[:QUEUE_DISPLAY_COUNT]:
                msg += f"            • {track.display_name}\n"

        msg += f"{MESSAGES['queue_footer']}"
        
        if player.upcoming and len(player.upcoming) <= QUEUE_DISPLAY_COUNT:
            msg += f"\n\n{MESSAGES['queue_will_loop']}"

        await player.cleanup_manager.send_with_ttl(
            player.text_channel or ctx.channel,
            msg,
            'queue',
            ctx.message
        )

    @bot.command(name='tracks', aliases=COMMAND_ALIASES['tracks'])
    @commands.guild_only()
    async def tracks_command(ctx, *, identifier: str = None):
        """Show tracks in current playlist OR switch to different playlist."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if await player.spam_protector.check_user_spam(ctx.author.id, "tracks"):
            return

        if player.spam_protector.check_global_rate_limit():
            return

        # If identifier provided, try to switch playlist (if playlists exist and feature enabled)
        if identifier and has_playlist_structure() and PLAYLIST_SWITCHING_ENABLED:
            await player.spam_protector.debounce_command(
                "tracks",
                lambda: _execute_tracks_switch(ctx, identifier, bot),
                TRACKS_DEBOUNCE_WINDOW,
                TRACKS_COOLDOWN,
                TRACKS_SPAM_THRESHOLD,
                MESSAGES.get('spam_tracks')
            )
        else:
            # No identifier OR no playlist structure = show tracks
            # Try parsing identifier as page number
            page = 1
            if identifier:
                try:
                    page = int(identifier)
                except ValueError:
                    pass  # Not a number, just show page 1

            if not LIBRARY_DISPLAY_ENABLED:
                await player.cleanup_manager.send_with_ttl(
                    player.text_channel or ctx.channel,
                    MESSAGES['feature_library_disabled'],
                    'error',
                    ctx.message
                )
                return

            await player.spam_protector.debounce_command(
                "tracks",
                lambda: _execute_tracks_show(ctx, page, bot),
                TRACKS_DEBOUNCE_WINDOW,
                TRACKS_COOLDOWN,
                TRACKS_SPAM_THRESHOLD,
                None
            )

    async def _execute_tracks_show(ctx, page: int, bot):
        """Execute tracks command - show tracks in current playlist."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if not player.library:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                MESSAGES['error_no_tracks'],
                'error',
                ctx.message
            )
            return

        page_size = LIBRARY_PAGE_SIZE
        total_pages = (len(player.library) + page_size - 1) // page_size
        page = max(1, min(page, total_pages))

        start = (page - 1) * page_size
        end = min(start + page_size, len(player.library))

        msg = MESSAGES['tracks_header'].format(page=page, total_pages=total_pages)
        for track in player.library[start:end]:
            msg += f"{track.library_index + 1}. {sanitize_for_format(track.display_name)}\n"

        if page < total_pages:
            msg += MESSAGES['tracks_next_page'].format(next_page=page + 1)

        if player.shuffle_enabled:
            msg += MESSAGES['tracks_shuffle_note']
            msg += f"\n{MESSAGES['tracks_shuffle_help']}"
        else:
            msg += f"\n{MESSAGES['tracks_normal_help']}"

        await player.cleanup_manager.send_with_ttl(
            player.text_channel or ctx.channel,
            msg,
            'tracks',
            ctx.message
        )

    async def _execute_tracks_switch(ctx, identifier: str, bot):
        """Execute tracks command - switch to different playlist."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if not player.available_playlists:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                MESSAGES['error_no_playlists'],
                'error',
                ctx.message
            )
            return

        # Check if we were playing music before switch
        was_playing = False
        if player.voice_client and player.voice_client.is_connected():
            try:
                was_playing = player.voice_client.is_playing() or player.voice_client.is_paused()
            except Exception as e:
                logger.debug("Guild %s: voice state probe failed: %s", ctx.guild.id, e)

        # Switch playlist
        success, message = await player.switch_playlist(identifier, player.voice_client)

        if success:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                MESSAGES['playlist_switched'].format(message=sanitize_for_format(message)),
                'tracks',
                ctx.message
            )

            # Auto-play first track if music was playing before switch
            if was_playing and player.voice_client and player.voice_client.is_connected():
                await player.spam_protector.queue_command(
                    lambda: _play_first(ctx.guild.id, bot, players)
                )
        else:
            # Check error type
            if "not found" in message.lower():
                await player.cleanup_manager.send_with_ttl(
                    player.text_channel or ctx.channel,
                    MESSAGES['error_playlist_not_found'].format(query=sanitize_for_format(identifier)),
                    'error',
                    ctx.message
                )
            elif "already using" in message.lower():
                await player.cleanup_manager.send_with_ttl(
                    player.text_channel or ctx.channel,
                    MESSAGES['error_playlist_already_active'],
                    'error',
                    ctx.message
                )
            else:
                await player.cleanup_manager.send_with_ttl(
                    player.text_channel or ctx.channel,
                    f"❌ {message}",
                    'error',
                    ctx.message
                )

    # =========================================================================
    # PLAYLIST COMMANDS
    # =========================================================================

    @bot.command(name='playlists', aliases=COMMAND_ALIASES['playlists'])
    @commands.guild_only()
    async def playlists_command(ctx, page: int = 1):
        """Show available playlists."""
        # Only enable if playlist structure exists
        if not has_playlist_structure():
            return

        player = await get_player(ctx.guild.id, bot, bot.user.id)

        # Check if feature is enabled
        if not PLAYLIST_SWITCHING_ENABLED:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                MESSAGES['feature_playlists_disabled'],
                'error',
                ctx.message
            )
            return

        if await player.spam_protector.check_user_spam(ctx.author.id, "playlists"):
            return

        if player.spam_protector.check_global_rate_limit():
            return

        await player.spam_protector.debounce_command(
            "playlists",
            lambda: _execute_playlists(ctx, page, bot),
            PLAYLISTS_DEBOUNCE_WINDOW,
            PLAYLISTS_COOLDOWN,
            PLAYLISTS_SPAM_THRESHOLD,
            MESSAGES.get('spam_playlists')
        )

    async def _execute_playlists(ctx, page: int, bot):
        """Execute playlists command."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if not player.available_playlists:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                MESSAGES['error_no_playlists'],
                'error',
                ctx.message
            )
            return

        page_size = PLAYLIST_PAGE_SIZE
        total_pages = (len(player.available_playlists) + page_size - 1) // page_size
        page = max(1, min(page, total_pages))

        start = (page - 1) * page_size
        end = min(start + page_size, len(player.available_playlists))

        msg = MESSAGES['playlists_header'].format(page=page, total_pages=total_pages)
        for idx, playlist in enumerate(player.available_playlists[start:end], start + 1):
            # Mark current playlist
            current_marker = " ← Current" if player.current_playlist and playlist.playlist_id == player.current_playlist.playlist_id else ""
            msg += f"`{idx:02d}.` {sanitize_for_format(playlist.display_name)} ({playlist.track_count} tracks){current_marker}\n"

        if page < total_pages:
            msg += MESSAGES['playlists_next_page'].format(next_page=page + 1)

        msg += MESSAGES['playlists_help']

        await player.cleanup_manager.send_with_ttl(
            player.text_channel or ctx.channel,
            msg,
            'playlists',
            ctx.message
        )

    # switchplaylist command merged into tracks command above

    # =========================================================================
    # HELP COMMAND
    # =========================================================================

    @bot.command(name='help', aliases=COMMAND_ALIASES['help'])
    @commands.guild_only()
    async def help_command(ctx):
        """Show help message."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if await player.spam_protector.check_user_spam(ctx.author.id, "help"):
            return

        if player.spam_protector.check_global_rate_limit():
            return

        await player.spam_protector.debounce_command(
            "help",
            lambda: _execute_help(ctx, bot),
            HELP_DEBOUNCE_WINDOW,
            HELP_COOLDOWN,
            HELP_SPAM_THRESHOLD,
            None
        )

    async def _execute_help(ctx, bot):
        """Execute help command."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        help_msg = f"{HELP_TEXT['header']}\n\n{HELP_TEXT['volume_note']}\n\n"

        help_msg += f"{HELP_TEXT['playback_title']}\n"
        for cmd in HELP_TEXT['playback_commands']:
            help_msg += f"{cmd}\n"

        if QUEUE_DISPLAY_ENABLED:
            help_msg += f"\n{HELP_TEXT['queue_title']}\n"
            for cmd in HELP_TEXT['queue_commands']:
                help_msg += f"{cmd}\n"

        # Show playlist commands only if playlist structure exists and features enabled
        if has_playlist_structure() and PLAYLIST_SWITCHING_ENABLED and LIBRARY_DISPLAY_ENABLED:
            help_msg += f"\n{HELP_TEXT['playlist_title']}\n"
            for cmd in HELP_TEXT['playlist_commands']:
                help_msg += f"{cmd}\n"

        if SHUFFLE_MODE_ENABLED:
            help_msg += f"\n{HELP_TEXT['shuffle_title']}\n"
            for cmd in HELP_TEXT['shuffle_commands']:
                help_msg += f"{cmd}\n"

        help_msg += f"\n{HELP_TEXT['info_title']}\n"
        for cmd in HELP_TEXT['info_commands']:
            help_msg += f"{cmd}\n"

        help_msg += f"\n{HELP_TEXT['footer']}"

        await player.cleanup_manager.send_with_ttl(
            player.text_channel or ctx.channel,
            help_msg,
            'help',
            ctx.message
        )
