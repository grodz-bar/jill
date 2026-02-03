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

"""Permission system for Jill."""

import asyncio
import functools
import os
from pathlib import Path
from typing import Any, Callable

import discord
import yaml
from loguru import logger


# =============================================================================
# DEFAULT PERMISSIONS SCHEMA
# =============================================================================
# Role-based permission system with three tiers:
#
#   customer  - Available to everyone (no role required)
#   bartender - Requires bartender_role_id role OR admin permissions
#   owner     - Requires manage_guild or administrator permission
#
# Fields:
#   enabled          - If False, all permissions bypass (everyone can use everything)
#   bartender_role_id - Discord role ID (get via Developer Mode > right-click role)
#   tiers            - Maps tier name to list of command names
#
# Commands not listed in any tier default to "customer" (most permissive).
# Admins always have access to all tiers.
# =============================================================================

DEFAULT_PERMISSIONS = {
    "enabled": False,
    "bartender_role_id": None,
    "tiers": {
        "customer": ["queue", "playlists", "np"],
        "bartender": [
            "play", "pause", "skip", "previous", "stop",
            "seek", "shuffle", "loop", "playlist", "volume"
        ],
        "owner": ["rescan"]
    }
}


class PermissionManager:
    """Manages role-based permission checks for commands.

    The permission system is optional - when disabled, all commands are available
    to everyone. When enabled, commands are restricted based on tier assignments.

    Tier hierarchy:
    - customer: No restrictions (default for unlisted commands)
    - bartender: Requires configured role OR admin permissions
    - owner: Requires manage_guild or administrator permission

    Configuration loaded from permissions.yaml, with env var overrides:
    - ENABLE_PERMISSIONS=true enables the system
    - BARTENDER_ROLE_ID=123 sets the bartender role

    Usage:
        if perm_manager.check_permission(interaction, "play"):
            # User allowed to use /play
        else:
            # Send "no permission" message

    Attributes:
        config_path: Path to permissions.yaml
        enabled: Whether permission checking is active
        bartender_role_id: Discord role ID for bartender tier (None if not set)
        tiers: Dict mapping tier names to command lists
    """

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path / "permissions.yaml"
        self.enabled = False
        self.bartender_role_id: int | None = None
        self.tiers: dict[str, list[str]] = {}

    async def load(self) -> None:
        """Load permissions from permissions.yaml.

        Creates default file if missing. Applies environment variable overrides
        after loading YAML. Logs whether permissions are enabled/disabled.
        """
        if not self.config_path.exists():
            await self._create_default()

        try:
            content = await asyncio.to_thread(self.config_path.read_text, encoding='utf-8')
            config = yaml.safe_load(content) or {}

            self.enabled = config.get("enabled", False)
            self.bartender_role_id = config.get("bartender_role_id")
            self.tiers = config.get("tiers", DEFAULT_PERMISSIONS["tiers"])

            # Environment variables override YAML
            if os.getenv("ENABLE_PERMISSIONS", "").lower() == "true":
                self.enabled = True

            if bartender_id := os.getenv("BARTENDER_ROLE_ID"):
                try:
                    self.bartender_role_id = int(bartender_id)
                except ValueError:
                    logger.warning(f"invalid bartender_role_id: {bartender_id}")

            if self.enabled:
                logger.info("permissions enabled")
                if not self.bartender_role_id:
                    logger.warning("bartender role not configured")
            else:
                logger.info("permissions not enabled")

        except Exception:
            logger.opt(exception=True).error("failed to load permissions")
            self.enabled = False
            self.tiers = DEFAULT_PERMISSIONS["tiers"]

    async def _create_default(self) -> None:
        """Create default permissions file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        content = """# Jill Permission System
# Set enabled: true to activate role-based permissions

enabled: false

# Discord role ID for Bartender tier
# Get this by enabling Developer Mode and right-clicking the role
bartender_role_id: null

# Command tier assignments (only these 3 tiers are supported)
# customer: Available to everyone
# bartender: Requires bartender role
# owner: Requires admin/manage_guild permission
# Move commands between tiers as needed
tiers:
  customer:
    - queue
    - playlists
    - np
  bartender:
    - play
    - pause
    - skip
    - previous
    - stop
    - seek
    - shuffle
    - loop
    - playlist
    - volume
  owner:
    - rescan
"""
        await asyncio.to_thread(self.config_path.write_text, content, encoding='utf-8')
        logger.debug(f"generated {self.config_path.name}")

    def get_tier(self, command_name: str) -> str:
        """Get the permission tier for a command.

        Args:
            command_name: Slash command name (e.g., "play", "rescan")

        Returns:
            Tier name: "customer", "bartender", or "owner".
            Returns "customer" if command not found in any tier.
        """
        for tier, commands in self.tiers.items():
            if command_name in commands:
                return tier
        return "customer"  # Default to most permissive

    def check_permission(
        self,
        interaction: discord.Interaction,
        command_name: str
    ) -> bool:
        """Check if user has permission to use a command.

        Args:
            interaction: Discord interaction containing user info
            command_name: Slash command name to check

        Returns:
            True if user is allowed, False if denied.
            Always returns True when permissions are disabled.
        """
        # Disabled = everyone has access (no logging)
        if not self.enabled:
            return True

        tier = self.get_tier(command_name)
        member = interaction.user

        # Customer tier - everyone
        if tier == "customer":
            logger.debug(f"{command_name} allowed for {member.display_name} (customer)")
            return True

        # Owner tier - admins only
        if tier == "owner":
            if member.guild_permissions.manage_guild or member.guild_permissions.administrator:
                logger.debug(f"{command_name} allowed for {member.display_name} (admin)")
                return True
            logger.debug(f"{command_name} denied for {member.display_name} (requires admin)")
            return False

        # Bartender tier - bartender role or admin
        if tier == "bartender":
            # Admins always have access
            if member.guild_permissions.manage_guild or member.guild_permissions.administrator:
                logger.debug(f"{command_name} allowed for {member.display_name} (admin)")
                return True

            # Check if bartender role is configured
            if not self.bartender_role_id:
                logger.debug(f"{command_name} denied for {member.display_name} (bartender role not set)")
                return False

            # Check if user has bartender role
            if self.bartender_role_id in [r.id for r in member.roles]:
                logger.debug(f"{command_name} allowed for {member.display_name} (bartender)")
                return True

            logger.debug(f"{command_name} denied for {member.display_name} (missing bartender role)")
            return False

        # Unknown tier - allow (shouldn't happen)
        return True


def require_permission(command_name: str) -> Callable:
    """Decorator to check permissions before command execution.

    Apply to slash command methods to enforce tier-based access.
    If denied, sends "no_permission" message and returns early.

    Args:
        command_name: Command name to check (e.g., "play", "volume")

    Usage:
        @require_permission("play")
        async def play(self, interaction, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs) -> Any:
            perm_manager = getattr(self.bot, 'permission_manager', None)

            if perm_manager and not perm_manager.check_permission(interaction, command_name):
                config = getattr(self.bot, 'config_manager', None)
                message = config.msg("no_permission") if config else "sorry, that's for staff only"
                delete_after = None
                if config:
                    ui_config = config.get("ui", {})
                    timeout = ui_config.get("brief_auto_delete", 10)
                    delete_after = timeout if timeout > 0 else None
                await interaction.response.send_message(message, ephemeral=True, delete_after=delete_after)
                return

            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator


def require_command_enabled(command_name: str) -> Callable:
    """Decorator to check if command is enabled in settings.yaml.

    Use BEFORE @require_permission so disabled commands fail fast.
    Checks commands.[name]_command setting.
    If disabled, sends command_disabled message and returns early.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs) -> Any:
            config = getattr(self.bot, 'config_manager', None)
            if config:
                commands_config = config.get("commands", {})
                setting_key = f"{command_name}_command"
                if not commands_config.get(setting_key, True):
                    msg = config.msg("command_disabled", command=command_name)
                    ui_config = config.get("ui", {})
                    timeout = ui_config.get("brief_auto_delete", 10)
                    delete_after = timeout if timeout > 0 else None
                    await interaction.response.send_message(msg, ephemeral=True, delete_after=delete_after)
                    return
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator
