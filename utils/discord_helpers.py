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

Provides safe wrappers around common Discord API operations with error handling.
All functions gracefully handle None values and Discord API errors.
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
    """
    if not voice_client:
        return True  # No-op success for idempotency
    try:
        await voice_client.disconnect(force=force)
        return True
    except (disnake.ClientException, disnake.HTTPException) as e:
        logger.debug("Disconnect failed (non-critical): %s", e)
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
    Create FFmpegOpusAudio source for playback.

    Creates a fresh audio source for each playback - audio sources are
    single-use and cannot be reused after consumption.

    Args:
        path: Path to opus audio file

    Returns:
        FFmpegOpusAudio: Audio source object for Discord voice playback

    Note:
        FFmpeg options are configurable via FFMPEG_BEFORE_OPTIONS in config/timing.py.
        Default options optimize for low latency and real-time playback.
    """
    return disnake.FFmpegOpusAudio(
        path,
        before_options=FFMPEG_BEFORE_OPTIONS
    )
