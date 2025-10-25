"""
Message Cleanup System

Implements dual cleanup architecture for keeping Discord chat clean:
1. TTL Cleanup - Scheduled deletion with expiry times
2. Channel Sweep - Periodic history scanning

Both systems operate independently for redundancy and robustness.
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import disnake

logger = logging.getLogger(__name__)

# Import from config
from config.timing import (
    TTL_CHECK_INTERVAL,
    MESSAGE_TTL,
    USER_COMMAND_TTL,
    HISTORY_CLEANUP_INTERVAL,
    CLEANUP_SAFE_AGE_THRESHOLD,
    CLEANUP_HISTORY_LIMIT,
    CLEANUP_BATCH_SIZE,
    CLEANUP_BATCH_DELAY,
    SPAM_CLEANUP_DELAY,
    MESSAGE_BURIAL_CHECK_LIMIT,
    MESSAGE_BURIAL_THRESHOLD,
    USER_COMMAND_MAX_LENGTH,
)
from config.features import (
    AUTO_CLEANUP_ENABLED,
    TTL_CLEANUP_ENABLED,
    BATCH_DELETE_ENABLED,
    DELETE_OTHER_BOTS,
    SMART_MESSAGE_MANAGEMENT,
)
from utils.discord_helpers import safe_delete_message, safe_send


class CleanupManager:
    """
    Manages dual cleanup systems for Discord message cleanup.

    SYSTEM 1: TTL Cleanup - Tracks specific messages with expiration times
    SYSTEM 2: Channel Sweep - Scans channel history periodically

    Both systems run independently for redundancy. If one fails, the other
    ensures chat stays clean.
    """

    def __init__(self, guild_id: int, text_channel: Optional[disnake.TextChannel] = None, bot_user_id: Optional[int] = None):
        """
        Initialize cleanup manager.

        Args:
            guild_id: Discord guild ID for logging
            text_channel: Text channel to clean up (can be set later)
            bot_user_id: Bot's Discord user ID for message filtering
        """
        self.guild_id = guild_id
        self.text_channel = text_channel
        self.bot_user_id = bot_user_id

        # TTL Cleanup state
        self._message_cleanup_queue: List[Tuple[disnake.Message, float]] = []  # (msg, delete_time)
        self._cleanup_event = asyncio.Event()  # Event-driven wake
        self._last_now_playing_msg: Optional[disnake.Message] = None

        # History Cleanup state
        self._last_history_cleanup: float = 0

        # Worker tasks
        self._ttl_task: Optional[asyncio.Task] = None
        self._history_task: Optional[asyncio.Task] = None

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    def start_workers(self):
        """
        Start both cleanup workers.

        Should be called after initialization to begin background cleanup.
        """
        if not AUTO_CLEANUP_ENABLED:
            logger.info(f"Guild {self.guild_id}: Auto cleanup disabled - skipping workers")
            return

        if not self._ttl_task:
            self._ttl_task = asyncio.create_task(self._ttl_cleanup_worker())
            logger.info(f"Guild {self.guild_id}: TTL cleanup worker started")

        if not self._history_task:
            self._history_task = asyncio.create_task(self._history_cleanup_worker())
            logger.info(f"Guild {self.guild_id}: History cleanup worker started")

    async def shutdown(self):
        """
        Gracefully shutdown both cleanup workers.

        Cancels tasks and clears state.
        """
        # Cancel TTL worker
        if self._ttl_task and not self._ttl_task.done():
            self._ttl_task.cancel()
            try:
                await self._ttl_task
            except asyncio.CancelledError:
                pass

        # Cancel history worker
        if self._history_task and not self._history_task.done():
            self._history_task.cancel()
            try:
                await self._history_task
            except asyncio.CancelledError:
                pass

        logger.info(f"Guild {self.guild_id}: Cleanup manager shutdown complete")

    # =========================================================================
    # WORKER 1: TTL Cleanup (Scheduled Deletion)
    # =========================================================================

    async def _ttl_cleanup_worker(self):
        """
        Worker that processes scheduled message deletions.

        Checks queue periodically (TTL_CHECK_INTERVAL) and deletes expired messages.
        Uses event-driven wake for efficiency.
        """
        while True:
            try:
                # Event-driven wake: wait for new messages or timeout
                try:
                    await asyncio.wait_for(
                        self._cleanup_event.wait(),
                        timeout=TTL_CHECK_INTERVAL
                    )
                    self._cleanup_event.clear()
                except asyncio.TimeoutError:
                    pass  # Normal tick

                # Skip if nothing to clean
                if not self._message_cleanup_queue and not self._last_now_playing_msg:
                    continue

                await self._process_ttl_deletions()

            except Exception as e:
                logger.error(f"Guild {self.guild_id}: TTL cleanup worker error: {e}", exc_info=True)

    async def _process_ttl_deletions(self):
        """Process all expired messages in the TTL queue."""
        if not TTL_CLEANUP_ENABLED:
            return

        current_time = time.time()
        messages_to_delete = []
        remaining_messages = []

        # Process all messages: delete expired (unless protected), keep the rest
        for msg, delete_time in self._message_cleanup_queue:
            if current_time >= delete_time:
                # CRITICAL: Don't delete "now serving" message if music is playing
                if msg == self._last_now_playing_msg:
                    # Check if protected (would need voice_client reference)
                    # For now, keep in queue - will be handled by explicit delete
                    remaining_messages.append((msg, delete_time))
                    continue
                messages_to_delete.append(msg)
            else:
                remaining_messages.append((msg, delete_time))

        # Update queue
        self._message_cleanup_queue = remaining_messages

        # Delete in batches
        await self._batch_delete_messages(messages_to_delete)

        if messages_to_delete:
            logger.debug(f"Guild {self.guild_id}: TTL cleanup removed {len(messages_to_delete)} messages")

    # =========================================================================
    # WORKER 2: Channel Sweep (History Scanning)
    # =========================================================================

    async def _history_cleanup_worker(self):
        """
        Worker that periodically scans channel history for cleanup.

        Runs every HISTORY_CLEANUP_INTERVAL seconds to catch missed messages.
        """
        # Run initial cleanup
        if self.text_channel and self._last_history_cleanup == 0:
            await self.cleanup_channel_history()
            self._last_history_cleanup = time.time()

        while True:
            try:
                # Wait for next cleanup interval
                await asyncio.sleep(HISTORY_CLEANUP_INTERVAL)

                await self.cleanup_channel_history()
                self._last_history_cleanup = time.time()

            except Exception as e:
                logger.error(f"Guild {self.guild_id}: History cleanup worker error: {e}", exc_info=True)

    async def cleanup_channel_history(self):
        """
        Scan recent channel history and clean up old messages.

        Deletes:
        - Bot's own messages
        - User command messages (starting with !)
        - Other bots' messages (if enabled)

        Only deletes messages older than CLEANUP_SAFE_AGE_THRESHOLD.
        """
        if not AUTO_CLEANUP_ENABLED or not self.text_channel:
            return

        if CLEANUP_HISTORY_LIMIT <= 0:
            return

        try:
            messages_to_delete = []
            cutoff_dt = datetime.utcnow() - timedelta(seconds=CLEANUP_SAFE_AGE_THRESHOLD)
            other_bot_messages = []

            # Scan recent history
            async for message in self.text_channel.history(
                limit=CLEANUP_HISTORY_LIMIT,
                before=cutoff_dt,
                oldest_first=False
            ):
                # Skip protected "now serving" message
                if message == self._last_now_playing_msg:
                    continue

                # Bot's own messages
                if self.bot_user_id and message.author and message.author.id == self.bot_user_id:
                    messages_to_delete.append(message)

                # Other bots' messages
                elif DELETE_OTHER_BOTS and message.author.bot:
                    other_bot_messages.append(message)

                # User commands
                elif message.content.startswith('!') and len(message.content) <= USER_COMMAND_MAX_LENGTH:
                    messages_to_delete.append(message)

            # Keep most recent other bot message, delete older ones
            if other_bot_messages:
                for message in other_bot_messages[1:]:
                    messages_to_delete.append(message)

            # Delete in batches
            deleted_count = await self._batch_delete_messages(messages_to_delete)

            if deleted_count > 0:
                logger.debug(f"Guild {self.guild_id}: History cleanup removed {deleted_count} messages")

        except Exception as e:
            logger.debug(f"Guild {self.guild_id}: History cleanup failed (non-critical): {e}")

    # =========================================================================
    # TTL Scheduling (Public API)
    # =========================================================================

    async def schedule_message_deletion(self, message: Optional[disnake.Message], ttl_seconds: float):
        """
        Schedule a message for deletion after TTL expires.

        Uses binary search insertion to keep queue sorted for efficient processing.

        Args:
            message: Message to delete (None is safe)
            ttl_seconds: Time to live in seconds
        """
        if not message or not TTL_CLEANUP_ENABLED:
            return

        delete_time = time.time() + ttl_seconds

        # Binary search insertion (keeps queue sorted)
        insert_pos = 0
        for i, (_, existing_time) in enumerate(self._message_cleanup_queue):
            if existing_time <= delete_time:
                insert_pos = i + 1
            else:
                break

        self._message_cleanup_queue.insert(insert_pos, (message, delete_time))

        # Wake up TTL worker
        self._cleanup_event.set()

    async def send_with_ttl(
        self,
        channel: Optional[disnake.TextChannel],
        content: str,
        ttl_type: str,
        user_message: Optional[disnake.Message] = None
    ) -> Optional[disnake.Message]:
        """
        Send a message and schedule it for deletion.

        Args:
            channel: Text channel to send to
            content: Message content
            ttl_type: Type of message (key in MESSAGE_TTL dict)
            user_message: Optional user command to also delete

        Returns:
            The sent message, or None if send failed
        """
        if not channel:
            return None

        # Get TTL for this message type
        ttl_seconds = MESSAGE_TTL.get(ttl_type, MESSAGE_TTL.get('error', 15))

        # Send bot message
        bot_msg = await safe_send(channel, content)
        if not bot_msg:
            return None

        # Schedule deletions
        if TTL_CLEANUP_ENABLED:
            await self.schedule_message_deletion(bot_msg, ttl_seconds)

            if user_message:
                await self.schedule_message_deletion(user_message, ttl_seconds)

        return bot_msg

    # =========================================================================
    # Now Playing Message Management
    # =========================================================================

    async def delete_last_now_playing(self):
        """
        Immediately delete the last "Now serving" message.

        Removes it from TTL queue and deletes it.
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

    async def update_now_playing_message(
        self,
        content: str,
        voice_client = None
    ) -> Optional[disnake.Message]:
        """
        Update or send "Now serving" message with smart management.

        Tries to edit existing message if it's still visible.
        Otherwise sends a new message.

        Args:
            content: Message content
            voice_client: Voice client to check if playing (for protection)

        Returns:
            The message object (edited or new)
        """
        if not self.text_channel:
            return None

        # Try to edit existing message if smart management enabled
        if SMART_MESSAGE_MANAGEMENT and self._last_now_playing_msg:
            try:
                # Check if message is buried
                message_count = 0
                async for msg in self.text_channel.history(
                    limit=MESSAGE_BURIAL_CHECK_LIMIT,
                    after=self._last_now_playing_msg
                ):
                    message_count += 1

                if message_count < MESSAGE_BURIAL_THRESHOLD:
                    # Message still visible, edit it
                    await self._last_now_playing_msg.edit(content=content)

                    # Update TTL
                    if TTL_CLEANUP_ENABLED:
                        await self.schedule_message_deletion(
                            self._last_now_playing_msg,
                            MESSAGE_TTL['now_serving']
                        )

                    logger.debug(f"Guild {self.guild_id}: Edited 'now serving' message")
                    return self._last_now_playing_msg
                else:
                    # Message buried, send new one
                    raise Exception("Message buried by chat activity")

            except Exception as e:
                # Edit failed, delete old and send new
                logger.debug(f"Guild {self.guild_id}: Edit failed ({e}), sending new message")
                await self.delete_last_now_playing()

        # Send new message
        new_msg = await safe_send(self.text_channel, content)
        if new_msg:
            self._last_now_playing_msg = new_msg

            # Schedule deletion
            if TTL_CLEANUP_ENABLED:
                await self.schedule_message_deletion(
                    new_msg,
                    MESSAGE_TTL['now_serving']
                )

        return new_msg

    # =========================================================================
    # Spam Cleanup (Triggered by spam detection)
    # =========================================================================

    async def trigger_spam_cleanup(self):
        """
        Trigger cleanup after spam warning.

        Waits SPAM_CLEANUP_DELAY seconds to catch more spam,
        then runs history cleanup.
        """
        if not AUTO_CLEANUP_ENABLED:
            return

        try:
            await asyncio.sleep(SPAM_CLEANUP_DELAY)
            await self.cleanup_channel_history()
            self._last_history_cleanup = time.time()

            logger.debug(f"Guild {self.guild_id}: Spam cleanup completed")

        except Exception as e:
            logger.error(f"Guild {self.guild_id}: Spam cleanup error: {e}", exc_info=True)

    # =========================================================================
    # Utilities
    # =========================================================================

    async def _batch_delete_messages(self, messages: List[disnake.Message]) -> int:
        """
        Delete messages in batches with rate limiting.

        Args:
            messages: List of messages to delete

        Returns:
            Number of messages successfully deleted
        """
        if not messages or not self.text_channel:
            return 0

        deleted_count = 0
        batch_size = CLEANUP_BATCH_SIZE

        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]

            # Use bulk delete if enabled and multiple messages
            if BATCH_DELETE_ENABLED and len(batch) > 1:
                try:
                    await self.text_channel.delete_messages(batch)
                    deleted_count += len(batch)
                except Exception as e:
                    logger.debug(f"Guild {self.guild_id}: Bulk delete failed, fallback: {e}")
                    # Fallback to individual
                    for msg in batch:
                        if await safe_delete_message(msg):
                            deleted_count += 1
                        await asyncio.sleep(0.2)
            else:
                # Individual deletion
                for msg in batch:
                    if await safe_delete_message(msg):
                        deleted_count += 1
                    await asyncio.sleep(0.2)

            # Wait between batches
            if i + batch_size < len(messages):
                await asyncio.sleep(CLEANUP_BATCH_DELAY)

        return deleted_count

    # =========================================================================
    # Configuration
    # =========================================================================

    def set_text_channel(self, channel: disnake.TextChannel):
        """Set the text channel for cleanup operations."""
        self.text_channel = channel

    def set_bot_user_id(self, bot_user_id: int):
        """Set the bot's user ID for message filtering."""
        self.bot_user_id = bot_user_id
