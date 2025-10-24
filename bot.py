"""
VA-11 Hall-A Discord Music Bot
================================
VERSION: 0.9.x - Pre-release development version
================================

ARCHITECTURE OVERVIEW:
---------------------
This bot uses a multi-layer defense system against spam and race conditions:

SPAM PROTECTION EXPLAINED:
-------------------------
LAYER 0: Per-User Spam Filter (USER_COMMAND_SPAM_THRESHOLD threshold)
    - Ignores commands sent too rapidly by any user
    - Stops error message spam
    - First line of defense

LAYER 1: Validation (instant feedback)
    - Checks permissions, voice state, bot state
    - Fast error messages for user experience
    - Happens BEFORE queueing expensive operations

LAYER 2: Global Rate Limiter (GLOBAL_RATE_LIMIT between commands)
    - Protects Discord API from rate limiting
    - Prevents queue flooding
    - Per-server limit

LAYER 3: Command Debouncing (configurable per command)
    - Waits for spam to stop before executing
    - Catches Discord-rate-limited spam (Discord sometimes delays messages)
    - Shows spam warnings on moderate spam
    - Generic system - works for any command
    - Each command type uses its own timing constants (QUEUE_*, LIBRARY_*, PAUSE_*)

LAYER 4: Queue System
    - Serializes ALL state-modifying operations
    - Eliminates race conditions entirely
    - One operation at a time per server

LAYER 5: Post-Execution Cooldowns
    - Prevents rapid re-execution
    - Configurable per command type

KEY DESIGN PATTERNS:
-------------------
1. Multi-Server Support: Each Discord server (guild) gets its own MusicPlayer instance
2. Track Identity: Unique IDs prevent object reference bugs
3. Queue Model: played ← now_playing → upcoming (supports navigation)
4. State Preservation: Stop always resets, play always starts fresh
5. Debouncing: Generic system reusable for any command (per-command timing constants)
6. Safe Operations: All Discord API calls wrapped in error handlers
7. Async Concurrency: Uses asyncio.Lock and async get_player() for thread safety
8. Shuffle System: Toggle-based with auto-reshuffle on loop
9. Library Navigation: Track numbers (01, 02, 03...) work the same whether shuffle is on or off
10. Track-Specific Callbacks: Each callback knows its track_id, ignores itself if track changed
11. Channel Persistence: Remembers last used text channel per server across restarts
12. Guild-Only Commands: All commands use @commands.guild_only() decorator (prevents DM crashes)
13. Dual Cleanup Systems: SCHEDULED CLEANUP (TTL-based) + CHANNEL SWEEP (periodic + spam-triggered)
14. Dict Safety: Snapshot iteration prevents crashes during concurrent modifications
15. Permission Validation: Requires both Connect AND Speak permissions for voice operations
16. Performance Optimizations: Channel.members for voice checks, server-side message filtering, conditional logging

AUDIO PIPELINE:
--------------
Opus file → FFmpegOpusAudio (native passthrough) → Discord voice

Native opus playback = no re-encoding = less audio bugs
Files must be: 48kHz, stereo, 256kbps VBR, 20ms frames

FEATURES:
---------
- Queue navigation (!queue shows last + current + next QUEUE_DISPLAY_COUNT tracks)
- Library browsing (!library with pagination, LIBRARY_PAGE_SIZE per page)
- Track jumping (!play 32 jumps to track #32)
- Previous track (!previous with stop at beginning, no wrap-around)
- Shuffle mode (toggle with auto-reshuffle, !shuffle / !unshuffle)
- Multi-layer spam protection (prevents all abuse vectors)
- Resume from stop (remembers position)
- Channel switching (preserves playback state)
- Persistent channel memory (CHANNEL SWEEP resumes after restart)
- Automatic cleanup restoration (no manual intervention needed)

CLEANUP SYSTEMS:
---------------
DUAL CLEANUP ARCHITECTURE:
- SCHEDULED CLEANUP: Messages scheduled for deletion at specific times (TTL-based)
- CHANNEL SWEEP: Periodic history scan + manual spam cleanup (every HISTORY_CLEANUP_INTERVAL)

CLEANUP SYSTEMS EXPLAINED:
-------------------------
SCHEDULED CLEANUP (TTL-based):
- Individual messages get "expiration dates" when sent
- Bot checks every TTL_CHECK_INTERVAL seconds for expired messages
- Deletes messages when their time is up (like user commands after USER_COMMAND_TTL seconds)
- Works automatically in background, no manual triggering needed
- Examples: User commands (!play, !skip), bot responses, error messages

CHANNEL SWEEP (History scan):
- Scans recent channel history looking for bot messages and short user commands
- Runs automatically every HISTORY_CLEANUP_INTERVAL seconds (periodic)
- Also runs when spam detected (delayed trigger via _delayed_spam_cleanup)
- Deletes messages older than CLEANUP_SAFE_AGE_THRESHOLD to avoid deleting recent messages
- Catches messages that SCHEDULED CLEANUP might have missed (e.g., bot restarted)
- Examples: Old bot messages, missed user commands, spam cleanup

KEY DIFFERENCE:
- SCHEDULED CLEANUP = "Delete this specific message at this specific time" (TTL-based)
- CHANNEL SWEEP = "Look through channel history and clean up anything that should be gone" (history scan)

WHY BOTH SYSTEMS:
- SCHEDULED CLEANUP is fast and efficient for known messages
- CHANNEL SWEEP catches missed messages and handles edge cases
- Together they ensure clean chat with redundancy

CLEANUP ACTIVATION:
- First !play command sets text_channel and triggers initial CHANNEL SWEEP
- Spam detection triggers delayed CHANNEL SWEEP via _delayed_spam_cleanup() (waits SPAM_CLEANUP_DELAY seconds)
- Channel persistence (last_channels.json) remembers CHANNEL SWEEP target across restarts
- Restart recovery automatically resumes CHANNEL SWEEP in remembered channel

SPAM INTERACTION:
- When spam detected (USER_SPAM_WARNING_THRESHOLD+ rapid commands), spam warning message shown (if SPAM_WARNING_COOLDOWN+ seconds since last warning)
- CHANNEL SWEEP runs after SPAM_CLEANUP_DELAY delay to catch more spam and let users see warning message
- Resets cleanup timer to prevent double-cleanup
- Spam count resets after USER_SPAM_RESET_COOLDOWN seconds of no spam

ADDING NEW COMMANDS:
-------------------
See section "HOW TO ADD DEBOUNCING TO NEW COMMANDS" below for template.
All state-modifying commands should use the debounce system.

CUSTOMIZING MESSAGES:
--------------------
All bot text output is centralized in config/messages.py.
Edit the MESSAGES dict in that file to customize any message, error, or response the bot sends.
Supports string formatting with {placeholders} for dynamic content.
"""

import disnake
from disnake.ext import commands
import asyncio
import os
import sys
import re
import logging
import time
import random
import json
from pathlib import Path
from typing import Optional, List, Callable, Awaitable, Dict
from collections import deque
from enum import Enum
import itertools
from datetime import datetime, timedelta
from dotenv import load_dotenv
from functools import lru_cache
from config import *

# Load environment variables from .env file (if it exists)
# Falls back to system environment variables if .env not found
load_dotenv()

# =============================================================================
# LOGGING SETUP
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('jill')

# Reduce disnake noise - only show warnings and errors
# (Disnake is chatty about voice connections, we don't need the spam)
logging.getLogger('disnake').setLevel(logging.WARNING)
logging.getLogger('disnake.player').setLevel(logging.WARNING)
logging.getLogger('disnake.voice_state').setLevel(logging.WARNING)

# =============================================================================
# ENUMS
# =============================================================================

class PlaybackState(Enum):
    """
    Current state of voice playback.
    Used for cleaner state checking than multiple booleans.
    
    PLAYBACK STATES EXPLAINED:
    -------------------------
    IDLE: Bot is not playing anything (may or may not be connected to voice)
    PLAYING: Bot is actively playing a track
    PAUSED: Bot is connected and has a track loaded, but playback is paused
    
    State transitions:
    - IDLE → PLAYING: When !play starts a track
    - PLAYING → PAUSED: When !pause is used
    - PAUSED → PLAYING: When !play resumes
    - PLAYING/PAUSED → IDLE: When !stop or disconnect
    """
    IDLE = 0      # Not playing anything, may or may not be connected
    PLAYING = 1   # Currently playing a track
    PAUSED = 2    # Playback paused mid-track

# =============================================================================
# BOT SETUP
# =============================================================================

# Discord intents define what events the bot receives
intents = disnake.Intents.default()
intents.message_content = True  # Required to read command messages
intents.voice_states = True     # Required for voice channel events
intents.members = True           # Required to see all guild members (for auto-pause detection)

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None  # We provide custom !help command
)

# Watchdog task references (for clean cancellation on shutdown)
_playback_watchdog_task: Optional[asyncio.Task] = None
_alone_watchdog_task: Optional[asyncio.Task] = None

# Global presence state (bot-wide, not per-guild)
_last_presence_update: float = 0
_current_presence_text: Optional[str] = None

# =============================================================================
# HELPER FUNCTIONS (Discord API wrappers with error handling)
# =============================================================================

async def safe_disconnect(voice_client: Optional[disnake.VoiceClient], force: bool = True) -> bool:
    """
    Safely disconnect from voice channel with error handling.
    
    Args:
        voice_client: Voice client to disconnect (None is safe)
        force: Force disconnect even if playing
        
    Returns:
        bool: True if disconnected successfully, False otherwise
        
    Note:
        Logs errors at debug level since disconnect failures are non-critical.
    """
    if not voice_client:
        return False
    try:
        await voice_client.disconnect(force=force)
        return True
    except Exception as e:
        logger.debug("Disconnect failed (non-critical): %s", e)
        return False

async def safe_send(channel: Optional[disnake.TextChannel], content: str) -> Optional[disnake.Message]:
    """
    Safely send message to channel with error handling.
    
    Args:
        channel: Text channel to send to (None is safe)
        content: Message content
        
    Returns:
        Message object if sent successfully, None otherwise
        
    Note:
        Catches common Discord API errors:
        - NotFound: Channel was deleted
        - Forbidden: Bot lost permissions
        - HTTPException: Rate limited or other API error
    """
    if not channel:
        return None
    try:
        msg = await channel.send(content)
        return msg
    except (disnake.NotFound, disnake.Forbidden, disnake.HTTPException) as e:
        logger.debug("Could not send message: %s", e)
        return None

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
        return True
    except Exception as e:
        logger.debug("Voice state change failed (non-critical): %s", e)
        return False

async def update_presence(status_text: Optional[str]) -> bool:
    """
    Update bot's Discord presence (status shown under bot name).
    
    Global throttling and deduplication to avoid spammy API calls.
    
    Args:
        status_text: Status to display (None = clear status)
        
    Returns:
        bool: True if updated successfully, False otherwise
        
    Example:
        update_presence("Hopes and Dreams")  # Shows "Listening to Hopes and Dreams"
    """
    global _last_presence_update, _current_presence_text
    
    current_time = time.time()
    
    # Skip if same text and within throttle window
    if status_text == _current_presence_text and current_time - _last_presence_update < 10:
        return True
    
    try:
        if status_text:
            await bot.change_presence(activity=disnake.Activity(
                type=disnake.ActivityType.listening,
                name=status_text
            ))
        else:
            await bot.change_presence(activity=None)
        
        _last_presence_update = current_time
        _current_presence_text = status_text
        return True
    except Exception as e:
        logger.debug("Presence update failed (non-critical): %s", e)
        return False

def can_connect_to_channel(channel: disnake.VoiceChannel) -> bool:
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
        bool: True if deleted successfully or already deleted, False on permission/API errors
        
    Note:
        Catches common errors:
        - NotFound: Message already deleted (returns True - idempotent success)
        - Forbidden: Bot lacks permissions (returns False)
        - HTTPException: Rate limited or other API error (returns False)
    """
    if not message:
        return False
    try:
        await message.delete()
        return True
    except disnake.NotFound:
        return True  # Already deleted = success (idempotent)
    except (disnake.Forbidden, disnake.HTTPException) as e:
        logger.debug("Could not delete message: %s", e)
        return False

def make_audio_source(path: str):
    """
    Create FFmpegOpusAudio source for playback.
    
    Creates a fresh audio source for each playback - audio sources are
    single-use and cannot be reused after consumption.
    
    Args:
        path: Path to opus audio file
        
    Returns:
        FFmpegOpusAudio: Cached audio source object
    """
    return disnake.FFmpegOpusAudio(path, before_options='-re -nostdin -fflags +nobuffer')

# =============================================================================
# CHANNEL PERSISTENCE FUNCTIONS
# =============================================================================

# Cache for loaded channel data to avoid repeated file I/O
_channel_cache: Dict[int, int] = {}
_cache_loaded = False
# Async batch save optimization: reduces filesystem writes by batching channel saves
_last_save_task = None
_pending_saves = set()

def load_last_channels() -> Dict[int, int]:
    """
    Load the last used text channel IDs from persistent storage.
    
    Returns:
        Dict[int, int]: Mapping of guild_id -> channel_id
    """
    global _channel_cache, _cache_loaded
    
    # Return cached data if already loaded
    if _cache_loaded:
        return _channel_cache.copy()
    
    try:
        if os.path.exists(CHANNEL_STORAGE_FILE):
            with open(CHANNEL_STORAGE_FILE, 'r') as f:
                data = json.load(f)
                # Convert string keys back to integers (only when needed)
                _channel_cache = {int(guild_id): channel_id for guild_id, channel_id in data.items()}
        else:
            _channel_cache = {}
        
        _cache_loaded = True
        return _channel_cache.copy()
        
    except (json.JSONDecodeError, ValueError, FileNotFoundError) as e:
        logger.warning(f"Could not load channel storage: {e}")
        _channel_cache = {}
        _cache_loaded = True
        return {}

def save_last_channel(guild_id: int, channel_id: int) -> None:
    """
    Save the last used text channel ID for a guild.
    
    Args:
        guild_id: Discord guild ID
        channel_id: Discord channel ID
    """
    global _channel_cache, _cache_loaded
    
    try:
        # Use cached data if available, otherwise load
        if not _cache_loaded:
            load_last_channels()
        
        # Only save if channel actually changed (avoid unnecessary I/O)
        if _channel_cache.get(guild_id) != channel_id:
            _channel_cache[guild_id] = channel_id
            mark_channel_dirty(guild_id)
            
    except Exception as e:
        logger.warning(f"Could not save channel storage: {e}")

def mark_channel_dirty(guild_id: int):
    """
    Mark a guild's channel data as dirty for batch saving.
    
    This optimization reduces filesystem writes by batching channel saves
    with a 10-second delay instead of immediate writes on every change.
    
    Args:
        guild_id: Discord guild ID to mark as dirty
    """
    _pending_saves.add(guild_id)
    global _last_save_task
    if not _last_save_task or _last_save_task.done():
        _last_save_task = asyncio.create_task(_flush_channel_saves())

async def _flush_channel_saves():
    """
    Flush all pending channel saves to disk after a 10-second delay.
    
    This async batch save operation reduces I/O overhead by writing
    multiple channel changes in a single filesystem operation.
    """
    await asyncio.sleep(10)
    if not _pending_saves:
        return
    
    # Snapshot and clear to avoid RuntimeError from concurrent modifications
    to_save = list(_pending_saves)
    _pending_saves.clear()
    
    data = load_last_channels()
    for gid in to_save:
        data[gid] = _channel_cache[gid]
    with open(CHANNEL_STORAGE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# =============================================================================
# TRACK CLASS
# =============================================================================

class Track:
    """
    Represents a single music track with unique identity.
    
    Attributes:
        track_id: Unique identifier (auto-incremented)
        opus_path: Full path to .opus file
        library_index: Position in master library (immutable)
        display_name: Formatted name for display (without number prefix/extension)
        
    Design notes:
        - Each track gets a unique ID to prevent object reference bugs
        - library_index is the track's position in the sorted library (never changes)
        - display_name strips "01 - " prefix and ".opus" extension for clean display
        - Equality based on track_id, not file path (survives file moves)
    """
    
    _next_id = 0  # Class variable: auto-incrementing ID counter
    _prefix_re = re.compile(r'^\d+\s*-\s*')  # Precompiled regex for numeric prefix removal
    
    def __init__(self, opus_path: Path, library_index: int):
        """
        Create a new track.
        
        Args:
            opus_path: Full path to the .opus file
            library_index: Position in sorted library (0-based)
        """
        self.track_id = Track._next_id
        Track._next_id += 1
        self.opus_path = opus_path
        self.library_index = library_index
        self.display_name = self._get_display_name()
        
    def _get_display_name(self) -> str:
        """
        Format filename for display.
        
        Removes:
            - Leading numbers and dash ("01 - ")
            - File extension (case-insensitive)
            
        Example:
            "01 - Hopes and Dreams.opus" → "Hopes and Dreams"
        """
        name = self.opus_path.stem  # Filename without extension (case-insensitive)
        name = Track._prefix_re.sub('', name)  # Remove "01 - " using precompiled regex
        return name
    
    def __eq__(self, other) -> bool:
        """Tracks are equal if they have the same ID."""
        return isinstance(other, Track) and self.track_id == other.track_id
    
    def __hash__(self) -> int:
        """Hash based on ID allows tracks to be used in sets/dicts."""
        return hash(self.track_id)
    
    def __repr__(self) -> str:
        """Debug representation."""
        return f"Track(id={self.track_id}, name={self.display_name})"

# Note: HistoryEntry class removed - was unused dead code
# History with timestamps can be re-added in the future if needed

# =============================================================================
# MUSIC PLAYER CLASS (Per-Guild State)
# =============================================================================

class MusicPlayer:
    """
    Per-guild music player with multi-layer spam protection.
    
    Each Discord server (guild) gets its own independent MusicPlayer instance.
    This prevents servers from interfering with each other.
    
    QUEUE MODEL:
    -----------
    played ← now_playing → upcoming
    
    QUEUE MODEL EXPLAINED:
    ---------------------
    played: List of tracks already played (for !previous command)
    now_playing: Current track (or None if stopped)
    upcoming: Deque of tracks to play next
    
    Navigation:
    - !queue shows: [last played] ← [now playing] → [next QUEUE_DISPLAY_COUNT tracks]
    - !previous goes back through played list
    - !skip advances to next track in upcoming
    - !play [number] jumps to specific track in library
    
    Auto-loop behavior:
    - When upcoming queue is empty, it resets to full library
    - In shuffle mode, each loop generates a new random order
    - In normal mode, each loop uses canonical order (01, 02, 03...)
    
    SHUFFLE MODE:
    ------------
    - shuffle_enabled: Toggle flag (default False)
    - When ON: Queue is shuffled on reset, auto-reshuffles on loop
    - When OFF: Queue uses canonical library order (01, 02, 03...)
    - Library always maintains canonical order for track lookups
    - !play [number] works the same in both modes
    
    COMMAND PROCESSING:
    ------------------
    All state-modifying commands go through a serial queue:
    1. Commands are validated
    2. Commands are debounced (spam detection)
    3. Commands are queued
    4. Queue processor executes ONE at a time
    
    This eliminates race conditions entirely.
    """
    
    def __init__(self, guild_id: int):
        """
        Initialize a new music player for a guild.
        
        Args:
            guild_id: Discord guild (server) ID
        """
        self.guild_id = guild_id
        
        # =====================================================================
        # MUSIC LIBRARY & QUEUE
        # =====================================================================
        
        self.library: List[Track] = []              # All available tracks (immutable)
        self.track_by_index: Dict[int, Track] = {}  # Fast lookup by library_index
        self.played: deque[Track] = deque(maxlen=MAX_HISTORY)  # Already played (for !previous) with automatic size limit
        self.now_playing: Optional[Track] = None    # Current track
        self.upcoming: deque[Track] = deque()       # Upcoming tracks (mutable queue)
        
        # =====================================================================
        # STATE TRACKING
        # =====================================================================
        
        self.state: PlaybackState = PlaybackState.IDLE
        self.shuffle_enabled: bool = False               # Shuffle mode toggle
        
        # =====================================================================
        # VOICE CONNECTION
        # =====================================================================
        
        self.voice_client: Optional[disnake.VoiceClient] = None  # Discord voice connection
        self.text_channel: Optional[disnake.TextChannel] = None  # Where to send messages
        
        # Channel loading is done asynchronously after bot is ready
        # to prevent race conditions during startup
        
        # =====================================================================
        # COMMAND QUEUE (LAYER 4: Serialization)
        # =====================================================================
        
        self._command_queue: asyncio.Queue = asyncio.Queue(maxsize=COMMAND_QUEUE_MAXSIZE)  # Bounded to prevent memory exhaustion
        self._processor_task: Optional[asyncio.Task] = None              # Queue processor task
        
        # =====================================================================
        # UI STATE
        # =====================================================================
        
        # Rotating drink emojis for "Now serving" messages
        self._drink_cycle = itertools.cycle(DRINK_EMOJIS)
        
        # =====================================================================
        # SPAM PROTECTION
        # =====================================================================
        
        # LAYER 0: Per-user spam filter
        # Tracks when each user last sent ANY command
        self._user_last_command: dict[int, float] = {}  # user_id → timestamp
        self._user_spam_count: dict[int, int] = {}      # user_id → spam count
        
        # LAYER 2: Global rate limiter
        # Rate limiter: Commands must wait GLOBAL_RATE_LIMIT seconds between each other
        self._last_queue_time: float = 0
        
        # LAYER 3: Generic debouncing system
        # Each command type has its own debounce tracking
        self._debounce_tasks: dict[str, object] = {}  # command_name → task/handle (Task or call_later handle)
        self._spam_counts: dict[str, int] = {}              # command_name → count
        self._spam_warned: dict[str, bool] = {}             # command_name → warned
        self._last_execute: dict[str, float] = {}           # command_name → timestamp
        
        # LAYER 5: Per-command cooldowns
        # These are managed by debounce system, but play/reconnect need manual tracking
        self._last_play_time: float = 0
        self._last_callback_time: float = 0
        self._last_reconnect_time: float = 0
        
        # =====================================================================
        # FLAGS & WATCHDOG
        # =====================================================================
        
        self._is_reconnecting: bool = False      # Blocks callbacks during channel switches
        self._suppress_callback: bool = False    # Blocks callbacks during manual track changes
        
        # Watchdog tracking (detects hung FFmpeg processes)
        self._last_track_start: float = 0
        self._last_track_id: Optional[int] = None
        
        # =====================================================================
        # AUTO-PAUSE WHEN ALONE
        # =====================================================================
        
        self._alone_since: Optional[float] = None  # Timestamp when bot became alone
        self._was_playing_before_alone: bool = False  # Whether to auto-resume
        self._last_connect_time: Optional[float] = None  # When bot last connected (for grace period)
        
        # =====================================================================
        # MESSAGE CLEANUP
        # =====================================================================
        
        self._message_cleanup_queue: List[tuple[disnake.Message, float]] = []  # (msg, delete_time)
        self._cleanup_task: Optional[asyncio.Task] = None  # Background cleanup worker
        self._cleanup_event = asyncio.Event()  # Event-driven wake optimization: avoids idle polling
        self._last_now_playing_msg: Optional[disnake.Message] = None  # Track to delete early
        self._last_history_cleanup: float = 0  # Last time we did full history cleanup
        self._last_spam_warning_time: float = 0  # Last time we sent a spam warning message
        # Note: Presence update throttling is global (see update_presence function)
        
    # =========================================================================
    # COMMAND QUEUE PROCESSOR
    # =========================================================================
    
    def start_processor(self):
        """
        Start the command processor task.
        
        The processor runs in the background and executes queued commands
        one at a time. This is LAYER 4 of spam protection.
        
        Called automatically when player is created.
        """
        if not self._processor_task:
            self._processor_task = asyncio.create_task(self._process_commands())
            logger.info("Guild %s: Command processor started", self.guild_id)
    
    async def _process_commands(self):
        """
        Process commands from queue serially.
        
        This is the heart of our race condition prevention:
        - Commands execute ONE at a time
        - No concurrent state modifications possible
        - Simple, bulletproof
        
        Runs forever in background as an asyncio task.
        """
        while True:
            try:
                cmd = await self._command_queue.get()
                try:
                    await cmd()  # Execute the command
                finally:
                    self._command_queue.task_done()
            except Exception as e:
                logger.error(f"Guild {self.guild_id}: Command processor error: {e}", exc_info=True)
    
    async def queue_command(self, cmd: Callable[[], Awaitable[None]], priority: bool = False):
        """
        Queue a command for serial execution with optional priority handling.
        
        Args:
            cmd: Async function to execute
            priority: If True, command gets priority in queue (for critical operations)
            
        Note:
            Command will execute when all previous commands finish.
            This is how we prevent race conditions.
            Queue is bounded to prevent memory exhaustion attacks.
        """
        # Early validation: Check queue health before attempting to queue
        if self._command_queue.qsize() >= COMMAND_QUEUE_MAXSIZE * 0.9:  # 90% full
            logger.warning(f"Guild {self.guild_id}: Command queue nearly full ({self._command_queue.qsize()}/{COMMAND_QUEUE_MAXSIZE}), dropping command")
            return
            
        try:
            if priority:
                # For priority commands, use a shorter timeout
                await asyncio.wait_for(
                    self._command_queue.put(cmd),
                    timeout=COMMAND_QUEUE_TIMEOUT * 0.5  # Half timeout for priority
                )
            else:
                await asyncio.wait_for(
                    self._command_queue.put(cmd),
                    timeout=COMMAND_QUEUE_TIMEOUT  # Don't wait forever if queue is full
                )
        except asyncio.TimeoutError:
            logger.warning(f"Guild {self.guild_id}: Command queue full, dropping command")
    
    # =========================================================================
    # SPAM PROTECTION (LAYERS 0-3)
    # =========================================================================
    
    async def check_user_spam(self, user_id: int, command_name: str, ctx: commands.Context) -> bool:
        """
        LAYER 0: Check if user is spamming ANY commands.
        
        Prevents a single user from flooding the bot with any commands,
        which would spam error messages and waste resources.
        
        Shows warning message after multiple spam attempts.
        
        Args:
            user_id: Discord user ID
            command_name: Name of command being spammed (for specific messages)
            ctx: Discord context (for sending spam warnings)
            
        Returns:
            bool: True if spam detected (command should be silently ignored)
            
        Threshold:
            0.7 seconds between ANY commands from the same user
            3+ spam attempts = you get a warning (ONCE, then stays quiet)
        """
        current_time = time.time()
        last_time = self._user_last_command.get(user_id, 0)
        
        if current_time - last_time < USER_COMMAND_SPAM_THRESHOLD:
            # Spam detected! Increment counter
            self._user_spam_count[user_id] = self._user_spam_count.get(user_id, 0) + 1
            
            # Show spam warning message after exactly USER_SPAM_WARNING_THRESHOLD rapid fire attempts (but only ONCE until cooldown expires)
            if self._user_spam_count[user_id] == USER_SPAM_WARNING_THRESHOLD:  # Uses == so it only fires ONCE
                # Send command-specific warning if we have a message for it
                if SPAM_WARNING_ENABLED:
                    spam_key = f'spam_{command_name}'
                    if spam_key in MESSAGES and MESSAGES[spam_key]:
                        await safe_send(self.text_channel, MESSAGES[spam_key])
                        
                        # Only schedule cleanup if we haven't sent spam warning in last minute
                        if current_time - self._last_spam_warning_time > SPAM_WARNING_COOLDOWN:
                            asyncio.create_task(self._delayed_spam_cleanup())
                            self._last_spam_warning_time = current_time
            
            return True  # Spam detected, ignore command
        
        # Not spam - reset counters and update timestamp
        # BUT only reset if enough time has passed (USER_SPAM_RESET_COOLDOWN seconds of no spam)
        if current_time - last_time > USER_SPAM_RESET_COOLDOWN:  # Reset spam count after USER_SPAM_RESET_COOLDOWN seconds of no spam
            self._user_spam_count[user_id] = 0
        
        self._user_last_command[user_id] = current_time
        
        # OPTIMIZED MEMORY LEAK PREVENTION: Keep only recent users (max 1000)
        # More efficient cleanup using list comprehension and batch operations
        if len(self._user_last_command) > 1000:
            # Remove oldest 200 entries (keep most recent 800)
            # Use more efficient sorting and batch removal
            current_time = time.time()
            cutoff_time = current_time - 3600  # Remove users inactive for 1 hour
            
            # Batch remove old entries
            old_users = [user_id for user_id, timestamp in self._user_last_command.items() 
                        if timestamp < cutoff_time]
            
            for user_id in old_users[:200]:  # Limit to 200 removals per cleanup
                self._user_last_command.pop(user_id, None)
                self._user_spam_count.pop(user_id, None)
        
        return False
    
    def check_global_rate_limit(self) -> bool:
        """
        LAYER 2: Check global rate limit (max 5 commands/sec into queue).
        
        Prevents queue flooding and protects Discord API from rate limiting.
        
        Returns:
            bool: True if rate limit hit (command should be silently ignored)
            
        Threshold:
            GLOBAL_RATE_LIMIT seconds = max 5 commands per second
        """
        if not SPAM_PROTECTION_ENABLED:
            return False  # No rate limiting when spam protection disabled
            
        current_time = time.time()
        
        if current_time - self._last_queue_time < GLOBAL_RATE_LIMIT:
            return True  # Rate limit hit
        
        self._last_queue_time = current_time
        return False
    
    async def debounce_command(
        self,
        command_name: str,
        ctx: commands.Context,
        execute_func: Callable[[], Awaitable[None]],
        debounce_window: float,
        cooldown: float,
        spam_threshold: int = 5,
        spam_message: Optional[str] = None
    ):
        """
        LAYER 3: Generic command debouncing system.
        
        Waits for spam to stop, then executes command once.
        This is the key to handling Discord rate-limited spam.
        
        How it works:
        1. Each command restarts a timer
        2. If commands keep coming, timer keeps restarting
        3. When spam stops (no command for debounce_window seconds), execute
        4. Show spam warning if spam_threshold reached
        
        Args:
            command_name: Unique identifier for command type (e.g., "skip")
            ctx: Discord context (for sending messages)
            execute_func: Async function to execute after debounce completes
            debounce_window: How long to wait for spam to stop (seconds)
            cooldown: Cooldown after execution (seconds)
            spam_threshold: Show warning after N rapid commands (default: 5)
            spam_message: Optional spam warning message to show on spam
            
        Example:
            await player.debounce_command(
                "skip",
                ctx,
                lambda: _execute_skip(ctx),
                3.0,   # Wait 3s for spam to stop
                2.0,   # 2s cooldown after
                5,     # Warn after 5 rapid skips
                "Easy there, hotshot..."
            )
            
        Why this works:
            - Discord rate limits: Messages arrive slowly (1/sec)
            - Debounce window (3s) catches this slow spam
            - Only ONE command executes after spam stops
            - Cooldown prevents immediate re-trigger
        """
        # If spam protection is disabled, execute immediately without debouncing
        if not SPAM_PROTECTION_ENABLED:
            await execute_func()
            return
            
        # Check post-execution cooldown (LAYER 5)
        last_time = self._last_execute.get(command_name, 0)
        current_time = time.time()
        
        if current_time - last_time < cooldown:
            logger.debug("Guild %s: %s on cooldown", self.guild_id, command_name)
            return
        
        # Increment spam counter
        self._spam_counts[command_name] = self._spam_counts.get(command_name, 0) + 1
        
        # Cancel previous debounce timer (this is the debouncing magic)
        # Each new command restarts the timer
        handle = self._debounce_tasks.get(command_name)
        if handle and not handle.cancelled():
            handle.cancel()
        
        # Show spam warning if threshold reached (only once per spam session)
        if self._spam_counts[command_name] >= spam_threshold:
            if not self._spam_warned.get(command_name, False):
                self._spam_warned[command_name] = True
                if SPAM_WARNING_ENABLED and spam_message:
                    await safe_send(self.text_channel, spam_message)
        
        # Start debounce timer using loop.call_later (reduces task creation overhead)
        def _run_debounced():
            asyncio.create_task(self.queue_command(execute_func))
            self._last_execute[command_name] = time.time()
            self._spam_counts[command_name] = 0
            self._spam_warned[command_name] = False
        
        self._debounce_tasks[command_name] = bot.loop.call_later(debounce_window, _run_debounced)
    
    # =========================================================================
    # MESSAGE CLEANUP SYSTEM
    # =========================================================================
    
    def start_cleanup_worker(self):
        """
        Start the message cleanup background task.
        
        The worker has TWO jobs:
        1. Check TTL expiry queue every TTL_CHECK_INTERVAL (SYSTEM 1)
        2. Scan channel history every HISTORY_CLEANUP_INTERVAL (SYSTEM 2)
        
        Called automatically when player is created.
        """
        if not AUTO_CLEANUP_ENABLED:
            logger.info("Guild %s: Auto cleanup disabled - skipping cleanup worker startup", self.guild_id)
            return
            
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self._cleanup_messages())
            logger.info("Guild %s: Message cleanup worker started", self.guild_id)
    
    async def _cleanup_messages(self):
        """
        Background worker that handles BOTH cleanup systems.
        
        SCHEDULED CLEANUP: Checks scheduled deletions every TTL_CHECK_INTERVAL seconds
        CHANNEL SWEEP: Scans channel history every HISTORY_CLEANUP_INTERVAL seconds
        
        CLEANUP SYSTEM INTERACTIONS:
        ---------------------------
        1. FIRST !PLAY COMMAND: Sets text_channel and triggers initial CHANNEL SWEEP
        2. SPAM DETECTION: Triggers delayed CHANNEL SWEEP via _delayed_spam_cleanup() (waits SPAM_CLEANUP_DELAY seconds)
        3. CHANNEL PERSISTENCE: last_channels.json remembers CHANNEL SWEEP target across restarts
        4. RESTART RECOVERY: CHANNEL SWEEP resumes automatically in remembered channel
        
        SPAM INTERACTION:
        - When spam detected (USER_SPAM_WARNING_THRESHOLD+ rapid commands), spam warning message shown (if SPAM_WARNING_COOLDOWN+ seconds since last warning)
        - Runs CHANNEL SWEEP after SPAM_CLEANUP_DELAY delay to catch more spam and let users see warning message
        - Resets HISTORY_CLEANUP_INTERVAL timer to prevent double-cleanup
        - Spam count resets after USER_SPAM_RESET_COOLDOWN seconds of no spam
        
        All timing values are configurable in the config/timing.py file.
        """
        # Early return if cleanup is disabled
        if not AUTO_CLEANUP_ENABLED:
            return
            
        # Run initial CHANNEL SWEEP on startup if needed
        if AUTO_CLEANUP_ENABLED and self._last_history_cleanup == 0 and self.text_channel:
            await self.cleanup_channel_history()
            self._last_history_cleanup = time.time()
        
        while True:
            try:
                # Event-driven wake optimization: wait for new messages or timeout
                try:
                    await asyncio.wait_for(self._cleanup_event.wait(), timeout=TTL_CHECK_INTERVAL)
                    self._cleanup_event.clear()
                except asyncio.TimeoutError:
                    pass  # Normal tick - no new messages, proceed with routine cleanup
                
                current_time = time.time()
                
                # ===================================================================
                # CHANNEL SWEEP: Periodic history cleanup (every HISTORY_CLEANUP_INTERVAL seconds)
                # ===================================================================
                if AUTO_CLEANUP_ENABLED and current_time - self._last_history_cleanup >= HISTORY_CLEANUP_INTERVAL:
                    await self.cleanup_channel_history()
                    self._last_history_cleanup = current_time
                
                # ===================================================================
                # SCHEDULED CLEANUP: TTL-based cleanup (check scheduled deletions)
                # ===================================================================
                
                # Skip TTL cleanup if nothing to clean (optimization for small scale)
                if not self._message_cleanup_queue and not self._last_now_playing_msg:
                    continue
                if self._message_cleanup_queue:
                    messages_to_delete = []
                    remaining_messages = []
                    
                    # Process all messages: delete expired (unless protected), keep the rest
                    for msg, delete_time in self._message_cleanup_queue:
                        if current_time >= delete_time:
                            # CRITICAL: Don't delete current "now serving" message if music is playing
                            if msg == self._last_now_playing_msg and self.voice_client and self.voice_client.is_playing():
                                remaining_messages.append((msg, delete_time))  # Keep protected message in queue
                                continue
                            messages_to_delete.append(msg)
                        else:
                            # Not expired yet, keep in queue
                            remaining_messages.append((msg, delete_time))
                    
                    # Update queue (remove deleted messages, keep skipped + non-expired)
                    self._message_cleanup_queue = remaining_messages
                    
                    # Delete expired messages in bulk batches to avoid rate limits
                    batch_size = CLEANUP_BATCH_SIZE
                    delay_between_batches = CLEANUP_BATCH_DELAY  # Wait CLEANUP_BATCH_DELAY seconds between cleanup batches
                    
                    for i in range(0, len(messages_to_delete), batch_size):
                        batch = messages_to_delete[i:i + batch_size]
                        
                        # Use bulk delete if multiple messages, individual delete if just one
                        if BATCH_DELETE_ENABLED and len(batch) > 1:
                            try:
                                await self.text_channel.delete_messages(batch)
                            except Exception as e:
                                logger.debug("Guild %s: Bulk delete failed, falling back to individual: %s", self.guild_id, e)
                                # Fallback to individual deletes
                                for msg in batch:
                                    await safe_delete_message(msg)
                        else:
                            # Batch delete disabled or single message - use sequential individual delete
                            for msg in batch:
                                await safe_delete_message(msg)
                                await asyncio.sleep(0.2)  # Rate limit protection: ~5 deletes/sec
                        
                        # Wait between batches (except for the last batch)
                        if i + batch_size < len(messages_to_delete):
                            await asyncio.sleep(delay_between_batches)
                    
                    if messages_to_delete:
                        logger.debug("Guild %s: Cleaned up %d expired messages", self.guild_id, len(messages_to_delete))
                    
            except Exception as e:
                logger.error(f"Guild {self.guild_id}: Message cleanup worker error: {e}", exc_info=True)
    
    async def schedule_message_deletion(self, message: Optional[disnake.Message], ttl_seconds: float):
        """
        Schedule a message for deletion after TTL expires with smart scheduling.
        
        Args:
            message: Message to delete (None is safe to pass)
            ttl_seconds: Time to live in seconds
        """
        if not message:
            return
        
        delete_time = time.time() + ttl_seconds
        
        # OPTIMIZATION: Use binary search for insertion to keep queue sorted
        # This reduces cleanup processing time from O(n) to O(log n)
        insert_pos = 0
        for i, (_, existing_time) in enumerate(self._message_cleanup_queue):
            if existing_time <= delete_time:
                insert_pos = i + 1
            else:
                break
        
        self._message_cleanup_queue.insert(insert_pos, (message, delete_time))
        
        # Event-driven wake optimization: signal cleanup worker to wake up
        self._cleanup_event.set()
    
    async def send_with_ttl(
        self,
        channel: Optional[disnake.TextChannel],
        content: str,
        ttl_type: str,
        user_message: Optional[disnake.Message] = None
    ) -> Optional[disnake.Message]:
        """
        Send a message and schedule it for deletion after TTL.
        
        Args:
            channel: Text channel to send to
            content: Message content
            ttl_type: Type of message (key in MESSAGE_TTL dict)
            user_message: Optional user command message to also delete
            
        Returns:
            The sent message, or None if send failed
            
        Note:
            Both bot response and user command (if provided) will be deleted
            after the same TTL expires.
        """
        if not channel:
            return None
        
        # Get TTL for this message type
        ttl_seconds = MESSAGE_TTL.get(ttl_type, MESSAGE_TTL['error'])
        
        # Send bot message
        bot_msg = await safe_send(channel, content)
        if not bot_msg:
            return None
        
        # Schedule bot message deletion
        if TTL_CLEANUP_ENABLED:
            await self.schedule_message_deletion(bot_msg, ttl_seconds)
        
        # Also schedule user command deletion (if provided)
        if user_message and TTL_CLEANUP_ENABLED:
            await self.schedule_message_deletion(user_message, ttl_seconds)
        
        return bot_msg
    
    async def _delayed_spam_cleanup(self):
        """
        Clean up spam messages and warning response after SPAM_CLEANUP_DELAY seconds.
        Also resets the cleanup timer to be nice to Discord API.
        
        SPAM CLEANUP INTERACTION:
        ------------------------
        - Triggers when spam detected (Layer 0 spam filter: USER_SPAM_WARNING_THRESHOLD+ rapid commands in USER_COMMAND_SPAM_THRESHOLD seconds)
        - Shows spam warning message only if SPAM_WARNING_COOLDOWN+ seconds since last warning
        - Runs CHANNEL SWEEP after SPAM_CLEANUP_DELAY delay to catch more spam and let users see warning message
        - Resets _last_history_cleanup timer to prevent double-cleanup
        - Spam count resets after USER_SPAM_RESET_COOLDOWN seconds of no spam
        
        This prevents spam from accumulating while being respectful to Discord API.
        
        Timing is configurable in the config/timing.py file.
        """
        # Early return if cleanup is disabled
        if not AUTO_CLEANUP_ENABLED:
            return
            
        try:
            # Wait SPAM_CLEANUP_DELAY seconds to catch more spam and let user see the warning message
            await asyncio.sleep(SPAM_CLEANUP_DELAY)
            
            # Run cleanup manually
            if AUTO_CLEANUP_ENABLED:
                await self.cleanup_channel_history()
            
            # Reset the cleanup timer so we don't run again for another HISTORY_CLEANUP_INTERVAL seconds
            self._last_history_cleanup = time.time()
            
            logger.debug("Guild %s: Spam cleanup completed, timer reset", self.guild_id)
            
        except Exception as e:
            logger.error(f"Guild {self.guild_id}: Spam cleanup error: {e}", exc_info=True)
    
    async def delete_last_now_playing(self):
        """
        Immediately delete the last "Now serving" message.
        
        Called when a new track starts to keep only the current track visible.
        Also removes it from cleanup queue to avoid double-deletion.
        """
        if not self._last_now_playing_msg:
            return
        
        # Remove from cleanup queue
        self._message_cleanup_queue = [
            (msg, delete_time) 
            for msg, delete_time in self._message_cleanup_queue 
            if msg.id != self._last_now_playing_msg.id
        ]
        
        # Delete immediately
        await safe_delete_message(self._last_now_playing_msg)
        self._last_now_playing_msg = None
    
    async def cleanup_channel_history(self):
        """
        Clean up bot messages and short user commands from recent channel history.
        
        Called periodically (every HISTORY_CLEANUP_INTERVAL seconds) to:
        - Remove bot messages that didn't get deleted (e.g., bot restarted)
        - Remove user command messages (short messages starting with !)
        
        Uses TTL-aware cleanup: only deletes messages older than CLEANUP_SAFE_AGE_THRESHOLD.
        This prevents deleting messages users might still be reading.
        
        All timing values are configurable in the config/timing.py file.
        """
        # Early return if cleanup is disabled
        if not AUTO_CLEANUP_ENABLED:
            return
            
        if not self.text_channel or CLEANUP_HISTORY_LIMIT <= 0:
            return
        
        try:
            # Look at the last CLEANUP_HISTORY_LIMIT messages in the channel to find old messages to delete
            messages_to_delete = []
            current_time = time.time()
            safe_age_threshold = CLEANUP_SAFE_AGE_THRESHOLD  # Configurable safe age threshold
            
            # Use server-side filter to only fetch old messages
            cutoff_dt = datetime.utcnow() - timedelta(seconds=safe_age_threshold)
            
            # Track the most recent message from other bots (keep one visible)
            other_bot_messages = []
            
            async for message in self.text_channel.history(limit=CLEANUP_HISTORY_LIMIT, before=cutoff_dt, oldest_first=False):
                # Skip the current "now serving" message (keep it visible)
                if message == self._last_now_playing_msg:
                    continue
                
                # All messages here are guaranteed old (fetched with before filter)
                # Handle our bot's messages (use ID comparison for reliability)
                if message.author and message.author.id == bot.user.id:
                    messages_to_delete.append(message)
                
                # Handle other bots' messages
                elif DELETE_OTHER_BOTS and message.author.bot:
                    other_bot_messages.append(message)
                
                # Handle user commands
                elif message.content.startswith('!') and len(message.content) <= USER_COMMAND_MAX_LENGTH:
                    messages_to_delete.append(message)
            
            # For other bots: keep the most recent message, delete older ones
            if other_bot_messages:
                # Keep the first message (newest due to oldest_first=False), delete the rest
                for message in other_bot_messages[1:]:
                    messages_to_delete.append(message)
            
            # Delete them in bulk batches to avoid rate limits
            batch_size = CLEANUP_BATCH_SIZE
            delay_between_batches = CLEANUP_BATCH_DELAY  # CLEANUP_BATCH_DELAY delay between batches
            deleted_count = 0
            
            for i in range(0, len(messages_to_delete), batch_size):
                batch = messages_to_delete[i:i + batch_size]
                
                # Use bulk delete if multiple messages, individual delete if just one
                if BATCH_DELETE_ENABLED and len(batch) > 1:
                    try:
                        await self.text_channel.delete_messages(batch)
                        deleted_count += len(batch)
                    except Exception as e:
                        logger.debug("Guild %s: Bulk delete failed, falling back to individual: %s", self.guild_id, e)
                        # Fallback to sequential individual deletes
                        for msg in batch:
                            if await safe_delete_message(msg):
                                deleted_count += 1
                            await asyncio.sleep(0.2)  # Rate limit protection: ~5 deletes/sec
                else:
                    # Batch delete disabled or single message - use sequential individual delete
                    for msg in batch:
                        if await safe_delete_message(msg):
                            deleted_count += 1
                        await asyncio.sleep(0.2)  # Rate limit protection: ~5 deletes/sec
                
                # Wait between batches (except for the last batch)
                if i + batch_size < len(messages_to_delete):
                    await asyncio.sleep(delay_between_batches)
            
            if deleted_count > 0:
                logger.debug("Guild %s: History cleanup removed %d messages", self.guild_id, deleted_count)
                
        except Exception as e:
            logger.debug("Guild %s: History cleanup failed (non-critical): %s", self.guild_id, e)
    
    # =========================================================================
    # AUTO-PAUSE WHEN ALONE
    # =========================================================================
    
    def is_alone_in_channel(self, log_result: bool = False) -> bool:
        """
        Check if bot is alone in voice channel (no human users).
        
        Args:
            log_result: If True, log the result at INFO level (for debugging/state changes)
        
        Returns:
            bool: True if bot is alone or not connected, False if users present
            
        Note:
            Iterates through guild members to check who's in the voice channel.
            This is more reliable than channel.members which relies on cache.
        """
        if not self.voice_client or not self.voice_client.is_connected():
            return True
        
        channel = self.voice_client.channel
        if not channel:
            return True
        
        guild = channel.guild
        if not guild:
            return True
        
        # Count human members in this channel by checking each member's voice state
        human_count = 0
        # Get members directly from the channel (much more efficient than scanning all guild members)
        members = list(channel.members)
        human_count = sum(1 for m in members if not m.bot)
        
        # Only build expensive string if logging is enabled
        if logger.isEnabledFor(logging.INFO):
            member_names = [f"{m.name}(bot={m.bot})" for m in members]
        else:
            member_names = []
        
        is_alone = human_count == 0
        
        # Optional logging (only when requested, e.g., on state changes)
        if log_result:
            logger.info(
                "Guild %s: Alone check - Channel: %s, Total: %d, Humans: %d, Alone: %s, Members: %s",
                self.guild_id, channel.name, len(member_names), human_count, is_alone, member_names
            )
        
        return is_alone
    
    async def handle_alone_state(self):
        """
        Handle bot being alone in voice channel.
        
        Timeline:
        - 0s: User leaves, bot is alone
        - 10s: Auto-pause (if playing)
        - 10min: Auto-disconnect
        
        Called by on_voice_state_update when voice states change.
        """
        if not self.voice_client or not self.voice_client.is_connected():
            self._alone_since = None
            return
        
        is_alone = self.is_alone_in_channel()
        current_time = time.time()
        
        if is_alone:
            # Bot is alone
            if self._alone_since is None:
                # Just became alone - LOG THIS (state change)
                self._alone_since = current_time
                self.is_alone_in_channel(log_result=True)  # Log with details
                logger.info("Guild %s: Bot became alone in voice channel", self.guild_id)
            else:
                # Been alone for a while (don't log routine checks)
                alone_duration = current_time - self._alone_since
                
                # Check for auto-pause (ALONE_PAUSE_DELAY seconds)
                if AUTO_PAUSE_ENABLED and alone_duration >= ALONE_PAUSE_DELAY:
                    state = self.get_playback_state()
                    if state == PlaybackState.PLAYING and not self._was_playing_before_alone:
                        logger.info("Guild %s: Auto-pausing (alone for %.1fs)", self.guild_id, alone_duration)
                        self.voice_client.pause()
                        self.state = PlaybackState.PAUSED
                        self._was_playing_before_alone = True
                        
                        # Send message to text channel if available
                        if self.text_channel:
                            msg = await self.send_with_ttl(
                                self.text_channel,
                                MESSAGES['pause_auto'],
                                'pause'
                            )
                
                # Check for auto-disconnect (ALONE_DISCONNECT_DELAY seconds)
                if AUTO_DISCONNECT_ENABLED and alone_duration >= ALONE_DISCONNECT_DELAY:
                    logger.info("Guild %s: Auto-disconnecting (alone for %.1fs)", self.guild_id, alone_duration)
                    
                    # Send message before disconnecting
                    if self.text_channel:
                        msg = await self.send_with_ttl(
                            self.text_channel,
                            MESSAGES['stop'],
                            'stop'
                        )
                    
                    # Disconnect
                    await safe_disconnect(self.voice_client, force=True)
                    self.reset_state()
                    await update_presence(None)
                    self._alone_since = None
                    self._was_playing_before_alone = False
        else:
            # Bot is NOT alone (someone is in channel)
            if self._alone_since is not None:
                # Someone just joined - LOG THIS (state change)
                state = self.get_playback_state()
                self.is_alone_in_channel(log_result=True)  # Log with details
                logger.info("Guild %s: Not alone anymore, state=%s, was_playing_before=%s", self.guild_id, state, self._was_playing_before_alone)
                if AUTO_PAUSE_ENABLED and state == PlaybackState.PAUSED and self._was_playing_before_alone:
                    logger.info("Guild %s: Auto-resuming (someone joined)", self.guild_id)
                    self.voice_client.resume()
                    self.state = PlaybackState.PLAYING
                    
                    # Send message
                    if self.text_channel and self.now_playing:
                        msg = await self.send_with_ttl(
                            self.text_channel,
                            MESSAGES['resume'].format(track=self.now_playing.display_name),
                            'resume'
                        )
                
                # Reset alone tracking
                self._alone_since = None
                self._was_playing_before_alone = False
    
    # =========================================================================
    # PLAY COOLDOWN (Special case - not debounced)
    # =========================================================================
    
    def check_play_cooldown(self) -> bool:
        """
        Check play command cooldown.
        
        Play/join commands don't use debouncing (need instant response),
        but still need cooldown to prevent spam abuse.
        
        Returns:
            bool: True if on cooldown (command should be ignored)
        """
        current_time = time.time()
        
        if self.voice_client and self.voice_client.is_connected():
            if current_time - self._last_play_time < PLAY_COOLDOWN:
                return True
        
        self._last_play_time = current_time
        return False
    
    # =========================================================================
    # LIBRARY & QUEUE MANAGEMENT
    # =========================================================================
    
    def load_library(self) -> List[Track]:
        """
        Load all music files from disk into library.
        
        Files are sorted numerically by leading digits in filename:
        - "01 - Track.opus" comes before "02 - Track.opus"
        - "10 - Track.opus" comes after "9 - Track.opus" (numeric, not lexical)
        
        Returns:
            List[Track]: Loaded tracks (also stored in self.library)
            
        Side effects:
            - Sets self.library
            - Builds self.track_by_index for O(1) lookups
            - Initializes queue via reset_queue()
        """
        music_path = Path(MUSIC_FOLDER)
        if not music_path.exists():
            logger.warning(f"Music folder not found: {MUSIC_FOLDER}")
            return []
        
        files = [f for f in music_path.glob("*") if f.is_file() and f.suffix.lower() == '.opus']
        if not files:
            logger.warning(f"No .opus files found in {MUSIC_FOLDER}")
            return []
        
        def get_sort_key(filepath: Path) -> int:
            """Extract leading number from filename for sorting."""
            filename = filepath.name
            match = re.match(r'^(\d+)', filename)
            if match:
                return int(match.group(1))
            else:
                # Unnumbered files sort to end and trigger warning
                logger.warning(f"Guild {self.guild_id}: File missing numeric prefix (will sort last): {filename}")
                return 999999
        
        sorted_files = sorted(files, key=get_sort_key)
        self.library = [Track(filepath, idx) for idx, filepath in enumerate(sorted_files)]
        
        # Build fast lookup index
        self.track_by_index = {track.library_index: track for track in self.library}
        
        self.reset_queue()
        
        logger.info("Guild %s: Loaded %d tracks", self.guild_id, len(self.library))
        return self.library
    
    def reset_queue(self, shuffle: Optional[bool] = None) -> None:
        """
        Reset queue to full library.
        
        Called when:
        - Library is first loaded
        - Queue is exhausted (auto-loop)
        
        Args:
            shuffle: If provided, override shuffle_enabled. If None, use current shuffle_enabled.
        
        Side effects:
            - Clears upcoming queue
            - Copies entire library to upcoming (optionally shuffled)
            - Clears played list
            - Clears now_playing (for fresh start)
        """
        if not self.library:
            logger.warning(f"Guild {self.guild_id}: Cannot reset queue - library empty")
            return
        
        # Determine shuffle state
        do_shuffle = self.shuffle_enabled if shuffle is None else shuffle
        
        # Copy library and optionally shuffle
        queue_tracks = self.library.copy()
        if do_shuffle:
            random.shuffle(queue_tracks)
            logger.debug("Guild %s: Queue shuffled", self.guild_id)
        
        self.upcoming = deque(queue_tracks)
        self.played.clear()  # Clear played history (deque with maxlen will auto-limit)
        self.now_playing = None
    
    def refresh_upcoming_queue(self) -> None:
        """
        Refresh the upcoming queue based on current shuffle state.
        
        Called when:
        - Shuffle state changes mid-playback
        
        Side effects:
            - Clears upcoming queue only
            - Repopulates with shuffled or normal order
            - In shuffle: Excludes now_playing track to prevent immediate repeats
            - In normal: Continues sequentially from current track with wrap-around
            - Does NOT touch played or now_playing (preserves position)
        """
        if not self.library:
            logger.warning(f"Guild {self.guild_id}: Cannot refresh queue - library empty")
            return
        
        if self.shuffle_enabled:
            # Shuffle mode: Create new shuffled queue excluding current track
            if self.now_playing:
                queue_tracks = [t for t in self.library if t.track_id != self.now_playing.track_id]
            else:
                queue_tracks = self.library.copy()
            random.shuffle(queue_tracks)
            logger.debug("Guild %s: Upcoming queue shuffled (excluding current track)", self.guild_id)
        else:
            # Normal mode: Continue sequentially from current track with wrap-around
            if self.now_playing:
                start_idx = self.now_playing.library_index
                # Build queue: [current+1, current+2, ..., end, 0, 1, ..., current-1]
                after_tracks = self.library[start_idx + 1:]  # Everything after current
                before_tracks = self.library[:start_idx]     # Everything before current (wraps around)
                queue_tracks = after_tracks + before_tracks
            else:
                # No current track, just use library order
                queue_tracks = self.library.copy()
            logger.debug("Guild %s: Upcoming queue reset to normal order from current position", self.guild_id)
        
        # Only update upcoming, preserve everything else
        self.upcoming = deque(queue_tracks)
    
    def rebuild_queue_from_track(self, start_track: Track) -> None:
        """
        Rebuild upcoming queue starting from the track after start_track.
        
        Called when:
        - User jumps to a specific track with !play [number]
        
        Args:
            start_track: The track we just jumped to
        
        Side effects:
            - Clears upcoming queue
            - Repopulates starting from next track after start_track
            - Respects shuffle_enabled state
            - Wraps around to beginning after reaching end
            
        Example:
            Normal mode, jump to track 19:
            - upcoming = [20, 21, ..., 44, 1, 2, ..., 18]
            
            Shuffle mode, jump to track 19:
            - upcoming = [shuffled order, excluding track 19]
        """
        if not self.library:
            logger.warning(f"Guild {self.guild_id}: Cannot rebuild queue - library empty")
            return
        
        if self.shuffle_enabled:
            # Shuffle mode: Create new shuffled queue excluding current track
            queue_tracks = [t for t in self.library if t.track_id != start_track.track_id]
            random.shuffle(queue_tracks)
            logger.debug("Guild %s: Queue rebuilt with shuffle from track %d", self.guild_id, start_track.library_index + 1)
        else:
            # Normal mode: Continue sequentially from next track, wrapping around
            start_idx = start_track.library_index
            # Build queue: [start+1, start+2, ..., end, 0, 1, ..., start-1]
            after_tracks = self.library[start_idx + 1:]  # Everything after current
            before_tracks = self.library[:start_idx]     # Everything before current (wraps around)
            queue_tracks = after_tracks + before_tracks
            logger.debug("Guild %s: Queue rebuilt from track %d", self.guild_id, start_track.library_index + 1)
        
        self.upcoming = deque(queue_tracks)
    
    def get_current_track(self) -> Optional[Track]:
        """Get currently playing track (or None if stopped)."""
        return self.now_playing
    
    def has_next(self) -> bool:
        """Check if there are upcoming tracks in queue."""
        return len(self.upcoming) > 0
    
    def advance_to_next(self) -> Optional[Track]:
        """
        Advance queue to next track.
        
        Behavior:
        1. Move current track to played list
        2. Add to history with timestamp
        3. Pop next track from upcoming
        4. If queue exhausted, auto-loop via reset_queue()
        
        Returns:
            Optional[Track]: Next track (now in self.now_playing), or None if library empty
            
        Side effects:
            - Updates self.now_playing
            - Updates self.played
            - Updates self.history
            - May trigger queue reset (auto-loop)
        """
        if not self.library:
            logger.warning(f"Guild {self.guild_id}: Cannot advance - library empty")
            return None
        
        # Save current to played history
        if self.now_playing:
            self.played.append(self.now_playing)
        
        # Get next track
        if self.upcoming:
            self.now_playing = self.upcoming.popleft()
        else:
            # Queue exhausted - loop by resetting to full library
            logger.debug("Guild %s: Queue exhausted, looping", self.guild_id)
            self.reset_queue()
            if self.upcoming:
                self.now_playing = self.upcoming.popleft()
            else:
                self.now_playing = None
        
        return self.now_playing
    
    # =========================================================================
    # UI HELPERS
    # =========================================================================
    
    def get_drink_emoji(self) -> str:
        """
        Get next drink emoji in rotation.
        
        Returns rotating emoji for "Now serving" messages.
        Drink emojis are configurable in config/messages.py (DRINK_EMOJIS).
        
        Returns:
            str: Next emoji in cycle
        """
        return next(self._drink_cycle)
    
    def get_playback_state(self) -> PlaybackState:
        """
        Get current playback state safely.
        
        Returns:
            PlaybackState: IDLE, PLAYING, or PAUSED
            
        Note:
            Handles voice_client being None or in bad state gracefully.
        """
        try:
            # Capture voice client reference once to avoid race conditions
            vc = self.voice_client
            if not vc or not vc.is_connected():
                return PlaybackState.IDLE
            
            if vc.is_paused():
                return PlaybackState.PAUSED
            if vc.is_playing():
                return PlaybackState.PLAYING
        except Exception:
            return PlaybackState.IDLE
        return PlaybackState.IDLE
    
    def reset_state(self) -> None:
        """
        Reset player state on disconnect.
        
        Side effects:
            - Clears now_playing
            - Sets state to IDLE
            - Clears voice_client
            - Clears text_channel
        """
        self.now_playing = None
        self.state = PlaybackState.IDLE
        self.voice_client = None
        self.text_channel = None

    async def _load_last_channel_async(self) -> None:
        """
        Async version of _load_last_channel for use after bot is ready.
        
        This prevents race conditions during bot startup by deferring channel loading
        until the bot is fully initialized and guilds are available.
        """
        try:
            # Wait for bot to be ready
            await bot.wait_until_ready()
            
            last_channels = load_last_channels()
            channel_id = last_channels.get(self.guild_id)
            
            if channel_id:
                # Get the guild and try to find the channel
                guild = bot.get_guild(self.guild_id)
                if guild:
                    channel = guild.get_channel(channel_id)
                    if (channel and 
                        isinstance(channel, disnake.TextChannel) and
                        channel.permissions_for(guild.me).send_messages):
                        
                        self.text_channel = channel
                        logger.info("Guild %s: Restored text channel %s (%d)", self.guild_id, channel.name, channel_id)
                    else:
                        logger.warning(f"Guild {self.guild_id}: Restored channel {channel_id} not accessible")
                else:
                    logger.warning(f"Guild {self.guild_id}: Guild not found during channel restoration")
        except Exception as e:
            logger.warning(f"Guild {self.guild_id}: Error loading last channel: {e}")

# =============================================================================
# PLAYER MANAGEMENT (Multi-Guild Support)
# =============================================================================

# Global dict: guild_id → MusicPlayer instance
# Each Discord server gets its own independent player
players: Dict[int, MusicPlayer] = {}
players_lock = asyncio.Lock()  # Thread safety for concurrent guild additions

async def get_player(guild_id: int) -> MusicPlayer:
    """
    Get or create player for a guild (thread-safe).
    
    This is how multi-guild support works:
    - Each guild has its own MusicPlayer instance
    - Players are created on-demand
    - Players are never destroyed (persist for bot lifetime)
    - Uses asyncio.Lock for thread safety
    
    Args:
        guild_id: Discord guild (server) ID
        
    Returns:
        MusicPlayer: Player for this guild (created if doesn't exist)
        
    Note:
        This function is async to work with asyncio.Lock for better event loop integration.
        
    Side effects:
        - Creates new player if first time seeing this guild
        - Loads library for new player
        - Starts command processor for new player
        - Starts message cleanup worker for new player
    """
    # Fast path - player already exists (no lock needed for read)
    if guild_id in players:
        return players[guild_id]
    
    # Slow path - need to create player (lock needed for write)
    async with players_lock:
        # Double-check pattern - another thread might have created it
        if guild_id in players:
            return players[guild_id]
        
        # Build and initialize player atomically before adding to dict
        try:
            player = MusicPlayer(guild_id)
            player.load_library()
            player.start_processor()
            player.start_cleanup_worker()
            
            # Only add to dict after successful initialization
            players[guild_id] = player
            
            # Start async channel loading after bot is ready
            asyncio.create_task(player._load_last_channel_async())
        except Exception as e:
            logger.error(f"Failed to initialize player for guild {guild_id}: {e}", exc_info=True)
            raise  # Re-raise so caller knows init failed
        
    return players[guild_id]

# =============================================================================
# CORE PLAYBACK FUNCTIONS (Internal - called by queue processor)
# =============================================================================

async def _play_current(guild_id: int) -> None:
    """
    Play the current track (whatever is in now_playing).
    
    This function does NOT advance the queue - it just plays what's set.
    Queue advancement happens in _play_next().
    
    Args:
        guild_id: Guild to play in
        
    Side effects:
        - Starts playback via voice_client.play()
        - Sets callback for when track finishes
        - Updates bot presence status
        - Sends "Now serving" message
        - Updates watchdog tracking
        
    Error handling:
        - Validates voice_client is connected
        - Validates guild exists
        - Validates track exists and file is accessible
        - Logs errors but doesn't crash
    """
    player = await get_player(guild_id)
    
    # Validate voice client
    if not player.voice_client or not player.voice_client.is_connected():
        logger.warning(f"Guild {guild_id}: _play_current called but not connected")
        return
    
    # Get fresh guild reference (prevents stale reference bugs)
    guild = bot.get_guild(guild_id)
    if not guild:
        logger.error(f"Guild {guild_id} not found")
        return
    
    # Self-deafen (bot doesn't need to hear users)
    if player.voice_client.channel:
        await safe_voice_state_change(guild, player.voice_client.channel, self_deaf=True)
    
    # Get track to play
    track = player.get_current_track()
    if not track:
        logger.warning(f"Guild {guild_id}: No track to play")
        return
    
    # Validate file exists and is readable
    if not track.opus_path.exists():
        logger.error(f"Guild {guild_id}: Track file missing: {track.opus_path}")
        # Skip to next track
        await player.queue_command(lambda: _play_next(guild_id))
        return
    
    # Stop current playback if any (suppress callback to prevent race condition)
    try:
        # Capture voice client reference once to avoid race conditions
        vc = player.voice_client
        is_playing = vc.is_playing() if vc else False
        is_paused = vc.is_paused() if vc else False
    except Exception as e:
        logger.warning(f"Guild {guild_id}: Voice client state check failed: {e}")
        # Voice client in bad state, assume nothing is playing
        is_playing = False
        is_paused = False
    
    if is_playing or is_paused:
        player._suppress_callback = True  # Block callback from triggering during manual stop
        player.voice_client.stop()
        
        # Wait for voice client to fully stop (longer than just settle delay)
        # This prevents "Already playing audio" errors
        max_wait = VOICE_CONNECTION_MAX_WAIT  # Maximum wait time for voice connection
        wait_increment = VOICE_CONNECTION_CHECK_INTERVAL  # Check voice connection every VOICE_CONNECTION_CHECK_INTERVAL seconds
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
                # Voice client went bad during wait, just break
                break
        
        player._suppress_callback = False  # Re-enable callbacks
    
    # Small additional delay to let voice client settle
    await asyncio.sleep(VOICE_SETTLE_DELAY)
    
    audio_source = None
    try:
        # Create audio source (native opus passthrough - zero re-encoding)
        audio_source = make_audio_source(str(track.opus_path))
        
        # Capture track ID for this specific callback
        callback_track_id = track.track_id
        
        # Define callback for when track finishes
        def after_track(error):
            """
            Callback fired when track finishes playing.
            
            This runs in a DIFFERENT thread (not the asyncio thread),
            so we need to use run_coroutine_threadsafe() to queue work.
            
            Args:
                error: Error from FFmpeg (or None if successful)
            """
            if error:
                error_str = str(error)
                # Filter out expected errors from reconnects/stops
                if "Bad file descriptor" not in error_str and "_MissingSentinel" not in error_str:
                    logger.error(f'Guild {guild_id} playback error: {error}')
            
            # Clean up audio source if it exists
            nonlocal audio_source
            if audio_source:
                try:
                    audio_source.cleanup()
                except Exception:
                    pass  # Already cleaned
                audio_source = None
            
            # Don't advance if we're reconnecting (prevents track skip during channel moves)
            if player._is_reconnecting:
                logger.debug("Guild %s: Skipping callback during reconnect", guild_id)
                return
            
            # Don't advance if callback is suppressed (prevents race condition during manual track changes)
            if player._suppress_callback:
                logger.debug("Guild %s: Skipping callback (suppressed for manual track change)", guild_id)
                return
            
            # CRITICAL: Only advance if this callback's track is still the current track
            # This prevents callbacks from stopped tracks (during !previous or !play N) from
            # incorrectly advancing the queue
            if not player.now_playing or player.now_playing.track_id != callback_track_id:
                logger.debug("Guild %s: Ignoring callback from old track (was %s, now %s)", guild_id, callback_track_id, player.now_playing.track_id if player.now_playing else 'None')
                return
            
            # Anti-spam: Prevent rapid-fire callbacks
            current_time = time.time()
            if current_time - player._last_callback_time < CALLBACK_MIN_INTERVAL:
                logger.warning(f"Guild {guild_id}: Callback too quick, skipping")
                return
            
            player._last_callback_time = current_time
            
            # Queue the next track (goes through command queue for serialization)
            asyncio.run_coroutine_threadsafe(
                player.queue_command(lambda: _play_next(guild_id)),
                bot.loop
            )
        
        # Start playback with callback
        player.voice_client.play(audio_source, after=after_track)
        player.state = PlaybackState.PLAYING
        
        # Update watchdog tracking (for detecting hung FFmpeg)
        player._last_track_start = time.time()
        player._last_track_id = track.track_id
        
        logger.debug("Guild %s: Now playing: %s", guild_id, track.display_name)
        
        # Smart "Now serving" message management (edit vs send new)
        drink = player.get_drink_emoji()
        new_content = MESSAGES['now_serving'].format(drink=drink, track=track.display_name)
        
        # Small delay to avoid rapid-fire message operations
        await asyncio.sleep(MESSAGE_SETTLE_DELAY)
        
        # Try to edit existing message first (reduces API calls)
        if SMART_MESSAGE_MANAGEMENT and player._last_now_playing_msg:
            try:
                # Check if message is buried by counting messages after it
                message_count = 0
                async for msg in player.text_channel.history(limit=MESSAGE_BURIAL_CHECK_LIMIT, after=player._last_now_playing_msg):
                    message_count += 1
                
                if message_count < MESSAGE_BURIAL_THRESHOLD:  # Message is still visible (not buried by too many messages after it)
                    await player._last_now_playing_msg.edit(content=new_content)
                    # Success! No new message needed, just update TTL
                    if TTL_CLEANUP_ENABLED:
                        await player.schedule_message_deletion(player._last_now_playing_msg, MESSAGE_TTL['now_serving'])
                    logger.debug("Guild %s: Edited 'now serving' message", guild_id)
                else:
                    # Message is buried by chat activity, send new one
                    raise Exception("Message buried by chat activity")
            except Exception as e:
                # Edit failed, delete old message and send new one
                logger.debug("Guild %s: Edit failed (%s), sending new message", guild_id, e)
                await player.delete_last_now_playing()
                
                # Send new "Now serving" message
                msg = await player.send_with_ttl(
                    player.text_channel,
                    new_content,
                    'now_serving'
                )
                player._last_now_playing_msg = msg
        elif SMART_MESSAGE_MANAGEMENT and not player._last_now_playing_msg:
            # No existing message, send new one
            msg = await player.send_with_ttl(
                player.text_channel,
                new_content,
                'now_serving'
            )
            player._last_now_playing_msg = msg
        else:
            # Smart message management disabled - always send new message
            if player._last_now_playing_msg:
                await player.delete_last_now_playing()
            
            msg = await player.send_with_ttl(
                player.text_channel,
                new_content,
                'now_serving'
            )
            player._last_now_playing_msg = msg
        
        # Update bot presence status (global throttling handled in update_presence)
        await update_presence(track.display_name)
        
    except Exception as e:
        logger.error(f'Guild {guild_id} error in _play_current: {e}', exc_info=True)
        # Clean up audio source if it was created
        if audio_source:
            try:
                audio_source.cleanup()
            except Exception:
                pass  # Already cleaned
        # If playback fails, voice client might be broken - clear it
        # Use safe null checking to prevent AttributeError on None voice_client
        vc = player.voice_client
        if "Bad file descriptor" in str(e) or not (vc and vc.is_connected()):
            player.voice_client = None
    finally:
        # Ensure suppress flag is always reset, even if exception occurs
        player._suppress_callback = False

async def _play_next(guild_id: int) -> None:
    """
    Advance queue to next track and play it.
    
    This is called by:
    - Track finish callback (after_track)
    - !skip command (after debounce)
    
    Args:
        guild_id: Guild to advance queue in
        
    Side effects:
        - Calls player.advance_to_next() (modifies queue)
        - Calls _play_current() (starts playback)
    """
    player = await get_player(guild_id)
    next_track = player.advance_to_next()
    if next_track:
        await _play_current(guild_id)

async def _play_first(guild_id: int) -> None:
    """
    Start playback from beginning.
    
    This is called by:
    - !play command when not currently playing
    
    Behavior:
    - Always starts fresh from beginning of queue
    - If shuffle enabled: Reshuffles and starts
    - If shuffle disabled: Starts at track 01
    
    Args:
        guild_id: Guild to start playback in
        
    Side effects:
        - Resets queue (respects shuffle state)
        - Calls advance_to_next() to get first track
        - Calls _play_current() (starts playback)
    """
    player = await get_player(guild_id)
    
    # Reset to fresh queue (respects shuffle_enabled)
    player.reset_queue()
    
    # Start from first track in queue
    if player.has_next():
        player.advance_to_next()
        await _play_current(guild_id)

# =============================================================================
# INTERNAL COMMAND EXECUTORS (Called after debounce/queue)
# =============================================================================

async def _execute_skip(ctx: commands.Context) -> None:
    """
    Internal: Execute skip command (called after debounce completes).
    
    This function is called by the debounce system AFTER spam stops.
    It just stops the current track - the callback handles advancing to next.
    
    Args:
        ctx: Discord context
        
    Note:
        Multiple queued skips are harmless - they just try to stop an
        already-stopped track (no-op).
    """
    player = await get_player(ctx.guild.id)
    
    # Validate voice client
    if not player.voice_client or not player.voice_client.is_connected():
        logger.warning(f"Guild {ctx.guild.id}: Skip called but not connected")
        return
    
    try:
        # Capture voice client reference once to avoid race conditions
        vc = player.voice_client
        is_playing = vc.is_playing() if vc else False
        is_paused = vc.is_paused() if vc else False
    except Exception as e:
        logger.warning(f"Guild {ctx.guild.id}: Voice client in bad state: {e}")
        return
    
    if is_playing or is_paused:
        # Gentle stop: pause first to finish current frame, then stop
        if is_playing:
            player.voice_client.pause()
            await asyncio.sleep(FRAME_DURATION)
        player.voice_client.stop()  # This triggers after_track callback → _play_next
        # Delete user's skip command after short delay (no bot response for successful skip)
        if TTL_CLEANUP_ENABLED:
            await player.schedule_message_deletion(ctx.message, USER_COMMAND_TTL)
    else:
        await player.send_with_ttl(player.text_channel, MESSAGES['skip_no_disc'], 'error', ctx.message)

async def _execute_pause(ctx: commands.Context) -> None:
    """
    Internal: Execute pause command (called after debounce completes).
    
    Args:
        ctx: Discord context
    """
    player = await get_player(ctx.guild.id)
    
    state = player.get_playback_state()
    if state == PlaybackState.PLAYING:
        player.voice_client.pause()
        player.state = PlaybackState.PAUSED
        await player.send_with_ttl(player.text_channel, MESSAGES['pause'], 'pause', ctx.message)
        await update_presence(MESSAGES['pause_on_break'])
    else:
        await player.send_with_ttl(player.text_channel, MESSAGES['skip_no_disc'], 'error', ctx.message)

async def _execute_stop(ctx: commands.Context) -> None:
    """
    Internal: Execute stop command (called after debounce completes).
    
    Args:
        ctx: Discord context
        
    Note:
        Disconnects and resets all player state. User must use !play to restart.
    """
    player = await get_player(ctx.guild.id)
    
    await safe_disconnect(player.voice_client, force=True)
    player.reset_state()
    await update_presence(None)
    await player.send_with_ttl(player.text_channel, MESSAGES['stop'], 'stop', ctx.message)

async def _execute_previous(ctx: commands.Context) -> None:
    """
    Internal: Execute previous command (called after debounce completes).
    
    Goes back through played history. Stops at beginning (no wrap-around).
    
    Args:
        ctx: Discord context
        
    Side effects:
        - Pops track from played list
        - Prepends current track to upcoming
        - Sets previous track as now_playing
        - Starts playback
        
    Note:
        Race condition is handled by track-specific callbacks in _play_current().
        Old track's callback will see it's no longer the current track and ignore itself.
    """
    player = await get_player(ctx.guild.id)
    
    # Check if we have any history to go back through
    if not player.played:
        await player.send_with_ttl(player.text_channel, MESSAGES['previous_at_start'], 'error', ctx.message)
        return
    
    # Go back through history
    previous_track = player.played.pop()
    
    # Push current track to front of upcoming
    if player.now_playing:
        player.upcoming.appendleft(player.now_playing)
    
    # Play the previous track
    player.now_playing = previous_track
    await _play_current(ctx.guild.id)
    # Delete user's previous command after short delay (no bot response for successful previous)
    if TTL_CLEANUP_ENABLED:
        await player.schedule_message_deletion(ctx.message, USER_COMMAND_TTL)

async def _execute_shuffle(ctx: commands.Context) -> None:
    """
    Internal: Execute shuffle toggle (called after debounce completes).
    
    Toggles shuffle_enabled and refreshes upcoming queue so the new
    mode applies after the current track ends.
    
    Args:
        ctx: Discord context
        
    Side effects:
        - Toggles shuffle_enabled flag
        - Clears and refreshes upcoming queue only
        - Current track and played history preserved
    """
    player = await get_player(ctx.guild.id)
    
    # Toggle shuffle
    player.shuffle_enabled = not player.shuffle_enabled
    
    # Refresh upcoming queue with new shuffle state
    player.refresh_upcoming_queue()
    
    if player.shuffle_enabled:
        await player.send_with_ttl(player.text_channel, MESSAGES['shuffle_on'], 'shuffle', ctx.message)
    else:
        await player.send_with_ttl(player.text_channel, MESSAGES['shuffle_off'], 'shuffle', ctx.message)

async def _execute_unshuffle(ctx: commands.Context) -> None:
    """
    Internal: Execute unshuffle (called after debounce completes).
    
    Turns shuffle off and refreshes queue to normal order.
    Idempotent - safe to call when already unshuffled.
    
    Args:
        ctx: Discord context
        
    Side effects:
        - Sets shuffle_enabled to False
        - Clears and refreshes upcoming queue to normal order
        - Current track and played history preserved
    """
    player = await get_player(ctx.guild.id)
    
    if not player.shuffle_enabled:
        await player.send_with_ttl(player.text_channel, MESSAGES['shuffle_already_off'], 'shuffle', ctx.message)
        return
    
    # Turn off shuffle
    player.shuffle_enabled = False
    
    # Refresh upcoming queue to normal order
    player.refresh_upcoming_queue()
    
    await player.send_with_ttl(player.text_channel, MESSAGES['unshuffle_organized'], 'shuffle', ctx.message)

async def _cleanup_disconnect(guild_id: int) -> None:
    """
    Internal: Clean up after bot is disconnected.
    
    Called by on_voice_state_update when bot is forcibly disconnected
    (e.g., user drags bot out of channel).
    
    Args:
        guild_id: Guild that was disconnected from
    """
    player = await get_player(guild_id)
    player.reset_state()
    await update_presence(None)
    logger.info("Guild %s: Disconnected and cleaned up", guild_id)

# =============================================================================
# WATCHDOG (Detects Hung FFmpeg Processes)
# =============================================================================

async def playback_watchdog():
    """
    Monitor playback for hung FFmpeg processes.
    
    Runs in background, checks every WATCHDOG_INTERVAL seconds.
    
    Detection logic:
    - If same track is playing for >11 minutes → hung
    - Force stop to trigger callback and restart playback
    
    Why this is needed:
    - FFmpeg rarely hangs but when it does, bot appears stuck
    - Callback never fires because FFmpeg never finishes
    - Watchdog detects this and forces restart
    
    Side effects:
    - Calls voice_client.stop() if hung detected
    - Updates watchdog tracking timestamps
    """
    await bot.wait_until_ready()
    logger.debug("Playback watchdog started")
    
    while not bot.is_closed():
        try:
            # Adaptive sleep optimization: reduce polling when no active voice connections
            sleep_interval = WATCHDOG_INTERVAL
            if not any(p.voice_client and p.voice_client.is_connected() for p in players.values()):
                sleep_interval = min(300, WATCHDOG_INTERVAL * 6)
            await asyncio.sleep(sleep_interval)
            
            # Use snapshot iteration to prevent crashes during concurrent modifications
            for guild_id, player in list(players.items()):
                # Skip if not playing
                if not player.voice_client or not player.voice_client.is_connected():
                    continue
                
                state = player.get_playback_state()
                if state != PlaybackState.PLAYING:
                    continue
                
                current_time = time.time()
                current_track = player.get_current_track()
                
                # Check if stuck on same track
                if current_track and current_track.track_id == player._last_track_id:
                    time_on_track = current_time - player._last_track_start
                    
                    if time_on_track > WATCHDOG_TIMEOUT:
                        logger.error(f"Guild {guild_id}: Playback hung, restarting")
                        try:
                            # Stop hung track and manually advance to next
                            player._suppress_callback = True
                            player.voice_client.stop()
                            player._suppress_callback = False
                            # Manually queue next track since we suppressed the callback
                            await player.queue_command(lambda: _play_next(guild_id))
                        except Exception as e:
                            logger.error(f"Watchdog stop failed: {e}")
                            player._suppress_callback = False  # Ensure flag is reset
                else:
                    # Track changed, update tracking
                    if current_track:
                        player._last_track_id = current_track.track_id
                        player._last_track_start = current_time
                        
        except Exception as e:
            logger.error(f"Watchdog error: {e}", exc_info=True)

async def alone_watchdog():
    """
    Monitor for bot being alone in voice channel.
    
    Runs in background, checks every ALONE_WATCHDOG_INTERVAL seconds.
    
    Timeline when bot becomes alone:
    - 10s: Auto-pause (if playing)
    - 10min: Auto-disconnect
    
    This complements on_voice_state_update which triggers immediately
    on user join/leave, but we need continuous checking for timers.
    """
    await bot.wait_until_ready()
    logger.debug("Alone watchdog started")
    
    while not bot.is_closed():
        try:
            # Adaptive sleep optimization: reduce polling when no active voice connections
            sleep_interval = ALONE_WATCHDOG_INTERVAL
            if not any(p.voice_client and p.voice_client.is_connected() for p in players.values()):
                sleep_interval = min(300, ALONE_WATCHDOG_INTERVAL * 6)
            await asyncio.sleep(sleep_interval)
            
            # Use snapshot iteration to prevent crashes during concurrent modifications
            for guild_id, player in list(players.items()):
                if player.voice_client and player.voice_client.is_connected():
                    await player.handle_alone_state()
                    
        except Exception as e:
            logger.error(f"Alone watchdog error: {e}", exc_info=True)

# =============================================================================
# BOT EVENTS
# =============================================================================

@bot.event
async def on_ready():
    """
    Called when bot successfully connects to Discord.
    
    Side effects:
    - Logs connection
    - Starts playback watchdog
    - Starts alone watchdog (auto-pause feature)
    - Libraries are loaded on-demand when guilds use the bot
    """
    global _playback_watchdog_task, _alone_watchdog_task
    logger.info(f'Bot connected as {bot.user}')
    _playback_watchdog_task = bot.loop.create_task(playback_watchdog())
    _alone_watchdog_task = bot.loop.create_task(alone_watchdog())

@bot.event
async def on_disconnect():
    """
    Called when bot disconnects from Discord (shutdown or network loss).
    
    Clean up all voice connections and background tasks gracefully.
    
    Side effects:
    - Cancels watchdog tasks
    - Disconnects from all voice channels
    - Clears bot presence
    """
    global _playback_watchdog_task, _alone_watchdog_task
    logger.info("Bot disconnecting, cleaning up")
    
    # Cancel watchdog tasks
    if _playback_watchdog_task and not _playback_watchdog_task.done():
        _playback_watchdog_task.cancel()
    if _alone_watchdog_task and not _alone_watchdog_task.done():
        _alone_watchdog_task.cancel()
    
    # Use snapshot iteration to prevent crashes during concurrent modifications
    for player in list(players.values()):
        if player.voice_client:
            await safe_disconnect(player.voice_client, force=True)
    await update_presence(None)

@bot.event
async def on_voice_state_update(member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
    """
    Called when someone's voice state changes (join, leave, mute, etc.).
    
    Handles:
    - Bot being disconnected from channel
    - Users joining/leaving (for auto-pause feature)
    
    Args:
        member: Member whose voice state changed
        before: Voice state before change
        after: Voice state after change
        
    Note:
        Ignores disconnects during reconnects (channel switching).
    """
    # Check if bot was disconnected (optimized: member.id == bot.user.id instead of member == bot.user for explicit ID comparison)
    if member.id == bot.user.id and before.channel and not after.channel:
        player = await get_player(member.guild.id)
        
        # Don't clean up if we're just reconnecting to different channel
        if player._is_reconnecting:
            logger.debug("Guild %s: Ignoring disconnect during reconnect", member.guild.id)
            return
        
        # Queue cleanup (serialized)
        await player.queue_command(lambda: _cleanup_disconnect(member.guild.id))
        return
    
    # Check for auto-pause/resume when users join/leave voice channel
    # Only care if someone joins/leaves the channel where bot is
    if member.guild.id in players:
        player = await get_player(member.guild.id)
        if player.voice_client and player.voice_client.is_connected():
            # Check if the change happened in bot's channel
            bot_channel = player.voice_client.channel
            if before.channel == bot_channel or after.channel == bot_channel:
                # User joined or left bot's channel - check alone state
                await player.handle_alone_state()

@bot.event
async def on_guild_remove(guild: disnake.Guild):
    """
    Called when bot is removed from a guild (kicked/banned/guild deleted).
    
    Clean up player to prevent memory leak.
    
    Args:
        guild: Guild that was removed
    """
    if guild.id in players:
        logger.info("Guild %s: Removed from guild, cleaning up player", guild.id)
        player = players[guild.id]
        
        # Clean up voice connection if any
        if player.voice_client:
            await safe_disconnect(player.voice_client, force=True)
        
        # CRITICAL: Cancel all background tasks to prevent memory leaks
        if player._processor_task and not player._processor_task.done():
            player._processor_task.cancel()
        
        if player._cleanup_task and not player._cleanup_task.done():
            player._cleanup_task.cancel()
        
        # Cancel all debounce tasks/handles
        for handle in player._debounce_tasks.values():
            if hasattr(handle, 'done') and not handle.done():
                handle.cancel()
            elif hasattr(handle, 'cancel'):
                handle.cancel()
        player._debounce_tasks.clear()
        
        # Remove player from dict to free memory (thread-safe)
        async with players_lock:
            if guild.id in players:  # Double check after acquiring lock
                del players[guild.id]

# =============================================================================
# COMMANDS (Multi-layer spam protection with generic debouncing)
# =============================================================================

"""
HOW TO ADD DEBOUNCING TO NEW COMMANDS:
--------------------------------------

await player.debounce_command(
    command_name="mycommand",                    # Unique identifier
    ctx=ctx,                                     # Discord context
    execute_func=lambda: _execute_mycommand(ctx),# What to run after debounce
    debounce_window=QUEUE_DEBOUNCE_WINDOW,                         # Wait time for spam to stop (seconds)
    cooldown=QUEUE_COOLDOWN,                                # Cooldown after execution (seconds)
    spam_threshold=QUEUE_SPAM_THRESHOLD,                            # Show warning after N rapid commands
    spam_message="Custom spam warning here"             # Optional spam warning message
)

Then create the executor:

async def _execute_mycommand(ctx: commands.Context):
    '''Internal: Execute mycommand (called after debounce completes).'''
    player = await get_player(ctx.guild.id)
    # ... do the thing ...

WHEN TO USE DEBOUNCING:
- State-modifying commands that could be spammed (skip, pause, stop, etc.)
- Commands that trigger Discord API calls

WHEN NOT TO USE DEBOUNCING:
- Read-only commands (help)
- Commands needing instant response (play/join)
"""

# All commands use @commands.guild_only() decorator (prevents crashes from ctx.guild being None in DMs, returns clean "guild-only" error)
@commands.guild_only()
@bot.command(aliases=COMMAND_ALIASES['queue'])
async def queue(ctx: commands.Context):
    """
    Show current queue position.
    
    Displays:
    - Last played track
    - Currently playing track
    - Next QUEUE_DISPLAY_COUNT tracks
    
    Aliases: !q, !playing, !name, !song
    
    Note:
        Uses debouncing to prevent spam.
    """
    player = await get_player(ctx.guild.id)
    
    # Check if queue display feature is enabled
    if not QUEUE_DISPLAY_ENABLED:
        await player.send_with_ttl(player.text_channel, MESSAGES['feature_queue_disabled'], 'error', ctx.message)
        return
    
    # LAYER 0: User spam check
    if await player.check_user_spam(ctx.author.id, "queue", ctx):
        return
    
    # LAYER 2: Global rate limit
    if player.check_global_rate_limit():
        return
    
    # LAYER 3: Debounce
    await player.debounce_command(
        command_name="queue",
        ctx=ctx,
        execute_func=lambda: _execute_queue(ctx),
        debounce_window=QUEUE_DEBOUNCE_WINDOW,
        cooldown=QUEUE_COOLDOWN,
        spam_threshold=QUEUE_SPAM_THRESHOLD,
        spam_message=None  # Silent - just wait
    )

async def _execute_queue(ctx: commands.Context) -> None:
    """Internal: Execute queue display (called after debounce completes)."""
    player = await get_player(ctx.guild.id)
    
    if not player.now_playing:
        await player.send_with_ttl(player.text_channel or ctx.channel, MESSAGES['nothing_playing'], 'error', ctx.message)
        return
    
    # Build queue display
    lines = []
    
    # Last played
    if player.played:
        last = player.played[-1]
        lines.append(f"[←] **{last.display_name}**")
    
    # Current
    lines.append(f"[♪] **{player.now_playing.display_name}** ← Now playing")
    
    # Next QUEUE_DISPLAY_COUNT (uses QUEUE_DISPLAY_COUNT from config/features.py)
    upcoming_list = list(player.upcoming)[:QUEUE_DISPLAY_COUNT]
    for track in upcoming_list:
        lines.append(f"[→] **{track.display_name}**")
    
    if not upcoming_list:
        lines.append(MESSAGES['queue_will_loop'])
    
    await player.send_with_ttl(player.text_channel or ctx.channel, "\n".join(lines), 'queue', ctx.message)

@commands.guild_only()
@bot.command(aliases=COMMAND_ALIASES['library'])
async def library(ctx: commands.Context, page: int = 1):
    """
    Show the full library in canonical order.
    
    Shows LIBRARY_PAGE_SIZE tracks per page with current track indicator.
    Library always shows tracks in their canonical order (01, 02, 03...)
    regardless of shuffle mode.
    
    Args:
        page: Page number (default: 1)
    
    Aliases: !fullqueue, !fulllist, !biglist, !allsongs, !playlist, !fq, !all
    
    Example:
        !library     - Show page 1
        !library 2   - Show tracks 21-40
    
    Note:
        Uses debouncing to prevent spam (but allows reasonable page flipping).
    """
    player = await get_player(ctx.guild.id)
    
    # Check if library display feature is enabled
    if not LIBRARY_DISPLAY_ENABLED:
        await player.send_with_ttl(player.text_channel, MESSAGES['feature_library_disabled'], 'error', ctx.message)
        return
    
    # LAYER 0: User spam check
    if await player.check_user_spam(ctx.author.id, "library", ctx):
        return
    
    # LAYER 2: Global rate limit
    if player.check_global_rate_limit():
        return
    
    # LAYER 3: Debounce (lighter than other commands - allow browsing)
    await player.debounce_command(
        command_name="library",
        ctx=ctx,
        execute_func=lambda: _execute_library(ctx, page),
        debounce_window=LIBRARY_DEBOUNCE_WINDOW,
        cooldown=LIBRARY_COOLDOWN,
        spam_threshold=LIBRARY_SPAM_THRESHOLD,
        spam_message=None  # Silent
    )

async def _execute_library(ctx: commands.Context, page: int) -> None:
    """Internal: Execute library display (called after debounce completes)."""
    player = await get_player(ctx.guild.id)
    
    if not player.library:
        await player.send_with_ttl(player.text_channel or ctx.channel, MESSAGES['error_no_tracks'], 'error', ctx.message)
        return
    
    # Pagination (uses LIBRARY_PAGE_SIZE from config/features.py)
    per_page = LIBRARY_PAGE_SIZE
    total_tracks = len(player.library)
    total_pages = (total_tracks + per_page - 1) // per_page  # Ceiling division
    
    # Validate page
    if page < 1:
        page = 1
    if page > total_pages:
        page = total_pages
    
    start_idx = (page - 1) * per_page
    end_idx = min(start_idx + per_page, total_tracks)
    
    # Build display
    lines = [MESSAGES['library_header'].format(page=page, total_pages=total_pages)]
    
    tracks_slice = player.library[start_idx:end_idx]
    now_id = player.now_playing.track_id if player.now_playing else None
    lines.extend([
        (f"`{track.library_index + 1:02d}.` ♪ **{track.display_name}** ← Now playing"
         if track.track_id == now_id
         else f"`{track.library_index + 1:02d}.` {track.display_name}")
        for track in tracks_slice
    ])
    
    # Footer
    if total_pages > 1:
        if page < total_pages:
            lines.append(MESSAGES['library_next_page'].format(next_page=page + 1))
    
    # Show shuffle status and clarify what this list shows
    if player.shuffle_enabled:
        lines.append(MESSAGES['library_shuffle_note'])
        lines.append(MESSAGES['library_shuffle_help'])
    else:
        lines.append(MESSAGES['library_normal_help'])
    
    await player.send_with_ttl(player.text_channel or ctx.channel, "\n".join(lines), 'library', ctx.message)

@commands.guild_only()
@bot.command(aliases=COMMAND_ALIASES['play'])
async def play(ctx: commands.Context, track_number: Optional[int] = None):
    """
    Join channel and start/resume playing, or jump to specific track.
    
    Behavior:
    - !play: Join channel and start playing / Resume if paused / Move to user's channel
    - !play 32: Jump to track #32 in library (by library_index)
    
    Track jumping works in both shuffled and unshuffled modes.
    The number always refers to the canonical library position.
    
    Args:
        track_number: Optional track number to jump to (1-based, matches !library display)
    
    Aliases: !resume, !unpause, !start, !join, !skipto, !jumpto
    
    Note:
        Normal !play does NOT use debouncing (needs instant response).
        !play [number] DOES use debouncing (state-modifying).
    """
    player = await get_player(ctx.guild.id)
    
    # LAYER 0: Per-user spam check
    if await player.check_user_spam(ctx.author.id, "play", ctx):
        return
    
    # LAYER 1: Validation
    if not ctx.author.voice:
        await player.send_with_ttl(player.text_channel, MESSAGES['error_not_in_voice'], 'error', ctx.message)
        return
    
    # Handle jump-to-track
    if track_number is not None:
        # LAYER 2: Global rate limit
        if player.check_global_rate_limit():
            logger.debug("Guild %s: Play rate limited", ctx.guild.id)
            return
        
        # Queue jump command with debouncing
        await player.debounce_command(
            command_name="play_jump",
            ctx=ctx,
            execute_func=lambda: _execute_play_jump(ctx, track_number),
            debounce_window=PLAY_JUMP_DEBOUNCE_WINDOW,
            cooldown=PLAY_JUMP_COOLDOWN,
            spam_threshold=PLAY_JUMP_SPAM_THRESHOLD,
            spam_message=None  # Layer 0 shows the warning
        )
        return
    
    # Normal play behavior (existing code continues below)
    
    # LAYER 2: Global rate limit
    if player.check_global_rate_limit():
        logger.debug("Guild %s: Play rate limited", ctx.guild.id)
        return
    
    # LAYER 3: Per-command cooldown (atomic check and set)
    if player.check_play_cooldown():
        return
    
    # LAYER 4 & 5: Queue and execute
    await player.queue_command(lambda: _execute_play(ctx))

async def _execute_play(ctx: commands.Context):
    """
    Internal: Execute play command.
    
    This is complex because it handles multiple cases:
    1. Channel switching (user in different channel)
    2. Fresh connection (not connected at all)
    3. Resume from pause
    4. Already playing
    
    Args:
        ctx: Discord context
    """
    player = await get_player(ctx.guild.id)
    
    # Set text channel
    if player.text_channel != ctx.channel:
        # Validate channel accessibility before saving
        try:
            if (ctx.channel and 
                isinstance(ctx.channel, disnake.TextChannel) and
                ctx.channel.permissions_for(ctx.guild.me).send_messages):
                
                player.text_channel = ctx.channel
                # Save the new channel to persistent storage
                save_last_channel(ctx.guild.id, ctx.channel.id)
            else:
                logger.warning(f"Guild {ctx.guild.id}: Cannot access channel {ctx.channel.name if ctx.channel else 'None'}")
                # Still set the channel for current session, but don't save invalid ones
                player.text_channel = ctx.channel
        except Exception as e:
            logger.warning(f"Guild {ctx.guild.id}: Error validating channel: {e}")
            # Fallback: set channel but don't save
            player.text_channel = ctx.channel
    
    # =========================================================================
    # CASE 1: Bot connected, but user in different channel (channel switch)
    # =========================================================================
    
    if VOICE_RECONNECT_ENABLED and player.voice_client and player.voice_client.is_connected():
        user_channel = ctx.author.voice.channel
        
        if player.voice_client.channel != user_channel:
            # Check permission
            if not can_connect_to_channel(user_channel):
                await player.send_with_ttl(player.text_channel, MESSAGES['error_no_permission'].format(channel=user_channel.name), 'error', ctx.message)
                return
            
            # Check reconnect cooldown (prevents Discord rate limits)
            current_time = time.time()
            if current_time - player._last_reconnect_time < RECONNECT_COOLDOWN:
                logger.debug("Guild %s: Reconnect on cooldown", ctx.guild.id)
                return
            
            player._last_reconnect_time = current_time
            player._is_reconnecting = True  # Block callbacks during move
            
            try:
                # Save state
                state = player.get_playback_state()
                current_track = player.now_playing
                
                # Stop cleanly
                if state in (PlaybackState.PLAYING, PlaybackState.PAUSED):
                    if state == PlaybackState.PLAYING:
                        player.voice_client.pause()
                        await asyncio.sleep(FRAME_DURATION)
                    player.voice_client.stop()
                
                # Disconnect and reconnect
                await safe_disconnect(player.voice_client, force=True)
                player.voice_client = None
                await asyncio.sleep(VOICE_RECONNECT_DELAY)
                
                try:
                    player.voice_client = await user_channel.connect()
                    player._last_connect_time = time.time()  # Track connection time for grace period
                    await asyncio.sleep(VOICE_CONNECT_DELAY)
                    await safe_voice_state_change(ctx.guild, user_channel, self_deaf=True)
                except Exception as e:
                    player.voice_client = None
                    logger.error(f"Failed to reconnect: {e}")
                    await player.send_with_ttl(player.text_channel, MESSAGES['error_cant_connect'].format(error=e), 'error', ctx.message)
                    return
                finally:
                    # Always clear reconnecting flag even if connection fails
                    player._is_reconnecting = False
                
                # Resume playback
                if state == PlaybackState.PLAYING and current_track:
                    player.now_playing = current_track
                    await _play_current(ctx.guild.id)
                elif state == PlaybackState.PAUSED and current_track:
                    player.now_playing = current_track
                    player.state = PlaybackState.PAUSED
                else:
                    await _play_first(ctx.guild.id)
            
            finally:
                # Ensure flag is always cleared
                player._is_reconnecting = False
            
            return
    
    elif not VOICE_RECONNECT_ENABLED and player.voice_client and player.voice_client.is_connected():
        user_channel = ctx.author.voice.channel
        
        if player.voice_client.channel != user_channel:
            # Voice reconnect disabled - user must manually reconnect
            await player.send_with_ttl(player.text_channel, MESSAGES['error_no_permission'].format(channel=user_channel.name), 'error', ctx.message)
            return
    
    # =========================================================================
    # CASE 2: Not connected, need to join
    # =========================================================================
    
    if not player.voice_client or not player.voice_client.is_connected():
        channel = ctx.author.voice.channel
        
        if not can_connect_to_channel(channel):
            await player.send_with_ttl(player.text_channel, MESSAGES['error_no_permission'].format(channel=channel.name), 'error', ctx.message)
            return
        
        # Clean up any stale connections
        if ctx.guild.voice_client:
            await safe_disconnect(ctx.guild.voice_client, force=True)
        
        try:
            player.voice_client = await channel.connect()
            player._last_connect_time = time.time()  # Track connection time for grace period
            await asyncio.sleep(VOICE_CONNECT_DELAY)
            await safe_voice_state_change(ctx.guild, channel, self_deaf=True)
        except Exception as e:
            player.voice_client = None
            logger.error(f"Failed to connect: {e}")
            await player.send_with_ttl(player.text_channel, MESSAGES['error_cant_connect'].format(error=e), 'error', ctx.message)
            return
    
    # =========================================================================
    # CASE 3: Connected, check if paused or playing
    # =========================================================================
    
    state = player.get_playback_state()
    
    if state == PlaybackState.PAUSED:
        # Resume from pause
        track = player.get_current_track()
        if not track:
            await player.send_with_ttl(player.text_channel, MESSAGES['error_no_tracks'], 'error', ctx.message)
            return
        player.voice_client.resume()
        player.state = PlaybackState.PLAYING
        await player.send_with_ttl(player.text_channel, MESSAGES['resume'].format(track=track.display_name), 'resume', ctx.message)
        return
    
    # Start playing if not already
    if state != PlaybackState.PLAYING:
        await _play_first(ctx.guild.id)
        
        # Do initial CHANNEL SWEEP on first connection (after new "now serving" is sent)
        if AUTO_CLEANUP_ENABLED and player._last_history_cleanup == 0:
            await asyncio.sleep(MESSAGE_SETTLE_DELAY)  # Let new message settle
            asyncio.create_task(player.cleanup_channel_history())
            player._last_history_cleanup = time.time()
        
        # Delete user's play command after short delay
        if TTL_CLEANUP_ENABLED:
            await player.schedule_message_deletion(ctx.message, USER_COMMAND_TTL)
    else:
        await player.send_with_ttl(player.text_channel, MESSAGES['error_already_playing'], 'error_quick', ctx.message)

async def _execute_play_jump(ctx: commands.Context, track_number: int) -> None:
    """
    Internal: Execute play jump command (jump to specific track).
    
    Jumps to a track by its library_index. Works in both shuffled
    and unshuffled modes - the number always refers to the canonical
    library position shown in !library.
    
    Args:
        ctx: Discord context
        track_number: Track number to jump to (1-based)
        
    Side effects:
        - Does NOT add current track to played history (jumping breaks history)
        - Sets target track as now_playing
        - Rebuilds upcoming queue to continue from jumped-to track
        - Starts playback
        
    Behavior:
        Normal mode: Queue continues sequentially (19 → 20, 21, ..., 44, 1, 2...)
        Shuffle mode: Queue is reshuffled excluding the jumped-to track
        
    Note:
        Race condition is handled by track-specific callbacks in _play_current().
        Old track's callback will see it's no longer the current track and ignore itself.
        
        Jumping clears played history because the history becomes meaningless after a jump.
    """
    player = await get_player(ctx.guild.id)
    
    # Set text channel
    if player.text_channel != ctx.channel:
        player.text_channel = ctx.channel
    
    # Validate track number (also prevents huge number attacks)
    if track_number < 1 or track_number > len(player.library) or track_number > 10000:
        await player.send_with_ttl(player.text_channel, MESSAGES['error_invalid_track'].format(number=track_number, total=len(player.library)), 'error', ctx.message)
        return
    
    # Fast O(1) lookup using index map
    target_track = player.track_by_index.get(track_number - 1)  # Convert to 0-based
    
    if not target_track:
        # This should never happen, but just in case
        await player.send_with_ttl(player.text_channel, MESSAGES['error_invalid_track'].format(number=track_number, total=len(player.library)), 'error', ctx.message)
        return
    
    # Ensure we're connected
    if not player.voice_client or not player.voice_client.is_connected():
        # Need to connect first
        channel = ctx.author.voice.channel
        if not can_connect_to_channel(channel):
            await player.send_with_ttl(player.text_channel, MESSAGES['error_no_permission'].format(channel=channel.name), 'error', ctx.message)
            return
        
        try:
            player.voice_client = await channel.connect()
            player._last_connect_time = time.time()  # Track connection time for grace period
            await asyncio.sleep(VOICE_CONNECT_DELAY)
            await safe_voice_state_change(ctx.guild, channel, self_deaf=True)
            # Set text channel (already set above with initial cleanup, but ensure it's set)
            if not player.text_channel:
                player.text_channel = ctx.channel
        except Exception as e:
            player.voice_client = None
            logger.error(f"Failed to connect: {e}")
            await player.send_with_ttl(player.text_channel, MESSAGES['error_cant_connect'].format(error=e), 'error', ctx.message)
            return
    
    # Clear played history - jumping breaks the history chain
    player.played.clear()
    
    # Set target as now_playing
    player.now_playing = target_track
    
    # Rebuild queue to continue from this track
    # In normal mode: 19 → 20, 21, ..., 44, 1, 2, ..., 18
    # In shuffle mode: New shuffled order excluding track 19
    player.rebuild_queue_from_track(target_track)
    
    # Play it
    await _play_current(ctx.guild.id)

    # Do initial CHANNEL SWEEP on first connection (after new "now serving" is sent)
    if AUTO_CLEANUP_ENABLED and player._last_history_cleanup == 0:
            await asyncio.sleep(MESSAGE_SETTLE_DELAY)  # Let new message settle
            asyncio.create_task(player.cleanup_channel_history())
            player._last_history_cleanup = time.time()

    # Delete user's play jump command after short delay
    if TTL_CLEANUP_ENABLED:
        await player.schedule_message_deletion(ctx.message, USER_COMMAND_TTL)

@commands.guild_only()
@bot.command(aliases=COMMAND_ALIASES['pause'])
async def pause(ctx: commands.Context):
    """
    Pause playback.
    
    Alias: !break
    
    Uses debouncing with:
    - 1s window (pause is less spam-prone than skip)
    - 1s cooldown
    - 10 command threshold before warning
    """
    player = await get_player(ctx.guild.id)
    
    # LAYER 0: User spam check
    if await player.check_user_spam(ctx.author.id, "pause", ctx):
        return
    
    # LAYER 1: Validation
    if not player.voice_client or not player.voice_client.is_connected():
        await player.send_with_ttl(player.text_channel, MESSAGES['error_not_playing'], 'error', ctx.message)
        return
    
    if not ctx.author.voice:
        await player.send_with_ttl(player.text_channel, MESSAGES['error_not_in_voice'], 'error', ctx.message)
        return
    
    if ctx.author.voice.channel != player.voice_client.channel:
        return
    
    # LAYER 2: Global rate limit
    if player.check_global_rate_limit():
        return
    
    # LAYER 3: Debounce
    await player.debounce_command(
        command_name="pause",
        ctx=ctx,
        execute_func=lambda: _execute_pause(ctx),
        debounce_window=PAUSE_DEBOUNCE_WINDOW,
        cooldown=PAUSE_COOLDOWN,
        spam_threshold=PAUSE_SPAM_THRESHOLD,
        spam_message=None  # Layer 0 shows the warning
    )

@commands.guild_only()
@bot.command(aliases=COMMAND_ALIASES['skip'])
async def skip(ctx: commands.Context):
    """
    Skip to next track.
    
    Alias: !next
    
    Uses debouncing with:
    - 1.5s window (catches Discord rate-limited spam)
    - 2s cooldown
    - 5 command threshold before warning
    
    Design note:
        The 1.5-second window catches slow spam from Discord rate limiting.
        When you spam skip, Discord rate limits you and sends messages slowly.
        The window catches this and only executes ONE skip after it stops.
    """
    player = await get_player(ctx.guild.id)
    
    # LAYER 0: User spam check (with warnings!)
    if await player.check_user_spam(ctx.author.id, "skip", ctx):
        return
    
    # LAYER 1: Validation
    if not player.voice_client:
        await player.send_with_ttl(player.text_channel, MESSAGES['error_not_playing'], 'error', ctx.message)
        return
    
    try:
        is_connected = player.voice_client.is_connected()
    except Exception:
        is_connected = False
    
    if not is_connected:
        await player.send_with_ttl(player.text_channel, MESSAGES['error_not_playing'], 'error', ctx.message)
        return
    
    if not ctx.author.voice:
        await player.send_with_ttl(player.text_channel, MESSAGES['error_not_in_voice'], 'error', ctx.message)
        return
    
    if ctx.author.voice.channel != player.voice_client.channel:
        return
    
    # LAYER 2: Global rate limit
    if player.check_global_rate_limit():
        return
    
    # LAYER 3: Debounce (the magic that fixes spam)
    await player.debounce_command(
        command_name="skip",
        ctx=ctx,
        execute_func=lambda: _execute_skip(ctx),
        debounce_window=SKIP_DEBOUNCE_WINDOW,  # 2.5s to catch Discord's slow rate-limited spam
        cooldown=SKIP_COOLDOWN,
        spam_threshold=SKIP_SPAM_THRESHOLD,
        spam_message=None  # Layer 0 shows the warning, no need to show it twice
    )

@commands.guild_only()
@bot.command(aliases=COMMAND_ALIASES['stop'])
async def stop(ctx: commands.Context):
    """
    Disconnect bot from voice channel.
    
    Aliases: !leave, !disconnect, !dc, !bye
    
    Uses debouncing with:
    - 2s window
    - 2s cooldown
    - 5 command threshold before warning
    
    Note:
        Completely disconnects and resets state. Use !play to restart.
    """
    player = await get_player(ctx.guild.id)
    
    # LAYER 0: User spam check
    if await player.check_user_spam(ctx.author.id, "stop", ctx):
        return
    
    # LAYER 1: Validation
    if not player.voice_client or not player.voice_client.is_connected():
        if ctx.guild.voice_client:
            await safe_disconnect(ctx.guild.voice_client, force=True)
        await player.send_with_ttl(player.text_channel, MESSAGES['error_not_playing'], 'error', ctx.message)
        return
    
    if not ctx.author.voice or ctx.author.voice.channel != player.voice_client.channel:
        await player.send_with_ttl(player.text_channel, MESSAGES['error_fight_me'], 'error', ctx.message)
        return
    
    # LAYER 2: Global rate limit
    if player.check_global_rate_limit():
        return
    
    # LAYER 3: Debounce
    await player.debounce_command(
        command_name="stop",
        ctx=ctx,
        execute_func=lambda: _execute_stop(ctx),
        debounce_window=STOP_DEBOUNCE_WINDOW,
        cooldown=STOP_COOLDOWN,
        spam_threshold=STOP_SPAM_THRESHOLD,
        spam_message=None  # Layer 0 shows the warning
    )

@commands.guild_only()
@bot.command(aliases=COMMAND_ALIASES['previous'])
async def previous(ctx: commands.Context):
    """
    Go back to previous track.
    
    Goes through your play history (played tracks only).
    Stops at the beginning - no wrap-around.
    
    Aliases: !prev, !back, !ps
    
    Uses debouncing like !skip to prevent spam abuse.
    """
    player = await get_player(ctx.guild.id)
    
    # LAYER 0: User spam check
    if await player.check_user_spam(ctx.author.id, "previous", ctx):
        return
    
    # LAYER 1: Validation
    if not player.voice_client or not player.voice_client.is_connected():
        await player.send_with_ttl(player.text_channel, MESSAGES['error_not_playing'], 'error', ctx.message)
        return
    
    if not ctx.author.voice:
        await player.send_with_ttl(player.text_channel, MESSAGES['error_not_in_voice'], 'error', ctx.message)
        return
    
    if ctx.author.voice.channel != player.voice_client.channel:
        return
    
    # LAYER 2: Global rate limit
    if player.check_global_rate_limit():
        return
    
    # LAYER 3: Debounce
    await player.debounce_command(
        command_name="previous",
        ctx=ctx,
        execute_func=lambda: _execute_previous(ctx),
        debounce_window=PREVIOUS_DEBOUNCE_WINDOW,  # Matches !skip - catches Discord's slow rate-limited spam perfectly
        cooldown=PREVIOUS_COOLDOWN,
        spam_threshold=PREVIOUS_SPAM_THRESHOLD,
        spam_message=None  # Layer 0 shows the warning
    )

@commands.guild_only()
@bot.command(aliases=COMMAND_ALIASES['shuffle'])
async def shuffle(ctx: commands.Context):
    """
    Toggle shuffle mode.
    
    When enabled: Library is shuffled and auto-reshuffles on loop.
    When disabled: Returns to normal order.
    
    Current track continues playing, shuffle applies after it ends.
    Acts as a toggle - calling !shuffle twice turns it back off.
    
    Aliases: !mess, !scramble
    
    Uses debouncing to prevent spam toggling.
    """
    player = await get_player(ctx.guild.id)
    
    # Check if shuffle feature is enabled
    if not SHUFFLE_MODE_ENABLED:
        await player.send_with_ttl(player.text_channel, MESSAGES['feature_shuffle_disabled'], 'error', ctx.message)
        return
    
    # LAYER 0: User spam check
    if await player.check_user_spam(ctx.author.id, "shuffle", ctx):
        return
    
    # LAYER 1: Validation
    if not ctx.author.voice:
        await player.send_with_ttl(player.text_channel, MESSAGES['error_not_in_voice'], 'error', ctx.message)
        return
    
    # LAYER 2: Global rate limit
    if player.check_global_rate_limit():
        return
    
    # LAYER 3: Debounce
    await player.debounce_command(
        command_name="shuffle",
        ctx=ctx,
        execute_func=lambda: _execute_shuffle(ctx),
        debounce_window=SHUFFLE_DEBOUNCE_WINDOW,  # Increased from 2.0s to catch Discord's slow rate-limited spam
        cooldown=SHUFFLE_COOLDOWN,
        spam_threshold=SHUFFLE_SPAM_THRESHOLD,
        spam_message=None  # Layer 0 shows the warning
    )

@commands.guild_only()
@bot.command(aliases=COMMAND_ALIASES['unshuffle'])
async def unshuffle(ctx: commands.Context):
    """
    Disable shuffle mode and return to normal order.
    
    Idempotent - safe to call even if shuffle is already off.
    Current track continues playing, normal order applies after it ends.
    
    Aliases: !fix, !organize
    
    Uses debouncing to prevent spam.
    """
    player = await get_player(ctx.guild.id)
    
    # Check if shuffle feature is enabled
    if not SHUFFLE_MODE_ENABLED:
        await player.send_with_ttl(player.text_channel, MESSAGES['feature_shuffle_disabled'], 'error', ctx.message)
        return
    
    # LAYER 0: User spam check
    if await player.check_user_spam(ctx.author.id, "unshuffle", ctx):
        return
    
    # LAYER 1: Validation
    if not ctx.author.voice:
        await player.send_with_ttl(player.text_channel, MESSAGES['error_not_in_voice'], 'error', ctx.message)
        return
    
    # LAYER 2: Global rate limit
    if player.check_global_rate_limit():
        return
    
    # LAYER 3: Debounce
    await player.debounce_command(
        command_name="unshuffle",
        ctx=ctx,
        execute_func=lambda: _execute_unshuffle(ctx),
        debounce_window=UNSHUFFLE_DEBOUNCE_WINDOW,  # Increased from 2.0s to match !shuffle
        cooldown=UNSHUFFLE_COOLDOWN,
        spam_threshold=UNSHUFFLE_SPAM_THRESHOLD,
        spam_message=None  # Layer 0 shows the warning
    )

def generate_help_text() -> str:
    """
    Generate help text based on enabled features.
    
    CUSTOMIZATION: Edit the help components in config/messages.py
    - Change headers, footers, section titles, command descriptions
    - Each section only appears if the corresponding feature is enabled
    """
    try:
        help_parts = []
        
        # Header (always shown)
        help_parts.extend([
            HELP_TEXT['header'],
            "",
            HELP_TEXT['volume_note'],
            ""
        ])
        
        # Playback section (always shown)
        help_parts.extend([
            HELP_TEXT['playback_title'],
            *HELP_TEXT['playback_commands'],
            ""
        ])
        
        # Queue & Library section (conditional)
        if QUEUE_DISPLAY_ENABLED or LIBRARY_DISPLAY_ENABLED:
            help_parts.append(HELP_TEXT['queue_title'])
            if QUEUE_DISPLAY_ENABLED:
                help_parts.extend(HELP_TEXT['queue_commands'])
            if LIBRARY_DISPLAY_ENABLED:
                help_parts.extend(HELP_TEXT['library_commands'])
            help_parts.append("")
        
        # Shuffle section (conditional)
        if SHUFFLE_MODE_ENABLED:
            help_parts.extend([
                HELP_TEXT['shuffle_title'],
                *HELP_TEXT['shuffle_commands'],
                ""
            ])
        
        # Info section (always shown)
        help_parts.extend([
            HELP_TEXT['info_title'],
            *HELP_TEXT['info_commands'],
            "",
            HELP_TEXT['footer']
        ])
        
        return "\n".join(help_parts)
        
    except Exception as e:
        logger.error(f"Help text generation failed: {e}")
        return HELP_TEXT['generation_error']

@commands.guild_only()
@bot.command(aliases=COMMAND_ALIASES['help'])
async def help(ctx: commands.Context):
    """
    Display all available commands.
    
    Aliases: !commands, !jill
    
    Note:
        Uses debouncing to prevent spam.
    """
    player = await get_player(ctx.guild.id)
    
    # LAYER 0: User spam check
    if await player.check_user_spam(ctx.author.id, "help", ctx):
        return
    
    # LAYER 2: Global rate limit
    if player.check_global_rate_limit():
        return
    
    # LAYER 3: Debounce
    await player.debounce_command(
        command_name="help",
        ctx=ctx,
        execute_func=lambda: _execute_help(ctx),
        debounce_window=HELP_DEBOUNCE_WINDOW,
        cooldown=HELP_COOLDOWN,
        spam_threshold=HELP_SPAM_THRESHOLD,
        spam_message=None  # Silent
    )

async def _execute_help(ctx: commands.Context) -> None:
    """Internal: Execute help display (called after debounce completes)."""
    player = await get_player(ctx.guild.id)
    help_text = generate_help_text()
    await player.send_with_ttl(player.text_channel or ctx.channel, help_text, 'help', ctx.message)

# =============================================================================
# RUN BOT
# =============================================================================

if __name__ == "__main__":
    # Load bot token from environment variable
    # Token can be set via:
    #   1. .env file in bot directory: DISCORD_BOT_TOKEN=your_token_here
    #   2. System environment variable: export DISCORD_BOT_TOKEN='your_token_here'
    #   3. systemd service file: Environment="DISCORD_BOT_TOKEN=your_token_here"
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    
    if not TOKEN:
        logger.critical("DISCORD_BOT_TOKEN not found!")
        logger.critical("Set it in one of these ways:")
        logger.critical("  1. Create a .env file: DISCORD_BOT_TOKEN=your_token_here")
        logger.critical("  2. Export it: export DISCORD_BOT_TOKEN='your_token_here'")
        logger.critical("  3. Add to systemd service file")
        sys.exit(1)
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.critical(f"Bot crashed: {e}", exc_info=True)