# Copyright (C) 2026 grodz
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

"""Persistent state management."""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from loguru import logger


class StateManager:
    """Manages runtime state that persists across bot restarts.

    Unlike config (read-only settings), state changes during bot operation
    and must survive restarts. Stored in state.json with atomic writes.

    Persisted values:
    - volume: Current playback volume (0-100), applied when joining voice
    - last_playlist: Name of last loaded playlist, restored on startup
    - shuffle: Whether shuffle mode is enabled (persisted across restarts)
    - last_track: Filename of last played track, restored to current_index on startup

    Usage:
        state_manager.get("volume", 50)     # Read with default
        state_manager.set("volume", 80)     # Update in memory
        await state_manager.save()          # Persist to disk

    File safety:
    - Uses atomic temp-file-then-rename pattern
    - Exceptions logged but not raised (fire-and-forget)
    - Unknown keys in state.json are logged, kept in memory, but filtered out on save

    Attributes:
        data_path: Directory containing state.json
        state_file: Full path to state.json
        state: Current state dict (in-memory)
    """

    # State fields with their default values:
    # - volume: Playback volume percentage (restored when joining voice)
    # - last_playlist: Most recently loaded playlist (restored on startup)
    # - shuffle: Shuffle mode enabled (persisted and restored on startup)
    # - last_track: Filename of last played track (restored to current_index on startup)
    DEFAULT_STATE = {
        "volume": 50,
        "last_playlist": None,
        "shuffle": False,
        "last_track": None,
    }

    def __init__(self, data_path: Path) -> None:
        self.data_path = data_path
        self.state_file = data_path / "state.json"
        self.state: dict = self.DEFAULT_STATE.copy()
        self._save_lock = asyncio.Lock()

    async def load(self) -> dict:
        """Load state from state.json on startup.

        Merges saved state with defaults (handles missing keys from updates).
        If file is corrupt, backs up to .bak and uses defaults.
        If file is missing, uses defaults.
        Returns the loaded state dict for convenience.
        """
        if self.state_file.exists():
            try:
                content = await asyncio.to_thread(self.state_file.read_text, encoding='utf-8')
                loaded = json.loads(content)

                # Warn about unknown keys
                if loaded:
                    unknown = set(loaded.keys()) - set(self.DEFAULT_STATE.keys())
                    if unknown:
                        logger.warning(f"ignoring unknown state keys: {', '.join(unknown)}")

                # Merge with defaults (handles missing keys from updates)
                self.state = {**self.DEFAULT_STATE, **loaded}
                vol = self.state.get('volume', 50)
                shuffle = 'on' if self.state.get('shuffle', False) else 'off'
                last_track = self.state.get('last_track')
                track_info = f", track '{last_track}'" if last_track else ""
                logger.info(f"restored state: volume {vol}%, shuffle {shuffle}{track_info}")
            except (json.JSONDecodeError, IOError) as e:
                # Preserve corrupted file for debugging
                backup = self.state_file.with_suffix('.json.bak')
                try:
                    self.state_file.rename(backup)
                    logger.warning(f"state file corrupt, backed up to {backup.name}")
                except OSError:
                    logger.warning("state file corrupt, using defaults")
                self.state = self.DEFAULT_STATE.copy()
        else:
            logger.info("state file not found, using defaults")
            self.state = self.DEFAULT_STATE.copy()
        return self.state

    async def save(self) -> None:
        """Persist current state to state.json.

        Uses atomic temp-file-then-rename pattern. Lock serializes concurrent
        saves. Only saves keys defined in DEFAULT_STATE (ignores extras).
        Exceptions are logged but not raised.
        """
        async with self._save_lock:
            temp_path = None
            try:
                self.data_path.mkdir(parents=True, exist_ok=True)
                temp_fd, temp_path = tempfile.mkstemp(dir=self.data_path, suffix='.tmp')
                # Only persist keys that are in DEFAULT_STATE
                clean_state = {k: v for k, v in self.state.items() if k in self.DEFAULT_STATE}
                await asyncio.to_thread(self._write_atomic, temp_fd, temp_path, clean_state)
                logger.debug("state saved")
            except Exception:
                if temp_path:
                    Path(temp_path).unlink(missing_ok=True)
                logger.opt(exception=True).warning("failed to save state.json")

    def _write_atomic(self, temp_fd: int, temp_path: str, data: dict) -> None:
        """Synchronous helper for atomic JSON write."""
        # fdopen can fail after mkstemp - close fd manually to prevent leak
        try:
            f = os.fdopen(temp_fd, 'w', encoding='utf-8')
        except Exception:
            os.close(temp_fd)
            raise
        with f:
            json.dump(data, f, indent=2)
        Path(temp_path).replace(self.state_file)

    def get(self, key: str, default=None) -> Any:
        """Get a state value from memory.

        Args:
            key: State key (e.g., "volume", "last_playlist", "shuffle")
            default: Value to return if key not found

        Returns:
            Current value for key, or default if not set
        """
        return self.state.get(key, default)

    def set(self, key: str, value) -> None:
        """Update a state value in memory. Call save() to persist to disk.

        Args:
            key: State key to update
            value: New value to store
        """
        self.state[key] = value
