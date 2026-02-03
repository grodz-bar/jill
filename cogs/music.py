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

"""Music playback commands for Jill."""

import asyncio
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

import aiohttp
import discord
import mafic
from discord import app_commands
from discord.ext import commands
from loguru import logger

from ui.control_panel import ControlPanelLayout, DrinkCounter
from utils.library import ROOT_PLAYLIST_NAME
from utils.permissions import require_permission
from utils.response import (
    ResponseMixin,
    escape_markdown,
    truncate_for_display,
    CHOICE_NAME_MAX,
    EMBED_FIELD_MAX,
)
from utils.search import autocomplete_search, get_best_match
from utils.holidays import get_active_holiday


def _load_json(path: Path) -> dict:
    """Load JSON file synchronously."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


@dataclass
class GuildQueue:
    """Queue state for playback.

    Note: Named 'GuildQueue' following Discord.py conventions. For this single-guild
    bot, there will only ever be one instance, but the pattern remains correct.

    Metadata Architecture:
    - metadata_cache: Loaded from data/metadata/<playlist>.json on playlist switch (dict keyed by filename)
    - current_metadata: Captured when track starts playing (survives playlist switches)
    - Display uses current_metadata for "now playing", metadata_cache for queue tracks
    """
    playlist_name: str = ""
    tracks: list[Path] = field(default_factory=list)  # Full playlist (canonical order)
    current: Path | None = None  # Currently playing track
    current_index: int | None = None  # Position in active playlist (None = orphaned/no position)

    # Metadata (Mutagen cache - single source of truth)
    metadata_cache: dict[str, dict] = field(default_factory=dict)  # filename -> metadata
    current_metadata: dict | None = None  # Frozen on track start, survives playlist switches

    # Playback modes
    shuffle: bool = False
    shuffled_tracks: list[Path] | None = None  # Stable shuffled order (None when shuffle OFF)
    song_loop: bool = False  # Loop current song (playlist always loops)

    @property
    def display_playlist_name(self) -> str | None:
        """Playlist name for display. None if using root folder (no playlists)."""
        if self.playlist_name and self.playlist_name != ROOT_PLAYLIST_NAME:
            return self.playlist_name
        return None

    @property
    def active_tracks(self) -> list[Path]:
        """Get the active playlist (shuffled if shuffle=True, else canonical)."""
        return self.shuffled_tracks if (self.shuffle and self.shuffled_tracks) else self.tracks

    async def load_metadata_cache(self, cache_dir: Path, playlist_name: str) -> None:
        """Load metadata cache from JSON file into memory.

        Called on playlist switch. Cache is keyed by filename for O(1) lookup.
        """
        cache_file = cache_dir / f'{playlist_name}.json'

        if not cache_file.exists():
            self.metadata_cache = {}
            return

        try:
            data = await asyncio.to_thread(_load_json, cache_file)
            # Convert from {file_id: metadata} to {filename: metadata}
            self.metadata_cache = {
                entry.get("filename", ""): entry
                for entry in data.values()
                if entry.get("filename")
            }
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
            logger.warning(f"failed to load cache for '{playlist_name}': {e}")
            self.metadata_cache = {}

    def capture_current_metadata(self) -> None:
        """Capture metadata for current track (call on track start).

        This freezes the metadata so it survives playlist switches.
        """
        if self.current:
            filename = self.current.name
            self.current_metadata = self.metadata_cache.get(filename, {
                "title": self.current.stem,
                "artist": None
            })
        else:
            self.current_metadata = None

    def get_current_display(self) -> tuple[str, str | None]:
        """Get (title, artist) for current track with fallbacks.

        Uses current_metadata (frozen at track start) for consistency.
        Returns None for artist if missing.
        """
        if self.current_metadata:
            title = self.current_metadata.get("title", self.current.stem if self.current else "unknown")
            artist = self.current_metadata.get("artist")
            return (title, artist)
        if self.current:
            return (self.current.stem, None)
        return ("unknown", None)

    def get_track_display(self, track: Path) -> tuple[str, str | None]:
        """Get (title, artist) for any track in the queue.

        Uses metadata_cache for upcoming/history tracks.
        Returns None for artist if missing.
        """
        metadata = self.metadata_cache.get(track.name, {})
        title = metadata.get("title", track.stem)
        artist = metadata.get("artist")
        return (title, artist)

    def set_current_track(self, index: int | None) -> None:
        """Set current track by index, keeping current_index and current in sync.

        Use this instead of manually setting current_index to prevent sync bugs.
        """
        if index is None or not self.active_tracks:
            self.current_index = None
            self.current = None
            self.current_metadata = None
        elif 0 <= index < len(self.active_tracks):
            self.current_index = index
            self.current = self.active_tracks[index]
        else:
            # Invalid index - reset to beginning
            self.current_index = 0
            self.current = self.active_tracks[0]
            logger.warning(f"invalid track index {index}, reset to 0")

    def set_playlist(self, name: str, tracks: list[Path]) -> None:
        """Load a new playlist (sync part - call load_metadata_cache separately)."""
        self.playlist_name = name
        self.tracks = tracks.copy()
        self.current_index = None  # Orphaned - current track not in new playlist
        logger.debug(f"loaded {len(self.tracks)} tracks from {self.playlist_name!r}")

        # Clear orphaned track reference - prevents navigation issues and 404s
        # Keep current_metadata for display (documented at line 71 to survive playlist switches)
        if self.current and self.current not in self.tracks:
            self.current = None

        # Disable loop on playlist switch (clean slate)
        self.song_loop = False

        # Regenerate shuffle if shuffle is active
        if self.shuffle:
            self._regenerate_shuffle(exclude_last=None)
        else:
            self.shuffled_tracks = None

    def clear(self) -> None:
        """Clear current track state. Preserves current_index for resume after reconnect."""
        self.current = None
        self.current_metadata = None

    def advance_track(self) -> Path | None:
        """Advance to next track, handling loop and shuffle regeneration."""
        # Song loop - repeat current
        if self.song_loop and self.current:
            return self.current

        # No tracks loaded
        if not self.tracks:
            return None

        # Orphaned track (playlist switched) - start at beginning
        if self.current_index is None:
            self.current_index = 0
            self.current = self.active_tracks[0]
            return self.current

        # Advance index
        next_index = (self.current_index + 1) % len(self.active_tracks)

        # Loop boundary - regenerate shuffle if needed
        if next_index == 0 and self.shuffle and self.shuffled_tracks:
            self._regenerate_shuffle(exclude_last=self.current)

        self.current_index = next_index
        self.current = self.active_tracks[next_index]
        return self.current

    def previous_track(self) -> Path | None:
        """Go to previous track in playlist."""
        if not self.tracks:
            return None

        # No current index - can't go back
        if self.current_index is None:
            return None

        # Song loop - restart current
        if self.song_loop and self.current:
            return self.current

        # Go back one position
        prev_index = (self.current_index - 1) % len(self.active_tracks)
        self.current_index = prev_index
        self.current = self.active_tracks[prev_index]
        return self.current

    def enable_shuffle(self) -> None:
        """Enable shuffle mode - generate shuffled playlist."""
        self.shuffle = True
        self._regenerate_shuffle(exclude_last=None)

        if self.current and self.shuffled_tracks:
            if self.current in self.shuffled_tracks:
                # Move current to front for full queue ahead
                self.shuffled_tracks.remove(self.current)
                self.shuffled_tracks.insert(0, self.current)
                self.current_index = 0
            else:
                # Current track not in new shuffle (e.g., after playlist switch)
                self.set_current_track(0)
                logger.debug("current track not in shuffled list, reset to first")

    def disable_shuffle(self) -> None:
        """Disable shuffle - return to canonical order."""
        self.shuffle = False
        self.shuffled_tracks = None

        # Update current_index to position in canonical list
        if self.current:
            try:
                self.current_index = self.tracks.index(self.current)
            except ValueError:
                # Current track not in playlist (e.g., after playlist switch)
                self.set_current_track(0)
                logger.debug("current track not in canonical list, reset to first")

    def _regenerate_shuffle(self, exclude_last: Path | None) -> None:
        """Generate new shuffled order, optionally excluding last track."""
        if exclude_last and exclude_last in self.tracks:
            # Shuffle all except last, then append last to end
            to_shuffle = [t for t in self.tracks if t != exclude_last]
            random.shuffle(to_shuffle)
            self.shuffled_tracks = to_shuffle + [exclude_last]
        else:
            # Fresh shuffle of entire playlist
            self.shuffled_tracks = self.tracks.copy()
            random.shuffle(self.shuffled_tracks)


@dataclass
class VoiceSessionState:
    """Track why playback was paused to avoid unwanted resume."""
    was_paused_by_user: bool = False  # /pause command
    was_auto_paused: bool = False     # Auto-paused when alone


class Music(ResponseMixin, commands.Cog):
    """Core music playback functionality."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Single-guild bot: This dict will only ever have one entry.
        # Pattern kept for Discord.py convention compatibility.
        self.guild_queues: dict[int, GuildQueue] = {}

        # Phase 8: Inactivity timer and auto-pause state
        self.inactivity_tasks: dict[int, asyncio.Task] = {}
        self.pause_states: dict[int, VoiceSessionState] = {}

        # Progress bar update task
        self.progress_update_tasks: dict[int, asyncio.Task] = {}

        # Panel update debounce tasks (prevents rapid concurrent edits)
        self._panel_update_tasks: dict[int, asyncio.Task] = {}
        # Panel update lock (prevents out-of-order execution)
        self._panel_update_lock: dict[int, asyncio.Lock] = {}

        # Playback operation lock (prevents concurrent skip/previous/play races)
        self._playback_locks: dict[int, asyncio.Lock] = {}

    def _get_playback_lock(self, guild_id: int) -> asyncio.Lock:
        """Get or create playback lock for a guild.

        Prevents race conditions when multiple operations try to change
        the current track simultaneously (skip, previous, on_track_end).
        All playback-modifying operations should acquire this lock.
        """
        if guild_id not in self._playback_locks:
            self._playback_locks[guild_id] = asyncio.Lock()
        return self._playback_locks[guild_id]

    async def cog_unload(self) -> None:
        """Cleanup when cog is unloaded."""
        for task in self.inactivity_tasks.values():
            if not task.done():
                task.cancel()
        for task in self.progress_update_tasks.values():
            if not task.done():
                task.cancel()
        for task in self._panel_update_tasks.values():
            if not task.done():
                task.cancel()

        # Clear per-guild state dictionaries
        self.guild_queues.clear()
        self.inactivity_tasks.clear()
        self.pause_states.clear()
        self.progress_update_tasks.clear()
        self._panel_update_tasks.clear()
        self._panel_update_lock.clear()
        self._playback_locks.clear()

    def get_queue(self, guild_id: int) -> GuildQueue:
        """Get or create queue for guild with restored state."""
        if guild_id not in self.guild_queues:
            # Create queue with restored shuffle state
            # Note: enable_shuffle() will be called when playlist is loaded
            state = self.bot.state_manager
            self.guild_queues[guild_id] = GuildQueue(
                shuffle=state.get("shuffle", False),
                # song_loop always False on startup (not persisted)
            )
        return self.guild_queues[guild_id]

    def _resolve_playlist(self, names: list[str], warn_invalid: bool = False) -> str:
        """Resolve playlist using priority: default_playlist > last_playlist > names[0].

        Args:
            names: Available playlist names from library
            warn_invalid: Log warning if default_playlist is set but invalid

        Returns:
            Resolved playlist name (always returns something if names is non-empty)
        """
        # Priority 1: default_playlist from config (env > yaml)
        default = self.bot.config_manager.get("default_playlist")
        if default and (default := default.strip()):
            default_lower = default.lower()
            for pname in names:
                if pname == default_lower:
                    return pname
            if warn_invalid:
                logger.warning(f"default_playlist '{default}' not found, ignoring")

        # Priority 2: last_playlist from saved state
        saved = self.bot.state_manager.get("last_playlist")
        if saved:
            for pname in names:
                if pname == saved:
                    return pname

        # Priority 3: first available
        return names[0]

    async def preload_playlist(self, guild_id: int) -> None:
        """Preload playlist and metadata cache on startup."""
        names = self.bot.library.get_playlist_names()
        if not names:
            return

        queue = self.get_queue(guild_id)
        playlist_name = self._resolve_playlist(names, warn_invalid=True)

        tracks = self.bot.library.get_playlist(playlist_name)
        queue.set_playlist(playlist_name, tracks)
        await queue.load_metadata_cache(self.bot.metadata_cache_path, playlist_name)
        logger.debug(f"preloaded '{playlist_name}'")

    def get_drink_counter(self, guild_id: int) -> DrinkCounter:
        """Get or create drink counter for guild.

        Automatically recreates counter when holiday status changes (e.g., midnight
        on Christmas Eve), so themed emojis appear without bot restart.
        """
        panel_config = self.bot.config_manager.get("panel", {})
        drink_emojis_enabled = panel_config.get("drink_emojis_enabled", True)

        # Determine current emojis (holiday or default)
        holiday = get_active_holiday()
        if holiday and drink_emojis_enabled and "emojis" in holiday:
            drink_emojis = holiday["emojis"]
        else:
            drink_emojis = panel_config.get("drink_emojis", ['🍸', '🍹', '🍻', '🍸', '🍷', '🧉', '🍶', '🥃'])

        # Check if existing counter has different emojis (holiday changed)
        if guild_id in self.bot.drink_counters:
            existing = self.bot.drink_counters[guild_id]
            # Compare emoji lists - if same, return cached counter
            if existing.drink_emojis == drink_emojis and existing.enabled == drink_emojis_enabled:
                return existing
            # Holiday status changed - recreate counter (position resets to 0)

        counter = DrinkCounter(drink_emojis, enabled=drink_emojis_enabled)
        self.bot.drink_counters[guild_id] = counter
        return counter

    def _panel_enabled(self) -> bool:
        """Check if control panel is enabled in config."""
        panel_config = self.bot.config_manager.get("panel", {})
        return panel_config.get("enabled", True)

    async def reload_metadata(self, guild_id: int) -> None:
        """Reload metadata cache for guild's queue from disk."""
        if guild_id not in self.guild_queues:
            return
        queue = self.guild_queues[guild_id]
        if not queue.playlist_name:
            return
        try:
            await queue.load_metadata_cache(self.bot.metadata_cache_path, queue.playlist_name)
        except Exception as e:
            logger.warning(f"failed to reload cache for '{queue.playlist_name}': {e}")
        await self.update_panel(guild_id)

    async def update_panel(self, guild_id: int) -> None:
        """Update the control panel if it exists (debounced).

        Follows the task cleanup pattern: cancel existing before creating new.
        This coalesces rapid updates into a single edit, preventing the race
        condition that causes multiple panel recreations.
        """
        if not self._panel_enabled():
            return

        # Cancel existing pending update for this guild (task cleanup pattern)
        if guild_id in self._panel_update_tasks:
            task = self._panel_update_tasks[guild_id]
            if not task.done():
                task.cancel()

        # Schedule update with debounce delay
        self._panel_update_tasks[guild_id] = asyncio.create_task(
            self._debounced_panel_update(guild_id)
        )

    async def _debounced_panel_update(self, guild_id: int) -> None:
        """Debounced panel update - coalesces rapid updates into one.

        Waits for configured debounce period (default 500ms), then acquires
        a lock and performs the actual update. If a newer update is triggered
        during the wait, this task is cancelled (preventing stale updates).

        This pattern batches rapid-fire events (button clicks, track changes)
        into a single Discord API call.
        """
        try:
            panel_config = self.bot.config_manager.get("panel", {})
            debounce_ms = panel_config.get("update_debounce_ms", 500)
            await asyncio.sleep(debounce_ms / 1000.0)

            # Get or create lock for this guild
            if guild_id not in self._panel_update_lock:
                self._panel_update_lock[guild_id] = asyncio.Lock()

            # Only one update can execute at a time per guild (prevents out-of-order edits)
            async with self._panel_update_lock[guild_id]:
                await self._do_update_panel(guild_id)
        except asyncio.CancelledError:
            pass  # Superseded by a newer update
        except aiohttp.ClientError:
            pass  # Connection closed during shutdown
        finally:
            self._panel_update_tasks.pop(guild_id, None)

    def _should_recreate_panel(self) -> bool:
        """Check if panel should be recreated based on age.

        Returns True if panel is older than configured interval, or on restart
        (when _panel_created_at is 0).
        """
        panel_config = self.bot.config_manager.get("panel", {})
        interval = panel_config.get("recreate_interval", 30)
        if interval <= 0:
            return False  # Recreation disabled

        age = asyncio.get_running_loop().time() - self.bot.panel_manager._panel_created_at
        return age > (interval * 60)

    async def _do_update_panel(self, guild_id: int) -> None:
        """Actually perform the panel update."""
        async with self.bot.panel_manager._ensure_panel_lock:
            player = self._get_player_by_guild_id(guild_id)

            # Build layout first (needed for both update and recreation)
            layout = ControlPanelLayout(self.bot, guild_id)
            layout.update_button_states(guild_id)
            layout.header_display.content = layout.build_header_content(guild_id)
            layout.progress_display.content = layout.build_progress_content(guild_id, player)
            layout.body_display.content = layout.build_body_content(guild_id, player)
            layout.info_display.content = layout.build_info_content(guild_id)

            # Try to get existing panel for update
            panel_msg = await self.bot.panel_manager.get_message(self.bot)
            if not panel_msg:
                return  # IDs None or deleted - already logged in get_message()

            # Recreate panel if too old (only if panel exists)
            if self._should_recreate_panel():
                age_minutes = int((asyncio.get_running_loop().time() - self.bot.panel_manager._panel_created_at) / 60)
                logger.debug(f"panel is {age_minutes}m old, recreating")
                # Shield from CancelledError to prevent partial recreation (delete without create)
                await asyncio.shield(self.bot.panel_manager.recreate_panel(self.bot, layout))
                return

            try:
                # CRITICAL: embed=None, content=None for transition from old embed
                await panel_msg.edit(view=layout, embed=None, content=None)
            except discord.HTTPException as e:
                if e.code == 10008:
                    # Message deleted - clear state and skip update
                    # Only user commands should create panels
                    self.bot.panel_manager.invalidate_cache()
                    self.bot.panel_manager.channel_id = None
                    self.bot.panel_manager.message_id = None
                    logger.debug("skipping panel update, message was deleted")
                elif e.code == 30046:
                    # Edit limit - recreate in same channel
                    self.bot.panel_manager.invalidate_cache()
                    await asyncio.shield(self.bot.panel_manager.recreate_panel(self.bot, layout))
                else:
                    self.bot.panel_manager.invalidate_cache()
                    logger.warning(f"panel update failed: {e}")

    def _start_progress_update(self, guild_id: int) -> None:
        """Start periodic progress bar update task."""
        if not self._panel_enabled():
            return

        self._stop_progress_update(guild_id)  # Cancel existing first

        panel_config = self.bot.config_manager.get("panel", {})
        if not panel_config.get("progress_bar_enabled", True):
            return  # Progress bar disabled, no need for updates

        interval = panel_config.get("progress_update_interval", 15)

        self.progress_update_tasks[guild_id] = asyncio.create_task(
            self._progress_update_loop(guild_id, interval)
        )

    def _stop_progress_update(self, guild_id: int) -> None:
        """Stop periodic progress bar update task."""
        if guild_id in self.progress_update_tasks:
            self.progress_update_tasks[guild_id].cancel()
            del self.progress_update_tasks[guild_id]

    async def _progress_update_loop(self, guild_id: int, interval: int) -> None:
        """Background loop to update progress bar periodically."""
        # No playback lock: read-only display, worst case is momentary staleness
        try:
            while True:
                await asyncio.sleep(interval)

                # Re-fetch player state after await (stale state pattern)
                player = self._get_player_by_guild_id(guild_id)
                if not player or not player.current or player.paused:
                    # Stop updating if not playing
                    break

                await self.update_panel(guild_id)

        except asyncio.CancelledError:
            pass  # Task was cancelled, clean exit
        except Exception as e:
            logger.warning(f"progress update error: {e}")
        finally:
            # Clean up task reference
            self.progress_update_tasks.pop(guild_id, None)

    async def ensure_panel(self, interaction: discord.Interaction, guild_id: int) -> None:
        """Create control panel if it doesn't exist, or update it.

        Uses lock to prevent concurrent recreation races.
        Proactively recreates panel if it exceeds configured age threshold.
        """
        if not self._panel_enabled():
            return

        async with self.bot.panel_manager._ensure_panel_lock:
            player = self._get_player_by_guild_id(guild_id)

            # Build layout once
            layout = ControlPanelLayout(self.bot, guild_id)
            layout.update_button_states(guild_id)
            layout.header_display.content = layout.build_header_content(guild_id)
            layout.progress_display.content = layout.build_progress_content(guild_id, player)
            layout.body_display.content = layout.build_body_content(guild_id, player)
            layout.info_display.content = layout.build_info_content(guild_id)

            # Try to get existing panel first
            panel_msg = await self.bot.panel_manager.get_message(self.bot)

            if panel_msg:
                # Panel exists - check if too old
                if self._should_recreate_panel():
                    # Shield from CancelledError to prevent partial recreation
                    await asyncio.shield(self.bot.panel_manager.recreate_panel(self.bot, layout))
                    return

                # Update existing panel
                try:
                    # CRITICAL: embed=None, content=None for transition from old embed
                    await panel_msg.edit(view=layout, embed=None, content=None)
                except discord.HTTPException as e:
                    if e.code == 10008:
                        # Message deleted - clear stale state and create in interaction.channel
                        self.bot.panel_manager.invalidate_cache()
                        self.bot.panel_manager.channel_id = None
                        self.bot.panel_manager.message_id = None
                        try:
                            panel_msg = await interaction.channel.send(view=layout)
                            await self.bot.panel_manager.set_message(panel_msg)
                            logger.info(f"created panel in #{interaction.channel.name}")
                        except discord.HTTPException as create_err:
                            logger.error(f"failed to create panel: {create_err}")
                    elif e.code == 30046:
                        # Edit limit - recreate in same channel is OK
                        self.bot.panel_manager.invalidate_cache()
                        await asyncio.shield(self.bot.panel_manager.recreate_panel(self.bot, layout))
                    else:
                        logger.warning(f"panel update failed: {e}")
            else:
                # No panel exists - create in interaction channel
                try:
                    panel_msg = await interaction.channel.send(view=layout)
                    await self.bot.panel_manager.set_message(panel_msg)
                    logger.info(f"created panel in #{interaction.channel.name}")
                except discord.HTTPException as e:
                    logger.error(f"failed to create panel: {e}")

    def _get_player_by_guild_id(self, guild_id: int) -> mafic.Player | None:
        """Get player by guild ID for background tasks."""
        guild = self.bot.get_guild(guild_id)
        if guild and guild.voice_client and isinstance(guild.voice_client, mafic.Player):
            return guild.voice_client
        return None

    def _get_timeout_seconds(self) -> int:
        """Get inactivity timeout in seconds from config."""
        minutes = self.bot.config_manager.get("inactivity_timeout", 10)
        return minutes * 60

    def _start_inactivity_timer(self, guild_id: int) -> None:
        """Start countdown - cancel existing first (Rule 7: prevents orphaned tasks)."""
        self._cancel_inactivity_timer(guild_id)  # CRITICAL: Cancel existing before new
        self.inactivity_tasks[guild_id] = asyncio.create_task(
            self._inactivity_countdown(guild_id)
        )
        timeout = self._get_timeout_seconds()
        if timeout > 0:
            logger.debug(f"starting {timeout}s inactivity timer")

    def _cancel_inactivity_timer(self, guild_id: int) -> None:
        """Cancel if exists and not done."""
        if task := self.inactivity_tasks.pop(guild_id, None):
            if not task.done():
                task.cancel()
                logger.debug("inactivity timer cancelled")

    async def _handle_now_alone(self, guild_id: int, player: mafic.Player) -> None:
        """Handle bot being alone in voice channel.

        Two separate behaviors:
        1. Starts inactivity timer - will DISCONNECT after inactivity_timeout minutes
        2. Auto-pauses after 2s debounce (allows quick rejoin without interruption)

        The 2s delay handles users switching voice channels briefly.
        Sets was_auto_paused flag so _handle_not_alone can auto-resume.
        """
        self._start_inactivity_timer(guild_id)

        if not player.current or player.paused:
            return

        await asyncio.sleep(2)  # 2-second debounce

        # Re-fetch player after await (bot may have moved or disconnected)
        player = self._get_player_by_guild_id(guild_id)
        if not player or not player.connected or not player.channel:
            return

        active_members = [
            m for m in player.channel.members
            if not m.bot and not m.voice.self_deaf and not m.voice.deaf
        ]
        if not active_members:
            state = self.pause_states.setdefault(guild_id, VoiceSessionState())
            state.was_auto_paused = True
            await player.pause()
            await self.update_panel(guild_id)
            logger.info("auto-paused, channel empty")

    async def _handle_not_alone(self, guild_id: int, player: mafic.Player) -> None:
        """Handle listener joining the voice channel.

        Cancels any pending inactivity disconnect timer. If playback was
        auto-paused (not manually paused by user), automatically resumes.
        This provides seamless experience when users briefly leave and return.
        """
        self._cancel_inactivity_timer(guild_id)

        if player.paused:
            state = self.pause_states.get(guild_id)
            if state and state.was_auto_paused and not state.was_paused_by_user:
                await player.resume()
                state.was_auto_paused = False
                self._start_progress_update(guild_id)
                await self.update_panel(guild_id)
                logger.info("auto-resumed, listener joined")

    async def _inactivity_countdown(self, guild_id: int) -> None:
        """Background task that disconnects after timeout."""
        try:
            timeout = self._get_timeout_seconds()
            if timeout <= 0:
                return  # Feature disabled

            await asyncio.sleep(timeout)

            # Timeout completed - disconnect
            guild = self.bot.get_guild(guild_id)
            if guild and guild.voice_client:
                player = guild.voice_client
                if isinstance(player, mafic.Player):
                    logger.info("channel empty, disconnecting")
                    # Clear pause state (fresh state for next session)
                    self.pause_states.pop(guild_id, None)
                    await player.disconnect()

        except asyncio.CancelledError:
            pass  # Expected when activity resumes

    def get_player(self, interaction: discord.Interaction) -> mafic.Player | None:
        """Safely get the Mafic player."""
        vc = interaction.guild.voice_client
        if vc and isinstance(vc, mafic.Player):
            return vc
        return None

    async def ensure_voice(self, interaction: discord.Interaction) -> mafic.Player | None:
        """Ensure bot is in voice channel with user. Returns player or None."""
        # Check user is in VC
        if not interaction.user.voice:
            await self.respond(interaction, "not_in_vc")
            return None

        user_channel = interaction.user.voice.channel

        # Check if bot already connected
        if interaction.guild.voice_client:
            player = self.get_player(interaction)
            if not player:
                await self.respond(interaction, "voice_error")
                return None

            # Check same channel
            if player.channel != user_channel:
                await self.respond(interaction, "wrong_vc", channel=player.channel.mention)
                return None

            return player

        # Not connected - join user's channel
        permissions = user_channel.permissions_for(interaction.guild.me)
        if not permissions.connect or not permissions.speak:
            await self.respond(interaction, "need_vc_permissions")
            return None

        try:
            player = await user_channel.connect(cls=mafic.Player, self_deaf=True)

            # Apply saved volume on connect (Phase 8 addition)
            default_vol = self.bot.config_manager.get("default_volume", 50)
            saved_volume = self.bot.state_manager.get("volume", default_vol)
            await player.set_volume(saved_volume)

            logger.info(f"summoned by {interaction.user.display_name} to #{user_channel.name}")
            return player
        except Exception as e:
            logger.error(f"voice connection failed: {e}")
            await self.respond(interaction, "failed_join_vc")
            return None

    async def play_track(self, player: mafic.Player, track: Path, playlist_name: str) -> bool:
        """Play a track via Lavalink. Returns True on success, False on failure."""
        # Get actual folder name (preserves filesystem casing on Linux)
        if playlist_name == ROOT_PLAYLIST_NAME:
            folder_name = ROOT_PLAYLIST_NAME
        else:
            folder_name = self.bot.library.get_playlist_path(playlist_name).name
        http_url = f"http://{self.bot.http_url_host}:{self.bot.http_port}/files/{quote(folder_name, safe='')}/{quote(track.name, safe='')}"
        try:
            tracks = await player.fetch_tracks(http_url)
            if tracks:
                await player.play(tracks[0])
                return True
        except aiohttp.ClientConnectionError as e:
            logger.error(f"playback failed for {track.name}: {e}")
            # Handler uses lock - safe to call from exception block
            await self.bot.handle_lavalink_connection_error()
        except Exception as e:
            logger.error(f"playback failed for {track.name}: {e}")

        return False

    async def play_next(self, player: mafic.Player, guild_id: int) -> bool:
        """Advance queue and play next track. Returns True on success, False if queue empty or playback failed."""
        queue = self.get_queue(guild_id)
        next_track = queue.advance_track()

        if not next_track:
            logger.debug("queue is empty, nothing to play")
            return False

        return await self.play_track(player, next_track, queue.playlist_name)

    async def song_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete callback for song search.

        Must respond within 3 seconds, returns up to 25 choices.
        Shows "Title - Artist" in dropdown, value is the exact title.
        When input is empty, shows first 25 tracks if playlist is loaded.
        """
        guild_id = interaction.guild_id
        queue = self.get_queue(guild_id)

        # Empty input: show first 25 tracks only if we have cached metadata
        # Don't trigger a load here - user needs to select a playlist first
        if not current:
            if not queue.metadata_cache:
                return []
            choices = []
            for track in list(queue.metadata_cache.values())[:25]:
                title = track.get('title', 'unknown')
                artist = track.get('artist')
                display = f"{artist} - {title}" if artist else title
                display = truncate_for_display(display, CHOICE_NAME_MAX)
                choices.append(app_commands.Choice(name=display, value=title))
            return choices

        # Only search if we have cached metadata (playlist must be loaded first)
        if not queue.metadata_cache:
            return []

        metadata = list(queue.metadata_cache.values())

        # Search and return top 25 as Choice objects
        results = autocomplete_search(current, metadata, max_results=25)

        choices = []
        for track, score in results:
            if score < 55:  # Skip low-relevance matches
                continue
            title = track.get('title', 'unknown')
            artist = track.get('artist')
            # Display: "Artist - Title" if artist exists, else just "Title"
            display = f"{artist} - {title}" if artist else title
            display = truncate_for_display(display, CHOICE_NAME_MAX)
            choices.append(app_commands.Choice(name=display, value=title))

        return choices[:25]

    @app_commands.command(name="play", description="play a song or resume playback")
    @app_commands.guild_only()
    @app_commands.describe(song="type to search (/queue shows all tracks)")
    @app_commands.autocomplete(song=song_autocomplete)
    @require_permission("play")
    async def play(self, interaction: discord.Interaction, song: str | None = None) -> None:
        """Play a song or resume if paused.

        When a specific song is requested, acquires playback lock before modifying
        queue state. Re-validates player and re-fetches queue inside lock to handle
        races with concurrent skip/previous/playlist operations.
        """
        # Check Lavalink availability (Rule 38)
        if not self.bot.pool.nodes:
            await self.respond(interaction, "music_unavailable")
            return

        player = await self.ensure_voice(interaction)
        if not player:
            return

        await interaction.response.defer(ephemeral=True)

        # Resume if paused and no song specified
        if player.paused and not song:
            await player.resume()
            # Clear manual pause flag so auto-resume works in future
            if state := self.pause_states.get(interaction.guild_id):
                state.was_paused_by_user = False
            logger.info(f"resumed by {interaction.user.display_name}")
            await self.respond(interaction, "resumed")
            await self.ensure_panel(interaction, interaction.guild_id)
            return

        # If song specified, skip to search (even if already playing)
        # This allows users to interrupt current playback with a new request
        if song:
            pass  # Continue to search logic below
        elif player.current:
            # No song specified and already playing
            await self.respond(interaction, "already_playing")
            await self.ensure_panel(interaction, interaction.guild_id)
            return

        # Get current playlist
        guild_id = interaction.guild_id
        queue = self.get_queue(guild_id)

        if not queue.playlist_name:
            # Load saved or first available playlist
            names = self.bot.library.get_playlist_names()
            if not names:
                await self.respond(interaction, "no_playlists")
                return

            playlist_name = self._resolve_playlist(names)
            tracks = self.bot.library.get_playlist(playlist_name)
            if not tracks:
                await self.respond(interaction, "playlist_empty")
                return
            queue.set_playlist(playlist_name, tracks)

            # Validate and apply restored current_index (if shuffle is enabled, it was already applied by enable_shuffle)
            if queue.current_index is not None:
                if not (0 <= queue.current_index < len(queue.tracks)):
                    logger.warning(f"invalid saved queue index {queue.current_index}, resetting to 0")
                    queue.set_current_track(0)

        # Get metadata for search (use in-memory cache if loaded, otherwise scan)
        playlist_path = self.bot.library.get_playlist_path(queue.playlist_name)

        # Ensure metadata cache is loaded
        if not queue.metadata_cache:
            await queue.load_metadata_cache(self.bot.metadata_cache_path, queue.playlist_name)

        # If still empty (no cache file), scan to create it
        if not queue.metadata_cache:
            from utils.metadata import scan_playlist_metadata
            metadata_list, _, _, _ = await scan_playlist_metadata(
                playlist_path,
                self.bot.metadata_cache_path,
                queue.playlist_name
            )
            # Use scan result directly instead of re-reading from disk
            queue.metadata_cache = {
                entry.get("filename", ""): entry
                for entry in metadata_list
                if entry.get("filename")
            }

        # Convert to list for search function
        metadata = list(queue.metadata_cache.values())

        if not metadata:
            await self.respond(interaction, "playlist_empty")
            return

        # If no song specified, start playing or resume
        if not song:
            # Restore track from preserved position (after /stop or disconnect)
            if queue.current_index is not None and not queue.current and queue.tracks:
                queue.set_current_track(queue.current_index)

            # If no current index, start from beginning
            if queue.current_index is None and queue.tracks:
                queue.set_current_track(0)

            # Resume if we have a current track but player isn't playing
            if queue.current and not player.current:
                success = await self.play_track(player, queue.current, queue.playlist_name)
                if success:
                    title, _ = queue.get_current_display()
                    await self.respond(interaction, "now_playing", title=escape_markdown(title))
                    await self.ensure_panel(interaction, guild_id)
                else:
                    await self.respond(interaction, "track_play_error")
                return

            # Start fresh if nothing is current
            if not queue.current and queue.tracks:
                success = await self.play_next(player, guild_id)
                if success:
                    title, _ = queue.get_current_display()
                    await self.respond(interaction, "now_playing", title=escape_markdown(title))
                    await self.ensure_panel(interaction, guild_id)
                else:
                    await self.respond(interaction, "track_play_error")
            return

        # Search for song
        best, confidence, alternatives = get_best_match(song, metadata)

        # Log search result
        query_display = (song[:50] + "...") if len(song) > 50 else song
        if best:
            logger.info(f"{interaction.user.display_name} searched '{query_display}' -> \"{best['title']}\" ({confidence:.0f}%)")
        elif alternatives:
            logger.info(f"{interaction.user.display_name} searched '{query_display}' -> ambiguous ({len(alternatives)} options)")
        else:
            logger.info(f"{interaction.user.display_name} searched '{query_display}' -> no match")

        if best:
            # High confidence - play directly
            track_path = Path(best['path'])

            async with self._get_playback_lock(guild_id):
                # Re-validate after acquiring lock (matches /skip pattern)
                player = self.get_player(interaction)
                if not player or not player.connected:
                    await self.respond(interaction, "nothing_playing")
                    return

                queue = self.get_queue(guild_id)  # Re-fetch inside lock

                # Find track in active playlist (handles shuffle mode automatically)
                try:
                    index = queue.active_tracks.index(track_path)
                except ValueError:
                    await self.respond(interaction, "song_not_found")
                    return

                queue.set_current_track(index)
                success = await self.play_track(player, track_path, queue.playlist_name)

            if success:
                logger.info(f"{interaction.user.display_name} started \"{best['title']}\"")
                await self.respond(interaction, "track_selected", title=escape_markdown(best['title']))
                await self.ensure_panel(interaction, guild_id)
            else:
                await self.respond(interaction, "track_play_error")
                return

        elif alternatives:
            # Show selection menu
            from ui.views import SearchSelectionView
            view = SearchSelectionView(alternatives, bot=self.bot)
            msg = await interaction.followup.send(
                "which one?",
                view=view,
                ephemeral=True
            )
            view.message = msg  # Store for auto-delete on timeout

            # Wait for selection
            await view.wait()
            if view.selected:
                track_path = Path(view.selected['path'])

                async with self._get_playback_lock(guild_id):
                    # Re-validate after acquiring lock
                    player = self.get_player(interaction)
                    if not player or not player.connected:
                        await self.respond(interaction, "nothing_playing")
                        return

                    queue = self.get_queue(guild_id)  # Re-fetch inside lock

                    # Find track in active playlist
                    try:
                        index = queue.active_tracks.index(track_path)
                    except ValueError:
                        await self.respond(interaction, "song_not_found")
                        return

                    queue.set_current_track(index)
                    success = await self.play_track(player, track_path, queue.playlist_name)

                if success:
                    logger.info(f"{interaction.user.display_name} started \"{view.selected['title']}\"")
                    # Callback already showed track_selected via edit_message
                    await self.ensure_panel(interaction, guild_id)
                else:
                    await self.respond(interaction, "track_play_error")

        else:
            await self.respond(interaction, "song_not_found")

    @app_commands.command(name="pause", description="pause playback")
    @app_commands.guild_only()
    @require_permission("pause")
    async def pause(self, interaction: discord.Interaction) -> None:
        """Pause playback, marking as manual pause for auto-resume logic."""
        player = self.get_player(interaction)
        if not player or not player.current:
            await self.respond(interaction, "nothing_playing")
            return

        if not await self._check_same_vc(interaction, player):
            return

        await interaction.response.defer(ephemeral=True)

        state = self.pause_states.setdefault(interaction.guild_id, VoiceSessionState())
        state.was_paused_by_user = True  # Mark as manual pause
        await player.pause()
        logger.info(f"paused by {interaction.user.display_name}")
        await self.respond(interaction, "paused")
        await self.update_panel(interaction.guild_id)

    @app_commands.command(name="seek", description="seek to a position in the track")
    @app_commands.guild_only()
    @app_commands.describe(position="position as percentage (0-100)")
    @require_permission("seek")
    async def seek(self, interaction: discord.Interaction, position: app_commands.Range[int, 0, 100]) -> None:
        """Seek to a position in the current track."""
        player = self.get_player(interaction)

        if not player or not player.current:
            await self.respond(interaction, "nothing_playing")
            return

        # Check user is in same VC as bot
        if not await self._check_same_vc(interaction, player):
            return

        if not player.current.seekable:
            await self.respond(interaction, "cant_seek")
            return

        # Guard against zero-length tracks (corrupted metadata, streams)
        if player.current.length <= 0:
            await self.respond(interaction, "cant_seek")
            return

        # Convert percentage to milliseconds
        position_ms = int((position / 100.0) * player.current.length)

        await player.seek(position_ms)
        await self.update_panel(interaction.guild_id)

        logger.info(f"{interaction.user.display_name} seeked to {position}%")
        queue = self.get_queue(interaction.guild_id)
        title, _ = queue.get_current_display()
        await self.respond(interaction, "seek_to", position=position, title=escape_markdown(title))

    @app_commands.command(name="np", description="show now playing details")
    @app_commands.guild_only()
    async def now_playing(self, interaction: discord.Interaction) -> None:
        """Show detailed current track info."""
        player = self.get_player(interaction)
        if not player or not player.current:
            await self.respond(interaction, "nothing_playing")
            return

        track = player.current
        guild_id = interaction.guild_id
        queue = self.get_queue(guild_id)

        # Format position
        position_ms = player.position or 0
        length_ms = track.length or 0

        def format_time(ms: int) -> str:
            seconds = ms // 1000
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{minutes}:{seconds:02d}"

        pos_str = format_time(position_ms)
        len_str = format_time(length_ms)

        # Get metadata from in-memory cache (no file I/O!)
        # get_current_display() defined in Phase 5 - uses frozen current_metadata captured at track start
        title, artist = queue.get_current_display()

        panel_color = self.bot.config_manager.get_panel_color()
        embed = discord.Embed(color=panel_color)
        embed.add_field(
            name="song",
            value=escape_markdown(truncate_for_display(title, EMBED_FIELD_MAX)),
            inline=True
        )

        # Get album from frozen metadata (captured at track start)
        album = None
        if queue.current_metadata:
            album = queue.current_metadata.get('album')

        # Dynamic fields based on available metadata
        if album:
            embed.add_field(
                name="album",
                value=escape_markdown(truncate_for_display(album, EMBED_FIELD_MAX)),
                inline=True
            )

        if artist:
            embed.add_field(
                name="artist",
                value=escape_markdown(truncate_for_display(artist, EMBED_FIELD_MAX)),
                inline=True
            )

        # Position/Progress bar
        embed.add_field(name="position", value=f"{pos_str} / {len_str}", inline=True)

        # Mode field (priority: Loop > Shuffle > Normal)
        if queue.song_loop:
            mode = "loop"
        elif queue.shuffle:
            mode = "shuffle"
        else:
            mode = "normal"
        embed.add_field(name="mode", value=mode, inline=True)

        # Track position in playlist (priority: Loop > Shuffle > Normal)
        total_tracks = len(queue.tracks)
        try:
            current_pos = queue.tracks.index(queue.current) + 1  # 1-based
            if queue.song_loop:
                position_display = f"↻ {current_pos}/{total_tracks}"
            elif queue.shuffle:
                position_display = f"?/{total_tracks}"
            else:
                position_display = f"{current_pos}/{total_tracks}"
        except (ValueError, AttributeError):
            # Current track not in playlist (shouldn't happen, but handle gracefully)
            position_display = f"?/{total_tracks}"

        embed.add_field(name="track #", value=position_display, inline=True)

        # Get auto-delete timeout from config
        ui_config = self.bot.config_manager.get("ui", {})
        timeout = ui_config.get("extended_auto_delete", 90)
        delete_after = timeout if timeout > 0 else None

        # Use native delete_after (response path)
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=delete_after)

    @app_commands.command(name="previous", description="go back to the previous track")
    @app_commands.guild_only()
    @require_permission("previous")
    async def previous(self, interaction: discord.Interaction) -> None:
        """Go back to the previous track."""
        player = self.get_player(interaction)
        if not player or not player.current:
            await self.respond(interaction, "nothing_playing")
            return

        if not await self._check_same_vc(interaction, player):
            return

        guild_id = interaction.guild_id

        await interaction.response.defer(ephemeral=True)

        async with self._get_playback_lock(guild_id):
            # Re-validate after acquiring lock
            player = self.get_player(interaction)
            if not player or not player.connected:
                await self.respond(interaction, "nothing_playing")
                return

            queue = self.get_queue(guild_id)
            prev_track = queue.previous_track()

            if not prev_track:
                await self.respond(interaction, "history_empty")
                return

            success = await self.play_track(player, prev_track, queue.playlist_name)
            if success:
                # Only decrement drink counter if not looping same song
                if not queue.song_loop:
                    drinks = self.get_drink_counter(guild_id)
                    drinks.decrement()
                logger.info(f"{interaction.user.display_name} went to previous track")
                title, _ = queue.get_track_display(prev_track)
                await self.respond(interaction, "now_playing", title=escape_markdown(title))
            else:
                await self.respond(interaction, "track_play_error")

    @app_commands.command(name="skip", description="skip to the next track")
    @app_commands.guild_only()
    @require_permission("skip")
    async def skip(self, interaction: discord.Interaction) -> None:
        """Skip to the next track."""
        player = self.get_player(interaction)

        if not player or not player.current:
            await self.respond(interaction, "nothing_playing")
            return

        if not await self._check_same_vc(interaction, player):
            return

        guild_id = interaction.guild_id

        await interaction.response.defer(ephemeral=True)

        async with self._get_playback_lock(guild_id):
            # Re-validate after acquiring lock
            player = self.get_player(interaction)
            if not player or not player.connected:
                await self.respond(interaction, "nothing_playing")
                return

            queue = self.get_queue(guild_id)
            next_track = queue.advance_track()  # Get next track (handles loops)

            if not next_track:
                await self.respond(interaction, "queue_empty")
                return

            success = await self.play_track(player, next_track, queue.playlist_name)
            if success:
                # Only increment drink counter if not looping same song
                if not queue.song_loop:
                    drinks = self.get_drink_counter(guild_id)
                    drinks.increment()
                logger.info(f"{interaction.user.display_name} skipped to next track")
                title, _ = queue.get_track_display(next_track)
                await self.respond(interaction, "now_playing", title=escape_markdown(title))
            else:
                await self.respond(interaction, "track_play_error")

    @app_commands.command(name="stop", description="stop playback and disconnect")
    @app_commands.guild_only()
    @require_permission("stop")
    async def stop(self, interaction: discord.Interaction) -> None:
        """Stop playback and disconnect from voice."""
        player = self.get_player(interaction)
        if not player:
            await self.respond(interaction, "nothing_playing")
            return

        if not await self._check_same_vc(interaction, player):
            return

        guild_id = interaction.guild_id

        # Cancel inactivity timer (we're manually disconnecting)
        self._cancel_inactivity_timer(guild_id)

        # Clear queue
        if guild_id in self.guild_queues:
            self.guild_queues[guild_id].clear()

        # Update panel to show "Nothing playing" state
        await self.update_panel(guild_id)

        # Clear pause state (fresh state for next session)
        self.pause_states.pop(guild_id, None)

        logger.info(f"stopped by {interaction.user.display_name}")
        await player.disconnect()
        await self.respond(interaction, "stopped")

    @commands.Cog.listener()
    async def on_track_end(self, event: mafic.TrackEndEvent) -> None:
        # event.player is the correct player for this event, don't re-fetch
        # Note: mafic.EndReason values are lowercase ("replaced", not "REPLACED")
        if event.reason == mafic.EndReason.REPLACED:
            return

        # Guard: player may be disconnecting (inactivity timeout race)
        if not event.player.connected:
            return

        guild_id = event.player.guild.id

        async with self._get_playback_lock(guild_id):
            # Re-validate after acquiring lock (player may have disconnected)
            if not event.player.connected:
                return

            # If something is already playing, skip/previous already handled it
            if event.player.current:
                return

            queue = self.get_queue(guild_id)
            drinks = self.get_drink_counter(guild_id)

            # Advance to next track
            next_track = queue.advance_track()

            if next_track:
                # Note: Panel update handled by on_track_start (which captures correct metadata)
                if await self.play_track(event.player, next_track, queue.playlist_name):
                    # Only increment drink emoji if not looping same song
                    if not queue.song_loop:
                        drinks.increment()
                    self._cancel_inactivity_timer(guild_id)  # Activity resumed
                # Error already logged by play_track()
            else:
                logger.info("queue finished")
                self._stop_progress_update(guild_id)  # Stop progress bar updates
                await self.bot.update_presence()  # Clear presence
                await self.update_panel(guild_id)  # Show "Nothing playing" state

    @commands.Cog.listener()
    async def on_track_start(self, event: mafic.TrackStartEvent) -> None:
        """Handle track start: capture metadata, update panel, and cancel inactivity timer."""
        guild_id = event.player.guild.id
        queue = self.get_queue(guild_id)

        # Diagnostic: log what Lavalink is playing vs queue state
        # Helps debug rapid-skip desync issues
        if queue.current:
            queue_title, _ = queue.get_current_display()
            player_title = event.player.current.title if event.player.current else None
            # Only log if titles look completely different (not just formatting)
            if player_title and queue_title:
                if player_title.lower() not in queue_title.lower() and queue_title.lower() not in player_title.lower():
                    logger.debug(f"track start: queue={queue_title!r}, lavalink={player_title!r}")

        # Capture current track's metadata (freezes it for display)
        # This survives playlist switches - panel/np will show correct metadata
        queue.capture_current_metadata()

        # Update bot presence with current song
        title, artist = queue.get_current_display()
        await self.bot.update_presence(title=title, artist=artist)

        await self.update_panel(guild_id)

        self._cancel_inactivity_timer(guild_id)

        # Start periodic progress bar updates
        self._start_progress_update(guild_id)

    @commands.Cog.listener()
    async def on_websocket_closed(self, event: mafic.WebSocketClosedEvent) -> None:
        """Diagnostic: log when voice WebSocket closes."""
        logger.debug(
            f"voice websocket closed: code={event.code}, "
            f"reason={event.reason!r}, by_discord={event.by_discord}"
        )

    @commands.Cog.listener()
    async def on_track_exception(self, event: mafic.TrackExceptionEvent) -> None:
        """Handle track playback errors (corrupted file, codec issues)."""
        guild_id = event.player.guild.id
        queue = self.get_queue(guild_id)
        title, _ = queue.get_current_display()
        logger.warning(f"track exception for '{title}': {event.exception}")
        # on_track_end will handle queue advancement - this is for logging/diagnostics

    @commands.Cog.listener()
    async def on_track_stuck(self, event: mafic.TrackStuckEvent) -> None:
        """Handle stuck track (no audio progress for threshold_ms)."""
        guild_id = event.player.guild.id
        queue = self.get_queue(guild_id)
        title, _ = queue.get_current_display()
        logger.warning(f"track stuck for '{title}' (threshold: {event.threshold_ms}ms)")
        # Mafic will fire on_track_end after this - just log for diagnostics

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        """Handle users joining/leaving bot's voice channel."""
        guild_id = member.guild.id

        # Handle bot's own channel changes (moved or disconnected by user)
        if member.id == self.bot.user.id:
            if before.channel and not after.channel:
                # Bot was disconnected from voice
                logger.info("disconnected from voice")
                self._cancel_inactivity_timer(guild_id)
                self.pause_states.pop(guild_id, None)
                # Clear current track so panel shows idle state (preserves position for resume)
                queue = self.get_queue(guild_id)
                queue.current = None
                queue.current_metadata = None
                await self.bot.update_presence()  # Clear presence
                await self.update_panel(guild_id)
            elif before.channel != after.channel and after.channel:
                # Bot was moved to a different channel
                logger.info(f"moved to #{after.channel.name}")
                player = self._get_player_by_guild_id(guild_id)
                if player:
                    active_members = [
                        m for m in after.channel.members
                        if not m.bot and not m.voice.self_deaf and not m.voice.deaf
                    ]
                    if not active_members:
                        await self._handle_now_alone(guild_id, player)
                    else:
                        await self._handle_not_alone(guild_id, player)
            return

        # Ignore other bots
        if member.bot:
            return
        player = self._get_player_by_guild_id(guild_id)
        if not player or not player.connected:
            return

        bot_channel = player.channel

        # Check if this affects bot's channel
        left_bot_channel = before.channel == bot_channel and after.channel != bot_channel
        joined_bot_channel = after.channel == bot_channel and before.channel != bot_channel

        if left_bot_channel or joined_bot_channel:
            # Count active members (exclude bots + deafened users)
            active_members = [
                m for m in bot_channel.members
                if not m.bot
                and not m.voice.self_deaf
                and not m.voice.deaf
            ]

            if not active_members:
                await self._handle_now_alone(guild_id, player)
            else:
                await self._handle_not_alone(guild_id, player)


async def setup(bot: commands.Bot) -> None:
    """Load the Music cog."""
    await bot.add_cog(Music(bot))
