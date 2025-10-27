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
Persistence System - Reference Implementation

Manages saving/loading guild state (channels, playlists) to persistent JSON storage.
Allows bot to resume state after restart without data loss.

CRITICAL SAFETY PATTERN (MUST FOLLOW FOR ALL PERSISTENCE):

    1. In-memory cache is the SOURCE OF TRUTH, not disk files
    2. Load from disk ONLY when cache is empty (first access)
    3. During flush/save: serialize from cache, NEVER re-read from disk

    WHY: If the file becomes corrupted between startup and flush (disk error,
    manual edit, etc.), re-reading the file would wipe the in-memory cache,
    causing permanent data loss for all guilds.

CORRECT PATTERN (see _flush_channel_saves and _write_playlists_to_disk):

    if not _cache_loaded:
        load_from_disk()  # Populate cache from file (only if empty)
    data = _cache.copy()  # Serialize from cache (source of truth)
    atomic_write(data)     # Write to disk with tempfile + os.replace()

INCORRECT PATTERN (DO NOT USE):

    data = load_from_disk()  # ❌ DANGEROUS: Could wipe cache if file corrupted
    for key in pending:
        data[key] = _cache[key]  # ❌ Partial update, loses other guilds
    write(data)

ADDITIONAL SAFETY FEATURES:
    - Atomic writes: tempfile + os.replace() prevents partial writes
    - Batch saves: 10-second delay reduces filesystem I/O
    - Graceful degradation: Corrupted files default to empty dict (log warning)
    - Shutdown flush: flush_all_immediately() ensures no data loss on exit

This file serves as the reference implementation for any future persistence needs.
"""

import os
import json
import asyncio
import logging
import tempfile
from typing import Dict, Iterable

logger = logging.getLogger(__name__)

# Import from config
from config.paths import CHANNEL_STORAGE_FILE, PLAYLIST_STORAGE_FILE

# =============================================================================
# CHANNEL PERSISTENCE
# =============================================================================

# Cache for loaded channel data to avoid repeated file I/O
_channel_cache: Dict[int, int] = {}
_cache_loaded = False
# Async batch save optimization: reduces filesystem writes by batching channel saves
_last_save_task = None
_pending_saves = set()

# =============================================================================
# PLAYLIST PERSISTENCE
# =============================================================================

# Cache for loaded playlist data to avoid repeated file I/O
_playlist_cache: Dict[int, str] = {}
_playlist_cache_loaded = False
# Async batch save optimization: reduces filesystem writes by batching playlist saves
_last_playlist_save_task = None
_pending_playlist_saves = set()


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
            with open(CHANNEL_STORAGE_FILE, 'r', encoding='utf-8') as f:
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

    except (OSError, json.JSONDecodeError, ValueError):
        logger.exception("Could not save channel storage")


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


async def _flush_channel_saves(immediate: bool = False):
    """
    Flush all pending channel saves to disk after a 10-second delay.

    This async batch save operation reduces I/O overhead by writing
    multiple channel changes in a single filesystem operation.

    Args:
        immediate: If True, flush immediately without delay (for shutdown)
    """
    global _last_save_task

    if not immediate:
        await asyncio.sleep(10)
    if not _pending_saves:
        return

    # Snapshot and clear to avoid RuntimeError from concurrent modifications
    to_save = list(_pending_saves)
    _pending_saves.clear()

    try:
        # Ensure cache is loaded, then serialize entire cache from memory.
        # This prevents data loss if the file becomes corrupted between startup and flush:
        # re-reading a corrupted file would wipe _channel_cache, losing all guilds.
        if not _cache_loaded:
            load_last_channels()
        data = _channel_cache.copy()

        # Atomic write: write to temp file then replace
        _dir = os.path.dirname(CHANNEL_STORAGE_FILE) or "."
        os.makedirs(_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile('w', delete=False, dir=_dir, encoding='utf-8') as _tmp:
            json.dump(data, _tmp, indent=2)
            _tmp_path = _tmp.name
        try:
            os.replace(_tmp_path, CHANNEL_STORAGE_FILE)
        except Exception:
            os.unlink(_tmp_path)
            raise

        logger.debug(f"Flushed {len(to_save)} channel save(s) to disk")

    except (OSError, json.JSONDecodeError, ValueError):
        logger.exception("Failed to flush channel saves")
    finally:
        # If more saves came in during the flush, schedule another pass
        if _pending_saves:
            _last_save_task = asyncio.create_task(_flush_channel_saves())


# =============================================================================
# PLAYLIST PERSISTENCE FUNCTIONS
# =============================================================================


def load_last_playlists() -> Dict[int, str]:
    """
    Load the last used playlist IDs from persistent storage.

    Returns:
        Dict[int, str]: Mapping of guild_id -> playlist_id
    """
    global _playlist_cache, _playlist_cache_loaded

    # Return cached data if already loaded
    if _playlist_cache_loaded:
        return _playlist_cache.copy()

    try:
        if os.path.exists(PLAYLIST_STORAGE_FILE):
            with open(PLAYLIST_STORAGE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert string keys back to integers (JSON stores keys as strings)
                _playlist_cache = {int(guild_id): playlist_id for guild_id, playlist_id in data.items()}
        else:
            _playlist_cache = {}

        _playlist_cache_loaded = True
        return _playlist_cache.copy()

    except (json.JSONDecodeError, ValueError, FileNotFoundError) as e:
        logger.warning(f"Could not load playlist storage: {e}")
        _playlist_cache = {}
        _playlist_cache_loaded = True
        return {}


def save_last_playlist(guild_id: int, playlist_id: str) -> None:
    """
    Save the last used playlist ID for a guild.

    Args:
        guild_id: Discord guild ID
        playlist_id: Playlist identifier (folder name)

    Note:
        Uses lazy batching to reduce filesystem writes.
        Actual save happens after 10-second delay via mark_playlist_dirty().
    """
    global _playlist_cache, _playlist_cache_loaded

    try:
        # Use cached data if available, otherwise load
        if not _playlist_cache_loaded:
            load_last_playlists()

        # Only save if playlist actually changed (avoid unnecessary I/O)
        if _playlist_cache.get(guild_id) != playlist_id:
            _playlist_cache[guild_id] = playlist_id
            mark_playlist_dirty(guild_id)

    except (OSError, json.JSONDecodeError, ValueError):
        logger.exception("Could not save playlist storage")


def mark_playlist_dirty(guild_id: int):
    """
    Mark a guild's playlist data as dirty for batch saving.

    This optimization reduces filesystem writes by batching playlist saves
    with a 10-second delay instead of immediate writes on every change.

    Args:
        guild_id: Discord guild ID to mark as dirty
    """
    _pending_playlist_saves.add(guild_id)
    global _last_playlist_save_task
    if not _last_playlist_save_task or _last_playlist_save_task.done():
        _last_playlist_save_task = asyncio.create_task(_flush_playlist_saves())


async def _flush_playlist_saves(immediate: bool = False):
    """
    Flush all pending playlist saves to disk after a 10-second delay.

    This async batch save operation reduces I/O overhead by writing
    multiple playlist changes in a single filesystem operation.

    Args:
        immediate: If True, flush immediately without delay (for shutdown)
    """
    global _last_playlist_save_task

    if not immediate:
        await asyncio.sleep(10)
    if not _pending_playlist_saves:
        return

    # Snapshot and clear to avoid RuntimeError from concurrent modifications
    to_save = list(_pending_playlist_saves)
    _pending_playlist_saves.clear()

    try:
        _write_playlists_to_disk(to_save)
        logger.debug(f"Flushed {len(to_save)} playlist save(s) to disk")

    except (OSError, json.JSONDecodeError, ValueError):
        logger.exception("Failed to flush playlist saves")
    finally:
        # If more saves came in during the flush, schedule another pass
        if _pending_playlist_saves:
            _last_playlist_save_task = asyncio.create_task(_flush_playlist_saves())


def _write_playlists_to_disk(guild_ids: Iterable[int]) -> None:
    """
    Write playlist cache entries for the provided guilds to disk.

    Args:
        guild_ids: Iterable of guild IDs to write to disk
    """
    if not guild_ids:
        return

    # Ensure cache is loaded, then serialize entire cache from memory.
    # This prevents data loss if the file becomes corrupted between startup and flush:
    # re-reading a corrupted file would wipe _playlist_cache, losing all guilds.
    if not _playlist_cache_loaded:
        load_last_playlists()
    data = _playlist_cache.copy()

    # Atomic write: write to temp file then replace
    _dir = os.path.dirname(PLAYLIST_STORAGE_FILE) or "."
    os.makedirs(_dir, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', delete=False, dir=_dir, encoding='utf-8') as _tmp:
        json.dump(data, _tmp, indent=2)
        _tmp_path = _tmp.name
    try:
        os.replace(_tmp_path, PLAYLIST_STORAGE_FILE)
    except Exception:
        os.unlink(_tmp_path)
        raise


def save_last_playlist_immediate(guild_id: int, playlist_id: str) -> None:
    """
    Persist the last used playlist ID for a guild without waiting.

    This bypasses the normal 10-second batch delay and writes immediately
    to disk. Use this for critical state changes like fallback playlist
    selection where immediate persistence is required.

    Args:
        guild_id: Discord guild ID
        playlist_id: Playlist identifier (folder name)
    """
    global _playlist_cache, _playlist_cache_loaded

    try:
        if not _playlist_cache_loaded:
            load_last_playlists()

        # Skip if already matches
        if _playlist_cache.get(guild_id) == playlist_id:
            return

        _playlist_cache[guild_id] = playlist_id

        # Remove from pending saves to avoid duplicate writes
        _pending_playlist_saves.discard(guild_id)

        # Write immediately to disk
        _write_playlists_to_disk({guild_id})

    except Exception:
        # NOTE: Intentionally catching broad Exception here (vs specific OSError/JSON errors)
        # This is a critical immediate-save path used for fallback playlist selection.
        # Must be maximally defensive and log any failure, even unexpected ones.
        logger.exception("Could not persist playlist storage immediately")


async def flush_all_immediately():
    """
    Immediately flush all pending saves to disk without delay.

    This should be called during bot shutdown to ensure no data is lost.
    Flushes both channel and playlist persistence.
    """
    await _flush_channel_saves(immediate=True)
    await _flush_playlist_saves(immediate=True)
