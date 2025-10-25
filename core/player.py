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
from typing import Optional, List, Dict
import disnake

logger = logging.getLogger(__name__)

# Import our systems
from systems.spam_protection import SpamProtector
from systems.cleanup import CleanupManager
from systems.voice_manager import VoiceManager, PlaybackState
from core.track import Track, load_library
from config.messages import DRINK_EMOJIS
from config.timing import MAX_HISTORY
from utils.persistence import load_last_channels, save_last_channel


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
        # MUSIC LIBRARY & QUEUE
        # =====================================================================
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

        # Load library
        self.library, self.track_by_index = load_library(guild_id)
        self.reset_queue()

        # Wire up references between systems
        self._wire_systems()

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

        # Reset queue from this track
        self.played.clear()
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
        self.state = PlaybackState.IDLE
        self.voice_client = None
        self.voice_manager.reset_alone_state()

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
            except Exception as e:
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
