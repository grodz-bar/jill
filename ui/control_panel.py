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

"""Media control panel for Jill."""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import discord
import mafic
from discord.enums import SeparatorSpacing
from discord.ext import commands
from loguru import logger

from ui.views import AutoDeleteView, PaginationView
from utils.holidays import get_active_holiday
from utils.response import (
    escape_markdown,
    truncate_for_display,
    PLAYLIST_NAME_MAX,
    SELECT_LABEL_MAX,
)

# Track fire-and-forget cleanup tasks to prevent GC warnings
_cleanup_tasks: set[asyncio.Task] = set()


# =============================================================================
# PANEL TEXT TRUNCATION LIMITS
# =============================================================================
# The control panel width changes based on how many buttons are visible.
# These dicts map button_count -> character_limit to prevent text overflow.
#
# Button counts:
#   6 - All optional buttons enabled (shuffle, loop, playlist) + 3 core
#   5 - Two optional buttons + 3 core (previous, play/pause, next)
#   4 - One optional button + 3 core
#   3 - Core buttons only
#
# Values were manually tuned to prevent the Discord embed from stretching
# on both desktop and mobile clients. If the panel looks wrong, adjust these.
#
# Usage: threshold = SOME_THRESHOLD[button_count]
# =============================================================================

# "now serving" section - the current track title
# HEADING_SIZE: Titles longer than this threshold use smaller heading (### vs ##)
# TITLE_TRUNCATE: Titles longer than this get cut off with "..."
HEADING_SIZE_THRESHOLDS = {6: 24, 5: 28, 4: 24, 3: 17}
TITLE_TRUNCATE_THRESHOLDS = {6: 30, 5: 38, 4: 29, 3: 20}

# "coming up" and "previous" sections - track names in queue preview
COMING_UP_TRUNCATE_THRESHOLDS = {6: 37, 5: 46, 4: 36, 3: 27}

# Info line (bottom) - shows "album • artist"
# INFO_LINE_WIDTH: Max chars per line (applies to single-line AND two-line mode)
# ALBUM_TRUNCATE: When fitting both on one line, truncate album to this length
#                 (keeps artist intact; if still too long, splits to two lines)
INFO_LINE_WIDTH_LIMITS = {6: 41, 5: 51, 4: 41, 3: 29}
ALBUM_TRUNCATE_LIMITS = {6: 30, 5: 33, 4: 28, 3: 20}

# Progress bar - character count per button configuration
# Manually tuned to match panel width at each button count
PROGRESS_BAR_LENGTHS = {6: 14, 5: 17, 4: 14, 3: 10}


def build_progress_bar(position_ms: int, length_ms: int, config: dict, bar_length: int) -> str:
    """Build visual progress bar string.

    Args:
        position_ms: Current position in milliseconds
        length_ms: Total track length in milliseconds
        config: Panel config dict with progress bar settings
        bar_length: Number of characters in the progress bar

    Returns:
        Progress bar (e.g., "🟪🟪🟪⬛⬛⬛⬛⬛⬛⬛"),
        empty string if disabled, or ":" placeholder if invalid duration
    """
    if not config.get("progress_bar_enabled", True):
        return ""

    if length_ms <= 0:
        return ":"  # Fallback for tracks with invalid length

    # Check for holiday override
    holiday = get_active_holiday()
    if holiday and "progress_filled" in holiday:
        filled_char = holiday["progress_filled"]
    else:
        filled_char = config.get("progress_bar_filled", "🟪")

    empty_char = config.get("progress_bar_empty", "⬛")

    progress = min(1.0, max(0.0, position_ms / length_ms))
    filled_count = int(progress * bar_length)

    bar = filled_char * filled_count + empty_char * (bar_length - filled_count)

    return bar


class DrinkCounter:
    """Manages drink emoji rotation for the control panel header.

    The panel header shows a drink emoji that changes with each track,
    giving visual feedback that something happened (like a bartender
    serving a new drink). The emoji rotates through a configurable list.

    Lifecycle:
    - Created once per guild when playback starts
    - increment() called on track_end (new drink for new track)
    - decrement() called when going to previous track

    Attributes:
        drink_emojis: List of emoji strings to cycle through
        enabled: If False, get_emoji() returns empty string
        position: Current index in the emoji list (0 to len-1)
    """

    def __init__(self, drink_emojis: list[str], enabled: bool = True) -> None:
        self.drink_emojis = drink_emojis
        self.enabled = enabled
        self.position = 0

    def get_emoji(self, offset: int = 0) -> str:
        """Get emoji at current position (plus offset) with trailing space.

        Args:
            offset: Number of positions forward from current. Use offset=1
                    to peek at the next emoji without incrementing.

        Returns:
            Emoji string with trailing space (e.g., "🍸 "), or empty string
            if drink emojis are disabled in config.
        """
        if not self.enabled:
            return ""
        idx = (self.position + offset) % len(self.drink_emojis)
        return f"{self.drink_emojis[idx]} "

    def increment(self) -> None:
        """Advance to next emoji (called on track change)."""
        self.position = (self.position + 1) % len(self.drink_emojis)

    def decrement(self) -> None:
        """Go back to previous emoji (called on previous track)."""
        self.position = (self.position - 1) % len(self.drink_emojis)


class PlaylistSelectView(AutoDeleteView):
    """Ephemeral dropdown for selecting a playlist from the panel.

    Shows available playlists as a Discord select menu. If there are more
    than 25 playlists (Discord's limit), shows first 24 plus an overflow
    option that opens a paginated list view.

    When a playlist is selected, switches the queue to that playlist
    without starting playback (allows pre-selecting while paused).
    Saves selection as last_playlist and updates control panel.

    Attributes:
        bot: Bot instance for config and cog access
        selected: The playlist name chosen by user (set by callback)
    """

    def __init__(self, bot: commands.Bot, playlists: list[str], current: str | None) -> None:
        # Read pagination timeout from config
        ui_config = bot.config_manager.get("ui", {})
        timeout = ui_config.get("extended_auto_delete", 90)
        super().__init__(timeout=timeout)
        self.bot = bot
        self.selected: str | None = None

        # Discord limits select menus to 25 options
        has_overflow = len(playlists) > 25
        # Store the SHOWN list for index lookup (not full list)
        self.shown_playlists = playlists[:24] if has_overflow else playlists[:25]

        options = []
        for i, name in enumerate(self.shown_playlists):
            options.append(discord.SelectOption(
                label=truncate_for_display(name, SELECT_LABEL_MAX),
                value=str(i),  # Index-based (handles any name length)
                default=(name == current)
            ))

        if has_overflow:
            overflow_count = len(playlists) - 24
            playlist_word = "playlist" if overflow_count == 1 else "playlists"
            options.append(discord.SelectOption(
                label="[click here to see all playlists]",
                value="_overflow_hint",  # Special marker, NOT an index
                description=f"{overflow_count} more {playlist_word} available"
            ))

        select = discord.ui.Select(
            placeholder="select",
            options=options,
            custom_id="playlist:select"
        )
        select.callback = self.on_select
        self.add_item(select)

    async def on_select(self, interaction: discord.Interaction) -> None:
        """Handle playlist selection from the dropdown.

        Validates tracks exist BEFORE acquiring lock (read-only operation).
        Acquires playback lock before set_playlist() and metadata cache load to
        prevent races with concurrent playback operations. State save and panel
        update happen outside lock.
        """
        selected_value = interaction.data['values'][0]

        if not self._user_in_bot_vc(interaction):
            await interaction.response.edit_message(view=None)
            self.stop()
            return

        # CRITICAL: Check overflow BEFORE int() conversion
        if selected_value == "_overflow_hint":
            # Build same content as /playlists
            library = self.bot.library
            playlist_names = library.get_playlist_names()

            playlist_info = []
            for name in sorted(playlist_names):
                tracks = library.get_playlist(name)
                playlist_info.append((name, len(tracks) if tracks else 0))

            panel_color = self.bot.config_manager.get_panel_color()

            def format_playlists_page(items: list, page: int, total: int) -> discord.Embed:
                embed = discord.Embed(title="🎶 available playlists", color=panel_color)
                lines = [
                    f"• **{escape_markdown(truncate_for_display(name, PLAYLIST_NAME_MAX))}** [{count} {'track' if count == 1 else 'tracks'}]"
                    for name, count in items
                ]
                lines.append("\nuse `/playlist [name]` to switch")
                embed.description = "\n".join(lines)
                embed.set_footer(text=f"page {page + 1}/{total}")
                return embed

            page_size = self.bot.config_manager.get("playlists_display_size", 15)

            view = PaginationView(
                items=playlist_info,
                page_size=page_size,
                format_page=format_playlists_page,
                bot=self.bot
            )

            embed = format_playlists_page(view.get_page_items(), 0, view.total_pages)
            await interaction.response.edit_message(content=None, embed=embed, view=view)
            view.message = interaction.message
            self.stop()  # Stop this view's timeout before transitioning
            return

        # Now safe to convert to int and look up actual name
        selected_name = self.shown_playlists[int(selected_value)]
        self.selected = selected_name

        music_cog = self.bot.get_cog("Music") if self.bot else None
        if not music_cog:
            await interaction.response.edit_message(
                content=self.bot.config_manager.msg("music_unavailable"),
                view=None
            )
            return

        guild_id = interaction.guild_id

        # Check tracks BEFORE acquiring lock (read-only library operation)
        tracks = self.bot.library.get_playlist(selected_name)
        if not tracks:
            await interaction.response.edit_message(
                content=self.bot.config_manager.msg("playlist_empty"),
                view=None
            )
            return

        async with music_cog._get_playback_lock(guild_id):
            queue = music_cog.get_queue(guild_id)
            queue.set_playlist(selected_name, tracks)
            await queue.load_metadata_cache(self.bot.metadata_cache_path, selected_name)

        # Save last playlist for restore on restart (outside lock - has own atomic save)
        self.bot.state_manager.set("last_playlist", selected_name)
        await self.bot.state_manager.save()

        # Shuffle is already applied by set_playlist() if queue.shuffle is True

        logger.info(f"{interaction.user.display_name} switched to \"{selected_name}\"")

        if self.bot.config_manager.is_enabled("playlist_switched"):
            await interaction.response.edit_message(
                content=self.bot.config_manager.msg("playlist_switched", playlist=escape_markdown(selected_name)),
                view=None
            )
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

        # Update the main panel
        await music_cog.update_panel(guild_id)

        self.stop()


class ControlPanelLayout(discord.ui.LayoutView):
    """The main music control panel displayed in Discord.

    Uses Discord's Components V2 (LayoutView) to create an integrated media
    player with colored border, progress bar, and playback buttons.

    Structure:
    - Header: "now serving:" + current track title with drink emoji
    - Progress bar: Visual indicator of track position (optional)
    - Body: Upcoming/previous tracks, position in queue
    - Buttons: Previous, Play/Pause, Next + optional Shuffle, Loop, Playlist
    - Info line: Album and artist information

    Button configuration:
    - Core buttons (always shown): Previous, Play/Pause, Next
    - Optional buttons (config-controlled): Shuffle, Loop, Playlist
    - When all 6 buttons enabled, splits into 2 rows with text labels
    - Playlist button hidden if only 1 playlist exists

    Voice channel checks:
    - _check_vc(): Message-sending check with standby bypass (shuffle/loop/playlist)
    - _user_in_bot_vc(): Silent check, no standby bypass (skip/previous/play-pause)
    - See ResponseMixin._check_same_vc() for slash command equivalent

    Attributes:
        bot: Bot instance for config access and cog retrieval
        _guild_id: Guild this panel belongs to
        _button_count: Number of visible buttons (affects text truncation)
    """

    def __init__(self, bot: commands.Bot = None, guild_id: int = None) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self._guild_id = guild_id
        self._setup_components()

    def _setup_components(self) -> None:
        """Build the layout structure."""
        # Build action rows first (sets _button_count needed by progress bar)
        self.action_rows = self._build_action_rows()

        # Header content ("Now Serving" line)
        self.header_display = discord.ui.TextDisplay(
            self._build_idle_header()
        )

        # Visible separator between header and body
        self.header_separator = discord.ui.Separator(
            visible=True, spacing=SeparatorSpacing.small
        )

        # Progress bar (separate so we can add separator below it)
        self.progress_display = discord.ui.TextDisplay(
            self._build_idle_progress()
        )

        # Separator under progress bar
        self.progress_separator = discord.ui.Separator(
            visible=True, spacing=SeparatorSpacing.small
        )

        # Body content (coming up, last served, etc.)
        self.body_display = discord.ui.TextDisplay(
            self._build_idle_body()
        )

        # Visible separator between content and buttons
        self.separator = discord.ui.Separator(visible=True)

        # Info display (playlist • artist) - appears below buttons
        self.info_display = discord.ui.TextDisplay(
            self._build_idle_info()
        )

        # Build container contents
        container_items = [
            self.header_display,
            self.header_separator,
        ]

        # Only add progress section if enabled
        panel_config = self.bot.config_manager.get("panel", {}) if self.bot else {}
        if panel_config.get("progress_bar_enabled", True):
            container_items.append(self.progress_display)
            container_items.append(self.progress_separator)

        container_items.extend([
            self.body_display,
            self.separator,
        ])

        # Add button rows - with separator between if 2 rows
        if len(self.action_rows) == 2:
            container_items.append(self.action_rows[0])
            self.button_row_separator = discord.ui.Separator(visible=True)
            container_items.append(self.button_row_separator)
            container_items.append(self.action_rows[1])
        else:
            container_items.extend(self.action_rows)

        # Add info section below buttons
        self.info_separator = discord.ui.Separator(visible=True)
        container_items.append(self.info_separator)
        container_items.append(self.info_display)

        # Container wraps everything with accent color
        panel_color = self.bot.config_manager.get_panel_color() if self.bot else 0xA03E72
        self.container = discord.ui.Container(
            *container_items,
            accent_color=panel_color
        )

        # Add container to the LayoutView
        self.add_item(self.container)

    def _build_idle_header(self) -> str:
        """Build header for idle/startup state."""
        return "### now serving:\n[nothing]"

    def _build_idle_progress(self) -> str:
        """Build progress bar for idle/startup state."""
        if self.bot:
            panel_config = self.bot.config_manager.get("panel", {})
        else:
            panel_config = {}
        empty_char = panel_config.get("progress_bar_empty", "⬛")
        return empty_char * self._get_progress_bar_length()

    def _build_idle_body(self) -> str:
        """Build body for idle/startup state."""
        return "press `▶️play` to start"

    def _build_idle_info(self) -> str:
        """Build info line for idle/startup state."""
        if self.bot:
            panel_config = self.bot.config_manager.get("panel", {})
            return panel_config.get("info_fallback_message", "mixing drinks and changing lives")
        return "mixing drinks and changing lives"

    def _build_action_rows(self) -> list[discord.ui.ActionRow]:
        """Build ActionRow(s) with buttons based on config.

        Returns 1 row if ≤5 buttons, 2 rows (split 3/3) if 6 buttons.
        When using 2 rows, buttons get text labels for better visibility.
        Also stores button references as instance attributes for later updates.
        """
        # First, determine which optional buttons are enabled
        has_shuffle = False
        has_loop = False
        has_playlist = False

        if self.bot:
            panel_config = self.bot.config_manager.get("panel", {})
            playlist_count = len(self.bot.library.get_playlist_names())
            has_shuffle = panel_config.get("shuffle_button", True)
            has_loop = panel_config.get("loop_button", True)
            has_playlist = panel_config.get("playlist_button", True) and playlist_count > 1

        # Calculate total button count
        button_count = 3 + sum([has_shuffle, has_loop, has_playlist])
        self._button_count = button_count
        self._use_labels = button_count == 6

        # Labels for 6-button mode
        # Row 1: Previous, Pause/Play, Next
        # Row 2: Playlist, Shuffle, Loop
        LABEL_PREVIOUS = "previous" if self._use_labels else None
        LABEL_PLAY = "play" if self._use_labels else None
        LABEL_NEXT = "next" if self._use_labels else None
        LABEL_PLAYLIST = "playlist" if self._use_labels else None
        LABEL_SHUFFLE = "shuffle" if self._use_labels else None
        LABEL_LOOP = "loop" if self._use_labels else None

        # Core buttons (always present)
        self.previous_btn = discord.ui.Button(
            emoji="⏮", custom_id="panel:previous",
            style=discord.ButtonStyle.secondary,
            label=LABEL_PREVIOUS
        )
        self.playpause_btn = discord.ui.Button(
            emoji="▶️", custom_id="panel:playpause",
            style=discord.ButtonStyle.secondary,
            label=LABEL_PLAY
        )
        self.skip_btn = discord.ui.Button(
            emoji="⏭", custom_id="panel:skip",
            style=discord.ButtonStyle.secondary,
            label=LABEL_NEXT
        )

        buttons = [self.previous_btn, self.playpause_btn, self.skip_btn]

        # Optional buttons based on config
        self.shuffle_btn = None
        self.loop_btn = None
        self.playlist_btn = None

        if has_playlist:
            self.playlist_btn = discord.ui.Button(
                emoji="🇵", custom_id="panel:playlist",
                style=discord.ButtonStyle.secondary,
                label=LABEL_PLAYLIST
            )

        if has_shuffle:
            self.shuffle_btn = discord.ui.Button(
                emoji="🔀", custom_id="panel:shuffle",
                style=discord.ButtonStyle.secondary,
                label=LABEL_SHUFFLE
            )

        if has_loop:
            self.loop_btn = discord.ui.Button(
                emoji="🔂", custom_id="panel:loop",
                style=discord.ButtonStyle.secondary,
                label=LABEL_LOOP
            )

        # Append in column-aligned order: Playlist, Shuffle, Loop
        if self.playlist_btn:
            buttons.append(self.playlist_btn)
        if self.shuffle_btn:
            buttons.append(self.shuffle_btn)
        if self.loop_btn:
            buttons.append(self.loop_btn)

        # Assign callbacks to buttons
        self.previous_btn.callback = self.previous_button
        self.playpause_btn.callback = self.playpause_button
        self.skip_btn.callback = self.skip_button
        if self.shuffle_btn:
            self.shuffle_btn.callback = self.shuffle_button
        if self.loop_btn:
            self.loop_btn.callback = self.loop_button
        if self.playlist_btn:
            self.playlist_btn.callback = self.playlist_button

        # Distribute into rows: ≤5 = single row, 6 = split 3/3
        if len(buttons) <= 5:
            row = discord.ui.ActionRow()
            for btn in buttons:
                row.add_item(btn)
            return [row]
        else:
            # Split 3/3 for 6 buttons
            row1 = discord.ui.ActionRow()
            row2 = discord.ui.ActionRow()
            for i, btn in enumerate(buttons):
                if i < 3:
                    row1.add_item(btn)
                else:
                    row2.add_item(btn)
            return [row1, row2]

    # --- Helper methods ---

    def msg(self, key: str, **kwargs) -> str:
        """Shorthand for config_manager.msg()."""
        if self.bot and hasattr(self.bot, 'config_manager'):
            return self.bot.config_manager.msg(key, **kwargs)
        from utils.config import DEFAULT_MESSAGES
        entry = DEFAULT_MESSAGES.get(key, {})
        template = entry.get("text", key) if isinstance(entry, dict) else entry
        try:
            return template.format(**kwargs)
        except KeyError:
            return template

    def is_enabled(self, key: str) -> bool:
        """Check if a message should be shown."""
        if self.bot and hasattr(self.bot, 'config_manager'):
            return self.bot.config_manager.is_enabled(key)
        from utils.config import DEFAULT_MESSAGES
        entry = DEFAULT_MESSAGES.get(key, {})
        return entry.get("enabled", True) if isinstance(entry, dict) else True

    async def _delete_followup(self, msg: discord.Message, delay: float) -> None:
        """Delete a followup message after delay.

        IMPORTANT: For component interactions (buttons), do NOT use
        delete_original_response() - it deletes the panel message, not the
        ephemeral response. Always delete the specific message object returned
        by followup.send(wait=True).
        """
        try:
            await asyncio.sleep(delay)
            await msg.delete()
        except asyncio.CancelledError:
            pass  # Shutdown during wait
        except discord.NotFound:
            pass  # Already deleted
        except discord.HTTPException:
            pass

    async def respond(self, interaction: discord.Interaction, key: str, **kwargs) -> None:
        """Send message if enabled, otherwise acknowledge silently.

        NOTE: This is for COMPONENT interactions (panel buttons).
        For slash commands, use ResponseMixin.respond() instead.

        Component interactions require special handling:
        - delete_original_response() deletes THE PANEL (the message containing the button)
        - Must use followup.send(wait=True) and delete the returned message directly
        """
        if not self.is_enabled(key):
            # Silent acknowledgment - just defer, no delete needed
            # For components with thinking=False (default), defer is silent
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            # DO NOT call delete_original_response() - it deletes the panel!
            return

        text = self.msg(key, **kwargs)

        ui_config = self.bot.config_manager.get("ui", {}) if self.bot else {}
        timeout = ui_config.get("brief_auto_delete", 10)
        delete_after = timeout if timeout > 0 else None

        if not interaction.response.is_done():
            await interaction.response.send_message(text, ephemeral=True, delete_after=delete_after)
        else:
            # For followup path, must delete the specific message, not "original response"
            msg = await interaction.followup.send(text, ephemeral=True, wait=True)
            if delete_after:
                task = asyncio.create_task(self._delete_followup(msg, delete_after))
                _cleanup_tasks.add(task)
                task.add_done_callback(_cleanup_tasks.discard)

    def get_player(self, interaction: discord.Interaction) -> mafic.Player | None:
        """Get player from interaction's guild."""
        vc = interaction.guild.voice_client
        if vc and isinstance(vc, mafic.Player):
            return vc
        return None

    def _get_player_by_guild(self, guild_id: int) -> mafic.Player | None:
        """Get player for guild, or None."""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return None
        vc = guild.voice_client
        return vc if vc and isinstance(vc, mafic.Player) else None

    def _get_progress_bar_length(self) -> int:
        """Get progress bar length based on button count."""
        return PROGRESS_BAR_LENGTHS.get(self._button_count, 14)

    def _get_info_line_width(self) -> int:
        """Get max character width for info line based on button count."""
        return INFO_LINE_WIDTH_LIMITS.get(self._button_count, 42)

    async def _check_panel_deleted(self, interaction: discord.Interaction) -> bool:
        """Validate panel before button interaction. Returns True if caller should abort. Side effects: sends panel_deleted or panel_orphaned message, deletes orphaned panels (wrong ID), repairs panel.json (empty IDs)."""
        if interaction.message is None:
            await self.respond(interaction, "panel_deleted")
            return True

        # If clicked panel doesn't match tracked panel, delete the orphaned one
        if self.bot.panel_manager.message_id and interaction.message.id != self.bot.panel_manager.message_id:
            try:
                await interaction.message.delete()
                logger.info("deleted orphaned panel")
            except discord.HTTPException:
                pass
            await self.respond(interaction, "panel_orphaned")

            # Auto-recover: ensure a panel exists (creates one if tracked panel is also gone)
            try:
                music_cog = self.bot.get_cog("Music")
                if music_cog:
                    await music_cog.ensure_panel(interaction, interaction.guild_id)
            except Exception as e:
                logger.warning(f"failed to recover panel after orphan cleanup: {e}")

            return True

        # Repair panel.json if empty (orphaned panel scenario)
        # Set IDs directly (not set_message) so _panel_created_at stays 0 and triggers recreation
        if not self.bot.panel_manager.channel_id or not self.bot.panel_manager.message_id:
            self.bot.panel_manager.channel_id = interaction.message.channel.id
            self.bot.panel_manager.message_id = interaction.message.id
            await self.bot.panel_manager.save()
            logger.info(f"recovered orphaned panel in #{interaction.message.channel.name}")

        return False

    async def _safe_edit_message(self, interaction: discord.Interaction) -> bool:
        """Edit message with error recovery. Returns True if successful."""
        try:
            await interaction.response.edit_message(view=self)
            return True
        except discord.HTTPException as e:
            if e.code in (30046, 10008):
                # Edit limit or message deleted - recreate panel
                self.bot.panel_manager.invalidate_cache()
                music_cog = self.bot.get_cog("Music")
                if music_cog:
                    await music_cog.update_panel(interaction.guild_id)
            return False

    def _user_in_bot_vc(self, interaction: discord.Interaction) -> bool:
        """Check if user is in the same VC as bot. Silent — no message on denial.

        Returns False when bot is not connected (no standby bypass).
        Used by: skip, previous, play/pause buttons.
        See also: _check_vc() for message-sending denial (shuffle, loop, playlist buttons).
        """
        player = self.get_player(interaction)
        if not player:
            return False
        if not interaction.user.voice:
            return False
        return interaction.user.voice.channel == player.channel

    async def _check_permission(self, interaction: discord.Interaction, action: str) -> bool:
        """Check if user has role permission for this action.

        Returns True if allowed, False if denied (and sends error message).
        """
        perm_manager = getattr(self.bot, 'permission_manager', None)
        if not perm_manager:
            return True

        if not perm_manager.check_permission(interaction, action):
            await self.respond(interaction, "no_permission")
            return False
        return True

    async def _check_vc(self, interaction: discord.Interaction) -> bool:
        """Check if user is in same VC as bot. Returns True if allowed, False if denied.

        Sends not_in_vc or wrong_vc message on denial (respects messages.yaml enabled flag).
        Skips check when bot isn't connected (standby bypass — allows pre-configuration).

        Used by: shuffle, loop, playlist buttons.
        See also: _user_in_bot_vc() for silent rejection (skip, previous, play/pause buttons).
        See also: ResponseMixin._check_same_vc() for slash command equivalent (no standby bypass).
        """
        player = self.get_player(interaction)
        if not player:
            return True  # Bot not connected — standby bypass
        if not interaction.user.voice:
            await self.respond(interaction, "not_in_vc")
            return False
        if not player.channel:
            return True  # Treat as not connected — standby bypass
        if interaction.user.voice.channel != player.channel:
            await self.respond(interaction, "wrong_vc", channel=player.channel.mention)
            return False
        return True

    # --- Content building ---

    def build_header_content(self, guild_id: int) -> str:
        """Build header content (Now Serving line)."""
        music_cog = self.bot.get_cog("Music") if self.bot else None
        if not music_cog:
            return self.msg("music_unavailable")

        queue = music_cog.get_queue(guild_id)
        drinks = music_cog.get_drink_counter(guild_id)

        # Change header when song repeat is on or single-song playlist
        is_single_track = len(queue.active_tracks) == 1 if queue.active_tracks else False
        header = "### now serving only:" if queue.song_loop or is_single_track else "### now serving:"

        if queue.current or queue.current_metadata:
            current_title, _ = queue.get_current_display()
            # Get thresholds based on button count
            truncate_threshold = TITLE_TRUNCATE_THRESHOLDS.get(self._button_count, 34)
            heading_threshold = HEADING_SIZE_THRESHOLDS.get(self._button_count, 23)
            # Truncate very long titles
            if len(current_title) > truncate_threshold:
                current_title = current_title[:truncate_threshold - 3] + "..."
            # Use smaller heading for long titles
            if len(current_title) > heading_threshold:
                heading = "###"
            else:
                heading = "##"
            current_title = escape_markdown(current_title)
            return f"{header}\n{heading} {drinks.get_emoji(0)}{current_title}"
        else:
            return f"{header}\n[nothing]"

    def build_progress_content(self, guild_id: int, player: mafic.Player | None = None) -> str:
        """Build progress bar content."""
        panel_config = self.bot.config_manager.get("panel", {}) if self.bot else {}
        bar_length = self._get_progress_bar_length()

        if player and player.current:
            return build_progress_bar(
                player.position or 0,
                player.current.length or 0,
                panel_config,
                bar_length
            )
        else:
            empty_char = panel_config.get("progress_bar_empty", "⬛")
            return empty_char * bar_length

    def build_body_content(self, guild_id: int, player: mafic.Player | None = None) -> str:
        """Build body content (coming up, previous track sections)."""
        music_cog = self.bot.get_cog("Music") if self.bot else None
        if not music_cog:
            return ":"  # Fallback for missing music cog

        queue = music_cog.get_queue(guild_id)
        drinks = music_cog.get_drink_counter(guild_id)

        # If nothing playing, show hint instead of queue content
        if not queue.current and (not player or not player.current):
            return "press `▶️play` to start"

        # Get truncation threshold based on button count
        coming_up_threshold = COMING_UP_TRUNCATE_THRESHOLDS.get(self._button_count, 40)

        lines = []

        # 1. Coming Up (always show, behavior depends on loop mode or single-song playlist)
        is_single_track = len(queue.active_tracks) == 1 if queue.active_tracks else False
        if (queue.song_loop or is_single_track) and queue.current:
            # Loop ON: show current track to indicate repeat
            current_title, _ = queue.get_current_display()
            if len(current_title) > coming_up_threshold:
                current_title = current_title[:coming_up_threshold - 3] + "..."
            lines.append(f"### {drinks.get_emoji(1)}coming up:")
            lines.append(f"  • {current_title}")
        elif queue.tracks:
            # Show next tracks based on mode
            lines.append(f"### {drinks.get_emoji(1)}coming up:")

            # Start from next track (or beginning if orphaned)
            start_index = 0 if queue.current_index is None else queue.current_index + 1
            active = queue.active_tracks

            if queue.shuffle:
                # Shuffle: show up to 3 remaining tracks (no wrap-around)
                remaining = min(3, len(active) - start_index)

                for i in range(remaining):
                    index = start_index + i  # No modulo
                    track_title, _ = queue.get_track_display(active[index])
                    if len(track_title) > coming_up_threshold:
                        track_title = track_title[:coming_up_threshold - 3] + "..."
                    track_title = escape_markdown(track_title)
                    lines.append(f"  • {track_title}")

                # Show reshuffle indicator when near end (can't show full 3 tracks)
                # Only for 4+ song playlists (small playlists reshuffle constantly)
                if len(active) >= 4 and remaining < 3:
                    lines.append("  [reshuffle]")
            else:
                # Normal: always show 3 with modulo wrap
                for i in range(3):
                    index = (start_index + i) % len(active)
                    track_title, _ = queue.get_track_display(active[index])
                    if len(track_title) > coming_up_threshold:
                        track_title = track_title[:coming_up_threshold - 3] + "..."
                    track_title = escape_markdown(track_title)
                    lines.append(f"  • {track_title}")

        # 2. Previous (only when loop is OFF, not single-track, and index exists)
        if not queue.song_loop and not is_single_track and queue.current_index is not None and queue.tracks:
            active = queue.active_tracks
            prev_index = (queue.current_index - 1) % len(active)
            prev_title, _ = queue.get_track_display(active[prev_index])
            if len(prev_title) > coming_up_threshold:
                prev_title = prev_title[:coming_up_threshold - 3] + "..."
            prev_title = escape_markdown(prev_title)
            lines.append(f"### {drinks.get_emoji(-1)}previous:")
            lines.append(f"  • {prev_title}")

        # Fallback if empty (shouldn't happen during playback)
        return "\n".join(lines) if lines else ":"

    def build_info_content(self, guild_id: int) -> str:
        """Build info line with dynamic width and smart truncation."""
        if not self.bot:
            return ":"

        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            return ":"

        queue = music_cog.get_queue(guild_id)
        max_width = self._get_info_line_width()

        # Collect album/playlist and artist
        album = None
        artist = None

        # Priority 1: Album from metadata
        if queue.current_metadata:
            album = queue.current_metadata.get("album")

        # Priority 2: Playlist name (fallback)
        if not album and queue.display_playlist_name:
            album = queue.display_playlist_name

        # Always try to get artist
        if queue.current:
            _, artist = queue.get_current_display()

        # Escape for Discord markdown display
        if album:
            album = escape_markdown(album)
        if artist:
            artist = escape_markdown(artist)

        # Fallback if neither exists
        if not album and not artist:
            panel_config = self.bot.config_manager.get("panel", {})
            return panel_config.get("info_fallback_message", "mixing drinks and changing lives")

        # Case 1: Only album/playlist
        if album and not artist:
            if len(album) > max_width:
                return album[:max_width - 3] + "..."
            return album

        # Case 2: Only artist
        if artist and not album:
            if len(artist) > max_width:
                return artist[:max_width - 3] + "..."
            return artist

        # Case 3: Both - try single line first
        separator = " • "
        single_line = f"{album}{separator}{artist}"

        if len(single_line) <= max_width:
            return single_line

        # Doesn't fit on one line - for non-3-button configs, try truncating album
        if self._button_count != 3:
            album_limit = ALBUM_TRUNCATE_LIMITS.get(self._button_count, 28)
            truncated_album = album if len(album) <= album_limit else album[:album_limit - 3] + "..."
            single_line_truncated = f"{truncated_album}{separator}{artist}"
            if len(single_line_truncated) <= max_width:
                return single_line_truncated

        # Still doesn't fit - split to two lines, truncate each
        album_line = album if len(album) <= max_width else album[:max_width - 3] + "..."
        artist_line = artist if len(artist) <= max_width else artist[:max_width - 3] + "..."

        return f"{album_line}\n{artist_line}"

    def update_button_states(self, guild_id: int) -> None:
        """Update button styles/emojis/labels based on current state."""
        music_cog = self.bot.get_cog("Music") if self.bot else None
        if not music_cog:
            return

        queue = music_cog.get_queue(guild_id)
        player = self._get_player_by_guild(guild_id)

        # Play/pause - show play icon when paused OR nothing playing
        is_playing = player and player.current and not player.paused
        self.playpause_btn.emoji = "⏸" if is_playing else "▶️"
        if self._use_labels:
            self.playpause_btn.label = "pause" if is_playing else "play"

        # Shuffle (may not exist if disabled in config)
        if self.shuffle_btn:
            self.shuffle_btn.style = discord.ButtonStyle.primary if queue.shuffle else discord.ButtonStyle.secondary

        # Loop (may not exist if disabled in config) - simple toggle like shuffle
        if self.loop_btn:
            self.loop_btn.style = (
                discord.ButtonStyle.primary if queue.song_loop
                else discord.ButtonStyle.secondary
            )

    # --- Button callbacks ---

    async def previous_button(self, interaction: discord.Interaction) -> None:
        """Go to previous track."""
        if await self._check_panel_deleted(interaction):
            return
        if not await self._check_permission(interaction, "previous"):
            return

        # Silently ignore if user not in bot's VC
        if not self._user_in_bot_vc(interaction):
            await self._safe_edit_message(interaction)
            return

        player = self.get_player(interaction)
        music_cog = self.bot.get_cog("Music") if self.bot else None
        if not music_cog:
            await self._safe_edit_message(interaction)
            return

        await interaction.response.defer()

        guild_id = interaction.guild_id

        # Serialize playback operations to prevent race conditions
        async with music_cog._get_playback_lock(guild_id):
            # Re-validate after acquiring lock (state may have changed)
            player = self.get_player(interaction)
            if not player or not player.connected:
                return

            queue = music_cog.get_queue(guild_id)

            # Nothing playing - do nothing
            if not player.current:
                return

            # When loop is ON, restart current song (like skip does)
            if queue.song_loop and queue.current:
                success = await music_cog.play_track(player, queue.current, queue.playlist_name)
                # Note: Panel update handled by on_track_start (which captures correct metadata)
                if success:
                    logger.info(f"{interaction.user.display_name} went to previous track")
                else:
                    await self.respond(interaction, "track_play_error")
            else:
                # Normal mode: go back in history
                prev = queue.previous_track()
                if prev:
                    success = await music_cog.play_track(player, prev, queue.playlist_name)
                    # Note: Panel update handled by on_track_start (which captures correct metadata)
                    if success:
                        # Only decrement drink counter if not looping same song
                        drinks = music_cog.get_drink_counter(guild_id)
                        drinks.decrement()
                        logger.info(f"{interaction.user.display_name} went to previous track")
                    else:
                        await self.respond(interaction, "track_play_error")
                else:
                    await self.respond(interaction, "history_empty")

    async def playpause_button(self, interaction: discord.Interaction) -> None:
        """Toggle play/pause, or start playback if not connected."""
        if await self._check_panel_deleted(interaction):
            return
        if not await self._check_permission(interaction, "play"):
            return

        player = self.get_player(interaction)

        if not player:
            # No player - attempt to start playback
            music_cog = self.bot.get_cog("Music") if self.bot else None
            if not music_cog:
                await self.respond(interaction, "music_unavailable")
                return

            # Validate BEFORE deferring
            if not interaction.user.voice:
                await self.respond(interaction, "not_in_vc")
                return

            user_channel = interaction.user.voice.channel
            permissions = user_channel.permissions_for(interaction.guild.me)
            if not permissions.connect or not permissions.speak:
                await self.respond(interaction, "need_vc_permissions")
                return

            # Check Lavalink before connecting to voice (same check as /play command)
            if not self.bot.pool or not self.bot.pool.nodes:
                await self.respond(interaction, "music_unavailable")
                return

            # Check playlists available BEFORE connecting to voice
            guild_id = interaction.guild_id
            queue = music_cog.get_queue(guild_id)
            if not queue.playlist_name:
                names = self.bot.library.get_playlist_names()
                if not names:
                    await self.respond(interaction, "no_playlists")
                    return

            await interaction.response.defer()

            try:
                player = await user_channel.connect(cls=mafic.Player, self_deaf=True)
                # Apply saved volume on connect (parity with ensure_voice)
                default_vol = self.bot.config_manager.get("default_volume", 50)
                saved_volume = self.bot.state_manager.get("volume", default_vol)
                await player.set_volume(saved_volume)
            except Exception as e:
                logger.error(f"failed to connect to voice: {e}")
                await self.respond(interaction, "failed_join_vc")
                return

            # Load saved or first available playlist (already checked names exist above)
            if not queue.playlist_name:
                names = self.bot.library.get_playlist_names()
                playlist_name = music_cog._resolve_playlist(names)
                tracks = self.bot.library.get_playlist(playlist_name)
                if not tracks:
                    await self.respond(interaction, "playlist_empty")
                    return
                queue.set_playlist(playlist_name, tracks)
                await queue.load_metadata_cache(self.bot.metadata_cache_path, playlist_name)

            # Restore track from preserved position (after /stop or disconnect)
            if queue.current_index is not None and not queue.current and queue.tracks:
                queue.set_current_track(queue.current_index)

            # If no current index, start from beginning
            if queue.current_index is None and queue.tracks:
                queue.set_current_track(0)

            # Resume if we have a current track but player isn't playing
            if queue.current and not player.current:
                if not await music_cog.play_track(player, queue.current, queue.playlist_name):
                    await self.respond(interaction, "track_play_error")
                return

            # Start playback from current index
            # Note: Panel update handled by on_track_start (which captures correct metadata)
            if not await music_cog.play_next(player, guild_id) and queue.tracks:
                await self.respond(interaction, "track_play_error")
            return

        # Player exists - require user in same VC (silent ignore if not)
        if not self._user_in_bot_vc(interaction):
            await self._safe_edit_message(interaction)
            return

        # Defer to acknowledge interaction
        await interaction.response.defer()

        # Re-fetch player after await (stale state pattern)
        player = self.get_player(interaction)
        if not player or not player.connected:
            return  # Player disconnected during defer

        # Normal pause/resume logic
        music_cog = self.bot.get_cog("Music")
        if not music_cog:
            return

        guild_id = interaction.guild_id

        # Serialize playback operations to prevent race conditions
        async with music_cog._get_playback_lock(guild_id):
            # Re-validate after acquiring lock (state may have changed)
            player = self.get_player(interaction)
            if not player or not player.connected:
                return

            # If nothing playing, start from queue
            if not player.current:
                queue = music_cog.get_queue(guild_id)
                track = queue.current
                if not track and queue.tracks:
                    queue.set_current_track(0)
                    track = queue.current
                if track:
                    success = await music_cog.play_track(player, track, queue.playlist_name)
                    if success:
                        logger.info(f"started by {interaction.user.display_name}")
                    else:
                        await self.respond(interaction, "track_play_error")
                return

            if player.paused:
                await player.resume()
                logger.info(f"resumed by {interaction.user.display_name}")
                # Clear manual pause flag so auto-resume works in future
                if state := music_cog.pause_states.get(guild_id):
                    state.was_paused_by_user = False
                music_cog._start_progress_update(guild_id)
            else:
                await player.pause()
                logger.info(f"paused by {interaction.user.display_name}")
                # Mark as manual pause to prevent auto-resume
                from cogs.music import VoiceSessionState
                state = music_cog.pause_states.setdefault(guild_id, VoiceSessionState())
                state.was_paused_by_user = True

            # Schedule debounced panel update (coalesces with other updates)
            await music_cog.update_panel(guild_id)

    async def skip_button(self, interaction: discord.Interaction) -> None:
        """Skip to next track."""
        if await self._check_panel_deleted(interaction):
            return
        if not await self._check_permission(interaction, "skip"):
            return

        # Silently ignore if user not in bot's VC
        if not self._user_in_bot_vc(interaction):
            await self._safe_edit_message(interaction)
            return

        player = self.get_player(interaction)
        if not player or not player.current:
            await self._safe_edit_message(interaction)
            return

        await interaction.response.defer()

        # Manually advance queue (like /skip command does)
        guild_id = interaction.guild_id
        music_cog = self.bot.get_cog("Music") if self.bot else None
        if not music_cog:
            return

        # Serialize playback operations to prevent race conditions
        async with music_cog._get_playback_lock(guild_id):
            # Re-validate after acquiring lock (state may have changed)
            player = self.get_player(interaction)
            if not player or not player.connected:
                return

            queue = music_cog.get_queue(guild_id)
            drinks = music_cog.get_drink_counter(guild_id)

            # Advance to next track
            next_track = queue.advance_track()
            if next_track:
                # Play next track directly (panel update handled by on_track_start event)
                if await music_cog.play_track(player, next_track, queue.playlist_name):
                    # Only increment drink emoji if not looping same song
                    if not queue.song_loop:
                        drinks.increment()
                    logger.info(f"{interaction.user.display_name} skipped to next track")
                else:
                    await self.respond(interaction, "track_play_error")
            else:
                # Queue empty - stop playback
                await player.stop()

    async def shuffle_button(self, interaction: discord.Interaction) -> None:
        """Toggle shuffle mode via panel button.

        Acquires playback lock before enable/disable to prevent races with
        concurrent skip/previous/on_track_end operations. Captures shuffle_state
        inside lock, uses it outside for state save, logging, and panel update.
        No player re-validation needed (standby bypass allows operation without player).
        """
        if await self._check_panel_deleted(interaction):
            return
        if not await self._check_permission(interaction, "shuffle"):
            return
        if not await self._check_vc(interaction):
            return

        music_cog = self.bot.get_cog("Music") if self.bot else None
        if not music_cog:
            await self.respond(interaction, "music_unavailable")
            return

        await interaction.response.defer()

        guild_id = interaction.guild_id

        async with music_cog._get_playback_lock(guild_id):
            queue = music_cog.get_queue(guild_id)
            # Toggle state and perform action
            if queue.shuffle:
                queue.disable_shuffle()
                shuffle_state = False
            else:
                queue.enable_shuffle()
                shuffle_state = True

        # Outside lock (safe)
        self.bot.state_manager.set("shuffle", shuffle_state)
        logger.info(f"shuffle {'enabled' if shuffle_state else 'disabled'} by {interaction.user.display_name}")

        # Schedule debounced panel update (coalesces with other updates)
        await music_cog.update_panel(guild_id)

        # Save state after responding (avoid blocking interaction)
        await self.bot.state_manager.save()

    async def loop_button(self, interaction: discord.Interaction) -> None:
        """Toggle song repeat mode."""
        if await self._check_panel_deleted(interaction):
            return
        if not await self._check_permission(interaction, "loop"):
            return
        if not await self._check_vc(interaction):
            return

        music_cog = self.bot.get_cog("Music") if self.bot else None
        if not music_cog:
            await self.respond(interaction, "music_unavailable")
            return

        await interaction.response.defer()

        guild_id = interaction.guild_id
        queue = music_cog.get_queue(guild_id)

        # Simple toggle like shuffle (song_loop not persisted - resets on restart)
        queue.song_loop = not queue.song_loop
        if queue.song_loop:
            logger.info(f"loop enabled by {interaction.user.display_name}")
        else:
            logger.info(f"loop disabled by {interaction.user.display_name}")

        # Schedule debounced panel update (coalesces with other updates)
        await music_cog.update_panel(guild_id)

    async def playlist_button(self, interaction: discord.Interaction) -> None:
        """Show playlist selector dropdown."""
        if await self._check_panel_deleted(interaction):
            return
        if not await self._check_permission(interaction, "playlist"):
            return
        if not await self._check_vc(interaction):
            return

        library = self.bot.library if self.bot else None
        if not library:
            await self.respond(interaction, "library_unavailable")
            return

        names = library.get_playlist_names()
        if not names:
            await self.respond(interaction, "no_playlists")
            return

        music_cog = self.bot.get_cog("Music") if self.bot else None
        current_playlist = None
        if music_cog:
            queue = music_cog.get_queue(interaction.guild_id)
            current_playlist = queue.playlist_name

        view = PlaylistSelectView(self.bot, names, current_playlist)
        await interaction.response.defer(ephemeral=True)
        view.message = await interaction.followup.send(
            self.msg("select_playlist"),
            view=view,
            ephemeral=True
        )


# Panel tracking
class PanelManager:
    """Tracks the control panel message location and handles recreation.

    The control panel is a persistent Discord message that shows playback status.
    This manager tracks which channel/message it's in so the bot can find and
    update it across restarts.

    Persistence:
    - panel.json stores channel_id and message_id
    - Loaded on startup, saved when panel is created/moved
    - If panel is deleted, IDs are cleared and panel stops updating

    Message caching:
    - _cached_message avoids repeated Discord API calls
    - Cache is invalidated on error, deletion, or recreation

    Recreation strategy:
    - Discord has an edit limit on old messages (error 30046)
    - When hit, delete old panel and create new one in same channel
    - _recreate_lock prevents concurrent recreations from button spam
    - 15-second cooldown prevents recreation loops
    - _panel_created_at tracks age for proactive recreation

    Locks:
    - _recreate_lock: Serializes panel recreation (one at a time)
    - _ensure_panel_lock: Prevents concurrent panel creation
    - _save_lock: Prevents concurrent file writes

    Attributes:
        file_path: Path to panel.json
        channel_id: Discord channel containing the panel (None if not set)
        message_id: Discord message ID of the panel (None if not set)
    """

    def __init__(self, data_path: Path) -> None:
        self.file_path = data_path / "panel.json"
        self.channel_id: int | None = None
        self.message_id: int | None = None
        self._cached_message: discord.PartialMessage | None = None
        self._recreate_lock = asyncio.Lock()
        self._last_recreate: float = 0
        self._panel_created_at: float = 0
        self._ensure_panel_lock = asyncio.Lock()
        self._save_lock = asyncio.Lock()

    async def load(self) -> None:
        """Load panel location from panel.json on startup.

        If file exists and is valid, restores channel_id and message_id.
        On failure, logs warning and leaves IDs as None (panel will be
        created fresh when a command is run).
        """
        if self.file_path.exists():
            try:
                data = await asyncio.to_thread(self._load_json)
                self.channel_id = data.get("channel_id")
                self.message_id = data.get("message_id")
            except Exception as e:
                # Preserve corrupted file for debugging
                backup = self.file_path.with_suffix('.json.bak')
                try:
                    self.file_path.rename(backup)
                    logger.warning(f"panel state corrupt, backed up to {backup.name}: {e}")
                except OSError:
                    logger.warning(f"failed to load panel state: {e}")

    async def save(self) -> None:
        """Save panel location to panel.json.

        Uses atomic temp-file-then-rename pattern to prevent corruption.
        Exceptions are logged but not raised (fire-and-forget pattern).
        """
        async with self._save_lock:
            temp_path = None
            try:
                self.file_path.parent.mkdir(parents=True, exist_ok=True)
                temp_fd, temp_path = tempfile.mkstemp(dir=self.file_path.parent, suffix='.tmp')
                await asyncio.to_thread(self._write_atomic, temp_fd, temp_path)
            except Exception:
                if temp_path:
                    Path(temp_path).unlink(missing_ok=True)
                logger.opt(exception=True).warning("failed to save panel.json")

    def _load_json(self) -> dict:
        with open(self.file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _write_atomic(self, temp_fd: int, temp_path: str) -> None:
        """Synchronous helper for atomic JSON write."""
        # fdopen can fail after mkstemp - close fd manually to prevent leak
        try:
            f = os.fdopen(temp_fd, 'w', encoding='utf-8')
        except Exception:
            os.close(temp_fd)
            raise
        with f:
            json.dump({
                "channel_id": self.channel_id,
                "message_id": self.message_id
            }, f, indent=2)
        Path(temp_path).replace(self.file_path)

    async def get_message(self, bot: commands.Bot) -> discord.PartialMessage | None:
        """Get the panel message (cached for performance). Returns a PartialMessage for edit/delete without READ_MESSAGE_HISTORY. Uses local object construction (no API call)."""
        if not self.channel_id or not self.message_id:
            return None

        # Return cached message if available and IDs match
        if (self._cached_message and
            self._cached_message.id == self.message_id and
            self._cached_message.channel.id == self.channel_id):
            return self._cached_message

        # Create PartialMessage (no API call, no READ_MESSAGE_HISTORY needed)
        try:
            channel = bot.get_channel(self.channel_id)
            if channel:
                self._cached_message = channel.get_partial_message(self.message_id)
                return self._cached_message
        except Exception:
            self._cached_message = None
            logger.warning("failed to fetch panel")

        return None

    def invalidate_cache(self) -> None:
        """Clear cached message (call after recreate or on error)."""
        self._cached_message = None

    async def set_message(self, message: discord.Message) -> None:
        """Register a new panel message and persist to panel.json.

        Called when creating a new panel. Stores IDs, caches message object,
        records creation time (for age-based recreation), and saves to disk.
        """
        self.channel_id = message.channel.id
        self.message_id = message.id
        self._cached_message = message  # Cache immediately
        self._panel_created_at = asyncio.get_running_loop().time()  # Track creation time
        await self.save()

    async def recreate_panel(self, bot: commands.Bot, view: discord.ui.LayoutView) -> discord.Message | None:
        """Delete old panel and create new one in the same channel. Used when hitting Discord's old-message edit limit (error 30046). Returns the new message, or None if recreation failed. Uses lock to serialize recreations and 15-second cooldown to prevent loops."""
        async with self._recreate_lock:
            # Check cooldown to prevent recreation loop (queued tasks deleting each other's work)
            now = asyncio.get_running_loop().time()
            if now - self._last_recreate < 15.0:
                # Recently recreated - return current panel instead
                return await self.get_message(bot)

            if not self.channel_id:
                return None

            channel = bot.get_channel(self.channel_id)
            if not channel:
                return None

            # Delete old message (best effort, may already be gone)
            # Use PartialMessage - no API call, no READ_MESSAGE_HISTORY needed
            if self.message_id:
                try:
                    old_msg = channel.get_partial_message(self.message_id)
                    await old_msg.delete()
                    logger.debug("deleted old panel")
                except discord.NotFound:
                    logger.debug("old panel already deleted")
                except discord.HTTPException as e:
                    logger.warning(f"couldn't delete old panel: {e}")
                except Exception as e:
                    logger.warning(f"unexpected error deleting old panel: {e}")

            self.invalidate_cache()  # Clear cache after deletion attempt

            # Create new panel in same channel (LayoutView only, no embed)
            try:
                new_msg = await channel.send(view=view)
                await self.set_message(new_msg)
                self._last_recreate = now  # Update cooldown timestamp
                logger.info(f"recreated panel in #{channel.name}")
                return new_msg
            except discord.HTTPException as e:
                logger.error(f"failed to recreate panel: {e}")
                return None
