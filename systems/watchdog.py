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
Watchdog Systems

Background monitoring tasks for detecting and recovering from edge cases:
1. Playback Watchdog - Detects hung FFmpeg processes
2. Alone Watchdog - Monitors for auto-pause/disconnect triggers
"""

import asyncio
from time import monotonic as _now
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Import from config
from config.timing import WATCHDOG_INTERVAL, WATCHDOG_TIMEOUT, ALONE_WATCHDOG_INTERVAL
from systems.voice_manager import PlaybackState
from utils.context_managers import suppress_callbacks


async def playback_watchdog(bot, players: Dict[int, 'MusicPlayer']):
    """
    Monitor playback for hung FFmpeg processes.

    Runs in background, checks every WATCHDOG_INTERVAL seconds.

    Detection logic:
    - If same track is playing for >WATCHDOG_TIMEOUT seconds → hung
    - Force stop to trigger callback and restart playback

    Why this is needed:
    - FFmpeg rarely hangs but when it does, bot appears stuck
    - Callback never fires because FFmpeg never finishes
    - Watchdog detects this and forces restart

    Args:
        bot: Discord bot instance
        players: Dict of guild_id → MusicPlayer instances

    Side effects:
    - Calls voice_client.stop() if hung detected
    - Queues next track manually
    """
    await bot.wait_until_ready()
    logger.debug("Playback watchdog started")

    while not bot.is_closed():
        try:
            # Adaptive sleep: reduce polling when no active voice connections
            sleep_interval = WATCHDOG_INTERVAL
            if not any(p.voice_client and p.voice_client.is_connected() for p in players.values()):
                # When idle, check at least every base interval, but not more than once per 5 min
                sleep_interval = max(WATCHDOG_INTERVAL, 300)  # At least 5 min when idle

            await asyncio.sleep(sleep_interval)

            # Snapshot iteration to prevent crashes during modifications
            for guild_id, player in list(players.items()):
                # Skip if not playing
                if not player.voice_client or not player.voice_client.is_connected():
                    continue

                state = player.voice_manager.get_playback_state()
                if state != PlaybackState.PLAYING:
                    continue

                current_time = _now()
                current_track = player.now_playing

                # Check if stuck on same track
                if current_track and current_track.track_id == player._last_track_id:
                    time_on_track = current_time - player._last_track_start

                    if time_on_track > WATCHDOG_TIMEOUT:
                        logger.error(f"Guild {guild_id}: Playback hung, restarting")
                        try:
                            # Stop hung track and manually advance to next
                            with suppress_callbacks(player):
                                player.voice_client.stop()

                            # Manually queue next track since we suppressed the callback (priority=True for internal commands)
                            from core.playback import _play_next
                            await player.spam_protector.queue_command(
                                lambda gid=guild_id: _play_next(gid, bot),
                                priority=True
                            )

                        except Exception:
                            logger.exception("Watchdog stop failed")

                else:
                    # Track changed, update tracking
                    if current_track:
                        player._last_track_id = current_track.track_id
                        player._last_track_start = current_time

        except asyncio.CancelledError:
            # Task was cancelled during shutdown - exit cleanly
            logger.debug("Playback watchdog cancelled, shutting down")
            break
        except Exception:
            logger.exception("Playback watchdog error")


async def alone_watchdog(bot, players: Dict[int, 'MusicPlayer']):
    """
    Monitor for bot being alone in voice channel.

    Runs in background, checks every ALONE_WATCHDOG_INTERVAL seconds.

    Timeline when bot becomes alone:
    - 10s: Auto-pause (if playing)
    - 10min: Auto-disconnect

    This complements on_voice_state_update which triggers immediately
    on user join/leave, but we need continuous checking for timers.

    Args:
        bot: Discord bot instance
        players: Dict of guild_id → MusicPlayer instances
    """
    await bot.wait_until_ready()
    logger.debug("Alone watchdog started")

    while not bot.is_closed():
        try:
            # Adaptive sleep: reduce polling when no active voice connections
            sleep_interval = ALONE_WATCHDOG_INTERVAL
            if not any(p.voice_client and p.voice_client.is_connected() for p in players.values()):
                # When idle, check at least every base interval, but not more than once per 5 min
                sleep_interval = max(ALONE_WATCHDOG_INTERVAL, 300)  # At least 5 min when idle

            await asyncio.sleep(sleep_interval)

            # Snapshot iteration to prevent crashes during modifications
            for _guild_id, player in list(players.items()):
                if player.voice_client and player.voice_client.is_connected():
                    # Handle alone state (auto-pause/disconnect)
                    current_state = player.voice_manager.get_playback_state()
                    new_state = await player.voice_manager.handle_alone_state(
                        bot,
                        current_state,
                        player.now_playing
                    )

                    # Update player state if changed
                    if new_state is not None:
                        player.state = new_state

        except asyncio.CancelledError:
            # Task was cancelled during shutdown - exit cleanly
            logger.debug("Alone watchdog cancelled, shutting down")
            break
        except Exception:
            logger.exception("Alone watchdog error")
