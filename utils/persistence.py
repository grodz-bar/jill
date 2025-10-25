"""
Channel Persistence System

Manages saving/loading the last used text channel per guild to persistent storage.
Allows cleanup features to resume in the correct channel after bot restart.
"""

import os
import json
import asyncio
import logging
from typing import Dict

logger = logging.getLogger(__name__)

# Import from config
from config.paths import CHANNEL_STORAGE_FILE

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
                # Convert string keys back to integers (JSON stores keys as strings)
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

    Note:
        Uses lazy batching to reduce filesystem writes.
        Actual save happens after 10-second delay via mark_channel_dirty().
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

    try:
        data = load_last_channels()
        for gid in to_save:
            if gid in _channel_cache:
                data[gid] = _channel_cache[gid]

        with open(CHANNEL_STORAGE_FILE, 'w') as f:
            json.dump(data, f, indent=2)

        logger.debug(f"Flushed {len(to_save)} channel save(s) to disk")

    except Exception as e:
        logger.error(f"Failed to flush channel saves: {e}")
