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
Spam Protection System

Implements 5 layers of spam protection to prevent abuse and protect the Discord API.

LAYER 0: Per-User Spam Filter - Prevents individual users from flooding
LAYER 1: Validation - Fast checks before expensive operations (handled in commands)
LAYER 2: Global Rate Limiter - Protects Discord API from rate limiting
LAYER 3: Command Debouncing - Waits for spam to stop before executing
LAYER 4: Serial Queue - Executes commands one at a time (prevents race conditions)
LAYER 5: Post-Execution Cooldowns - Prevents rapid re-execution

NOTE: LAYER 2 (Global Rate Limiter) is skipped in Modern (/play) mode since
Discord handles rate limiting for slash commands internally.
"""

import asyncio
from time import monotonic as _now
import logging
from typing import Optional, Callable, Awaitable, Dict, Any

logger = logging.getLogger(__name__)

# Import from config
from config import (
    COMMAND_MODE,
    USER_COMMAND_SPAM_THRESHOLD,
    GLOBAL_RATE_LIMIT,
    USER_SPAM_WARNING_THRESHOLD,
    USER_SPAM_RESET_COOLDOWN,
    SPAM_WARNING_COOLDOWN,
    SPAM_CLEANUP_DELAY,
    COMMAND_QUEUE_MAXSIZE,
    COMMAND_QUEUE_TIMEOUT,
    SPAM_PROTECTION_ENABLED,
    SPAM_WARNING_ENABLED,
    AUTO_CLEANUP_ENABLED,
    MESSAGES,
)


class SpamProtector:
    """
    Multi-layer spam protection system for Discord bot commands.

    Prevents abuse through 5 defense layers while maintaining responsiveness.
    Each layer serves a specific purpose and can function independently.
    """

    def __init__(self, guild_id: int, bot_loop, text_channel=None):
        """
        Initialize spam protection for a guild.

        Args:
            guild_id: Discord guild ID for logging
            bot_loop: Discord bot's event loop (for debouncing)
            text_channel: Optional text channel for sending spam warnings
        """
        self.guild_id = guild_id
        self.bot_loop = bot_loop
        self.text_channel = text_channel  # Can be set later

        # LAYER 0: Per-user spam protection
        self._user_last_command: Dict[int, float] = {}  # user_id → timestamp
        self._user_spam_count: Dict[int, int] = {}      # user_id → spam count

        # LAYER 2: Global rate limiting
        self._last_queue_time: float = 0

        # LAYER 3: Command debouncing
        self._debounce_tasks: Dict[str, Any] = {}  # command_name → handle
        self._spam_counts: Dict[str, int] = {}     # command_name → count
        self._spam_warned: Dict[str, bool] = {}    # command_name → warned
        self._last_execute: Dict[str, float] = {}  # command_name → timestamp

        # LAYER 4: Command queue (serial execution)
        self._command_queue: asyncio.Queue = asyncio.Queue(maxsize=COMMAND_QUEUE_MAXSIZE)
        self._processor_task: Optional[asyncio.Task] = None

        # Spam warning timing
        self._last_spam_warning_time: float = 0

        # Reference to cleanup callback (set by player)
        self._cleanup_callback: Optional[Callable[[], Awaitable[None]]] = None

        # Track all auxiliary tasks (cleanup, debounce) for proper lifecycle management
        self._aux_tasks: set[asyncio.Task] = set()

    # =========================================================================
    # LAYER 0: Per-User Spam Filter
    # =========================================================================

    async def check_user_spam(self, user_id: int, command_name: str) -> bool:
        """
        LAYER 0: Check if user is spamming ANY commands.

        Prevents a single user from flooding the bot with commands,
        which would spam error messages and waste resources.

        Args:
            user_id: Discord user ID
            command_name: Name of command being spammed (for specific warnings)

        Returns:
            bool: True if spam detected (command should be silently ignored)
        """
        if not SPAM_PROTECTION_ENABLED:
            return False

        current_time = _now()
        last_time = self._user_last_command.get(user_id, 0)

        if current_time - last_time < USER_COMMAND_SPAM_THRESHOLD:
            # Spam detected! Increment counter
            self._user_spam_count[user_id] = self._user_spam_count.get(user_id, 0) + 1

            # Show spam warning after exactly N rapid attempts (only ONCE)
            if self._user_spam_count[user_id] == USER_SPAM_WARNING_THRESHOLD:
                if SPAM_WARNING_ENABLED:
                    await self._send_spam_warning(command_name)

            return True  # Spam detected, ignore command

        # Not spam - reset counters if enough time has passed
        if current_time - last_time > USER_SPAM_RESET_COOLDOWN:
            self._user_spam_count[user_id] = 0

        self._user_last_command[user_id] = current_time

        # Memory leak prevention: Keep only recent users (max 1000)
        if len(self._user_last_command) > 1000:
            self._cleanup_user_tracking()

        return False

    def _cleanup_user_tracking(self):
        """Remove old user tracking data to prevent memory leaks."""
        current_time = _now()
        cutoff_time = current_time - 3600  # Remove users inactive for 1 hour

        # Batch remove old entries
        old_users = [
            user_id for user_id, timestamp in self._user_last_command.items()
            if timestamp < cutoff_time
        ]

        for user_id in old_users[:200]:  # Limit to 200 removals per cleanup
            self._user_last_command.pop(user_id, None)
            self._user_spam_count.pop(user_id, None)

    async def _send_spam_warning(self, command_name: str):
        """Send spam warning message for a command."""
        spam_key = f'spam_{command_name}'
        if spam_key not in MESSAGES or not MESSAGES[spam_key]:
            return

        if not self.text_channel:
            return

        # Only send if enough time has passed since last warning
        current_time = _now()
        if current_time - self._last_spam_warning_time < SPAM_WARNING_COOLDOWN:
            return

        # Import here to avoid circular dependency
        from utils.discord_helpers import safe_send

        await safe_send(self.text_channel, MESSAGES[spam_key])
        self._last_spam_warning_time = current_time

        # Trigger delayed cleanup if callback is set
        if self._cleanup_callback and AUTO_CLEANUP_ENABLED:
            task = asyncio.create_task(self._delayed_spam_cleanup())
            self._aux_tasks.add(task)
            # Remove task from set when done to prevent memory leak
            task.add_done_callback(lambda t: self._aux_tasks.discard(t))

    async def _delayed_spam_cleanup(self):
        """
        Trigger cleanup after spam warning.

        Waits SPAM_CLEANUP_DELAY seconds to catch more spam and let
        users see the warning message before cleaning up.
        """
        await asyncio.sleep(SPAM_CLEANUP_DELAY)

        if self._cleanup_callback:
            await self._cleanup_callback()

    # =========================================================================
    # LAYER 2: Global Rate Limiter
    # =========================================================================

    def check_global_rate_limit(self) -> bool:
        """
        LAYER 2: Check global rate limit.

        Prevents queue flooding and protects Discord API from rate limiting.
        Max ~6.7 commands per second per guild.

        Returns:
            bool: True if rate limit hit (command should be silently ignored)
        """
        # Skip rate limiting for slash (Discord handles it)
        if COMMAND_MODE == 'slash':
            return False

        if not SPAM_PROTECTION_ENABLED:
            return False

        current_time = _now()

        if current_time - self._last_queue_time < GLOBAL_RATE_LIMIT:
            return True  # Rate limited

        self._last_queue_time = current_time
        return False

    # =========================================================================
    # LAYER 3: Command Debouncing
    # =========================================================================

    async def debounce_command(
        self,
        command_name: str,
        execute_func: Callable[[], Awaitable[None]],
        debounce_window: float,
        cooldown: float,
        spam_threshold: int = 5,
        spam_message: Optional[str] = None
    ):
        """
        LAYER 3: Generic command debouncing system.

        Waits for spam to stop, then executes command once.
        This handles Discord rate-limited spam gracefully.

        How it works:
        1. Each command restarts a timer
        2. If commands keep coming, timer keeps restarting
        3. When spam stops (no command for debounce_window), execute
        4. Show spam warning if spam_threshold reached

        Args:
            command_name: Unique identifier for command type (e.g., "skip")
            execute_func: Async function to execute after debounce
            debounce_window: How long to wait for spam to stop (seconds)
            cooldown: Cooldown after execution (seconds)
            spam_threshold: Show warning after N rapid commands
            spam_message: Optional spam warning message
        """
        # If spam protection disabled, execute immediately
        if not SPAM_PROTECTION_ENABLED:
            await execute_func()
            return

        # Check post-execution cooldown (LAYER 5)
        last_time = self._last_execute.get(command_name, 0)
        current_time = _now()

        if current_time - last_time < cooldown:
            logger.debug(f"Guild {self.guild_id}: {command_name} on cooldown")
            return

        # Increment spam counter
        self._spam_counts[command_name] = self._spam_counts.get(command_name, 0) + 1

        # Cancel previous debounce timer (this is the debouncing magic)
        handle = self._debounce_tasks.get(command_name)
        if handle:
            handle.cancel()

        # Show spam warning if threshold reached (only once per spam session)
        if self._spam_counts[command_name] >= spam_threshold:
            if not self._spam_warned.get(command_name, False):
                self._spam_warned[command_name] = True
                if SPAM_WARNING_ENABLED and spam_message and self.text_channel:
                    from utils.discord_helpers import safe_send
                    await safe_send(self.text_channel, spam_message)

        # Start debounce timer
        def _run_debounced():
            t = asyncio.create_task(self.queue_command(execute_func))
            self._aux_tasks.add(t)
            t.add_done_callback(lambda task: self._aux_tasks.discard(task))
            self._last_execute[command_name] = _now()
            self._spam_counts[command_name] = 0
            self._spam_warned[command_name] = False

        self._debounce_tasks[command_name] = self.bot_loop.call_later(
            debounce_window,
            _run_debounced
        )

    # =========================================================================
    # LAYER 4: Serial Command Queue
    # =========================================================================

    def start_processor(self):
        """
        Start the command queue processor.

        The processor runs in the background and executes queued commands
        one at a time. This is LAYER 4 of spam protection.

        Should be called when the spam protector is created.
        """
        if not self._processor_task:
            self._processor_task = asyncio.create_task(self._process_commands())
            logger.info(f"Guild {self.guild_id}: Command processor started")

    async def _process_commands(self):
        """
        Process commands from queue serially.

        This is the heart of our race condition prevention:
        - Commands execute ONE at a time
        - No concurrent state modifications possible

        Runs forever in background as an asyncio task.
        """
        while True:
            try:
                cmd = await self._command_queue.get()
                try:
                    await cmd()  # Execute the command
                finally:
                    self._command_queue.task_done()
            except asyncio.CancelledError:
                # Task was cancelled during shutdown - exit cleanly
                logger.debug(f"Guild {self.guild_id}: Command processor cancelled, shutting down")
                break
            except Exception as e:
                logger.error(f"Guild {self.guild_id}: Command processor error: {e}", exc_info=True)

    async def queue_command(
        self,
        cmd: Callable[[], Awaitable[None]],
        priority: bool = False
    ):
        """
        Queue a command for serial execution.

        Args:
            cmd: Async function to execute
            priority: If True, skip queue health check and use shorter timeout (for critical internal operations like _play_next)

        Note:
            Command will execute when all previous commands finish.
            This is how we prevent race conditions.
            Priority commands (internal operations) are never dropped to prevent playback stalls.
        """
        # Check queue health (skip for priority/internal commands)
        if not priority and self._command_queue.qsize() >= COMMAND_QUEUE_MAXSIZE * 0.9:  # 90% full
            logger.warning(
                f"Guild {self.guild_id}: Command queue nearly full "
                f"({self._command_queue.qsize()}/{COMMAND_QUEUE_MAXSIZE}), dropping non-priority command"
            )
            return

        try:
            timeout = COMMAND_QUEUE_TIMEOUT * (0.5 if priority else 1.0)
            await asyncio.wait_for(
                self._command_queue.put(cmd),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Guild {self.guild_id}: Command queue full, dropping command")

    # =========================================================================
    # Cleanup & Shutdown
    # =========================================================================

    async def shutdown(self):
        """
        Gracefully shutdown the spam protector.

        Cancels all tasks and clears state.
        """
        # Cancel processor task
        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        # Cancel all debounce timers
        for handle in self._debounce_tasks.values():
            if hasattr(handle, 'cancel'):
                handle.cancel()

        self._debounce_tasks.clear()

        # Cancel all auxiliary tasks (cleanup, debounce queue tasks)
        for task in list(self._aux_tasks):
            if not task.done():
                task.cancel()

        # Wait for auxiliary tasks to finish cancelling
        if self._aux_tasks:
            await asyncio.gather(*self._aux_tasks, return_exceptions=True)

        self._aux_tasks.clear()

        logger.info(f"Guild {self.guild_id}: Spam protector shutdown complete")

    # =========================================================================
    # Configuration
    # =========================================================================

    def set_text_channel(self, channel):
        """Set the text channel for spam warnings."""
        self.text_channel = channel

    def set_cleanup_callback(self, callback: Callable[[], Awaitable[None]]):
        """Set callback for cleanup after spam warnings."""
        self._cleanup_callback = callback
