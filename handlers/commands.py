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
- Spam protection (4-layer system with guild isolation)
- Permission checks (VA-11 HALL-A themed decorator)
- Automatic message cleanup (TTL-based)
- Context-aware behavior (e.g., !play resumes or jumps)

Spam protection architecture:
- Layer 1: Per-User Spam Sessions (Discord drip-feed handling, filters first)
- Layer 2: Circuit Breaker (guild isolation, counts after Layer 1 filtering)
- Layer 3: Serial Queue (race condition prevention)
- Layer 4: Post-Execution Cooldowns

Layer 2 counts commands AFTER Layer 1 filtering to prevent single-user
spam from triggering guild-wide lockouts.

WARNING: USE "config/prefix/aliases.py" TO CHANGE/ADD/REMOVE COMMAND ALIASES,
NOT THIS FILE! Prefix is configurable in "config/prefix/features.py".
"""

import asyncio
import logging
import random
import disnake
from collections import deque
from typing import Optional
from disnake.ext import commands

logger = logging.getLogger(__name__)
user_logger = logging.getLogger('jill')

# Import from our modules
from core.playback import _play_current, _play_next, _play_first
from core.track import has_playlist_structure
from config import (
    COMMAND_ALIASES,
    PAUSE_COOLDOWN,
    SKIP_COOLDOWN,
    STOP_COOLDOWN,
    PREVIOUS_COOLDOWN,
    SHUFFLE_COOLDOWN,
    QUEUE_COOLDOWN,
    TRACKS_COOLDOWN,
    PLAYLISTS_COOLDOWN,
    HELP_COOLDOWN,
    PLAY_JUMP_COOLDOWN,
    VOICE_CONNECT_DELAY,
    USER_COMMAND_TTL,
    SHUFFLE_MODE_ENABLED,
    QUEUE_DISPLAY_ENABLED,
    LIBRARY_DISPLAY_ENABLED,
    PLAYLIST_SWITCHING_ENABLED,
    QUEUE_DISPLAY_COUNT,
    LIBRARY_PAGE_SIZE,
    PLAYLIST_PAGE_SIZE,
    COMMAND_PREFIX,
    MESSAGES,
    HELP_TEXT,
)
from utils.discord_helpers import can_connect_to_channel, safe_disconnect, update_presence, sanitize_for_format, get_guild_player, ensure_voice_connected, send_player_message, spam_protected_execute, format_guild_log, format_user_log, fuzzy_match
from utils.permission_checks import permission_check
from systems.voice_manager import PlaybackState


def setup(bot):
    """
    Register all commands with the bot.

    Command Structure:
    - Each command uses spam_protected_execute() for 4-layer spam protection
      (except play which has special voice/resume/jump logic)
    - Messages use send_player_message() for automatic sanitization & TTL cleanup
    - Player retrieval uses get_guild_player() helper
    - Voice validation uses ensure_voice_connected() helper

    See utils/discord_helpers.py for helper function documentation.
    """

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
        needs to happen before determining which action to take. Track jumping
        uses spam protection via spam_protected_execute().
        """
        player = await get_guild_player(ctx, bot)

        # Validation: User must be in voice
        if not ctx.author.voice:
            await send_player_message(player, ctx, 'error_not_in_voice', 'error')
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

        # Handle track jumping (by number or name) - uses spam protection
        if track_arg is not None:
            await spam_protected_execute(
                player, ctx, bot, "play_jump",
                lambda ctx, bot: _execute_play_jump(ctx, track_arg, bot),
                PLAY_JUMP_COOLDOWN
            )
            return

        # Handle resume - instant action, no spam protection needed
        current_state = player.voice_manager.get_playback_state()
        if current_state == PlaybackState.PAUSED:
            player.voice_client.resume()
            player.state = PlaybackState.PLAYING
            if player.now_playing:
                await send_player_message(player, ctx, 'resume', 'resume', track=player.now_playing.display_name)
            return

        # Handle start playback - queue directly (internal operation)
        if current_state == PlaybackState.IDLE:
            await player.spam_protector.queue_command(
                lambda: _play_first(player.guild_id, bot)
            )

    async def _execute_play_jump(ctx, track_arg: str, bot):
        """Execute track jump command (by number or name)."""
        player = await get_guild_player(ctx, bot)

        # Resolve identifier to track using fuzzy matching
        found = fuzzy_match(
            track_arg,
            player.library,
            lambda t: t.display_name,
            lambda t: t.library_index
        )

        if found is None:
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

        player.jump_to_track(found.library_index)
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
            player, ctx, bot, "pause", _execute_pause, PAUSE_COOLDOWN
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
            player, ctx, bot, "skip", _execute_skip, SKIP_COOLDOWN
        )

    async def _execute_skip(ctx, bot):
        """Execute skip command."""
        player = await get_guild_player(ctx, bot)

        if not await ensure_voice_connected(player, ctx, MESSAGES['skip_no_disc']):
            return

        state = player.voice_manager.get_playback_state()
        if state in [PlaybackState.PLAYING, PlaybackState.PAUSED]:
            # Queue next track - _play_current() handles stopping current track cleanly
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
            player, ctx, bot, "stop", _execute_stop, STOP_COOLDOWN
        )

    async def _execute_stop(ctx, bot):
        """Execute stop command."""
        player = await get_guild_player(ctx, bot)

        if player.voice_client:
            await send_player_message(player, ctx, 'stop', 'stop')
            await safe_disconnect(player.voice_client, force=True)
            player.reset_state()
            await update_presence(bot, None)

            # Log stop command
            user_logger.info(f"{format_guild_log(ctx.guild.id, bot)}－{format_user_log(ctx.author, bot)} stopped jill")

    @bot.command(name='previous', aliases=COMMAND_ALIASES['previous'])
    @permission_check()
    @commands.guild_only()
    async def previous_command(ctx):
        """Go to previous track."""
        player = await get_guild_player(ctx, bot)
        await spam_protected_execute(
            player, ctx, bot, "previous", _execute_previous, PREVIOUS_COOLDOWN
        )

    async def _execute_previous(ctx, bot):
        """Execute previous command."""
        player = await get_guild_player(ctx, bot)

        prev_track = player.go_to_previous()
        if prev_track:
            # Queue via spam_protector with priority for consistency with internal playback operations
            await player.spam_protector.queue_command(
                lambda: _play_current(player.guild_id, bot, going_backward=True),
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

        await spam_protected_execute(
            player, ctx, bot, "shuffle", _execute_shuffle, SHUFFLE_COOLDOWN
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

        await spam_protected_execute(
            player, ctx, bot, "queue", _execute_queue, QUEUE_COOLDOWN
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

        await spam_protected_execute(
            player, ctx, bot, "tracks",
            lambda ctx, bot: _execute_tracks_show(ctx, page, bot),
            TRACKS_COOLDOWN
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

        await spam_protected_execute(
            player, ctx, bot, "playlist",
            lambda ctx, bot: _execute_playlist_switch(ctx, name, bot),
            TRACKS_COOLDOWN
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
                logger.debug(f"{format_guild_log(ctx.guild.id, bot)}: voice state probe failed: {e}")

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
            # Use .get() with fallback for configs that don't define this key
            msg = MESSAGES.get('error_no_playlists', '❌ No playlists found. Music must be in subfolders.')
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                msg,
                'error',
                ctx.message
            )
            return

        await spam_protected_execute(
            player, ctx, bot, "playlists",
            lambda ctx, bot: _execute_playlists(ctx, page, bot),
            PLAYLISTS_COOLDOWN
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
            player, ctx, bot, "help", _execute_help, HELP_COOLDOWN
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

        # Show aliases command if any aliases are configured
        if any(aliases for aliases in COMMAND_ALIASES.values()):
            help_msg += '`!aliases` - Show command shortcuts\n'

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
            HELP_COOLDOWN
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
