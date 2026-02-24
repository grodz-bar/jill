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

"""Response utilities for Discord interactions.

Provides ResponseMixin for consistent message handling across cogs.
All cogs inherit from this mixin to get respond() and msg() helpers.
"""

import asyncio

import discord

# Track fire-and-forget cleanup tasks to prevent GC warnings
_cleanup_tasks: set[asyncio.Task] = set()


def escape_markdown(text: str) -> str:
    """Escape underscores for Discord embed/message display.

    Discord interprets _text_ as italics when underscores are at word
    boundaries (common with Unicode characters). Escaping with backslash
    preserves literal underscores.

    Use for: embed descriptions, embed field values, message content.
    Do NOT use for: SelectOption labels, autocomplete choices (plain text).
    """
    return text.replace("_", "\\_")


# =============================================================================
# DISPLAY TRUNCATION
# =============================================================================
# Discord limits and safe truncation thresholds.
# Always truncate BEFORE escape_markdown (escaping can add characters).

# Per-item limits for paginated embeds (must stay under 4096 total)
QUEUE_TITLE_MAX = 60       # 50 items × ~66 chars/line = ~3300 (under 4096)
QUEUE_ARTIST_MAX = 18      # 15 visible + "..." — artist in multi-artist /queue lines
QUEUE_TITLE_MULTI_MAX = 33 # 30 visible + "..." — title when sharing line with artist
PLAYLIST_NAME_MAX = 50     # Same consideration
FOOTER_ARTIST_MAX = 35     # Artist name in /queue footer (single-artist mode, UX choice)

# Discord API hard limits
CHOICE_NAME_MAX = 97       # app_commands.Choice.name (limit 100) - room for "..."
SELECT_LABEL_MAX = 97      # discord.SelectOption.label (limit 100) - room for "..."
EMBED_FIELD_MAX = 1000     # embed field value (limit 1024) - room for "..." + escapes
EMBED_TITLE_MAX = 240      # embed title (limit 256) - room for prefixes like "🔀 mixed: "


def truncate_for_display(text: str, max_length: int) -> str:
    """Truncate text with ellipsis for Discord display.

    Args:
        text: Text to truncate (must not be None)
        max_length: Maximum length including "..." suffix

    Returns:
        Original text if within limit, else truncated with "..."

    Note:
        Always call BEFORE escape_markdown(). Escaping can add characters
        (underscores become \\_) which would throw off length calculations.

    Example:
        title = truncate_for_display(title, QUEUE_TITLE_MAX)
        title = escape_markdown(title)  # After truncation
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


# Generic/placeholder artist names that provide no value in display contexts.
# Still extracted and used internally (metadata, search index, /np detail view).
GENERIC_ARTISTS = {
    "various artists", "various", "va", "v/a", "v.a.",
    "unknown artist", "unknown", "no artist",
}


def display_artist(artist: str | None) -> str | None:
    """Return None if artist is generic/placeholder, otherwise return as-is.

    Generic names like "Various Artists" clutter casual display (panel, queue,
    autocomplete) without adding value. The /np command should NOT use this
    — it shows full metadata detail where even generic names are informative.
    """
    if artist and artist.strip().lower() in GENERIC_ARTISTS:
        return None
    return artist


def format_playlists_page(
    items: list, page_num: int, total: int, *,
    current_name: str | None, color: int
) -> discord.Embed:
    """Format a page of playlists as a Discord embed.

    Used by /playlists command and panel overflow picker.
    """
    embed = discord.Embed(title="available playlists", color=color)
    lines = []

    for name, count in items:
        if name == current_name:
            display_name = truncate_for_display(name, PLAYLIST_NAME_MAX).replace("`", "'")
            lines.append(f"- **`{display_name}`** [{count}]")
        else:
            display_name = escape_markdown(truncate_for_display(name, PLAYLIST_NAME_MAX))
            lines.append(f"- {display_name} [{count}]")

    lines.append("\nuse `/playlist [name]` to switch")
    embed.description = "\n".join(lines)
    embed.set_footer(text=f"page {page_num + 1}/{total}")
    return embed


class ResponseMixin:
    """Mixin providing standardized interaction responses for cogs.

    Provides respond() which handles:
    - Per-message enable/disable from messages.yaml
    - Auto-deletion after configurable timeout
    - Both response and followup paths

    Requirements:
        self.bot must have a config_manager with:
        - msg(key, **kwargs) -> str
        - is_enabled(key) -> bool
        - get(key, default) -> value

    Usage:
        class MyCog(ResponseMixin, commands.Cog):
            async def my_command(self, interaction):
                await self.respond(interaction, "success_message", count=5)
    """

    def msg(self, key: str, **kwargs) -> str:
        """Get formatted message text from config.

        Args:
            key: Message key from messages.yaml
            **kwargs: Format variables for the message template

        Returns:
            Formatted message string
        """
        return self.bot.config_manager.msg(key, **kwargs)

    async def _delete_followup(self, msg: discord.Message, delay: float) -> None:
        """Delete a followup message after delay.

        Used internally when delete_after isn't available (followup messages).
        Deletes the specific message object rather than using
        delete_original_response(), matching the pattern in
        ControlPanelLayout and bot.py error handler.
        """
        try:
            await asyncio.sleep(delay)
            await msg.delete()
        except asyncio.CancelledError:
            pass  # Shutdown during wait - acceptable
        except discord.NotFound:
            pass
        except discord.HTTPException:
            pass

    async def respond(self, interaction: discord.Interaction, key: str, **kwargs) -> None:
        """Send ephemeral message if enabled, otherwise acknowledge silently.

        Checks messages.yaml for `enabled: true/false` on the message key.
        If disabled, defers and deletes to silently acknowledge.
        If enabled, sends message with auto-delete after ui.brief_auto_delete.

        Args:
            interaction: Discord interaction to respond to
            key: Message key from messages.yaml
            **kwargs: Format variables for the message template

        Config:
            messages.yaml - Per-message `enabled` flag
            settings.yaml - `ui.brief_auto_delete` (default 10s, 0 to disable)
        """
        if not self.bot.config_manager.is_enabled(key):
            # Silent acknowledgment - defer then delete
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            try:
                await interaction.delete_original_response()
            except discord.NotFound:
                pass  # Already deleted or never created
            return

        text = self.msg(key, **kwargs)

        ui_config = self.bot.config_manager.get("ui", {})
        timeout = ui_config.get("brief_auto_delete", 10)
        delete_after = timeout if timeout > 0 else None

        if not interaction.response.is_done():
            # Response path - use native delete_after
            await interaction.response.send_message(text, ephemeral=True, delete_after=delete_after)
        else:
            # Followup path - manual deletion via task
            msg = await interaction.followup.send(text, ephemeral=True, wait=True)
            if delete_after:
                task = asyncio.create_task(self._delete_followup(msg, delete_after))
                _cleanup_tasks.add(task)
                task.add_done_callback(_cleanup_tasks.discard)

    async def _check_same_vc(self, interaction: discord.Interaction, player) -> bool:
        """Check user is in same VC as bot. Returns True if allowed, False if denied.

        Sends not_in_vc or wrong_vc message via respond() on denial.
        Used by slash commands (cogs). No standby bypass - caller must check player first.
        See also: ControlPanelLayout._check_vc() for button equivalent (with standby bypass).
        See also: ControlPanelLayout._user_in_bot_vc() for silent button check (no standby bypass).
        """
        if not interaction.user.voice:
            await self.respond(interaction, "not_in_vc")
            return False
        if not player.channel:
            await self.respond(interaction, "not_in_vc")
            return False
        if interaction.user.voice.channel != player.channel:
            await self.respond(interaction, "wrong_vc", channel=player.channel.mention)
            return False
        return True
