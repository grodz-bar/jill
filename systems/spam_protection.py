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
Spam Protection System (4-Layer Architecture)

Spam protection with guild isolation via circuit breakers.
Solves the Discord client drip-feed problem while maintaining responsiveness.

LAYER 1: Per-User Spam Sessions - Detects and stops individual spammers (first filter)
LAYER 2: Per-Guild Circuit Breaker - Isolates misbehaving guilds (counts after Layer 1)
LAYER 3: Serial Queue - Executes commands one at a time (prevents race conditions)
LAYER 4: Post-Execution Cooldowns - Prevents rapid re-execution (handled in commands)

Key Features:
- Spam session detection: Handles Discord's drip-feed behavior (Layer 1 filters first)
- Guild isolation: Bad guilds can't affect good guilds (Layer 2 counts filtered commands)
- Warning messages: Preserves bot personality
- Optional abuser timeouts: Configurable punishment system
- Progressive penalties: Repeat offenders get longer lockouts
- Single-user spam protection: Layer 2 counts commands AFTER Layer 1 filtering,
  so individual spammers don't trip guild-wide circuit breaker

PREFIX vs SLASH COMMAND DIFFERENCES:

Prefix Commands (!skip):
    - Go through ALL 4 layers (full protection needed)
    - Discord client can spam, needs drip-feed handling
    - Uses spam_protected_execute() helper

Slash Commands (/skip):
    - Only use LAYER 3 (Serial Queue with priority=True)
    - BYPASS Layers 1, 2, 4 - Discord provides built-in protection:
      * Rate limiting (prevents spam)
      * Global cooldowns
      * Ephemeral responses (no message spam)
    - Call playback functions directly (e.g., _play_next())
    - Serial queue ensures race condition prevention still works

This design ensures:
    ✓ Prefix spammers can't affect slash users
    ✓ Slash commands remain responsive (no unnecessary checks)
    ✓ Both modes benefit from race condition prevention (serial queue)
"""

import asyncio
import random
from time import monotonic as _now
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Awaitable, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# Import from config
from config import (
    CIRCUIT_BREAKER_ENABLED,
    GUILD_MAX_COMMANDS_PER_SECOND,
    GUILD_MAX_QUEUE_SIZE,
    CIRCUIT_BREAK_DURATION,
    CIRCUIT_PROGRESSIVE_PENALTIES,
    CIRCUIT_TRIP_PENALTIES,
    CIRCUIT_PENALTY_RESET_TIME,
    USER_SPAM_SESSION_TRIGGER_COUNT,
    USER_SPAM_SESSION_TRIGGER_WINDOW,
    USER_SPAM_SESSION_DURATION,
    USER_SPAM_WARNINGS_ENABLED,
    USER_SPAM_WARNINGS,
    ABUSER_TIMEOUT_ENABLED,
    ABUSER_TIMEOUT_THRESHOLD,
    ABUSER_TIMEOUT_DURATION,
    ABUSER_TIMEOUT_MESSAGE,
    ABUSER_TIMEOUT_ESCALATION,
    ABUSER_TIMEOUT_ESCALATION_MULTIPLIER,
    COMMAND_QUEUE_TIMEOUT,
    SPAM_PROTECTION_ENABLED,
    AUTO_CLEANUP_ENABLED,
    SPAM_CLEANUP_DELAY,
)


# =============================================================================
# LAYER 2: PER-GUILD CIRCUIT BREAKER
# =============================================================================

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Circuit tripped, dropping commands
    HALF_OPEN = "half_open"    # Testing if guild recovered


class GuildCircuitBreaker:
    """
    Per-guild circuit breaker for resource isolation.

    Tracks command rate and trips circuit if guild exceeds limits.
    Prevents one misbehaving guild from affecting others.

    Command Counting:
        - Commands counted AFTER spam session filtering (Layer 1)
        - Only commands that actually execute count toward guild rate limit
        - Single-user spam handled by Layer 1, won't trip Layer 2
        - Multi-user abuse trips Layer 2 circuit appropriately

    States:
        CLOSED: Normal operation (commands execute normally)
        OPEN: Circuit tripped (drop all non-critical commands)
        HALF_OPEN: Testing recovery (allow one command to test)

    Triggers:
        - Commands/second exceeds GUILD_MAX_COMMANDS_PER_SECOND
        - Queue size exceeds GUILD_MAX_QUEUE_SIZE

    Recovery:
        - After CIRCUIT_BREAK_DURATION seconds, enter HALF_OPEN
        - If next command succeeds, return to CLOSED
        - If command fails, return to OPEN
    """

    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.state = CircuitState.CLOSED

        # Command rate tracking
        self.recent_commands: deque = deque(maxlen=100)  # (timestamp, command_name)

        # Circuit trip tracking
        self.trip_count = 0
        self.opened_at: Optional[float] = None
        self.last_trip_time: Optional[float] = None

        # Penalty tracking
        self.penalty_multiplier = 1.0

    def record_command(self, command_name: str, current_time: float):
        """Record a command attempt for rate tracking."""
        self.recent_commands.append((current_time, command_name))

    def get_commands_per_second(self, current_time: float) -> float:
        """Calculate current commands/second rate."""
        if not self.recent_commands:
            return 0.0

        # Count commands in last 1 second
        one_sec_ago = current_time - 1.0
        recent_count = sum(1 for t, _ in self.recent_commands if t > one_sec_ago)

        return float(recent_count)

    def should_allow_command(self, command_name: str, is_critical: bool) -> Tuple[bool, str]:
        """
        Check if command should be allowed through circuit breaker.

        NOTE: This only CHECKS the circuit state. Call record_allowed_command()
        after the command passes spam session filtering to count it toward the rate limit.

        Args:
            command_name: Name of command being checked
            is_critical: True for internal/priority commands that should always pass

        Returns:
            (allow: bool, reason: str) - Whether to allow and why
        """
        current_time = _now()

        # ALWAYS allow critical internal commands (playback operations)
        if is_critical:
            return (True, "critical")

        # Check circuit state
        if self.state == CircuitState.OPEN:
            # Circuit is open - check if we should try half-open
            time_open = current_time - self.opened_at
            lockout_duration = CIRCUIT_BREAK_DURATION * self.penalty_multiplier

            if time_open > lockout_duration:
                self.state = CircuitState.HALF_OPEN
                logger.info(
                    f"Guild {self.guild_id}: Circuit breaker entering HALF_OPEN "
                    f"(locked for {time_open:.1f}s)"
                )
            else:
                remaining = lockout_duration - time_open
                return (False, f"circuit_open (reopens in {remaining:.0f}s)")

        # Don't record yet - wait until command passes spam session filtering
        # This prevents single-user spam from tripping guild-wide circuit breaker

        # Check if rate limit would be exceeded if we recorded this command
        commands_per_sec = self.get_commands_per_second(current_time)

        if commands_per_sec > GUILD_MAX_COMMANDS_PER_SECOND:
            # Rate limit exceeded - don't allow
            return (False, f"rate_limit ({commands_per_sec:.1f}/s > {GUILD_MAX_COMMANDS_PER_SECOND}/s)")

        # In HALF_OPEN, we'll transition to CLOSED when command is recorded
        return (True, "allowed")

    def record_allowed_command(self, command_name: str):
        """
        Record that a command passed all filters and is being queued.

        This should be called AFTER spam session filtering, so only commands
        that actually execute count toward the guild rate limit.

        Args:
            command_name: Name of command being recorded
        """
        current_time = _now()
        self.record_command(command_name, current_time)

        # If we're in HALF_OPEN, transition back to CLOSED
        if self.state == CircuitState.HALF_OPEN:
            self._close_circuit(current_time)

        # Check if this command puts us over the rate limit
        commands_per_sec = self.get_commands_per_second(current_time)
        if commands_per_sec > GUILD_MAX_COMMANDS_PER_SECOND:
            self._trip_circuit(current_time, commands_per_sec)

    def _trip_circuit(self, current_time: float, rate: float):
        """Trip the circuit breaker."""
        self.state = CircuitState.OPEN
        self.opened_at = current_time
        self.last_trip_time = current_time
        self.trip_count += 1

        # Calculate penalty for repeat offenders
        if CIRCUIT_PROGRESSIVE_PENALTIES:
            self.penalty_multiplier = CIRCUIT_TRIP_PENALTIES.get(
                self.trip_count,
                CIRCUIT_TRIP_PENALTIES[max(CIRCUIT_TRIP_PENALTIES.keys())]
            )

        lockout_duration = CIRCUIT_BREAK_DURATION * self.penalty_multiplier

        logger.warning(
            f"Guild {self.guild_id}: Circuit breaker TRIPPED "
            f"(rate: {rate:.1f}/s, trip #{self.trip_count}, "
            f"lockout: {lockout_duration:.0f}s, penalty: {self.penalty_multiplier}x)"
        )

    def _close_circuit(self, current_time: float):
        """Close the circuit (return to normal operation)."""
        self.state = CircuitState.CLOSED

        # Reset penalty if enough time has passed since last trip
        if self.last_trip_time:
            time_since_trip = current_time - self.last_trip_time
            if time_since_trip > CIRCUIT_PENALTY_RESET_TIME:
                self.trip_count = 0
                self.penalty_multiplier = 1.0
                logger.info(f"Guild {self.guild_id}: Circuit breaker penalties RESET (good behavior)")

        logger.info(f"Guild {self.guild_id}: Circuit breaker CLOSED (recovered)")


# =============================================================================
# LAYER 1: PER-USER SPAM SESSIONS
# =============================================================================

@dataclass
class UserSpamSession:
    """
    Tracks spam session for a single user.

    Spam session is triggered when user sends commands too rapidly.
    During session, commands are dropped to prevent Discord's drip-feed
    from continually resetting our protection.

    Key insight: Discord client drip-feeds spam at ~1 command/sec after
    the first 5 rapid commands. Without session tracking, each drip-fed
    command would reset our debounce timer, causing lag.
    """
    user_id: int
    command_name: str

    # Command timing tracking
    command_times: deque = field(default_factory=lambda: deque(maxlen=20))

    # Spam session state
    in_spam_session: bool = False
    session_start: Optional[float] = None
    commands_during_session: int = 0
    warning_sent: bool = False

    # Abuser timeout state
    timeout_until: Optional[float] = None
    timeout_count: int = 0


class UserSpamTracker:
    """
    Tracks spam sessions for all users in a guild.

    Each user is tracked independently so multiple users don't interfere.
    Handles Discord's client-side rate limiting and drip-feed behavior.
    """

    def __init__(self, guild_id: int, text_channel=None):
        self.guild_id = guild_id
        self.text_channel = text_channel

        # Track spam sessions: (user_id, command_name) → UserSpamSession
        self._sessions: Dict[Tuple[int, str], UserSpamSession] = {}

        # Track last command time per user (for cleanup)
        self._user_last_seen: Dict[int, float] = {}

    async def check_user_spam(
        self,
        user_id: int,
        command_name: str,
        execute_func: Callable[[], Awaitable[None]]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if user is spamming and handle spam session.

        Args:
            user_id: Discord user ID
            command_name: Command being executed
            execute_func: Function to execute (called once if spam detected)

        Returns:
            (should_execute: bool, reason: str) - Whether to execute command and why

        Behavior:
            - Normal command: Execute immediately
            - First spam detection (3 in 1.5s): Execute once, send warning, enter session
            - During spam session: Drop all commands until session ends
            - Session ends: After USER_SPAM_SESSION_DURATION of no commands
        """
        if not SPAM_PROTECTION_ENABLED:
            return (True, "spam_protection_disabled")

        current_time = _now()
        self._user_last_seen[user_id] = current_time

        # Get or create session for this user+command combo
        session_key = (user_id, command_name)
        if session_key not in self._sessions:
            self._sessions[session_key] = UserSpamSession(user_id, command_name)

        session = self._sessions[session_key]

        # Check if user is timed out
        if session.timeout_until and current_time < session.timeout_until:
            remaining = session.timeout_until - current_time
            return (False, f"timed_out (for {remaining:.0f}s more)")
        elif session.timeout_until and current_time >= session.timeout_until:
            # Timeout expired
            session.timeout_until = None
            logger.info(f"Guild {self.guild_id} User {user_id}: Timeout expired")

        # Record this command
        session.command_times.append(current_time)

        # Check if in active spam session
        if session.in_spam_session:
            # Calculate time since session started
            time_in_session = current_time - session.session_start

            # Check if session should end
            if len(session.command_times) > 0:
                last_command_time = session.command_times[-1]
                time_since_last = current_time - last_command_time

                # Session ends after USER_SPAM_SESSION_DURATION of silence
                # (This is the KEY to handling Discord's drip-feed)
                if time_in_session > USER_SPAM_SESSION_DURATION:
                    # Exit spam session
                    logger.info(
                        f"Guild {self.guild_id} User {user_id}: Spam session ended "
                        f"({session.commands_during_session} commands dropped)"
                    )
                    session.in_spam_session = False
                    session.session_start = None
                    session.commands_during_session = 0
                    session.warning_sent = False
                    # Fall through to normal processing
                else:
                    # Still in spam session - drop command
                    session.commands_during_session += 1

                    # Check if user should be timed out (heavy abuse)
                    if (ABUSER_TIMEOUT_ENABLED and
                        session.commands_during_session >= ABUSER_TIMEOUT_THRESHOLD and
                        not session.timeout_until):
                        await self._timeout_user(session, current_time)

                    return (False, f"spam_session (dropped {session.commands_during_session})")

        # Not in spam session - check if we should enter one
        # Count recent commands within trigger window
        trigger_time = current_time - USER_SPAM_SESSION_TRIGGER_WINDOW
        recent_commands = [t for t in session.command_times if t > trigger_time]

        if len(recent_commands) >= USER_SPAM_SESSION_TRIGGER_COUNT:
            # ENTER SPAM SESSION
            session.in_spam_session = True
            session.session_start = current_time
            session.commands_during_session = 0

            logger.info(
                f"Guild {self.guild_id} User {user_id}: Spam session started "
                f"({len(recent_commands)} commands in {USER_SPAM_SESSION_TRIGGER_WINDOW}s)"
            )

            # Send warning message
            if USER_SPAM_WARNINGS_ENABLED and not session.warning_sent:
                await self._send_warning(user_id, command_name)
                session.warning_sent = True

            # Execute the command ONCE (first command that triggered session)
            await execute_func()

            return (False, "spam_session_started (executed once)")

        # Normal command - allow execution
        return (True, "normal")

    async def _send_warning(self, user_id: int, command_name: str):
        """Send spam warning message to user."""
        if not self.text_channel or not USER_SPAM_WARNINGS:
            return

        # Pick random warning message
        warning = random.choice(USER_SPAM_WARNINGS)

        try:
            from utils.discord_helpers import safe_send
            await safe_send(self.text_channel, warning)

            # Schedule cleanup if enabled
            if AUTO_CLEANUP_ENABLED:
                # Import here to avoid circular dependency
                from core.player import get_player
                try:
                    player = await get_player(self.guild_id, None, None)
                    if player and player.cleanup_manager:
                        asyncio.create_task(self._delayed_cleanup(player))
                except Exception as e:
                    logger.debug(f"Guild {self.guild_id}: Could not schedule warning cleanup: {e}")
        except Exception as e:
            logger.error(f"Guild {self.guild_id}: Failed to send spam warning: {e}")

    async def _delayed_cleanup(self, player):
        """Trigger cleanup after spam warning."""
        await asyncio.sleep(SPAM_CLEANUP_DELAY)
        if player.cleanup_manager:
            await player.cleanup_manager.cleanup_old_messages()

    async def _timeout_user(self, session: UserSpamSession, current_time: float):
        """Timeout a user for excessive spam."""
        session.timeout_count += 1

        # Calculate timeout duration with escalation
        duration = ABUSER_TIMEOUT_DURATION
        if ABUSER_TIMEOUT_ESCALATION and session.timeout_count > 1:
            duration *= (ABUSER_TIMEOUT_ESCALATION_MULTIPLIER ** (session.timeout_count - 1))

        session.timeout_until = current_time + duration

        logger.warning(
            f"Guild {self.guild_id} User {session.user_id}: TIMED OUT for {duration:.0f}s "
            f"(timeout #{session.timeout_count}, {session.commands_during_session} commands in session)"
        )

        # Send timeout message
        if self.text_channel:
            try:
                from utils.discord_helpers import safe_send
                message = ABUSER_TIMEOUT_MESSAGE.format(
                    user=f"<@{session.user_id}>",
                    duration=int(duration)
                )
                await safe_send(self.text_channel, message)
            except Exception as e:
                logger.error(f"Guild {self.guild_id}: Failed to send timeout message: {e}")

    def cleanup_old_sessions(self, current_time: float):
        """Remove old session data to prevent memory leaks."""
        # Remove sessions for users not seen in 1 hour
        cutoff = current_time - 3600
        old_users = [uid for uid, last_seen in self._user_last_seen.items() if last_seen < cutoff]

        for user_id in old_users:
            # Remove all sessions for this user
            self._sessions = {
                key: session for key, session in self._sessions.items()
                if session.user_id != user_id
            }
            del self._user_last_seen[user_id]

        if old_users:
            logger.debug(f"Guild {self.guild_id}: Cleaned up {len(old_users)} old user sessions")


# =============================================================================
# MAIN SPAM PROTECTOR CLASS
# =============================================================================

class SpamProtector:
    """
    4-layer spam protection system for Discord bot commands.

    Architecture:
        LAYER 1: User Spam Sessions - Per-user tracking and spam detection (first filter)
        LAYER 2: Circuit Breaker - Guild isolation (bad guilds can't touch good guilds)
        LAYER 3: Serial Queue - One command at a time (race condition prevention)
        LAYER 4: Post-Execution Cooldowns - Handled in command handlers

    Layer Interaction:
        - Layer 1 filters spam sessions first
        - Layer 2 counts commands AFTER Layer 1 filtering
        - Single-user spam handled by Layer 1, won't trip Layer 2
        - Multi-user abuse trips Layer 2 circuit breaker appropriately
        - Commands execute serially through Layer 3 regardless of spam state

    Key features:
        - Discord drip-feed handling: Spam sessions can't be reset by slow commands
        - Guild isolation: Circuit breakers prevent one guild from affecting others
        - Per-guild rate limiting: Each guild has independent resource limits
        - Per-user tracking: Multiple users in a guild don't interfere with each other
        - Single-user spam protection: Won't trigger guild-wide lockouts
    """

    def __init__(self, guild_id: int, bot_loop, text_channel=None):
        """
        Initialize spam protection for a guild.

        Args:
            guild_id: Discord guild ID
            bot_loop: Discord bot's event loop
            text_channel: Optional text channel for warnings
        """
        self.guild_id = guild_id
        self.bot_loop = bot_loop
        self.text_channel = text_channel

        # LAYER 1: User Spam Tracking
        self.user_tracker = UserSpamTracker(guild_id, text_channel)

        # LAYER 2: Circuit Breaker
        self.circuit_breaker = GuildCircuitBreaker(guild_id) if CIRCUIT_BREAKER_ENABLED else None

        # LAYER 3: Serial command queue
        self._command_queue: asyncio.Queue = asyncio.Queue(maxsize=GUILD_MAX_QUEUE_SIZE)
        self._processor_task: Optional[asyncio.Task] = None

        # LAYER 4: Post-execution cooldowns (tracked per command)
        self._last_execute: Dict[str, float] = {}  # command_name → timestamp

        # Cleanup callback
        self._cleanup_callback: Optional[Callable[[], Awaiting[None]]] = None

    # =========================================================================
    # LAYER 2: Circuit Breaker
    # =========================================================================

    def check_circuit_breaker(self, command_name: str, is_critical: bool = False) -> Tuple[bool, str]:
        """
        Check if circuit breaker allows this command.

        Args:
            command_name: Command being checked
            is_critical: True for internal/priority commands

        Returns:
            (allow: bool, reason: str)
        """
        if not self.circuit_breaker:
            return (True, "circuit_breaker_disabled")

        return self.circuit_breaker.should_allow_command(command_name, is_critical)

    def record_circuit_breaker_command(self, command_name: str):
        """
        Record that a command passed spam session filtering and is being queued.

        This should be called AFTER spam session check, so only commands that
        actually execute count toward guild rate limit.

        Args:
            command_name: Command being recorded
        """
        if self.circuit_breaker:
            self.circuit_breaker.record_allowed_command(command_name)

    # =========================================================================
    # LAYER 1: Per-User Spam Sessions
    # =========================================================================

    async def check_user_spam(
        self,
        user_id: int,
        command_name: str,
        execute_func: Callable[[], Awaitable[None]]
    ) -> Tuple[bool, str]:
        """
        Check if user is spamming and handle spam session.

        This is the main entry point for command spam checking.

        Args:
            user_id: Discord user ID
            command_name: Command being executed
            execute_func: Function to execute if spam session starts

        Returns:
            (should_execute: bool, reason: str)
        """
        return await self.user_tracker.check_user_spam(user_id, command_name, execute_func)

    # =========================================================================
    # LAYER 3: Serial Queue
    # =========================================================================

    def start_processor(self):
        """Start the command queue processor."""
        if not self._processor_task:
            self._processor_task = asyncio.create_task(self._process_commands())
            logger.debug(f"Guild {self.guild_id}: Command processor started")

    async def _process_commands(self):
        """
        Process commands from queue serially.

        Commands execute ONE at a time to prevent race conditions.
        This is critical for playback state consistency.
        """
        while True:
            try:
                cmd = await self._command_queue.get()
                try:
                    await cmd()
                finally:
                    self._command_queue.task_done()
            except asyncio.CancelledError:
                logger.debug(f"Guild {self.guild_id}: Command processor cancelled")
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
            priority: If True, use shorter timeout (for critical internal ops)
        """
        # Check queue health
        if not priority and self._command_queue.qsize() >= GUILD_MAX_QUEUE_SIZE * 0.9:
            logger.warning(
                f"Guild {self.guild_id}: Command queue nearly full "
                f"({self._command_queue.qsize()}/{GUILD_MAX_QUEUE_SIZE}), dropping command"
            )
            return

        try:
            timeout = COMMAND_QUEUE_TIMEOUT * (0.5 if priority else 1.0)
            await asyncio.wait_for(
                self._command_queue.put(cmd),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Guild {self.guild_id}: Command queue timeout, dropping command")

    # =========================================================================
    # LAYER 4: Post-Execution Cooldowns
    # =========================================================================

    def check_cooldown(self, command_name: str, cooldown: float) -> Tuple[bool, str]:
        """
        Check if command is on cooldown.

        Args:
            command_name: Command to check
            cooldown: Cooldown duration in seconds

        Returns:
            (allow: bool, reason: str)
        """
        last_time = self._last_execute.get(command_name, 0)
        current_time = _now()

        if current_time - last_time < cooldown:
            remaining = cooldown - (current_time - last_time)
            return (False, f"cooldown (for {remaining:.1f}s more)")

        return (True, "cooldown_ok")

    def record_execution(self, command_name: str):
        """Record that a command was executed (start cooldown)."""
        self._last_execute[command_name] = _now()

    # =========================================================================
    # Configuration
    # =========================================================================

    def set_text_channel(self, channel):
        """Set text channel for warnings."""
        self.text_channel = channel
        self.user_tracker.text_channel = channel

    def set_cleanup_callback(self, callback: Callable[[], Awaitable[None]]):
        """Set callback for cleanup after warnings."""
        self._cleanup_callback = callback

    # =========================================================================
    # Cleanup & Shutdown
    # =========================================================================

    async def shutdown(self):
        """Gracefully shutdown the spam protector."""
        # Cancel processor task
        if self._processor_task and not self._processor_task.done():
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        logger.debug(f"Guild {self.guild_id}: Spam protector shutdown complete")
