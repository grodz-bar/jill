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
Discord API Helper Functions

Provides safe wrappers around common Discord API operations with error handling,
plus adaptive voice health monitoring for auto-fixing stuttering audio.

All functions gracefully handle None values and Discord API errors.

Voice Health Monitoring:
- VoiceHealthMonitor: Adaptive state machine for connection quality monitoring
- check_voice_health_and_reconnect(): Main health check function
- ConnectionHealth: Health state enum (Normal/Suspicious/Post-Reconnect/Recovery)
"""

import asyncio
import disnake
import logging
from time import monotonic as _now
from typing import Optional

logger = logging.getLogger(__name__)

# Import config
from config.features import BOT_STATUS
from config.timing import FFMPEG_BEFORE_OPTIONS

# Global presence state (bot-wide, not per-guild)
_last_presence_update: float = 0
_current_presence_text: Optional[str] = None
_presence_lock = asyncio.Lock()  # Prevents race conditions from concurrent update_presence calls


def sanitize_for_format(text: str) -> str:
    """
    Escape braces in user-controlled strings to prevent .format() crashes.

    User-controlled data (track names, playlist names from filenames) can contain
    { and } characters. If these are passed directly to str.format(), they will
    cause KeyError. This function escapes them by doubling: { -> {{, } -> }}

    Args:
        text: User-controlled string (track name, playlist name, etc.)

    Returns:
        str: Sanitized string safe for use with .format()

    Example:
        >>> track_name = "Song {test}.opus"
        >>> sanitize_for_format(track_name)
        'Song {{test}}.opus'
        >>> MESSAGES['now_serving'].format(track=sanitize_for_format(track_name))
        'Now serving: Song {test}.opus'
    """
    return text.replace('{', '{{').replace('}', '}}')


def _get_status_enum() -> disnake.Status:
    """
    Convert BOT_STATUS config string to disnake.Status enum.

    Returns:
        disnake.Status: Status enum, defaults to DND if invalid
    """
    status_map = {
        'online': disnake.Status.online,
        'dnd': disnake.Status.dnd,
        'idle': disnake.Status.idle,
        'invisible': disnake.Status.invisible,
    }

    cfg = str(BOT_STATUS).lower()
    status = status_map.get(cfg, disnake.Status.dnd)

    if cfg not in status_map:
        logger.warning(f"Invalid BOT_STATUS '{BOT_STATUS}', defaulting to 'dnd'")

    return status


async def safe_disconnect(voice_client: Optional[disnake.VoiceClient], force: bool = True) -> bool:
    """
    Safely disconnect from voice channel with error handling.

    Args:
        voice_client: Voice client to disconnect (None is safe)
        force: Force disconnect even if playing

    Returns:
        bool: True if disconnected successfully or None (idempotent no-op), False on error

    Note:
        Logs errors at debug level since disconnect failures are non-critical.
        Treats None as successful no-op for cleaner calling code.
        Catches aiohttp transport errors that can occur during shutdown.
    """
    if not voice_client:
        return True  # No-op success for idempotency
    try:
        await voice_client.disconnect(force=force)
        return True
    except (disnake.ClientException, disnake.HTTPException) as e:
        logger.debug("Disconnect failed (non-critical): %s", e)
        return False
    except Exception as e:
        # Catch aiohttp transport errors during shutdown (e.g., ClientConnectionResetError)
        logger.debug("Disconnect failed with transport error (non-critical): %s", e)
        return False


async def safe_send(channel: Optional[disnake.TextChannel], content: str) -> Optional[disnake.Message]:
    """
    Safely send message to channel with error handling and mention suppression.

    Args:
        channel: Text channel to send to (None is safe)
        content: Message content

    Returns:
        Message object if sent successfully, None otherwise

    Note:
        - Disables all mentions (@everyone, @here, user/role mentions) to prevent abuse
        - Catches common Discord API errors:
          - NotFound: Channel was deleted
          - Forbidden: Bot lost permissions
          - HTTPException: Rate limited or other API error
    """
    if not channel:
        return None
    try:
        # Suppress all mentions to prevent mass-ping abuse from user-controlled content
        msg = await channel.send(content, allowed_mentions=disnake.AllowedMentions.none())
    except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException) as e:
        logger.debug("Could not send message: %s", e)
        return None
    else:
        return msg


async def safe_voice_state_change(guild: disnake.Guild, channel: disnake.VoiceChannel, self_deaf: bool = True) -> bool:
    """
    Safely change bot's voice state (e.g., self-deafen) with error handling.

    Args:
        guild: Guild to change voice state in
        channel: Voice channel we're in
        self_deaf: Whether to self-deafen (True = bot can't hear others)

    Returns:
        bool: True if state changed successfully, False otherwise

    Note:
        Self-deafening is good practice - bot doesn't need to hear users.
    """
    try:
        await guild.change_voice_state(channel=channel, self_deaf=self_deaf)
    except (disnake.ClientException, disnake.HTTPException) as e:
        logger.debug("Voice state change failed (non-critical): %s", e)
        return False
    else:
        return True


async def update_presence(bot, status_text: Optional[str]) -> bool:
    """
    Update bot's Discord presence (status shown under bot name).

    Uses atomic state update pattern: holds lock during entire operation
    (dedupe check → API call → state update) to prevent race conditions
    and ensure failed API calls don't block retries.

    Global throttling and deduplication to avoid spammy API calls.
    Uses BOT_STATUS from config/features.py for status indicator color.

    Args:
        bot: Discord bot instance
        status_text: Status to display (None = clear status)

    Returns:
        bool: True if updated successfully, False otherwise

    Thread Safety:
        Lock held for entire operation. State only updated on success.
        See AGENTS.md "Atomic state update pattern" for details.

    Example:
        update_presence(bot, "Hopes and Dreams")  # Shows "Listening to Hopes and Dreams"
    """
    global _last_presence_update, _current_presence_text

    current_time = _now()

    # Hold lock for entire operation to prevent races and ensure atomicity
    async with _presence_lock:
        # Deduplicate if same status and recent
        if status_text == _current_presence_text and current_time - _last_presence_update < 10:
            return True

        try:
            # Get configured status (online/dnd/idle/invisible)
            status = _get_status_enum()

            # Make API call while holding lock
            if status_text:
                await bot.change_presence(
                    activity=disnake.Activity(
                        type=disnake.ActivityType.listening,
                        name=status_text
                    ),
                    status=status
                )
            else:
                await bot.change_presence(activity=None, status=status)

            # Update state ONLY on success to allow retries if failed
            _last_presence_update = current_time
            _current_presence_text = status_text

        except (disnake.ClientException, disnake.HTTPException) as e:
            logger.debug("Presence update failed (non-critical): %s", e)
            return False
        else:
            return True


def can_connect_to_channel(channel: Optional[disnake.VoiceChannel]) -> bool:
    """
    Check if bot has permission to connect to a voice channel.

    Args:
        channel: Voice channel to check

    Returns:
        bool: True if bot can connect, False otherwise

    Note:
        Checks BEFORE attempting connection prevents error messages.
        Requires connect+speak permissions. Falls back to False if guild.me is None.
    """
    if not channel:
        return False
    if not channel.guild.me:
        return False  # Rare startup race - guild not fully ready
    perms = channel.permissions_for(channel.guild.me)
    return bool(perms and perms.connect and perms.speak)


async def safe_delete_message(message: Optional[disnake.Message]) -> bool:
    """
    Safely delete a message with error handling.

    Args:
        message: Message to delete (None is safe)

    Returns:
        bool: True if deleted successfully, already deleted (NotFound), or None (no-op)
              False only on permission/API errors

    Note:
        Idempotent behavior:
        - None: Returns True (no-op success, nothing to delete)
        - NotFound: Returns True (already deleted, goal achieved)
        - Forbidden/HTTPException: Returns False (actual error)
    """
    if not message:
        return True  # No-op success for idempotency
    try:
        await message.delete()
    except disnake.NotFound:
        return True  # Already deleted = success (idempotent)
    except (disnake.Forbidden, disnake.HTTPException) as e:
        logger.debug("Could not delete message: %s", e)
        return False
    else:
        return True


def make_audio_source(path: str):
    """
    Create audio source for playback (format-aware).

    For .opus files: Uses FFmpegOpusAudio (native passthrough, zero CPU overhead)
    For other formats: Uses FFmpegPCMAudio (real-time transcoding to Discord format)

    Creates a fresh audio source for each playback - audio sources are
    single-use and cannot be reused after consumption.

    Args:
        path: Path to audio file (supports .opus, .mp3, .flac, .wav, .m4a, .ogg)

    Returns:
        Audio source object for Discord voice playback (FFmpegOpusAudio or FFmpegPCMAudio)

    Note:
        FFmpeg options are configurable via FFMPEG_BEFORE_OPTIONS in config/timing.py.
        Default options optimize for low latency and real-time playback.

        Opus files use passthrough mode (no transcoding) for maximum performance.
        Other formats are transcoded to 48kHz stereo PCM, which Discord encodes to opus.
    """
    from pathlib import Path

    file_path = Path(path)
    extension = file_path.suffix.lower()

    if extension == '.opus':
        # Native opus passthrough (zero CPU overhead, Discord-native format)
        logger.debug(f"Creating opus passthrough source for: {file_path.name}")
        return disnake.FFmpegOpusAudio(
            path,
            before_options=FFMPEG_BEFORE_OPTIONS
        )
    else:
        # Transcode to PCM, then Discord re-encodes to opus
        # Output format: 48kHz stereo signed 16-bit PCM (Discord-compatible)
        logger.debug(f"Creating transcoded source for: {file_path.name} ({extension})")
        return disnake.FFmpegPCMAudio(
            path,
            before_options=FFMPEG_BEFORE_OPTIONS,
            options='-vn -f s16le -ar 48000 -ac 2'
        )


# =========================================================================================================
# VOICE HEALTH MONITORING - Adaptive connection monitoring and auto-reconnect
# =========================================================================================================

from enum import IntEnum
from typing import Tuple


class ConnectionHealth(IntEnum):
    """Voice connection health states for adaptive monitoring."""
    NORMAL = 0          # All good, relaxed monitoring
    SUSPICIOUS = 1      # Marginal latency detected, watch closely
    POST_RECONNECT = 2  # Just reconnected, verify fix worked
    RECOVERY = 3        # Fix confirmed working, stay vigilant


class VoiceHealthMonitor:
    """
    Adaptive voice connection health monitoring.

    Adjusts check frequency based on connection quality to catch issues
    fast while avoiding unnecessary overhead.
    """

    # Check intervals (seconds)
    NORMAL_INTERVAL = 35          # Everything fine
    SUSPICIOUS_INTERVAL = 10      # Problems detected, watch closely!
    POST_RECONNECT_INTERVAL = 8   # Just reconnected - verify quickly
    RECOVERY_INTERVAL = 20        # Fix working but stay vigilant

    # Thresholds
    MARGINAL_LATENCY = 0.150     # 150ms - getting concerning
    BAD_LATENCY = 0.250          # 250ms - reconnect needed
    GOOD_CHECKS_FOR_NORMAL = 3   # Good checks before returning to normal

    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.state = ConnectionHealth.NORMAL
        self.good_checks_count = 0
        self.last_check = 0.0
        self.last_reconnect = 0.0
        self.reconnect_count = 0

    def get_next_check_interval(self) -> float:
        """Get the next check interval based on current state."""
        intervals = {
            ConnectionHealth.NORMAL: self.NORMAL_INTERVAL,
            ConnectionHealth.SUSPICIOUS: self.SUSPICIOUS_INTERVAL,
            ConnectionHealth.POST_RECONNECT: self.POST_RECONNECT_INTERVAL,
            ConnectionHealth.RECOVERY: self.RECOVERY_INTERVAL,
        }
        return intervals[self.state]

    def should_check_now(self) -> bool:
        """Check if enough time has passed for next health check."""
        interval = self.get_next_check_interval()
        return _now() - self.last_check >= interval

    def record_check(self, latency: Optional[float]) -> Tuple[bool, bool]:
        """
        Record a health check result and update state.

        Args:
            latency: Current voice latency in seconds (None if unavailable)

        Returns:
            Tuple of (needs_reconnect, state_changed)
        """
        self.last_check = _now()
        old_state = self.state
        needs_reconnect = False

        # Evaluate connection health
        if latency is None:
            # Can't determine latency, be conservative
            health_status = "unknown"
        elif latency > self.BAD_LATENCY:
            health_status = "bad"
            needs_reconnect = True
        elif latency > self.MARGINAL_LATENCY:
            health_status = "marginal"
        else:
            health_status = "good"

        # State machine logic
        if health_status == "bad":
            # Need to reconnect regardless of state
            needs_reconnect = True

        elif health_status == "marginal":
            if self.state == ConnectionHealth.NORMAL:
                # Detected problems, enter suspicious mode
                self.state = ConnectionHealth.SUSPICIOUS
                self.good_checks_count = 0
                logger.info(
                    f"Guild {self.guild_id}: Voice latency marginal "
                    f"({latency*1000:.0f}ms), monitoring closely"
                )
            # Stay in current state if already suspicious/recovering

        elif health_status == "good":
            if self.state == ConnectionHealth.POST_RECONNECT:
                # First good check after reconnect, move to recovery
                self.state = ConnectionHealth.RECOVERY
                self.good_checks_count = 1
                logger.info(f"Guild {self.guild_id}: Reconnect successful, monitoring stability")

            elif self.state == ConnectionHealth.RECOVERY:
                self.good_checks_count += 1
                if self.good_checks_count >= self.GOOD_CHECKS_FOR_NORMAL:
                    # Sustained good performance, back to normal
                    self.state = ConnectionHealth.NORMAL
                    logger.debug(f"Guild {self.guild_id}: Connection stable, resuming normal monitoring")

            elif self.state == ConnectionHealth.SUSPICIOUS:
                # Connection improved, move to recovery
                self.state = ConnectionHealth.RECOVERY
                self.good_checks_count = 1
                logger.info(f"Guild {self.guild_id}: Connection improved, watching for stability")

        state_changed = (old_state != self.state)
        return needs_reconnect, state_changed

    def record_reconnect(self):
        """Record that a reconnect occurred."""
        self.state = ConnectionHealth.POST_RECONNECT
        self.good_checks_count = 0
        self.last_reconnect = _now()
        self.reconnect_count += 1


# Global health monitors per guild
_health_monitors = {}


def get_health_monitor(guild_id: int) -> VoiceHealthMonitor:
    """Get or create health monitor for a guild."""
    if guild_id not in _health_monitors:
        _health_monitors[guild_id] = VoiceHealthMonitor(guild_id)
    return _health_monitors[guild_id]


async def check_voice_health_and_reconnect(player, guild, bot) -> bool:
    """
    Check voice connection health with adaptive monitoring.

    Uses smart state machine to adjust monitoring frequency based on
    connection quality. Catches degraded connections quickly while
    avoiding unnecessary overhead.

    Args:
        player: MusicPlayer instance
        guild: Discord guild
        bot: Bot instance

    Returns:
        True if healthy or successfully reconnected, False if reconnect failed
    """
    from config.features import VOICE_HEALTH_CHECK_ENABLED

    # Feature toggle
    if not VOICE_HEALTH_CHECK_ENABLED:
        return True

    if not player.voice_client:
        return False

    monitor = get_health_monitor(guild.id)

    try:
        vc = player.voice_client

        # Basic connection check
        if not vc.is_connected():
            return False

        # Get latency (primary health indicator)
        latency = None
        if hasattr(vc, 'latency'):
            latency = vc.latency

        # Record check and get decision
        needs_reconnect, state_changed = monitor.record_check(latency)

        # Log state changes at appropriate levels
        if state_changed:
            interval = monitor.get_next_check_interval()
            logger.debug(
                f"Guild {guild.id}: Health monitor state changed to "
                f"{ConnectionHealth(monitor.state).name}, next check in {interval}s"
            )

        # Additional health checks if latency unavailable
        if latency is None:
            # Check WebSocket health
            if hasattr(vc, 'ws') and (vc.ws is None or vc.ws.closed):
                logger.warning(f"Guild {guild.id}: Voice WebSocket dead, forcing reconnect")
                needs_reconnect = True

            # Check if we can access channel
            try:
                _ = vc.channel
            except (AttributeError, RuntimeError):
                logger.warning(f"Guild {guild.id}: Voice client in bad state, forcing reconnect")
                needs_reconnect = True

        # Perform reconnect if needed
        if needs_reconnect:
            if latency:
                logger.warning(
                    f"Guild {guild.id}: Voice connection degraded "
                    f"(latency: {latency*1000:.0f}ms), reconnecting to fix stuttering"
                )
            return await _force_voice_reconnect(player, guild, bot, monitor)

        return True

    except Exception as e:
        logger.error(f"Guild {guild.id}: Voice health check error: {e}", exc_info=True)
        # Try reconnect on error
        return await _force_voice_reconnect(player, guild, bot, monitor)


async def _force_voice_reconnect(player, guild, bot, monitor: VoiceHealthMonitor) -> bool:
    """
    Force reconnect to voice channel to fix degraded connection.

    Creates a fresh UDP socket to fix stuttering from network issues.

    Args:
        player: MusicPlayer instance
        guild: Discord guild
        bot: Bot instance
        monitor: Health monitor for this guild

    Returns:
        True if reconnected successfully, False otherwise
    """
    from utils.context_managers import reconnecting_state, suppress_callbacks
    from config.timing import VOICE_RECONNECT_DELAY

    # Check reconnect cooldown (prevent rapid reconnects)
    time_since_last = _now() - monitor.last_reconnect
    if time_since_last < 30:  # 30 second minimum between reconnects
        logger.debug(
            f"Guild {guild.id}: Skipping reconnect, too recent "
            f"({time_since_last:.1f}s ago)"
        )
        return True

    # Get current channel
    old_vc = player.voice_client
    if not old_vc or not old_vc.channel:
        return False

    channel = old_vc.channel

    # Log reconnect attempt
    logger.info(
        f"Guild {guild.id}: Reconnecting voice to fix stuttering "
        f"(attempt #{monitor.reconnect_count + 1})"
    )

    # Mark as reconnecting
    with reconnecting_state(player):
        # Stop playback cleanly if playing
        try:
            if old_vc.is_playing():
                with suppress_callbacks(player):
                    old_vc.stop()
        except Exception:
            pass

        # Disconnect
        try:
            await old_vc.disconnect(force=True)
        except Exception as e:
            logger.debug(f"Guild {guild.id}: Disconnect error (continuing): {e}")

        player.voice_client = None

        # Wait for disconnect to settle
        await asyncio.sleep(VOICE_RECONNECT_DELAY)

        # Reconnect with fresh UDP socket
        try:
            new_vc = await channel.connect(timeout=5.0, reconnect=True)
            player.voice_client = new_vc
            player.voice_manager.set_voice_client(new_vc)

            # Self-deafen
            await safe_voice_state_change(guild, channel, self_deaf=True)

            # Record successful reconnect
            monitor.record_reconnect()

            logger.info(
                f"Guild {guild.id}: Voice reconnected successfully "
                f"(new connection established)"
            )

            return True

        except asyncio.TimeoutError:
            logger.error(f"Guild {guild.id}: Voice reconnect timed out after 5s")
            player.voice_client = None
            return False
        except Exception as e:
            logger.error(f"Guild {guild.id}: Voice reconnect failed: {e}")
            player.voice_client = None
            return False
