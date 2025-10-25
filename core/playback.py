"""
Playback Functions

Core music playback functionality including track playing, callbacks, and queue advancement.
"""

import asyncio
import time
import logging

logger = logging.getLogger(__name__)

# Import from config
from config.timing import (
    VOICE_SETTLE_DELAY,
    MESSAGE_SETTLE_DELAY,
    CALLBACK_MIN_INTERVAL,
    VOICE_CONNECTION_MAX_WAIT,
    VOICE_CONNECTION_CHECK_INTERVAL,
    MESSAGE_TTL,
)
from config.features import (
    SMART_MESSAGE_MANAGEMENT,
    TTL_CLEANUP_ENABLED,
)
from config.messages import MESSAGES, DRINK_EMOJIS
from systems.voice_manager import PlaybackState
from utils.discord_helpers import (
    make_audio_source,
    safe_voice_state_change,
    update_presence,
)


async def _play_current(guild_id: int, bot, players: dict) -> None:
    """
    Play the current track (whatever is in now_playing).

    This function does NOT advance the queue - it just plays what's set.
    Queue advancement happens in _play_next().

    Args:
        guild_id: Guild to play in
        bot: Bot instance
        players: Dict of guild_id → MusicPlayer

    Side effects:
        - Starts playback via voice_client.play()
        - Sets callback for when track finishes
        - Updates bot presence status
        - Sends "Now serving" message
        - Updates watchdog tracking
    """
    from core.player import get_player  # Import here to avoid circular
    player = await get_player(guild_id, bot, bot.user.id)

    # Validate voice client
    if not player.voice_client or not player.voice_client.is_connected():
        logger.warning(f"Guild {guild_id}: _play_current called but not connected")
        return

    # Get fresh guild reference
    guild = bot.get_guild(guild_id)
    if not guild:
        logger.error(f"Guild {guild_id} not found")
        return

    # Self-deafen (bot doesn't need to hear users)
    if player.voice_client.channel:
        await safe_voice_state_change(guild, player.voice_client.channel, self_deaf=True)

    # Get track to play
    track = player.now_playing
    if not track:
        logger.warning(f"Guild {guild_id}: No track to play")
        return

    # Validate file exists
    if not track.opus_path.exists():
        logger.error(f"Guild {guild_id}: Track file missing: {track.opus_path}")
        # Skip to next track
        await player.spam_protector.queue_command(lambda: _play_next(guild_id, bot, players))
        return

    # Stop current playback if any (suppress callback to prevent race condition)
    try:
        vc = player.voice_client
        is_playing = vc.is_playing() if vc else False
        is_paused = vc.is_paused() if vc else False
    except Exception as e:
        logger.warning(f"Guild {guild_id}: Voice client state check failed: {e}")
        is_playing = False
        is_paused = False

    if is_playing or is_paused:
        player._suppress_callback = True
        player.voice_client.stop()

        # Wait for voice client to fully stop
        max_wait = VOICE_CONNECTION_MAX_WAIT
        wait_increment = VOICE_CONNECTION_CHECK_INTERVAL
        waited = 0
        while waited < max_wait:
            remaining = max_wait - waited
            await asyncio.sleep(min(wait_increment, remaining))
            waited += wait_increment
            try:
                vc = player.voice_client
                if vc and not vc.is_playing() and not vc.is_paused():
                    break
            except Exception:
                break

        player._suppress_callback = False

    # Small delay to let voice client settle
    await asyncio.sleep(VOICE_SETTLE_DELAY)

    audio_source = None
    try:
        # Create audio source (native opus passthrough)
        audio_source = make_audio_source(str(track.opus_path))

        # Capture track ID for this specific callback
        callback_track_id = track.track_id
        _last_callback_time = getattr(player, '_last_callback_time', 0)

        # Define callback for when track finishes
        def after_track(error):
            """
            Callback fired when track finishes playing.

            This runs in a DIFFERENT thread, so we use run_coroutine_threadsafe().
            """
            nonlocal audio_source, _last_callback_time

            if error:
                error_str = str(error)
                if "Bad file descriptor" not in error_str and "_MissingSentinel" not in error_str:
                    logger.error(f'Guild {guild_id} playback error: {error}')

            # Clean up audio source
            if audio_source:
                try:
                    audio_source.cleanup()
                except Exception:
                    pass
                audio_source = None

            # Don't advance if reconnecting
            if player._is_reconnecting:
                logger.debug(f"Guild {guild_id}: Skipping callback during reconnect")
                return

            # Don't advance if callback suppressed
            if player._suppress_callback:
                logger.debug(f"Guild {guild_id}: Skipping callback (suppressed)")
                return

            # Only advance if this callback's track is still current
            if not player.now_playing or player.now_playing.track_id != callback_track_id:
                logger.debug(f"Guild {guild_id}: Ignoring callback from old track")
                return

            # Anti-spam: Prevent rapid-fire callbacks
            current_time = time.time()
            if current_time - _last_callback_time < CALLBACK_MIN_INTERVAL:
                logger.warning(f"Guild {guild_id}: Callback too quick, skipping")
                return

            _last_callback_time = current_time

            # Queue the next track
            asyncio.run_coroutine_threadsafe(
                player.spam_protector.queue_command(lambda: _play_next(guild_id, bot, players)),
                bot.loop
            )

        # Start playback with callback
        player.voice_client.play(audio_source, after=after_track)
        player.state = PlaybackState.PLAYING

        # Update watchdog tracking
        player._last_track_start = time.time()
        player._last_track_id = track.track_id

        logger.debug(f"Guild {guild_id}: Now playing: {track.display_name}")

        # Send "Now serving" message
        await asyncio.sleep(MESSAGE_SETTLE_DELAY)
        drink = player.get_drink_emoji()
        new_content = MESSAGES['now_serving'].format(drink=drink, track=track.display_name)

        # Use cleanup manager's smart message handling
        await player.cleanup_manager.update_now_playing_message(new_content, player.voice_client)

        # Update bot presence
        await update_presence(bot, track.display_name)

    except Exception as e:
        logger.error(f'Guild {guild_id} error in _play_current: {e}', exc_info=True)
        if audio_source:
            try:
                audio_source.cleanup()
            except Exception:
                pass
        vc = player.voice_client
        if "Bad file descriptor" in str(e) or not (vc and vc.is_connected()):
            player.voice_client = None
    finally:
        player._suppress_callback = False


async def _play_next(guild_id: int, bot, players: dict) -> None:
    """
    Advance queue to next track and play it.

    Called by:
    - Track finish callback (after_track)
    - !skip command (after debounce)

    Args:
        guild_id: Guild to advance queue in
        bot: Bot instance
        players: Dict of players
    """
    from core.player import get_player
    player = await get_player(guild_id, bot, bot.user.id)
    next_track = player.advance_to_next()
    if next_track:
        await _play_current(guild_id, bot, players)


async def _play_first(guild_id: int, bot, players: dict) -> None:
    """
    Start playback from beginning.

    Called by:
    - !play command when not currently playing

    Args:
        guild_id: Guild to start playback in
        bot: Bot instance
        players: Dict of players
    """
    from core.player import get_player
    player = await get_player(guild_id, bot, bot.user.id)

    # Reset to fresh queue (respects shuffle_enabled)
    player.reset_queue()

    # Start from first track
    if player.upcoming:
        player.advance_to_next()
        await _play_current(guild_id, bot, players)
