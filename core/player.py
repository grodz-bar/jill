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
Music Player - Per-Guild State Management

Manages music playback, queue, and coordination between all systems.
Uses composition pattern to delegate to specialized systems.
"""

import asyncio
import itertools
import random
import logging
from collections import deque
from difflib import SequenceMatcher
from typing import Optional, List, Dict, Tuple
import disnake

logger = logging.getLogger(__name__)

# Import our systems
from systems.spam_protection import SpamProtector
from systems.cleanup import CleanupManager
from systems.voice_manager import VoiceManager, PlaybackState
from core.track import Track, load_library, Playlist, discover_playlists, has_playlist_structure
from config.messages import DRINK_EMOJIS
from config.timing import MAX_HISTORY
from utils.persistence import load_last_channels, save_last_channel, load_last_playlists, save_last_playlist


class MusicPlayer:
    """
    Per-guild music player with composition-based architecture.

    Delegates to specialized systems:
    - SpamProtector: Command queueing and spam protection
    - CleanupManager: Message cleanup (TTL + history)
    - VoiceManager: Voice operations and auto-pause

    Manages:
    - Music library and queue
    - Playback state
    - Track navigation
    """

    def __init__(self, guild_id: int, bot_loop, bot_user_id: int):
        """
        Initialize player for a guild.

        Args:
            guild_id: Discord guild ID
            bot_loop: Bot's event loop (for debouncing)
            bot_user_id: Bot's user ID (for message filtering)
        """
        self.guild_id = guild_id

        # =====================================================================
        # DELEGATE SYSTEMS (Composition Pattern)
        # =====================================================================
        self.spam_protector = SpamProtector(guild_id, bot_loop)
        self.cleanup_manager = CleanupManager(guild_id, bot_user_id=bot_user_id)
        self.voice_manager = VoiceManager(guild_id)

        # =====================================================================
        # PLAYLISTS & MUSIC LIBRARY
        # =====================================================================
        self.available_playlists: List[Playlist] = []
        self.current_playlist: Optional[Playlist] = None

        self.library: List[Track] = []
        self.track_by_index: Dict[int, Track] = {}

        # Queue model: played ← now_playing → upcoming
        self.played: deque[Track] = deque(maxlen=MAX_HISTORY)
        self.now_playing: Optional[Track] = None
        self.upcoming: deque[Track] = deque()

        # =====================================================================
        # PLAYBACK STATE
        # =====================================================================
        self.state = PlaybackState.IDLE
        self.shuffle_enabled: bool = False

        # =====================================================================
        # VOICE CONNECTION
        # =====================================================================
        self.voice_client: Optional[disnake.VoiceClient] = None
        self.text_channel: Optional[disnake.TextChannel] = None

        # =====================================================================
        # UI STATE
        # =====================================================================
        self._drink_cycle = itertools.cycle(DRINK_EMOJIS)

        # =====================================================================
        # WATCHDOG TRACKING
        # =====================================================================
        self._last_track_start: float = 0
        self._last_track_id: Optional[int] = None
        self._last_callback_time: float = 0

        # =====================================================================
        # RACE CONDITION FLAGS
        # =====================================================================
        self._is_reconnecting: bool = False
        self._suppress_callback: bool = False
        # Session token used by playback.py to discard superseded callbacks.
        self._playback_session = None

        # Discover playlists and load library
        self._initialize_playlists()

        # Wire up references between systems
        self._wire_systems()

    def _initialize_playlists(self):
        """
        Initialize playlist system and load appropriate library.

        Called during player construction. Discovers playlists, loads last used
        playlist from persistence, or falls back to first available.
        """
        # Discover available playlists
        self.available_playlists = discover_playlists(self.guild_id)

        # Determine which playlist to load
        playlist_to_load = None

        if self.available_playlists:
            # Multi-playlist mode: load last used or first available
            saved_playlists = load_last_playlists()
            saved_playlist_id = saved_playlists.get(self.guild_id)

            if saved_playlist_id:
                # Try to find saved playlist
                for playlist in self.available_playlists:
                    if playlist.playlist_id == saved_playlist_id:
                        playlist_to_load = playlist
                        break

            # If saved playlist not found, use first available
            if not playlist_to_load:
                playlist_to_load = self.available_playlists[0]
                logger.info(f"Guild {self.guild_id}: Saved playlist not found, using first available: {playlist_to_load.display_name}")

            self.current_playlist = playlist_to_load
            self.library, self.track_by_index = load_library(self.guild_id, playlist_to_load.playlist_path)
        else:
            # Single-playlist mode: load from root music folder
            logger.info(f"Guild {self.guild_id}: No playlists found, using root music folder")
            self.library, self.track_by_index = load_library(self.guild_id)

        # Initialize queue
        self.reset_queue()

    def _wire_systems(self):
        """Wire up references between systems for intercommunication."""
        # Give systems access to shared state
        self.spam_protector.set_text_channel(self.text_channel)
        self.cleanup_manager.set_text_channel(self.text_channel)
        self.voice_manager.set_text_channel(self.text_channel)

        # Set callbacks
        self.spam_protector.set_cleanup_callback(self.cleanup_manager.trigger_spam_cleanup)
        self.voice_manager.set_send_message_callback(self.cleanup_manager.send_with_ttl)
        self.voice_manager.set_voice_client(self.voice_client)

    def start_background_tasks(self):
        """
        Start all background workers.

        Should be called after player is fully initialized.
        """
        self.spam_protector.start_processor()
        self.cleanup_manager.start_workers()

    async def shutdown(self):
        """
        Gracefully shutdown all systems.

        Cancels background tasks and cleans up state.
        """
        await self.spam_protector.shutdown()
        await self.cleanup_manager.shutdown()

    # =========================================================================
    # Queue Management
    # =========================================================================

    def reset_queue(self, shuffle: Optional[bool] = None):
        """
        Reset queue to full library.

        Args:
            shuffle: If provided, override shuffle_enabled
        """
        if not self.library:
            logger.warning(f"Guild {self.guild_id}: Cannot reset queue - library empty")
            return

        # Determine shuffle state
        use_shuffle = shuffle if shuffle is not None else self.shuffle_enabled

        # Clear state
        self.upcoming.clear()
        self.played.clear()
        self.now_playing = None

        # Fill upcoming with library
        if use_shuffle:
            tracks = list(self.library)
            random.shuffle(tracks)
            self.upcoming = deque(tracks)
        else:
            self.upcoming = deque(self.library)

    def advance_to_next(self) -> Optional[Track]:
        """
        Advance queue: now_playing → played, upcoming[0] → now_playing.

        Returns:
            Next track to play, or None if queue exhausted
        """
        # Move current to history
        if self.now_playing:
            self.played.append(self.now_playing)

        # Get next track
        if self.upcoming:
            self.now_playing = self.upcoming.popleft()
        else:
            # Queue exhausted - loop
            logger.debug(f"Guild {self.guild_id}: Queue exhausted, looping")
            self.reset_queue()
            if self.upcoming:
                self.now_playing = self.upcoming.popleft()
            else:
                self.now_playing = None

        return self.now_playing

    def go_to_previous(self) -> Optional[Track]:
        """
        Go to previous track.

        Returns:
            Previous track, or None if at beginning
        """
        if not self.played:
            return None

        # Move current back to upcoming
        if self.now_playing:
            self.upcoming.appendleft(self.now_playing)

        # Pop from history
        self.now_playing = self.played.pop()
        return self.now_playing

    def jump_to_track(self, track_index: int) -> Optional[Track]:
        """
        Jump to specific track by library index.

        Args:
            track_index: Index in library (0-based)

        Returns:
            Track to play, or None if invalid index
        """
        track = self.track_by_index.get(track_index)
        if not track:
            return None

        # Preserve current track in history so user can go back
        if self.now_playing:
            self.played.append(self.now_playing)

        self.now_playing = track

        # Build upcoming queue
        tracks_after = [t for t in self.library if t.library_index > track_index]

        if self.shuffle_enabled:
            random.shuffle(tracks_after)

        self.upcoming = deque(tracks_after)

        return track

    # =========================================================================
    # State Management
    # =========================================================================

    def reset_state(self):
        """Reset all playback state (called on disconnect)."""
        self.cancel_active_session()
        self.state = PlaybackState.IDLE
        self.voice_client = None
        self.voice_manager.reset_alone_state()

    def cancel_active_session(self):
        """Invalidate the current playback session token.

        Playback sessions are created by :func:`core.playback._play_current` and
        attached to the player before audio starts streaming. Any manual stop,
        disconnect, or playlist switch must cancel that session so that
        lingering callbacks from the old stream safely exit without mutating
        queue state.
        """
        session = getattr(self, "_playback_session", None)
        if session and hasattr(session, "cancel"):
            session.cancel()
        self._playback_session = None

    def set_text_channel(self, channel: disnake.TextChannel):
        """
        Set text channel and update all systems.

        Also saves to persistent storage for restart recovery.
        """
        self.text_channel = channel
        self.spam_protector.set_text_channel(channel)
        self.cleanup_manager.set_text_channel(channel)
        self.voice_manager.set_text_channel(channel)

        # Save to persistent storage
        if channel:
            save_last_channel(self.guild_id, channel.id)

    async def load_persistent_channel(self, bot):
        """
        Load last used channel from persistent storage.

        Args:
            bot: Bot instance to fetch channel
        """
        channels = load_last_channels()
        channel_id = channels.get(self.guild_id)

        if channel_id:
            try:
                channel = await bot.fetch_channel(channel_id)
                if isinstance(channel, disnake.TextChannel):
                    self.set_text_channel(channel)
                    logger.info(f"Guild {self.guild_id}: Restored channel {channel.name}")
            except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException) as e:
                logger.debug(f"Guild {self.guild_id}: Could not restore channel: {e}")

    def set_voice_client(self, voice_client: Optional[disnake.VoiceClient]):
        """Set voice client and update voice manager."""
        self.voice_client = voice_client
        self.voice_manager.set_voice_client(voice_client)

    # =========================================================================
    # UI Helpers
    # =========================================================================

    def get_drink_emoji(self) -> str:
        """Get next drink emoji in rotation."""
        return next(self._drink_cycle)

    # =========================================================================
    # Additional Helper Methods
    # =========================================================================

    def has_next(self) -> bool:
        """Check if there are upcoming tracks in queue."""
        return len(self.upcoming) > 0

    # =========================================================================
    # Playlist Management
    # =========================================================================

    def find_playlist_by_identifier(self, identifier: str) -> Optional[Playlist]:
        """
        Find playlist by number or name using fuzzy matching.

        Args:
            identifier: Either a number (1-based) or name substring

        Returns:
            Matching Playlist or None if not found

        Matching Algorithm:
            1. Try parsing as number (exact match)
            2. Find all playlists containing the search term (case-insensitive)
            3. Score each match by similarity ratio
            4. Return best match (highest score, then first in list order)

        Examples:
            find_playlist_by_identifier("1") → First playlist
            find_playlist_by_identifier("lo") → "Lo-Fi Beats" (best match)
            find_playlist_by_identifier("game") → "Game OST" (first if multiple matches)
        """
        if not self.available_playlists:
            return None

        # Try parsing as number (1-based index)
        try:
            index = int(identifier) - 1
            if 0 <= index < len(self.available_playlists):
                return self.available_playlists[index]
        except ValueError:
            pass

        # Fuzzy name matching with similarity scoring
        identifier_lower = identifier.lower()
        matches = []

        # Find all playlists that contain the search term
        for idx, playlist in enumerate(self.available_playlists):
            playlist_name_lower = playlist.display_name.lower()
            if identifier_lower in playlist_name_lower:
                # Calculate similarity ratio (0.0 to 1.0)
                similarity = SequenceMatcher(None, identifier_lower, playlist_name_lower).ratio()
                matches.append((similarity, idx, playlist))

        if not matches:
            return None

        # Sort by: similarity (descending), then list index (ascending)
        # This ensures: best match first, ties broken by playlist order
        matches.sort(key=lambda x: (-x[0], x[1]))

        # Return the best match
        best_match = matches[0]
        logger.debug(
            f"Guild {self.guild_id}: Fuzzy playlist match '{identifier}' → '{best_match[2].display_name}' "
            f"(similarity: {best_match[0]:.2f})"
        )
        return best_match[2]

    async def switch_playlist(self, identifier: str, voice_client=None) -> Tuple[bool, str]:
        """
        Switch to a different playlist.

        Stops playback, clears queue, loads new library, saves to persistence.

        Args:
            identifier: Playlist number or name substring
            voice_client: Optional voice client (to stop playback)

        Returns:
            Tuple of (success: bool, message: str)

        Examples:
            success, msg = await player.switch_playlist("3")
            success, msg = await player.switch_playlist("undertale")
        """
        # Find target playlist
        target_playlist = self.find_playlist_by_identifier(identifier)

        if not target_playlist:
            return False, f"Playlist not found: '{identifier}'"

        # Check if already on this playlist
        if self.current_playlist and target_playlist.playlist_id == self.current_playlist.playlist_id:
            return False, f"Already using playlist: {target_playlist.display_name}"

        # Stop playback if playing
        if voice_client and voice_client.is_connected():
            try:
                if voice_client.is_playing() or voice_client.is_paused():
                    # Cancel the session token before the manual stop so the
                    # playback callback bails out when it wakes up. This keeps
                    # the behavior identical to using suppress_callbacks()
                    # without the extra context manager.
                    self.cancel_active_session()
                    voice_client.stop()
            except disnake.ClientException as e:
                logger.debug("Guild %s: stop during playlist switch failed: %s", self.guild_id, e)

        # Clear playback state
        self.played.clear()
        self.now_playing = None
        self.upcoming.clear()
        self.state = PlaybackState.IDLE

        # Load new library
        self.current_playlist = target_playlist
        self.library, self.track_by_index = load_library(self.guild_id, target_playlist.playlist_path)

        # Reset queue with new library
        self.reset_queue()

        # Save to persistence
        save_last_playlist(self.guild_id, target_playlist.playlist_id)

        logger.info(
            f"Guild {self.guild_id}: Switched to playlist '{target_playlist.display_name}' "
            f"({len(self.library)} tracks)"
        )

        return True, f"Switched to **{target_playlist.display_name}** ({len(self.library)} tracks)"


# =============================================================================
# Player Management (Global)
# =============================================================================

# Global player storage
players: Dict[int, MusicPlayer] = {}
players_lock = asyncio.Lock()


async def get_player(guild_id: int, bot, bot_user_id: int) -> MusicPlayer:
    """
    Get or create player for a guild (thread-safe).

    Args:
        guild_id: Discord guild ID
        bot: Bot instance
        bot_user_id: Bot's user ID

    Returns:
        MusicPlayer instance for the guild
    """
    # Fast path - no lock
    if guild_id in players:
        return players[guild_id]

    # Slow path - need lock for creation
    async with players_lock:
        # Double-check
        if guild_id in players:
            return players[guild_id]

        # Create new player
        player = MusicPlayer(guild_id, bot.loop, bot_user_id)
        player.start_background_tasks()

        # Load persistent channel
        await player.load_persistent_channel(bot)

        players[guild_id] = player

    return players[guild_id]
