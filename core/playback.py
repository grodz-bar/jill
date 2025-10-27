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
Playback Functions

Core music playback functionality including track playing, callbacks, and queue advancement.
"""

import asyncio
from time import monotonic as _now
import logging
from dataclasses import dataclass, field
from itertools import count
from typing import Optional

logger = logging.getLogger(__name__)


_SESSION_IDS = count(1)


@dataclass(slots=True)
class PlaybackSession:
    """Immutable-style token that scopes callbacks to a specific play attempt.

    Each playback session receives a unique ``id`` so asynchronous callbacks can
    verify that they are still acting on the most recent request. The
    ``track_id`` is stored for logging and sanity checks, while ``started_at``
    captures diagnostic timing data for watchdog tooling. The ``cancelled``
    flag is toggled when a newer session supersedes the current one, allowing
    in-flight callbacks to bail out early without mutating shared state.
    """

    id: int = field(default_factory=lambda: next(_SESSION_IDS))
    track_id: Optional[int] = None
    started_at: float = field(default_factory=_now)
    cancelled: bool = False

    def cancel(self) -> None:
        """Mark the session as cancelled so callbacks know to exit early."""
        self.cancelled = True

# Import from config
from config.timing import (
    VOICE_SETTLE_DELAY,
    MESSAGE_SETTLE_DELAY,
    CALLBACK_MIN_INTERVAL,
    VOICE_CONNECTION_MAX_WAIT,
    VOICE_CONNECTION_CHECK_INTERVAL,
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
    sanitize_for_format,
)
from utils.context_managers import suppress_callbacks


async def _play_current(guild_id: int, bot) -> None:
    """
    Play the current track (whatever is in now_playing).

    This function does NOT advance the queue - it just plays what's set.
    Queue advancement happens in _play_next().

    Args:
        guild_id: Guild to play in
        bot: Bot instance

    Side effects:
        - Starts playback via voice_client.play()
        - Sets callback for when track finishes (with anti-spam protection)
        - Updates bot presence status
        - Sends "Now serving" message
        - Updates watchdog tracking

    Implementation notes:
        - Uses context manager to safely suppress callbacks during voice client stop
        - Callback includes anti-spam timer that persists across playback sessions
        - Uses priority queueing for internal _play_next commands to prevent dropping
    """
    from core.player import get_player  # Import here to avoid circular
    player = await get_player(guild_id, bot, bot.user.id)

    # Cancel any prior playback attempt before starting a new one
    player.cancel_active_session()

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
        # Skip to next track (priority=True to ensure internal commands aren't dropped)
        await player.spam_protector.queue_command(lambda: _play_next(guild_id, bot), priority=True)
        return

    # Create a playback session token so stale callbacks can be ignored safely.
    session = PlaybackSession(track_id=track.track_id)
    player._playback_session = session

    # Stop current playback if any (suppress callback to prevent race condition)
    try:
        vc = player.voice_client
        is_playing = vc.is_playing() if vc else False
        is_paused = vc.is_paused() if vc else False
    except (AttributeError, RuntimeError) as e:
        logger.debug("Guild %s: Voice client state probe failed: %s", guild_id, e)
        is_playing = False
        is_paused = False

    if is_playing or is_paused:
        # Use context manager to safely suppress callbacks, even if exceptions occur
        with suppress_callbacks(player):
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
                except (AttributeError, RuntimeError) as e:
                    logger.debug("Guild %s: settle check failed (ignored): %s", guild_id, e)
                    break

    # Small delay to let voice client settle
    await asyncio.sleep(VOICE_SETTLE_DELAY)

    audio_source = None
    try:
        # Create audio source (native opus passthrough)
        audio_source = make_audio_source(str(track.opus_path))

        # Capture track ID for this specific callback
        callback_track_id = track.track_id

        # Define callback for when track finishes
        def after_track(error):
            """
            Callback fired when track finishes playing.

            CRITICAL: This runs in FFmpeg's audio thread (NOT the event loop thread).
            - Use bot.loop.call_soon_threadsafe() for ANY player attribute mutations
            - Use asyncio.run_coroutine_threadsafe() for coroutine calls
            - Direct attribute assignment causes race conditions and crashes
            """
            nonlocal audio_source

            if error:
                error_str = str(error)
                if "Bad file descriptor" not in error_str and "_MissingSentinel" not in error_str:
                    logger.error(f'Guild {guild_id} playback error: {error}')

            # Clean up audio source
            if audio_source:
                try:
                    audio_source.cleanup()
                except (OSError, RuntimeError, AttributeError) as e:
                    logger.debug("Guild %s: audio_source.cleanup() failed: %s", guild_id, e, exc_info=True)
                finally:
                    audio_source = None

            # Don't advance if reconnecting
            if player._is_reconnecting:
                logger.debug(f"Guild {guild_id}: Skipping callback during reconnect")
                return

            # Don't advance if callback suppressed
            if player._suppress_callback:
                logger.debug(f"Guild {guild_id}: Skipping callback (suppressed)")
                return

            # Ignore callbacks from superseded sessions
            if session.cancelled or player._playback_session is not session:
                logger.debug(
                    f"Guild {guild_id}: Ignoring callback from superseded playback session"
                )
                return

            # Only advance if this callback's track is still current
            if not player.now_playing or player.now_playing.track_id != callback_track_id:
                logger.debug(f"Guild {guild_id}: Ignoring callback from old track")
                return

            # Anti-spam: Prevent rapid-fire callbacks
            # Always read from player attribute to avoid stale closure values
            current_time = _now()
            last_callback_time = getattr(player, '_last_callback_time', 0)
            if current_time - last_callback_time < CALLBACK_MIN_INTERVAL:
                logger.warning(f"Guild {guild_id}: Callback too quick, skipping")
                return

            # CRITICAL: Update player attribute so future callbacks see the latest timestamp.
            # Must use call_soon_threadsafe since after_track runs in FFmpeg's thread
            bot.loop.call_soon_threadsafe(setattr, player, '_last_callback_time', current_time)

            # Queue the next track (priority=True to ensure internal commands aren't dropped)
            # Bind guild_id in lambda to avoid late-binding surprises
            asyncio.run_coroutine_threadsafe(
                player.spam_protector.queue_command(lambda gid=guild_id: _play_next(gid, bot), priority=True),
                bot.loop
            )

            if player._playback_session is session:
                session.cancel()
                # Thread-safe mutation from FFmpeg thread
                bot.loop.call_soon_threadsafe(setattr, player, '_playback_session', None)

        # Start playback with callback
        player.voice_client.play(audio_source, after=after_track)
        player.state = PlaybackState.PLAYING

        # Update watchdog tracking
        player._last_track_start = _now()
        player._last_track_id = track.track_id

        logger.debug(f"Guild {guild_id}: Now playing: {track.display_name}")

        # Send "Now serving" message
        await asyncio.sleep(MESSAGE_SETTLE_DELAY)
        drink = player.get_drink_emoji()
        new_content = MESSAGES['now_serving'].format(drink=drink, track=sanitize_for_format(track.display_name))

        # Use cleanup manager's smart message handling
        await player.cleanup_manager.update_now_playing_message(new_content)

        # Update bot presence
        await update_presence(bot, track.display_name)

    except Exception as e:
        logger.exception("Guild %s error in _play_current", guild_id)
        if audio_source:
            try:
                audio_source.cleanup()
            except (OSError, RuntimeError, AttributeError) as cleanup_err:
                logger.debug("Guild %s: cleanup after exception failed: %s", guild_id, cleanup_err)
        vc = player.voice_client
        if "Bad file descriptor" in str(e) or not (vc and vc.is_connected()):
            # Close connection to avoid dangling references
            if vc:
                from utils.discord_helpers import safe_disconnect
                await safe_disconnect(vc, force=True)
            player.voice_client = None
        if player._playback_session is session:
            player.cancel_active_session()


async def _play_next(guild_id: int, bot) -> None:
    """
    Advance queue to next track and play it.

    Called by:
    - Track finish callback (after_track)
    - !skip command (after debounce)

    Args:
        guild_id: Guild to advance queue in
        bot: Bot instance
    """
    from core.player import get_player
    player = await get_player(guild_id, bot, bot.user.id)
    next_track = player.advance_to_next()
    if next_track:
        await _play_current(guild_id, bot)


async def _play_first(guild_id: int, bot) -> None:
    """
    Start playback from beginning.

    Called by:
    - !play command when not currently playing

    Args:
        guild_id: Guild to start playback in
        bot: Bot instance
    """
    from core.player import get_player
    player = await get_player(guild_id, bot, bot.user.id)

    # Reset to fresh queue (respects shuffle_enabled)
    player.reset_queue()

    # Start from first track
    if player.upcoming:
        player.advance_to_next()
        await _play_current(guild_id, bot)
