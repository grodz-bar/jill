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

"""Queue and playlist commands for Jill."""

import discord
from discord import app_commands
from discord.ext import commands
from loguru import logger

from ui.control_panel import PlaylistSelectView
from ui.views import PaginationView
from utils.permissions import require_command_enabled, require_permission
from utils.response import (
    ResponseMixin,
    escape_markdown,
    truncate_for_display,
    QUEUE_TITLE_MAX,
    QUEUE_TITLE_MULTI_MAX,
    QUEUE_ARTIST_MAX,
    PLAYLIST_NAME_MAX,
    CHOICE_NAME_MAX,
    EMBED_TITLE_MAX,
)
from utils.search import playlist_search


class Queue(ResponseMixin, commands.Cog):
    """Queue and playlist management commands.

    Provides slash commands for viewing and managing the playback queue:
    - /queue: Show upcoming tracks with pagination
    - /playlists: List available playlists with track counts
    - /playlist [name]: Switch to a different playlist
    - /shuffle [on|off]: Toggle shuffle mode
    - /loop [on|off]: Toggle single-track repeat

    All commands respect the permission system and can be restricted
    to specific roles via permissions.yaml.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @property
    def display_size(self) -> int:
        """Get queue display size from config."""
        return self.bot.config_manager.get("queue_display_size", 15)

    @property
    def playlists_display_size(self) -> int:
        """Get playlists display size from config."""
        return self.bot.config_manager.get("playlists_display_size", 15)

    async def playlist_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete for playlist names (fuzzy match)."""
        available = self.bot.library.get_playlist_names()

        # No autocomplete when <=1 playlist (includes root-only mode)
        if len(available) <= 1:
            return []

        if not current:
            # Show all playlists when no input
            return [
                app_commands.Choice(
                    name=truncate_for_display(name, CHOICE_NAME_MAX),
                    value=name
                )
                for name in available[:25]
            ]

        # Fuzzy match by current input
        matches = playlist_search(current, available, max_results=25, score_cutoff=55)

        return [
            app_commands.Choice(
                name=truncate_for_display(name, CHOICE_NAME_MAX),
                value=name
            )
            for name, score in matches
        ]

    @app_commands.command(name="playlists", description="list all available playlists")
    @app_commands.guild_only()
    @app_commands.describe(page="jump to page number")
    @require_permission("playlists")
    async def playlists(
        self,
        interaction: discord.Interaction,
        page: app_commands.Range[int, 1, 9999] | None = None
    ) -> None:
        """Show available playlists with pagination. Disabled when one or fewer playlists exist."""
        library = self.bot.library
        playlist_names = library.get_playlist_names()

        if not playlist_names:
            await self.respond(interaction, "no_playlists")
            return
        if len(playlist_names) == 1:
            await self.respond(interaction, "single_playlist")
            return

        # Build playlist info with track counts
        playlist_info = []
        for name in sorted(playlist_names):
            tracks = library.get_playlist(name)
            playlist_info.append((name, len(tracks) if tracks else 0))

        # Detect current playlist for highlighting
        current_playlist = None
        music_cog = self.bot.get_cog("Music")
        if music_cog:
            queue_obj = music_cog.get_queue(interaction.guild_id)
            current_playlist = queue_obj.playlist_name

        panel_color = self.bot.config_manager.get_panel_color()
        page_size = self.playlists_display_size

        def format_playlists_page(items: list, page_num: int, total: int) -> discord.Embed:
            embed = discord.Embed(title="available playlists", color=panel_color)
            lines = []

            for name, count in items:
                display_name = escape_markdown(truncate_for_display(name, PLAYLIST_NAME_MAX))
                if name == current_playlist:
                    lines.append(f"**\u2192 {display_name} \u2190** [{count}]")
                else:
                    lines.append(f"{display_name} [{count}]")

            lines.append("\nuse `/playlist [name]` to switch")
            embed.description = "\n".join(lines)
            embed.set_footer(text=f"page {page_num + 1}/{total}")
            return embed

        view = PaginationView(
            items=playlist_info,
            page_size=page_size,
            format_page=format_playlists_page,
            bot=self.bot
        )

        # Determine start page: explicit param > current playlist page > 0
        if page is not None:
            start_page = min(page - 1, view.total_pages - 1)
        elif current_playlist:
            start_page = 0
            for idx, (name, _) in enumerate(playlist_info):
                if name == current_playlist:
                    start_page = idx // page_size
                    break
        else:
            start_page = 0

        view.current_page = start_page
        view._update_buttons()

        embed = format_playlists_page(view.get_page_items(), start_page, view.total_pages)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @app_commands.command(name="queue", description="show the current queue")
    @app_commands.guild_only()
    @app_commands.describe(page="jump to page number")
    @require_permission("queue")
    async def queue(
        self,
        interaction: discord.Interaction,
        page: app_commands.Range[int, 1, 9999] | None = None
    ) -> None:
        """Show queue with pagination. Opens to the page containing the current track."""
        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            await self.respond(interaction, "music_unavailable")
            return

        guild_id = interaction.guild_id
        queue_obj = music_cog.get_queue(guild_id)

        if not queue_obj.tracks:
            await self.respond(interaction, "queue_empty")
            return

        # Build queue title (truncate for embed title limit of 256 chars)
        if queue_obj.display_playlist_name:
            playlist_name = truncate_for_display(queue_obj.display_playlist_name, EMBED_TITLE_MAX)
            playlist_name = escape_markdown(playlist_name)
        else:
            playlist_name = "queue"

        display_items = queue_obj.active_tracks.copy()

        if queue_obj.shuffle:
            queue_title = f"\U0001f500 mixed: {playlist_name}"
        else:
            queue_title = playlist_name

        # Detect artist display mode across all tracks
        unique_artists = set()
        for track in display_items:
            _, artist = queue_obj.get_track_display(track)
            unique_artists.add(artist)

        if unique_artists == {None}:
            artist_mode = "none"
        elif len(unique_artists) == 1 and None not in unique_artists:
            artist_mode = "single"
            single_artist = next(iter(unique_artists))
        else:
            artist_mode = "multi"

        panel_color = self.bot.config_manager.get_panel_color()
        display_size = self.display_size

        def format_queue_page(items: list, page_num: int, total: int) -> discord.Embed:
            embed = discord.Embed(title=queue_title, color=panel_color)
            lines = []
            is_last_page = (page_num == total - 1)

            start_num = page_num * display_size + 1
            for i, track in enumerate(items):
                track_title_raw, track_artist = queue_obj.get_track_display(track)
                track_num = start_num + i
                is_current = track == queue_obj.current

                # Show artist inline only in multi-artist mode for tracks that have one
                show_artist = (artist_mode == "multi"
                               and track_artist and track_artist.strip())

                if show_artist:
                    title = escape_markdown(truncate_for_display(
                        track_title_raw, QUEUE_TITLE_MULTI_MAX))
                    artist = escape_markdown(truncate_for_display(
                        track_artist, QUEUE_ARTIST_MAX))

                    if is_current:
                        lines.append(
                            f"{track_num}. \U0001f4bf "
                            f"**\u2192 *{artist}* \u2022 {title} \u2190**")
                    else:
                        lines.append(
                            f"{track_num}. *{artist}* \u2022 **{title}**")
                else:
                    title = escape_markdown(truncate_for_display(
                        track_title_raw, QUEUE_TITLE_MAX))

                    if is_current:
                        lines.append(
                            f"{track_num}. \U0001f4bf "
                            f"**\u2192 {title} \u2190**")
                    else:
                        lines.append(f"{track_num}. **{title}**")

            # Add loop indicator on last page
            if is_last_page and len(items) > 0:
                lines.append("")
                if queue_obj.shuffle:
                    lines.append("\u21bb reshuffles and loops")
                else:
                    lines.append("\u21bb loops to beginning")

            embed.description = "\n".join(lines)

            # Footer: page info + single-artist display
            if artist_mode == "single":
                footer_artist = truncate_for_display(single_artist, 40)
                embed.set_footer(text=f"page {page_num + 1}/{total} \u00b7 {footer_artist}")
            else:
                embed.set_footer(text=f"page {page_num + 1}/{total}")

            return embed

        view = PaginationView(
            items=display_items,
            page_size=display_size,
            format_page=format_queue_page,
            bot=self.bot
        )

        # Determine start page: explicit param > current track page > 0
        if page is not None:
            start_page = min(page - 1, view.total_pages - 1)
        elif queue_obj.current_index is not None:
            start_page = queue_obj.current_index // display_size
        else:
            start_page = 0

        view.current_page = start_page
        view._update_buttons()

        embed = format_queue_page(view.get_page_items(), start_page, view.total_pages)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        view.message = await interaction.original_response()

    @app_commands.command(name="playlist", description="switch to a playlist")
    @app_commands.guild_only()
    @app_commands.describe(name="search for a playlist (use /playlists to see all)")
    @app_commands.autocomplete(name=playlist_autocomplete)
    @require_permission("playlist")
    async def playlist(self, interaction: discord.Interaction, name: str | None = None) -> None:
        """Switch to a different playlist.

        Returns early when fewer than two playlists are available.
        Acquires playback lock before calling set_playlist() and loading metadata
        cache to prevent races with concurrent skip/previous/on_track_end operations.
        State save happens outside lock (has its own atomic save mechanism).
        """
        library = self.bot.library
        available = library.get_playlist_names()

        if not available:
            await self.respond(interaction, "no_playlists")
            return
        if len(available) == 1:
            await self.respond(interaction, "single_playlist")
            return

        # Get music cog and check VC early (before showing picker)
        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            await self.respond(interaction, "music_unavailable")
            return

        player = music_cog.get_player(interaction)
        if player and not await self._check_same_vc(interaction, player):
            return

        # No name provided — show picker directly
        if not name:
            queue = music_cog.get_queue(interaction.guild_id)
            current_playlist = queue.playlist_name
            view = PlaylistSelectView(self.bot, available, current_playlist)
            await interaction.response.send_message(
                "select a playlist:",
                view=view,
                ephemeral=True
            )
            view.message = await interaction.original_response()
            return

        # Find playlist (case-insensitive exact, then fuzzy fallback)
        matched = None
        for pname in available:
            if pname == name.lower():
                matched = pname
                break

        # Fuzzy fallback if no exact match
        if not matched:
            fuzzy_results = playlist_search(name, available, max_results=1, score_cutoff=70)
            if fuzzy_results:
                matched = fuzzy_results[0][0]

        if not matched:
            # Show playlist picker instead of just an error
            queue = music_cog.get_queue(interaction.guild_id)
            current_playlist = queue.playlist_name

            view = PlaylistSelectView(self.bot, available, current_playlist)
            display_name = name[:50] + "..." if len(name) > 50 else name
            await interaction.response.send_message(
                f"can't find '{escape_markdown(display_name)}', try these:",
                view=view,
                ephemeral=True
            )
            view.message = await interaction.original_response()
            return

        # Load playlist
        tracks = library.get_playlist(matched)
        if not tracks:
            await self.respond(interaction, "playlist_empty")
            return
        guild_id = interaction.guild_id

        async with music_cog._get_playback_lock(guild_id):
            queue = music_cog.get_queue(guild_id)
            queue.set_playlist(matched, tracks, self.bot.library.get_playlist_path(matched))
            # Load metadata cache for this playlist (O(1) lookups during playback)
            await queue.load_metadata_cache(self.bot.metadata_cache_path, matched)

        # Save last playlist for restore on restart (outside lock - has own atomic save)
        self.bot.state_manager.set("last_playlist", matched)
        await self.bot.state_manager.save()

        logger.info(f"{interaction.user.display_name} switched to \"{matched}\"")
        await self.respond(interaction, "playlist_switched", playlist=escape_markdown(matched))

        # Update panel to show new upcoming tracks
        await self.bot.panel_manager.notify(guild_id)

    @app_commands.command(name="shuffle", description="toggle shuffle on or off")
    @app_commands.guild_only()
    @app_commands.describe(mode="on or off")
    @app_commands.choices(mode=[
        app_commands.Choice(name="on", value="on"),
        app_commands.Choice(name="off", value="off"),
    ])
    @require_command_enabled("shuffle")
    @require_permission("shuffle")
    async def shuffle(self, interaction: discord.Interaction, mode: app_commands.Choice[str]) -> None:
        """Toggle shuffle mode.

        Acquires playback lock before enabling/disabling shuffle to prevent races
        with concurrent skip/previous/on_track_end operations that read active_tracks.
        Captures shuffle_state inside lock, uses it outside for state save and response.
        """
        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            await self.respond(interaction, "music_unavailable")
            return

        player = music_cog.get_player(interaction)
        if player and not await self._check_same_vc(interaction, player):
            return

        guild_id = interaction.guild_id

        async with music_cog._get_playback_lock(guild_id):
            queue = music_cog.get_queue(guild_id)
            if mode.value == "on":
                queue.enable_shuffle()
                shuffle_state = True
            else:
                queue.disable_shuffle()
                shuffle_state = False

        # Outside lock (safe)
        self.bot.state_manager.set("shuffle", shuffle_state)
        if shuffle_state:
            logger.info(f"shuffle enabled by {interaction.user.display_name}")
            await self.respond(interaction, "shuffle_on")
        else:
            logger.info(f"shuffle disabled by {interaction.user.display_name}")
            await self.respond(interaction, "shuffle_off")

        await self.bot.state_manager.save()

        # Update panel to reflect shuffle state
        await self.bot.panel_manager.notify(guild_id)

    @app_commands.command(name="loop", description="toggle track loop on or off")
    @app_commands.guild_only()
    @app_commands.describe(mode="on or off")
    @app_commands.choices(mode=[
        app_commands.Choice(name="on", value="on"),
        app_commands.Choice(name="off", value="off"),
    ])
    @require_command_enabled("loop")
    @require_permission("loop")
    async def loop(self, interaction: discord.Interaction, mode: app_commands.Choice[str]) -> None:
        """Toggle song repeat mode."""
        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            await self.respond(interaction, "music_unavailable")
            return

        player = music_cog.get_player(interaction)
        if player and not await self._check_same_vc(interaction, player):
            return

        guild_id = interaction.guild_id
        queue = music_cog.get_queue(guild_id)

        if mode.value == "on":
            queue.song_loop = True
            logger.info(f"loop enabled by {interaction.user.display_name}")
            await self.respond(interaction, "loop_on")
        else:
            queue.song_loop = False
            logger.info(f"loop disabled by {interaction.user.display_name}")
            await self.respond(interaction, "loop_off")

        # Note: song_loop not persisted (intentional - resets on restart)
        # Update panel to reflect loop state
        await self.bot.panel_manager.notify(guild_id)


async def setup(bot: commands.Bot) -> None:
    """Load the Queue cog."""
    await bot.add_cog(Queue(bot))
