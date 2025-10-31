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
Classic Mode Commands (Prefix Commands)

All 12 bot commands for Classic (!play) mode with:
- Spam protection (5-layer system)
- Permission checks (VA-11 HALL-A themed decorator)
- Automatic message cleanup (TTL-based)
- Context-aware behavior (e.g., !play resumes or jumps)

WARNING: USE "config/prefix/aliases.py" TO CHANGE/ADD/REMOVE COMMAND ALIASES,
NOT THIS FILE! Prefix is configurable in "config/prefix/features.py".
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
from core.playback import _play_current, _play_next, _play_first
from core.track import has_playlist_structure
from config import (
    COMMAND_ALIASES,
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
    VOICE_CONNECT_DELAY, USER_COMMAND_TTL, SKIP_SETTLE_DELAY,
    SHUFFLE_MODE_ENABLED,
    QUEUE_DISPLAY_ENABLED,
    LIBRARY_DISPLAY_ENABLED,
    PLAYLIST_SWITCHING_ENABLED,
    QUEUE_DISPLAY_COUNT,
    LIBRARY_PAGE_SIZE,
    PLAYLIST_PAGE_SIZE,
    COMMAND_PREFIX,
    MESSAGES, HELP_TEXT,
)
from utils.discord_helpers import can_connect_to_channel, safe_disconnect, update_presence, sanitize_for_format, get_guild_player, ensure_voice_connected, send_player_message, spam_protected_execute
from utils.permission_checks import permission_check
from systems.voice_manager import PlaybackState
from utils.context_managers import suppress_callbacks


def setup(bot):
    """
    Register all commands with the bot.

    Command Structure:
    - Each command uses spam_protected_execute() for 3-layer spam protection
      (except play which has special voice/resume/jump logic)
    - Messages use send_player_message() for automatic sanitization & TTL cleanup
    - Player retrieval uses get_guild_player() helper
    - Voice validation uses ensure_voice_connected() helper

    See utils/discord_helpers.py for helper function documentation.
    """

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

        # Exact match fast-path (case-insensitive)
        for t in player.library:
            if t.display_name.lower() == identifier_lower:
                return t.library_index

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
    @permission_check()
    @commands.guild_only()
    async def play_command(ctx, *, track_arg: str | None = None):
        """
        Play, resume, or jump to track by number or name.

        Note: This command does NOT use spam_protected_execute() because it has
        special logic (voice connection, resume detection, track jumping) that
        happens before spam protection layer 3 (debouncing). It manually applies
        layers 1 & 2, then conditionally applies layer 3 based on the action.
        """
        player = await get_guild_player(ctx, bot)

        # Layer 0: User spam check
        if await player.spam_protector.check_user_spam(ctx.author.id, "play"):
            return

        # Validation: User must be in voice
        if not ctx.author.voice:
            await send_player_message(player, ctx, 'error_not_in_voice', 'error')
            return

        # Layer 2: Global rate limit
        if player.spam_protector.check_global_rate_limit():
            return

        # Connect to voice if needed
        if not player.voice_client or not player.voice_client.is_connected():
            channel = ctx.author.voice.channel
            if not can_connect_to_channel(channel):
                await send_player_message(player, ctx, 'error_no_permission', 'error', channel=channel.name)
                return

            try:
                vc = await channel.connect(timeout=5.0, reconnect=True)
                player.set_voice_client(vc)
                await asyncio.sleep(VOICE_CONNECT_DELAY)
                # Update text channel ONLY after successful voice connection
                player.set_text_channel(ctx.channel)
            except (disnake.HTTPException, disnake.ClientException) as e:
                await send_player_message(player, ctx, 'error_cant_connect', 'error', error=str(e))
                return
            except Exception:
                logger.exception("Guild %s: Unexpected connect error", ctx.guild.id)
                await send_player_message(player, ctx, 'error_cant_connect', 'error', error="unexpected error")
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
                await send_player_message(player, ctx, 'resume', 'resume', track=player.now_playing.display_name)
            return

        # Handle start playback
        if current_state == PlaybackState.IDLE:
            await player.spam_protector.queue_command(
                lambda: _play_first(player.guild_id, bot)
            )

    async def _execute_play_jump(ctx, track_arg: str, bot):
        """Execute track jump command (by number or name)."""
        player = await get_guild_player(ctx, bot)

        # Resolve identifier to track index
        track_index = resolve_track_identifier(player, track_arg)

        if track_index is None:
            # Check if it was a number (out of range) or name (not found)
            try:
                track_number = int(track_arg)
                # Was a number but out of range
                await send_player_message(
                    player, ctx, 'error_invalid_track', 'error',
                    number=track_number, total=len(player.library)
                )
            except ValueError:
                # Was a name but not found
                await send_player_message(
                    player, ctx, 'error_track_not_found', 'error',
                    query=track_arg, prefix=COMMAND_PREFIX
                )
            return

        player.jump_to_track(track_index)
        await player.spam_protector.queue_command(
            lambda: _play_current(player.guild_id, bot)
        )

    @bot.command(name='pause', aliases=COMMAND_ALIASES['pause'])
    @permission_check()
    @commands.guild_only()
    async def pause_command(ctx):
        """Pause playback."""
        player = await get_guild_player(ctx, bot)
        await spam_protected_execute(
            player, ctx, bot, "pause", _execute_pause,
            PAUSE_DEBOUNCE_WINDOW, PAUSE_COOLDOWN, PAUSE_SPAM_THRESHOLD, 'spam_pause'
        )

    async def _execute_pause(ctx, bot):
        """Execute pause command."""
        player = await get_guild_player(ctx, bot)

        if not await ensure_voice_connected(player, ctx):
            return

        state = player.voice_manager.get_playback_state()
        if state == PlaybackState.PLAYING:
            player.voice_client.pause()
            player.state = PlaybackState.PAUSED
            await send_player_message(player, ctx, 'pause', 'pause')

    @bot.command(name='skip', aliases=COMMAND_ALIASES['skip'])
    @permission_check()
    @commands.guild_only()
    async def skip_command(ctx):
        """Skip to next track."""
        player = await get_guild_player(ctx, bot)
        await spam_protected_execute(
            player, ctx, bot, "skip", _execute_skip,
            SKIP_DEBOUNCE_WINDOW, SKIP_COOLDOWN, SKIP_SPAM_THRESHOLD, 'spam_skip'
        )

    async def _execute_skip(ctx, bot):
        """Execute skip command."""
        player = await get_guild_player(ctx, bot)

        if not await ensure_voice_connected(player, ctx, MESSAGES['skip_no_disc']):
            return

        state = player.voice_manager.get_playback_state()
        if state in [PlaybackState.PLAYING, PlaybackState.PAUSED]:
            if state == PlaybackState.PLAYING:
                player.voice_client.pause()
                await asyncio.sleep(SKIP_SETTLE_DELAY)
            with suppress_callbacks(player):
                player.voice_client.stop()
            await player.spam_protector.queue_command(
                lambda: _play_next(player.guild_id, bot)
            )
            await player.cleanup_manager.schedule_message_deletion(ctx.message, USER_COMMAND_TTL)

    @bot.command(name='stop', aliases=COMMAND_ALIASES['stop'])
    @permission_check()
    @commands.guild_only()
    async def stop_command(ctx):
        """Stop and disconnect."""
        player = await get_guild_player(ctx, bot)
        await spam_protected_execute(
            player, ctx, bot, "stop", _execute_stop,
            STOP_DEBOUNCE_WINDOW, STOP_COOLDOWN, STOP_SPAM_THRESHOLD, 'spam_stop'
        )

    async def _execute_stop(ctx, bot):
        """Execute stop command."""
        player = await get_guild_player(ctx, bot)

        if player.voice_client:
            await send_player_message(player, ctx, 'stop', 'stop')
            await safe_disconnect(player.voice_client, force=True)
            player.reset_state()
            await update_presence(bot, None)

    @bot.command(name='previous', aliases=COMMAND_ALIASES['previous'])
    @permission_check()
    @commands.guild_only()
    async def previous_command(ctx):
        """Go to previous track."""
        player = await get_guild_player(ctx, bot)
        await spam_protected_execute(
            player, ctx, bot, "previous", _execute_previous,
            PREVIOUS_DEBOUNCE_WINDOW, PREVIOUS_COOLDOWN, PREVIOUS_SPAM_THRESHOLD, 'spam_previous'
        )

    async def _execute_previous(ctx, bot):
        """Execute previous command."""
        player = await get_guild_player(ctx, bot)

        prev_track = player.go_to_previous()
        if prev_track:
            # Queue via spam_protector with priority for consistency with internal playback operations
            await player.spam_protector.queue_command(
                lambda: _play_current(player.guild_id, bot),
                priority=True
            )
        else:
            await send_player_message(player, ctx, 'previous_at_start', 'error')

    # =========================================================================
    # SHUFFLE COMMANDS
    # =========================================================================

    @bot.command(name='shuffle', aliases=COMMAND_ALIASES['shuffle'])
    @permission_check()
    @commands.guild_only()
    async def shuffle_command(ctx):
        """Toggle shuffle mode."""
        player = await get_guild_player(ctx, bot)

        if not SHUFFLE_MODE_ENABLED:
            await send_player_message(player, ctx, 'feature_shuffle_disabled', 'error')
            return

        await spam_protected_execute(
            player, ctx, bot, "shuffle", _execute_shuffle,
            SHUFFLE_DEBOUNCE_WINDOW, SHUFFLE_COOLDOWN, SHUFFLE_SPAM_THRESHOLD, 'spam_shuffle'
        )

    async def _execute_shuffle(ctx, bot):
        """Execute shuffle command (toggle)."""
        player = await get_guild_player(ctx, bot)

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
        await send_player_message(player, ctx, msg_key, 'shuffle')

    # =========================================================================
    # QUEUE & TRACKS COMMANDS
    # =========================================================================

    @bot.command(name='queue', aliases=COMMAND_ALIASES['queue'])
    @permission_check()
    @commands.guild_only()
    async def queue_command(ctx):
        """Show current queue."""
        player = await get_guild_player(ctx, bot)

        if not QUEUE_DISPLAY_ENABLED:
            await send_player_message(player, ctx, 'feature_queue_disabled', 'error')
            return

        await spam_protected_execute(
            player, ctx, bot, "queue", _execute_queue,
            QUEUE_DEBOUNCE_WINDOW, QUEUE_COOLDOWN, QUEUE_SPAM_THRESHOLD
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
        player = await get_guild_player(ctx, bot)

        if not player.now_playing:
            await send_player_message(player, ctx, 'nothing_playing', 'error')
            return

        msg = f"{MESSAGES['queue_header']}\n"
        
        if player.played:
            track = player.played[-1]
            msg += f"{MESSAGES['queue_last_played']} {sanitize_for_format(track.display_name)}\n"

        msg += f"{MESSAGES['queue_now_playing']} {sanitize_for_format(player.now_playing.display_name)}\n"

        if player.upcoming:
            msg += f"{MESSAGES['queue_up_next']}\n"
            for track in list(player.upcoming)[:QUEUE_DISPLAY_COUNT]:
                msg += f"            • {sanitize_for_format(track.display_name)}\n"

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
    @permission_check()
    @commands.guild_only()
    async def tracks_command(ctx, page: int = 1):
        """Show tracks in current playlist (paginated)."""
        player = await get_guild_player(ctx, bot)

        if not LIBRARY_DISPLAY_ENABLED:
            await send_player_message(player, ctx, 'feature_library_disabled', 'error')
            return

        await spam_protected_execute(
            player, ctx, bot, "tracks",
            lambda ctx, bot: _execute_tracks_show(ctx, page, bot),
            TRACKS_DEBOUNCE_WINDOW, TRACKS_COOLDOWN, TRACKS_SPAM_THRESHOLD
        )

    async def _execute_tracks_show(ctx, page: int, bot):
        """Execute tracks command - show tracks in current playlist."""
        player = await get_guild_player(ctx, bot)

        if not player.library:
            await send_player_message(player, ctx, 'error_no_tracks', 'error')
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

    # =========================================================================
    # PLAYLIST COMMANDS
    # =========================================================================

    @bot.command(name='playlist', aliases=COMMAND_ALIASES['playlist'])
    @permission_check()
    @commands.guild_only()
    async def playlist_command(ctx, *, name: str):
        """Switch to a different playlist."""
        player = await get_guild_player(ctx, bot)

        if not has_playlist_structure():
            await send_player_message(player, ctx, 'error_no_playlists', 'error')
            return

        if not PLAYLIST_SWITCHING_ENABLED:
            await send_player_message(player, ctx, 'feature_playlists_disabled', 'error')
            return

        await spam_protected_execute(
            player, ctx, bot, "playlist",
            lambda ctx, bot: _execute_playlist_switch(ctx, name, bot),
            TRACKS_DEBOUNCE_WINDOW, TRACKS_COOLDOWN, TRACKS_SPAM_THRESHOLD, 'spam_tracks'
        )

    async def _execute_playlist_switch(ctx, name: str, bot):
        """Execute playlist switch command."""
        player = await get_guild_player(ctx, bot)

        if not player.available_playlists:
            await send_player_message(player, ctx, 'error_no_playlists', 'error')
            return

        # Check if we were playing music before switch
        was_playing = False
        if player.voice_client and player.voice_client.is_connected():
            try:
                was_playing = player.voice_client.is_playing() or player.voice_client.is_paused()
            except (disnake.ClientException, RuntimeError) as e:
                logger.debug("Guild %s: voice state probe failed: %s", ctx.guild.id, e)

        # Switch playlist (synchronous operation - no await needed)
        success, message = player.switch_playlist(name, player.voice_client)

        if success:
            await send_player_message(player, ctx, 'playlist_switched', 'tracks', message=message)

            # Auto-play first track if music was playing before switch
            if was_playing and player.voice_client and player.voice_client.is_connected():
                await player.spam_protector.queue_command(
                    lambda: _play_first(player.guild_id, bot)
                )
        else:
            # Show error message from switch_playlist
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                f"❌ {sanitize_for_format(message)}",
                'error',
                ctx.message
            )

    @bot.command(name='playlists', aliases=COMMAND_ALIASES['playlists'])
    @permission_check()
    @commands.guild_only()
    async def playlists_command(ctx, page: int = 1):
        """Show available playlists."""
        player = await get_guild_player(ctx, bot)

        # Only enable if playlist structure exists
        if not has_playlist_structure():
            # Use .get() with fallback since this message may not exist in old configs
            msg = MESSAGES.get('error_no_playlists', '❌ No playlists found. Music must be in subfolders.')
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                msg,
                'error',
                ctx.message
            )
            return

        # Check if feature is enabled
        if not PLAYLIST_SWITCHING_ENABLED:
            await send_player_message(player, ctx, 'feature_playlists_disabled', 'error')
            return

        await spam_protected_execute(
            player, ctx, bot, "playlists",
            lambda ctx, bot: _execute_playlists(ctx, page, bot),
            PLAYLISTS_DEBOUNCE_WINDOW, PLAYLISTS_COOLDOWN, PLAYLISTS_SPAM_THRESHOLD, 'spam_playlists'
        )

    async def _execute_playlists(ctx, page: int, bot):
        """Execute playlists command."""
        player = await get_guild_player(ctx, bot)

        if not player.available_playlists:
            await send_player_message(player, ctx, 'error_no_playlists', 'error')
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
    @permission_check()
    @commands.guild_only()
    async def help_command(ctx):
        """Show help message."""
        player = await get_guild_player(ctx, bot)
        await spam_protected_execute(
            player, ctx, bot, "help",
            _execute_help,
            HELP_DEBOUNCE_WINDOW, HELP_COOLDOWN, HELP_SPAM_THRESHOLD
        )

    async def _execute_help(ctx, bot):
        """Execute help command."""
        player = await get_guild_player(ctx, bot)

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

    # =========================================================================
    # ALIASES COMMAND
    # =========================================================================

    @bot.command(name='aliases', aliases=COMMAND_ALIASES['aliases'])
    @permission_check()
    @commands.guild_only()
    async def aliases_command(ctx, *, command_name: str | None = None):
        """Show command aliases."""
        player = await get_guild_player(ctx, bot)
        await spam_protected_execute(
            player, ctx, bot, "aliases",
            lambda ctx, bot: _execute_aliases(ctx, command_name, bot),
            HELP_DEBOUNCE_WINDOW, HELP_COOLDOWN, HELP_SPAM_THRESHOLD
        )

    async def _execute_aliases(ctx, command_name: str | None, bot):
        """Execute aliases command."""
        player = await get_guild_player(ctx, bot)

        # Show specific command aliases
        if command_name:
            # Normalize input (remove ! prefix if present)
            cmd = command_name.lstrip('!')

            if cmd not in COMMAND_ALIASES:
                await send_player_message(
                    player, ctx, 'aliases_unknown', 'error',
                    command=f'{COMMAND_PREFIX}{cmd}', prefix=COMMAND_PREFIX
                )
                return

            aliases = COMMAND_ALIASES[cmd]
            if aliases:
                alias_str = ', '.join(f'`{COMMAND_PREFIX}{a}`' for a in aliases)
                await send_player_message(
                    player, ctx, 'aliases_for', 'help',
                    command=f'{COMMAND_PREFIX}{cmd}', aliases=alias_str
                )
            else:
                await send_player_message(
                    player, ctx, 'aliases_none', 'help',
                    command=f'{COMMAND_PREFIX}{cmd}'
                )
            return

        # Show all aliases (organized by command, filtered by enabled features)
        msg = MESSAGES['aliases_header']

        # Playback commands (always enabled)
        for cmd_name in ['play', 'pause', 'skip', 'stop', 'previous']:
            if COMMAND_ALIASES[cmd_name]:
                alias_str = ', '.join(f'`{COMMAND_PREFIX}{a}`' for a in COMMAND_ALIASES[cmd_name])
                msg += f"`{COMMAND_PREFIX}{cmd_name}` → {alias_str}\n"

        # Queue command (if enabled)
        if QUEUE_DISPLAY_ENABLED and COMMAND_ALIASES['queue']:
            alias_str = ', '.join(f'`{COMMAND_PREFIX}{a}`' for a in COMMAND_ALIASES['queue'])
            msg += f"`{COMMAND_PREFIX}queue` → {alias_str}\n"

        # Tracks command (if enabled)
        if LIBRARY_DISPLAY_ENABLED and COMMAND_ALIASES['tracks']:
            alias_str = ', '.join(f'`{COMMAND_PREFIX}{a}`' for a in COMMAND_ALIASES['tracks'])
            msg += f"`{COMMAND_PREFIX}tracks` → {alias_str}\n"

        # Playlists command (if playlist structure exists and enabled)
        if has_playlist_structure() and PLAYLIST_SWITCHING_ENABLED and COMMAND_ALIASES['playlists']:
            alias_str = ', '.join(f'`{COMMAND_PREFIX}{a}`' for a in COMMAND_ALIASES['playlists'])
            msg += f"`{COMMAND_PREFIX}playlists` → {alias_str}\n"

        # Shuffle command (if enabled)
        if SHUFFLE_MODE_ENABLED and COMMAND_ALIASES['shuffle']:
            alias_str = ', '.join(f'`{COMMAND_PREFIX}{a}`' for a in COMMAND_ALIASES['shuffle'])
            msg += f"`{COMMAND_PREFIX}shuffle` → {alias_str}\n"

        # Help command (always shown)
        if COMMAND_ALIASES['help']:
            alias_str = ', '.join(f'`{COMMAND_PREFIX}{a}`' for a in COMMAND_ALIASES['help'])
            msg += f"`{COMMAND_PREFIX}help` → {alias_str}\n"

        msg += MESSAGES['aliases_footer']

        await player.cleanup_manager.send_with_ttl(
            player.text_channel or ctx.channel,
            msg,
            'help',
            ctx.message
        )
