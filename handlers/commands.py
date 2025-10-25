"""
All Bot Commands

Comprehensive command implementations using the refactored architecture.
All commands include spam protection and proper error handling.
"""

import asyncio
import logging
from disnake.ext import commands

logger = logging.getLogger(__name__)

# Import from our modules
from core.player import get_player, players
from core.playback import _play_current, _play_next, _play_first
from config.aliases import COMMAND_ALIASES
from config.timing import (
    PLAY_COOLDOWN,
    PAUSE_DEBOUNCE_WINDOW, PAUSE_COOLDOWN, PAUSE_SPAM_THRESHOLD,
    SKIP_DEBOUNCE_WINDOW, SKIP_COOLDOWN, SKIP_SPAM_THRESHOLD,
    STOP_DEBOUNCE_WINDOW, STOP_COOLDOWN, STOP_SPAM_THRESHOLD,
    PREVIOUS_DEBOUNCE_WINDOW, PREVIOUS_COOLDOWN, PREVIOUS_SPAM_THRESHOLD,
    SHUFFLE_DEBOUNCE_WINDOW, SHUFFLE_COOLDOWN, SHUFFLE_SPAM_THRESHOLD,
    UNSHUFFLE_DEBOUNCE_WINDOW, UNSHUFFLE_COOLDOWN, UNSHUFFLE_SPAM_THRESHOLD,
    QUEUE_DEBOUNCE_WINDOW, QUEUE_COOLDOWN, QUEUE_SPAM_THRESHOLD,
    LIBRARY_DEBOUNCE_WINDOW, LIBRARY_COOLDOWN, LIBRARY_SPAM_THRESHOLD,
    HELP_DEBOUNCE_WINDOW, HELP_COOLDOWN, HELP_SPAM_THRESHOLD,
    PLAY_JUMP_DEBOUNCE_WINDOW, PLAY_JUMP_COOLDOWN, PLAY_JUMP_SPAM_THRESHOLD,
    VOICE_CONNECT_DELAY, USER_COMMAND_TTL,
)
from config.features import (
    SHUFFLE_MODE_ENABLED,
    QUEUE_DISPLAY_ENABLED,
    LIBRARY_DISPLAY_ENABLED,
    QUEUE_DISPLAY_COUNT,
    LIBRARY_PAGE_SIZE,
)
from config.messages import MESSAGES, HELP_TEXT
from utils.discord_helpers import can_connect_to_channel, safe_disconnect, update_presence
from systems.voice_manager import PlaybackState


def setup(bot):
    """Register all commands with the bot."""

    # =========================================================================
    # PLAYBACK COMMANDS
    # =========================================================================

    @bot.command(name='play', aliases=COMMAND_ALIASES['play'])
    @commands.guild_only()
    async def play_command(ctx, track_number: int = None):
        """Play, resume, or jump to track."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        # Layer 0: User spam check
        if await player.spam_protector.check_user_spam(ctx.author.id, "play"):
            return

        # Validation: User must be in voice
        if not ctx.author.voice:
            if player.text_channel:
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

        # Set text channel if not set
        if not player.text_channel:
            player.set_text_channel(ctx.channel)

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
            except Exception as e:
                await player.cleanup_manager.send_with_ttl(
                    player.text_channel,
                    MESSAGES['error_cant_connect'].format(error=str(e)),
                    'error',
                    ctx.message
                )
                return

        # Handle track jumping
        if track_number is not None:
            await player.spam_protector.debounce_command(
                "play_jump",
                lambda: _execute_play_jump(ctx, track_number, bot),
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
                    MESSAGES['resume'].format(track=player.now_playing.display_name),
                    'resume',
                    ctx.message
                )
            return

        # Handle start playback
        if current_state == PlaybackState.IDLE:
            await player.spam_protector.queue_command(
                lambda: _play_first(ctx.guild.id, bot, players)
            )

    async def _execute_play_jump(ctx, track_number: int, bot):
        """Execute track jump command."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        track_index = track_number - 1
        if track_index < 0 or track_index >= len(player.library):
            await player.cleanup_manager.send_with_ttl(
                player.text_channel,
                MESSAGES['error_invalid_track'].format(
                    number=track_number,
                    total=len(player.library)
                ),
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
            player.voice_client.stop()
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
        """Execute shuffle command."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        player.shuffle_enabled = not player.shuffle_enabled

        msg_key = 'shuffle_on' if player.shuffle_enabled else 'shuffle_off'
        await player.cleanup_manager.send_with_ttl(
            player.text_channel or ctx.channel,
            MESSAGES[msg_key],
            'shuffle',
            ctx.message
        )

    @bot.command(name='unshuffle', aliases=COMMAND_ALIASES['unshuffle'])
    @commands.guild_only()
    async def unshuffle_command(ctx):
        """Disable shuffle mode."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if not SHUFFLE_MODE_ENABLED:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                MESSAGES['feature_shuffle_disabled'],
                'error',
                ctx.message
            )
            return

        if await player.spam_protector.check_user_spam(ctx.author.id, "unshuffle"):
            return

        if player.spam_protector.check_global_rate_limit():
            return

        await player.spam_protector.debounce_command(
            "unshuffle",
            lambda: _execute_unshuffle(ctx, bot),
            UNSHUFFLE_DEBOUNCE_WINDOW,
            UNSHUFFLE_COOLDOWN,
            UNSHUFFLE_SPAM_THRESHOLD,
            MESSAGES.get('spam_unshuffle')
        )

    async def _execute_unshuffle(ctx, bot):
        """Execute unshuffle command."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if not player.shuffle_enabled:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                MESSAGES['shuffle_already_off'],
                'shuffle',
                ctx.message
            )
            return

        player.shuffle_enabled = False
        await player.cleanup_manager.send_with_ttl(
            player.text_channel or ctx.channel,
            MESSAGES['unshuffle_organized'],
            'shuffle',
            ctx.message
        )

    # =========================================================================
    # QUEUE & LIBRARY COMMANDS
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
        """Execute queue command."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if not player.now_playing:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                MESSAGES['nothing_playing'],
                'error',
                ctx.message
            )
            return

        msg = f"{MESSAGES['queue_now_playing']} {player.now_playing.display_name}"

        if player.played:
            msg += f"\n{MESSAGES['queue_last_played']} {player.played[-1].display_name}"

        if player.upcoming:
            msg += f"\n\n{MESSAGES['queue_up_next']}\n"
            for i, track in enumerate(list(player.upcoming)[:QUEUE_DISPLAY_COUNT], 1):
                msg += f"{i}. {track.display_name}\n"

            if len(player.upcoming) <= QUEUE_DISPLAY_COUNT:
                msg += f"\n{MESSAGES['queue_will_loop']}"

        await player.cleanup_manager.send_with_ttl(
            player.text_channel or ctx.channel,
            msg,
            'queue',
            ctx.message
        )

    @bot.command(name='library', aliases=COMMAND_ALIASES['library'])
    @commands.guild_only()
    async def library_command(ctx, page: int = 1):
        """Show library."""
        player = await get_player(ctx.guild.id, bot, bot.user.id)

        if not LIBRARY_DISPLAY_ENABLED:
            await player.cleanup_manager.send_with_ttl(
                player.text_channel or ctx.channel,
                MESSAGES['feature_library_disabled'],
                'error',
                ctx.message
            )
            return

        if await player.spam_protector.check_user_spam(ctx.author.id, "library"):
            return

        if player.spam_protector.check_global_rate_limit():
            return

        await player.spam_protector.debounce_command(
            "library",
            lambda: _execute_library(ctx, page, bot),
            LIBRARY_DEBOUNCE_WINDOW,
            LIBRARY_COOLDOWN,
            LIBRARY_SPAM_THRESHOLD,
            None
        )

    async def _execute_library(ctx, page: int, bot):
        """Execute library command."""
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

        msg = MESSAGES['library_header'].format(page=page, total_pages=total_pages)
        for track in player.library[start:end]:
            msg += f"{track.library_index + 1}. {track.display_name}\n"

        if page < total_pages:
            msg += MESSAGES['library_next_page'].format(next_page=page + 1)

        if player.shuffle_enabled:
            msg += MESSAGES['library_shuffle_note']
            msg += f"\n{MESSAGES['library_shuffle_help']}"
        else:
            msg += f"\n{MESSAGES['library_normal_help']}"

        await player.cleanup_manager.send_with_ttl(
            player.text_channel or ctx.channel,
            msg,
            'library',
            ctx.message
        )

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

        if LIBRARY_DISPLAY_ENABLED:
            help_msg += f"\n{HELP_TEXT['queue_title']}\n"
            for cmd in HELP_TEXT['library_commands']:
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
