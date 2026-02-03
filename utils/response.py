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
PLAYLIST_NAME_MAX = 50     # Same consideration

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

    async def _delete_response(self, interaction: discord.Interaction, delay: float) -> None:
        """Delete interaction response after delay (for followup path).

        Used internally when delete_after isn't available (followup messages).
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
            await interaction.followup.send(text, ephemeral=True)
            if delete_after:
                task = asyncio.create_task(self._delete_response(interaction, delete_after))
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
        if interaction.user.voice.channel != player.channel:
            await self.respond(interaction, "wrong_vc", channel=player.channel.mention)
            return False
        return True
