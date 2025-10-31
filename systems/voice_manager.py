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
Voice Management System

Handles voice channel operations, auto-pause when alone, and auto-disconnect.
Provides utilities for safely checking voice client state.
"""

import logging
from time import monotonic as _now  # Use _now() for all time tracking (monotonic clock, consistent across codebase)
from typing import Optional, Tuple
from enum import Enum
import disnake

logger = logging.getLogger(__name__)  # For debug/error logs
user_logger = logging.getLogger('jill')  # For user-facing messages

# Import from config
from config import (
    ALONE_PAUSE_DELAY, ALONE_DISCONNECT_DELAY,
    AUTO_PAUSE_ENABLED, AUTO_DISCONNECT_ENABLED,
    MESSAGES,
)
from utils.discord_helpers import safe_disconnect, update_presence, sanitize_for_format


class PlaybackState(Enum):
    """
    Current state of voice playback.

    IDLE: Bot is not playing anything (may or may not be connected to voice)
    PLAYING: Bot is actively playing a track
    PAUSED: Bot is connected and has a track loaded, but playback is paused
    """
    IDLE = 0
    PLAYING = 1
    PAUSED = 2


class VoiceManager:
    """
    Manages voice channel operations and auto-pause/disconnect behavior.

    Handles:
    - Voice state checking with error handling
    - Auto-pause when alone in channel
    - Auto-disconnect after extended alone time
    - Auto-resume when users rejoin
    """

    def __init__(self, guild_id: int):
        """
        Initialize voice manager for a guild.

        Args:
            guild_id: Discord guild ID for logging
        """
        self.guild_id = guild_id

        # Auto-pause state tracking (uses monotonic time for immunity to clock changes)
        self._alone_since: Optional[float] = None
        self._was_playing_before_alone: bool = False

        # References (set by player)
        self.voice_client: Optional[disnake.VoiceClient] = None
        self.text_channel: Optional[disnake.TextChannel] = None

        # Callback for sending messages with TTL
        self._send_message_callback = None

    # =========================================================================
    # Voice State Utilities
    # =========================================================================

    @staticmethod
    def get_voice_state_safe(voice_client: Optional[disnake.VoiceClient]) -> Optional[Tuple[bool, bool]]:
        """
        Safely get voice state.

        Args:
            voice_client: Voice client to check

        Returns:
            Tuple of (is_playing, is_paused) or None if not connected or error
        """
        if not voice_client or not voice_client.is_connected():
            return None

        try:
            return (voice_client.is_playing(), voice_client.is_paused())
        except (disnake.ClientException, RuntimeError) as e:
            logger.debug(f"Voice state check failed: {e}")
            return None

    def get_playback_state(self) -> PlaybackState:
        """
        Get current playback state safely.

        Returns:
            PlaybackState: IDLE, PLAYING, or PAUSED
        """
        state = self.get_voice_state_safe(self.voice_client)
        if state is None:
            return PlaybackState.IDLE

        is_playing, is_paused = state
        if is_paused:
            return PlaybackState.PAUSED
        if is_playing:
            return PlaybackState.PLAYING

        return PlaybackState.IDLE

    # =========================================================================
    # Alone Detection
    # =========================================================================

    def is_alone_in_channel(self, log_result: bool = False) -> bool:
        """
        Check if bot is alone in voice channel (no human users).

        Args:
            log_result: If True, log the result at INFO level

        Returns:
            bool: True if bot is alone or not connected, False if users present
        """
        if not self.voice_client or not self.voice_client.is_connected():
            return True

        channel = self.voice_client.channel
        if not channel or not channel.guild:
            return True

        # Count human members in this channel
        members = list(channel.members)
        human_count = sum(1 for m in members if not m.bot)

        is_alone = human_count == 0

        # Optional logging (only when requested)
        if log_result:
            member_names = [f"{m.name}(bot={m.bot})" for m in members]
            logger.info(
                f"Guild {self.guild_id}: Alone check - Channel: {channel.name}, "
                f"Total: {len(members)}, Humans: {human_count}, Alone: {is_alone}, "
                f"Members: {member_names}"
            )

        return is_alone

    # =========================================================================
    # Auto-Pause/Disconnect Logic
    # =========================================================================

    async def handle_alone_state(self, bot, current_state: PlaybackState, now_playing=None):
        """
        Handle bot being alone in voice channel.

        Timeline:
        - 0s: User leaves, bot is alone
        - 10s: Auto-pause (if playing)
        - 10min: Auto-disconnect

        Args:
            bot: Bot instance for presence updates
            current_state: Current playback state
            now_playing: Currently playing track (for resume message)

        Returns:
            New playback state if changed, None otherwise
        """
        if not self.voice_client or not self.voice_client.is_connected():
            self._alone_since = None
            return None

        is_alone = self.is_alone_in_channel()
        current_time = _now()

        if is_alone:
            # Bot is alone
            if self._alone_since is None:
                # Just became alone - log detailed channel state for debugging
                self._alone_since = current_time
                if self.voice_client and self.voice_client.channel:
                    channel = self.voice_client.channel
                    members = list(channel.members)
                    human_count = sum(1 for m in members if not m.bot)
                    logger.info(
                        f"Guild {self.guild_id}: Bot became alone in voice channel '{channel.name}' "
                        f"(Total: {len(members)}, Humans: {human_count})"
                    )
                else:
                    logger.info(f"Guild {self.guild_id}: Bot became alone in voice channel")

            else:
                # Been alone for a while
                alone_duration = current_time - self._alone_since

                # Check for auto-pause
                if AUTO_PAUSE_ENABLED and alone_duration >= ALONE_PAUSE_DELAY:
                    if current_state == PlaybackState.PLAYING and not self._was_playing_before_alone:
                        user_logger.info(f"Auto-pausing (alone for {alone_duration:.1f}s)")
                        self.voice_client.pause()
                        self._was_playing_before_alone = True

                        # Send message
                        if self._send_message_callback and self.text_channel:
                            await self._send_message_callback(
                                self.text_channel,
                                MESSAGES['pause_auto'],
                                'pause'
                            )

                        return PlaybackState.PAUSED

                # Check for auto-disconnect
                if AUTO_DISCONNECT_ENABLED and alone_duration >= ALONE_DISCONNECT_DELAY:
                    user_logger.info(f"Auto-disconnecting (alone for {alone_duration:.1f}s)")

                    # Send message before disconnecting
                    if self._send_message_callback and self.text_channel:
                        await self._send_message_callback(
                            self.text_channel,
                            MESSAGES['stop'],
                            'stop'
                        )

                    # Disconnect
                    await safe_disconnect(self.voice_client, force=True)
                    await update_presence(bot, None)
                    self._alone_since = None
                    self._was_playing_before_alone = False

                    return PlaybackState.IDLE

        else:
            # Bot is NOT alone (someone is in channel)
            if self._alone_since is not None:
                # Someone just joined - log detailed channel state for debugging
                if self.voice_client and self.voice_client.channel:
                    channel = self.voice_client.channel
                    members = list(channel.members)
                    human_count = sum(1 for m in members if not m.bot)
                    logger.info(
                        f"Guild {self.guild_id}: Not alone anymore in '{channel.name}' "
                        f"(Total: {len(members)}, Humans: {human_count}), "
                        f"state={current_state}, was_playing_before={self._was_playing_before_alone}"
                    )
                else:
                    logger.info(
                        f"Guild {self.guild_id}: Not alone anymore, state={current_state}, "
                        f"was_playing_before={self._was_playing_before_alone}"
                    )

                # Auto-resume if we auto-paused
                if AUTO_PAUSE_ENABLED and current_state == PlaybackState.PAUSED and self._was_playing_before_alone:
                    user_logger.info(f"Auto-resuming (someone joined)")
                    self.voice_client.resume()

                    # Send message
                    if self._send_message_callback and self.text_channel and now_playing:
                        await self._send_message_callback(
                            self.text_channel,
                            MESSAGES['resume'].format(track=sanitize_for_format(now_playing.display_name)),
                            'resume'
                        )

                    # Reset tracking
                    self._alone_since = None
                    self._was_playing_before_alone = False

                    return PlaybackState.PLAYING

                # Reset alone tracking
                self._alone_since = None
                self._was_playing_before_alone = False

        return None

    # =========================================================================
    # Configuration
    # =========================================================================

    def set_voice_client(self, voice_client: Optional[disnake.VoiceClient]):
        """Set the voice client reference."""
        self.voice_client = voice_client

    def set_text_channel(self, text_channel: Optional[disnake.TextChannel]):
        """Set the text channel for messages."""
        self.text_channel = text_channel

    def set_send_message_callback(self, callback):
        """Set callback for sending messages with TTL."""
        self._send_message_callback = callback

    def reset_alone_state(self):
        """Reset alone tracking state."""
        self._alone_since = None
        self._was_playing_before_alone = False
