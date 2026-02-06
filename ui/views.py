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

"""Reusable UI views for Jill.

Provides base classes and common views used across the bot:

AutoDeleteView:
    Base class that auto-deletes the message when the view times out.
    Inherit from this for any ephemeral view that should clean up.

PaginationView:
    Paginated list display with prev/next buttons. Used by /queue
    and /playlists commands to show large lists.

SearchSelectionView:
    Dropdown menu for selecting from fuzzy search results. Used by
    /play when multiple tracks match the query.

Timeout configuration:
    Views read timeout from ui.extended_auto_delete in settings.yaml.
    Default is 90 seconds.
"""

import asyncio

import discord
from typing import Callable

from utils.response import escape_markdown, truncate_for_display, SELECT_LABEL_MAX

# Track fire-and-forget cleanup tasks to prevent GC warnings
_cleanup_tasks: set[asyncio.Task] = set()


class AutoDeleteView(discord.ui.View):
    """Base class for views with auto-delete support.

    Provides:
    - on_timeout: Deletes self.message when view times out
    - _delete_response_after: Fire-and-forget deletion after delay
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.message: discord.Message | None = None
        self.bot = None

    async def _delete_response_after(self, interaction: discord.Interaction, delay: float) -> None:
        """Delete interaction's message after delay (fire-and-forget).

        Silently handles cancellation (shutdown) and Discord errors.
        """
        try:
            await asyncio.sleep(delay)
            await interaction.delete_original_response()
        except asyncio.CancelledError:
            pass  # Shutdown during wait - acceptable
        except discord.NotFound:
            pass
        except discord.HTTPException:
            pass

    async def on_timeout(self) -> None:
        """Delete message when view times out."""
        if self.message:
            try:
                await self.message.delete()
            except discord.NotFound:
                pass
            except discord.HTTPException:
                pass

    def _user_in_bot_vc(self, interaction: discord.Interaction) -> bool:
        """Check if user is in same VC as bot. Returns False if bot/guild unavailable, True if bot not in VC."""
        if not self.bot or not interaction.guild:
            return False
        vc = interaction.guild.voice_client
        if not vc:
            return True  # Bot not in VC - allow
        if not interaction.user.voice:
            return False
        return interaction.user.voice.channel == vc.channel


class PaginationView(AutoDeleteView):
    """Paginated view for displaying long lists with prev/next buttons.

    Splits a list into pages and provides navigation. The format_page callback
    generates the embed for each page.

    Args:
        items: Full list of items to paginate
        page_size: Items per page (default 15)
        format_page: Callback(items, page_num, total_pages) -> Embed
        timeout: Seconds before auto-delete (reads from config if None)
        bot: Bot instance for config access
    """

    def __init__(
        self,
        items: list,
        page_size: int = 15,
        format_page: Callable[[list, int, int], discord.Embed] = None,
        timeout: float = None,
        bot = None  # Pass bot for config access
    ) -> None:
        # Read timeout from config if not explicitly provided
        if timeout is None and bot:
            ui_config = bot.config_manager.get("ui", {})
            timeout = ui_config.get("extended_auto_delete", 90)
        elif timeout is None:
            timeout = 90  # Fallback default

        super().__init__(timeout=timeout)
        self.items = items
        self.page_size = page_size
        self.format_page = format_page
        self.current_page = 0
        self.total_pages = max(1, (len(items) + page_size - 1) // page_size)

        self._update_buttons()

    def _update_buttons(self) -> None:
        """Update button states based on current page."""
        self.prev_button.disabled = self.current_page <= 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1

    def get_page_items(self) -> list:
        """Get items for current page."""
        start = self.current_page * self.page_size
        end = start + self.page_size
        return self.items[start:end]

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            embed = self.format_page(self.get_page_items(), self.current_page, self.total_pages)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self._update_buttons()
            embed = self.format_page(self.get_page_items(), self.current_page, self.total_pages)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()


class SearchSelectionView(AutoDeleteView):
    """Dropdown menu for selecting from fuzzy search results.

    Used by /play when the query matches multiple tracks. Shows up to 25
    options (Discord's limit) with track title and artist.

    Allows selection if bot not in VC, or if user is in same VC as bot.

    Args:
        tracks: List of (track_dict, score) tuples from fuzzy_search (score unused)
        bot: Bot instance for config and VC access
    """

    def __init__(self, tracks: list[tuple[dict, float]], bot=None) -> None:
        # Read timeout from config
        if bot:
            ui_config = bot.config_manager.get("ui", {})
            timeout = ui_config.get("extended_auto_delete", 90)
        else:
            timeout = 90

        super().__init__(timeout=timeout)
        self.tracks = tracks
        self.selected: dict | None = None
        self.bot = bot

        # Create select menu (Discord limits to 25 options)
        options = []
        for i, (track, _) in enumerate(tracks[:25]):
            label = truncate_for_display(track['title'], SELECT_LABEL_MAX)
            description = truncate_for_display(track['artist'] or 'unknown', SELECT_LABEL_MAX)
            options.append(discord.SelectOption(
                label=label,
                description=description,
                value=str(i)
            ))

        placeholder = "select"
        select = discord.ui.Select(
            placeholder=placeholder,
            options=options
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction) -> None:
        """Handle track selection. Silently dismisses if user not in bot's VC. Shows track_selected message if enabled, auto-deletes."""
        if not self._user_in_bot_vc(interaction):
            await interaction.response.edit_message(view=None)
            self.stop()
            return

        index = int(interaction.data['values'][0])
        self.selected = self.tracks[index][0]

        if self.bot and self.bot.config_manager.is_enabled("track_selected"):
            content = self.bot.config_manager.msg("track_selected", title=escape_markdown(self.selected['title']))
            await interaction.response.edit_message(content=content, view=None)
            # Fire-and-forget auto-delete
            ui_config = self.bot.config_manager.get("ui", {})
            delete_after = ui_config.get("brief_auto_delete", 10)
            if delete_after > 0:
                task = asyncio.create_task(self._delete_response_after(interaction, delete_after))
                _cleanup_tasks.add(task)
                task.add_done_callback(_cleanup_tasks.discard)
        else:
            # Silent - defer to acknowledge, then delete message
            await interaction.response.defer()
            try:
                await interaction.delete_original_response()
            except discord.NotFound:
                pass

        self.stop()
