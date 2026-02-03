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

"""Settings commands for Jill."""

import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from utils.metadata import scan_playlist_metadata
from utils.permissions import require_command_enabled, require_permission
from utils.response import ResponseMixin


class Settings(ResponseMixin, commands.Cog):
    """Bot settings and maintenance."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._rescan_lock = asyncio.Lock()

    @app_commands.command(name="rescan", description="force full rebuild of metadata cache (re-reads all file tags)")
    @app_commands.guild_only()
    @require_command_enabled("rescan")
    @require_permission("rescan")
    async def rescan(self, interaction: discord.Interaction) -> None:
        """Rescan music library, rebuild metadata caches, and apply filtering.

        Stops playback before scan. Clears current track if removed, or resets
        queue if playlist deleted. Refreshes panel on completion.
        """
        if self._rescan_lock.locked():
            await self.respond(interaction, "rescan_in_progress")
            return

        async with self._rescan_lock:
            await interaction.response.defer(ephemeral=True, thinking=True)

            try:
                # Stop playback before rescan (prevents stale state during library changes)
                music_cog = self.bot.get_cog("Music")
                guild_id = interaction.guild_id
                if music_cog:
                    player = music_cog._get_player_by_guild_id(guild_id)
                    if player:
                        music_cog._cancel_inactivity_timer(guild_id)
                        music_cog.pause_states.pop(guild_id, None)
                        await player.disconnect()
                        logger.info("stopped for rescan")

                # Rescan library for new/removed files
                await self.bot.library.scan()

                # Delete ALL cache files (handles orphaned caches from deleted playlists)
                for cache_file in self.bot.metadata_cache_path.glob('*.json'):
                    await asyncio.to_thread(cache_file.unlink, missing_ok=True)
                logger.debug("cache cleared")

                # Rebuild metadata cache for all playlists in parallel
                playlist_names = self.bot.library.get_playlist_names()
                results = await asyncio.gather(
                    *[scan_playlist_metadata(
                        self.bot.library.get_playlist_path(name),
                        self.bot.metadata_cache_path,
                        name,
                        force_rebuild=True
                    ) for name in playlist_names],
                    return_exceptions=True
                )
                logger.debug("metadata rebuilt")

                # Apply metadata-based filtering and log failures
                for name, result in zip(playlist_names, results):
                    if isinstance(result, Exception):
                        logger.warning(f"scan failed for playlist '{name}': {result}")
                    else:
                        _, _, filtered_paths, _ = result
                        self.bot.library.update_playlist_files(name, filtered_paths)

                # Reload in-memory metadata for active guild
                music_cog = self.bot.get_cog("Music")
                if music_cog:
                    await music_cog.reload_metadata(interaction.guild_id)

                    # Lock: modifies queue.tracks and may regenerate shuffle
                    async with music_cog._get_playback_lock(interaction.guild_id):
                        queue = music_cog.get_queue(interaction.guild_id)
                        if queue.playlist_name:
                            updated_tracks = self.bot.library.get_playlist(queue.playlist_name)
                            if updated_tracks is not None:
                                queue.tracks = updated_tracks.copy()
                                if queue.shuffle:
                                    queue._regenerate_shuffle(exclude_last=queue.current)

                                # Handle current track removed from playlist
                                if queue.current and queue.current not in updated_tracks:
                                    queue.current = None
                                    queue.current_metadata = None
                                    player = music_cog._get_player_by_guild_id(interaction.guild_id)
                                    if player and player.current:
                                        await player.stop()
                                    logger.info("current track no longer in playlist, playback stopped")
                            else:
                                # Playlist deleted - reset queue to initial state
                                old_name = queue.playlist_name
                                queue.playlist_name = ""
                                queue.tracks = []
                                queue.current = None
                                queue.current_index = None
                                queue.current_metadata = None
                                queue.metadata_cache = {}
                                queue.shuffled_tracks = None
                                queue.shuffle = False
                                queue.song_loop = False
                                self.bot.state_manager.set("shuffle", False)
                                await self.bot.state_manager.save()

                                player = music_cog._get_player_by_guild_id(interaction.guild_id)
                                if player and player.current:
                                    await player.stop()

                                logger.warning(f"playlist '{old_name}' no longer exists, queue cleared")

                    # Refresh panel after rescan (debounced, cheap)
                    await music_cog.update_panel(interaction.guild_id)

                playlists = self.bot.library.playlists
                total_tracks = sum(len(t) for t in playlists.values())

                await self.respond(interaction, "rescan_complete", playlists=len(playlists), tracks=total_tracks)

            except Exception:
                logger.opt(exception=True).error("rescan failed")
                await self.respond(interaction, "rescan_failed")

    @app_commands.command(name="volume", description="set playback volume")
    @app_commands.guild_only()
    @app_commands.describe(level="volume level from 0 to 100")
    @require_permission("volume")
    async def volume(
        self,
        interaction: discord.Interaction,
        level: app_commands.Range[int, 0, 100]
    ) -> None:
        """Set volume level. Persists to state. VC check only when bot is connected."""
        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            await self.respond(interaction, "music_unavailable")
            return

        player = music_cog.get_player(interaction)
        if player:
            if not await self._check_same_vc(interaction, player):
                return
            await player.set_volume(level)

        # Save to state
        self.bot.state_manager.set("volume", level)
        await self.bot.state_manager.save()

        logger.info(f"{interaction.user.display_name} set volume to {level}")
        await self.respond(interaction, "volume_set", level=level)


async def setup(bot: commands.Bot) -> None:
    """Load the Settings cog."""
    await bot.add_cog(Settings(bot))
