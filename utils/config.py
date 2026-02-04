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

"""Configuration management for Jill."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import yaml
from loguru import logger

from utils.holidays import get_active_holiday


# =============================================================================
# DEFAULT SETTINGS SCHEMA
# =============================================================================
# These defaults are used when settings.yaml is missing or incomplete.
# Environment variables can override any setting (see _apply_env_overrides).
#
# Playback Settings:
#   queue_display_size     - Tracks shown per page in /queue command (1-100)
#   playlists_display_size - Playlists shown per page (1-100)
#   inactivity_timeout     - Minutes alone in VC before auto-disconnect (0 = never)
#   default_volume         - Initial volume when joining voice (0-100)
#   auto_rescan            - Scan music folder for new tracks on startup
#   default_playlist       - Override saved playlist on startup (None = use last)
#
# Panel Settings (panel.*):
#   enabled                - Show the control panel embed in Discord
#   color                  - Embed accent color as hex integer (e.g., 0xA03E72)
#   drink_emojis           - List of emojis to rotate through as tracks change
#   drink_emojis_enabled   - Show drink emoji in panel header
#   progress_bar_enabled   - Show visual progress bar
#   progress_bar_filled    - Emoji for filled portion of progress bar
#   progress_bar_empty     - Emoji for empty portion of progress bar
#   progress_update_interval - Seconds between progress bar updates (10-3600)
#   info_fallback_message  - Text shown when no track info available
#   shuffle_button         - Show shuffle toggle button on panel
#   loop_button            - Show loop toggle button on panel
#   playlist_button        - Show playlist selector button on panel
#   update_debounce_ms     - Milliseconds to wait before updating panel (batches rapid changes)
#   recreate_interval      - Minutes before recreating panel (refreshes Discord embed)
#
# Command Settings (commands.*):
#   shuffle_command        - Enable /shuffle slash command
#   loop_command           - Enable /loop slash command
#   rescan_command         - Enable /rescan slash command (admin)
#
# UI Settings (ui.*):
#   extended_auto_delete   - Seconds before auto-deleting pagination views (0 = never)
#   brief_auto_delete      - Seconds before auto-deleting simple responses (0 = never)
#
# Logging Settings (logging.*):
#   level                  - Log verbosity: "minimal", "verbose", or "debug"
# =============================================================================

DEFAULT_SETTINGS = {
    "queue_display_size": 15,
    "playlists_display_size": 15,
    "inactivity_timeout": 10,
    "default_volume": 50,
    "auto_rescan": True,
    "default_playlist": None,
    "presence_enabled": True,  # Show "Listening to [song]" in bot status
    # Panel appearance
    "panel": {
        "enabled": True,  # Set false to disable control panel entirely
        "color": 0xA03E72,
        "drink_emojis": ['🍸', '🍹', '🍻', '🍸', '🍷', '🧉', '🍶', '🥃'],
        "drink_emojis_enabled": True,
        "progress_bar_enabled": True,
        "progress_bar_filled": "🟪",
        "progress_bar_empty": "⬛",
        "progress_update_interval": 15,
        "info_fallback_message": "mixing drinks and changing lives",
        # Button visibility
        "shuffle_button": True,
        "loop_button": True,
        "playlist_button": True,
        # Panel update debounce
        "update_debounce_ms": 500,
        # Automatic panel recreation
        "recreate_interval": 30,
    },
    # Slash command availability
    "commands": {
        "shuffle_command": True,
        "loop_command": True,
        "rescan_command": True,
    },
    # UI behavior
    "ui": {
        "extended_auto_delete": 90,  # seconds, 0 to disable
        "brief_auto_delete": 10,  # seconds, 0 to disable
    },
    # Logging (LOG_LEVEL env var overrides this)
    "logging": {
        "level": "verbose",  # minimal, verbose, debug
    },
}

# =============================================================================
# DEFAULT MESSAGES SCHEMA
# =============================================================================
# Bot responses with per-message enable/disable control.
# Each message has two fields:
#   text    - The message template (supports {variables} for formatting)
#   enabled - Whether to show this message (True) or acknowledge silently (False)
#
# Categories:
#   Voice errors, Permissions, Playback, Search, Queue, Settings,
#   Seek, History, Admin, Errors, Hints
#
# The respond() helper in ResponseMixin checks the enabled flag before sending.
# Disabled messages still acknowledge the interaction (defer + delete) to prevent
# Discord showing "interaction failed" - they just don't show text to the user.
# =============================================================================

DEFAULT_MESSAGES = {
    # Voice errors
    "not_in_vc": {"text": "hey, come sit at the bar first", "enabled": True},
    "wrong_vc": {"text": "wrong bar, i'm at {channel}", "enabled": True},
    "voice_error": {"text": "voice hiccup, hit me again", "enabled": True},
    "need_vc_permissions": {"text": "don't have access to that channel", "enabled": True},
    "failed_join_vc": {"text": "can't get in there", "enabled": True},

    # Permissions
    "no_permission": {"text": "sorry, that's for staff only", "enabled": True},
    "command_disabled": {"text": "`/{command}` isn't available", "enabled": True},

    # Playback
    "nothing_playing": {"text": "bar's quiet right now", "enabled": True},
    "now_playing": {"text": "now serving: **{title}**", "enabled": False},
    "paused": {"text": "taking a break", "enabled": False},
    "resumed": {"text": "back at it", "enabled": False},
    "stopped": {"text": "shift's over, heading out", "enabled": False},
    "already_playing": {"text": "already serving that", "enabled": False},

    # Search
    "song_not_found": {"text": "don't have that one in stock", "enabled": True},
    "track_load_failed": {"text": "can't load that", "enabled": True},
    "track_play_error": {"text": "that broke, try again", "enabled": True},
    "track_selected": {"text": "got it, **{title}** coming up", "enabled": False},

    # Queue
    "queue_empty": {"text": "nothing in the queue", "enabled": True},
    "no_playlists": {"text": "shelves are empty", "enabled": True},
    "playlist_empty": {"text": "that one's empty", "enabled": True},
    "no_playlist_loaded": {"text": "no menu set", "enabled": False},
    "playlist_not_found": {"text": "can't find '{name}'", "enabled": True},
    "playlist_not_found_pick": {"text": "can't find '{name}', pick from available:", "enabled": True},
    "playlist_switched": {"text": "switching to **{playlist}** menu", "enabled": False},

    # Settings
    "volume_set": {"text": "volume set to {level}%", "enabled": False},
    "shuffle_on": {"text": "mixing it up", "enabled": False},
    "shuffle_off": {"text": "keeping it neat", "enabled": False},
    "loop_on": {"text": "i'll keep this one going", "enabled": False},
    "loop_off": {"text": "last pour for this one", "enabled": False},

    # Seek
    "seek_to": {"text": "jumped to {position}% of **{title}**", "enabled": False},
    "cant_seek": {"text": "can't do that for this drink", "enabled": True},

    # History
    "history_empty": {"text": "nothing before this", "enabled": False},

    # Admin
    "rescan_complete": {"text": "found {playlists} playlists and {tracks} songs", "enabled": True},
    "rescan_in_progress": {"text": "a rescan is already running, please wait", "enabled": True},
    "rescan_failed": {"text": "rescan failed, check the logs", "enabled": True},
    "music_unavailable": {"text": "music system's down", "enabled": True},

    # Errors
    "error_generic": {"text": "something broke, try again", "enabled": True},
    "panel_deleted": {"text": "panel's gone", "enabled": True},
    "panel_orphaned": {"text": "that panel's outdated", "enabled": True},
    "library_unavailable": {"text": "music library's offline", "enabled": True},
    "select_playlist": {"text": "pick a playlist:", "enabled": True},

    # Hints
    "shuffle_hint": {"text": "try `/shuffle on` or `/shuffle off`", "enabled": False},
    "loop_hint": {"text": "try `/loop on` or `/loop off`", "enabled": False},
}


def deep_merge(user: dict, defaults: dict) -> dict:
    """Merge user config with defaults, preserving nested structure.

    User values override defaults. For nested dicts, merges recursively.
    Unknown keys (not in defaults) are logged as warnings and ignored.

    Args:
        user: User-provided config from YAML file
        defaults: Default values to use for missing keys

    Returns:
        Merged config dict with all default keys present
    """
    result = defaults.copy()
    for key, value in user.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(value, result[key])
        elif key in defaults:
            result[key] = value
        else:
            logger.warning(f"unknown config key: {key}")
    return result


def load_yaml(path: Path, defaults: dict) -> dict:
    """Load YAML file with defaults and error handling.

    If file doesn't exist or is invalid, returns defaults without error.
    Invalid YAML syntax is logged and defaults are used.

    Args:
        path: Path to YAML file
        defaults: Default values if file missing or invalid

    Returns:
        Loaded config merged with defaults, or defaults on failure
    """
    if not path.exists():
        return defaults.copy()

    try:
        with open(path, 'r', encoding='utf-8') as f:
            user = yaml.safe_load(f) or {}

        if not isinstance(user, dict):
            logger.warning(f"{path.name} invalid, using defaults")
            return defaults.copy()

        return deep_merge(user, defaults)

    except yaml.YAMLError:
        logger.opt(exception=True).error(f"failed to parse {path.name}")
        return defaults.copy()


def save_yaml(path: Path, data: dict, header: str = "") -> None:
    """Save YAML atomically with optional header comment.

    Uses temp-file-then-rename pattern to prevent corruption if the bot
    crashes mid-write. Creates parent directories if they don't exist.

    Args:
        path: Destination file path
        data: Dict to serialize as YAML
        header: Optional comment text to prepend (include # and newlines)
    """
    temp_path = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_fd, temp_path = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
        try:
            f = os.fdopen(temp_fd, 'w', encoding='utf-8')
        except Exception:
            os.close(temp_fd)
            raise
        with f:
            if header:
                f.write(header)
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        Path(temp_path).replace(path)
    except Exception:
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)
        raise


class ConfigManager:
    """Manages bot configuration from settings.yaml and messages.yaml.

    Loads configuration at startup with this priority (highest wins):
    1. DEFAULT_SETTINGS / DEFAULT_MESSAGES (built-in defaults)
    2. settings.yaml / messages.yaml (user customization)
    3. Environment variables (Docker/deployment override)

    Access patterns:
        config_manager.get("key")           # Get setting value
        config_manager.get("key", default)  # Get with fallback
        config_manager.msg("key", **vars)   # Get formatted message
        config_manager.is_enabled("key")    # Check if message should show

    Settings are validated after loading - invalid values are clamped or
    reset to defaults with a warning logged.

    Attributes:
        config_path: Directory containing settings.yaml and messages.yaml
        settings: Loaded settings dict (after validation)
        messages: Loaded messages dict
    """

    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.settings: dict = {}
        self.messages: dict = {}

    async def load(self) -> None:
        """Load settings and messages from YAML, apply env overrides, validate.

        Generates missing config files with default values and header comments.
        """
        # Settings
        settings_path = self.config_path / "settings.yaml"
        self.settings = await asyncio.to_thread(
            load_yaml, settings_path, DEFAULT_SETTINGS
        )

        # Generate if missing
        if not settings_path.exists():
            header = "# Jill Bot Settings\n# Edit these values to customize behavior\n\n"
            await asyncio.to_thread(save_yaml, settings_path, DEFAULT_SETTINGS, header)
            logger.debug(f"generated {settings_path.name}")

        # Messages
        messages_path = self.config_path / "messages.yaml"
        self.messages = await asyncio.to_thread(
            load_yaml, messages_path, DEFAULT_MESSAGES
        )

        if not messages_path.exists():
            header = "# Jill's Responses\n# Customize the bot's personality here\n\n"
            await asyncio.to_thread(save_yaml, messages_path, DEFAULT_MESSAGES, header)
            logger.debug(f"generated {messages_path.name}")

        # Apply environment overrides and validate ranges
        self._apply_env_overrides()
        self._validate_settings()

        logger.debug("config loaded")

    def _validate_settings(self) -> None:
        """Validate and clamp settings after loading from all sources.

        Called after load_yaml and _apply_env_overrides to ensure valid config.

        Validation steps:
        1. Null-restore: YAML "key:" with no value becomes None. Restores defaults
           for null top-level keys and null nested keys in panel/ui/commands/logging sections.
        2. Drink emojis: Ensures drink_emojis is a non-empty list (prevents division
           by zero in DrinkCounter rotation).
        3. Bounded integers: Clamps queue_display_size, playlists_display_size,
           default_volume, inactivity_timeout to valid ranges (logs warning if clamped).
        4. Panel color: Coerces string hex values to int (handles "A03E72",
           "0xA03E72", "#A03E72" formats from env vars or YAML).
        5. Progress interval: Clamps progress_update_interval to 10-3600 range.
        6. Update debounce: Clamps update_debounce_ms to minimum 300ms.
        7. Recreate interval: Clamps recreate_interval to non-negative.

        Logs warnings for any values that needed correction.
        """
        # Restore defaults for null values (YAML "key:" with no value)
        for key in list(self.settings):
            if self.settings[key] is None and key in DEFAULT_SETTINGS:
                self.settings[key] = DEFAULT_SETTINGS[key]
        for section in ("panel", "ui", "commands", "logging"):
            sect = self.settings.get(section)
            defaults = DEFAULT_SETTINGS.get(section, {})
            if isinstance(sect, dict):
                for key in list(sect):
                    if sect[key] is None and key in defaults:
                        sect[key] = defaults[key]

        # Validate drink_emojis is a non-empty list
        panel = self.settings.get("panel", {})
        if isinstance(panel, dict):
            emojis = panel.get("drink_emojis")
            if not isinstance(emojis, list) or not emojis:
                panel["drink_emojis"] = DEFAULT_SETTINGS["panel"]["drink_emojis"]

        # Validate and clamp ranged integers
        validations = {
            "queue_display_size": (1, 50),
            "playlists_display_size": (1, 50),
            "default_volume": (0, 100),
            "inactivity_timeout": (0, None),  # 0+ (no upper bound)
        }
        for key, (min_val, max_val) in validations.items():
            value = self.settings.get(key)
            try:
                v = int(value)
                if max_val is not None:
                    clamped = max(min_val, min(max_val, v))
                    range_str = f"{min_val}-{max_val}"
                else:
                    clamped = max(min_val, v)
                    range_str = f"{min_val}+"
                if clamped != v:
                    logger.warning(f"{key}={v} out of range, clamped to {clamped} (valid: {range_str})")
                self.settings[key] = clamped
            except (ValueError, TypeError):
                logger.warning(f"{key}={value!r} invalid, using default")
                self.settings[key] = DEFAULT_SETTINGS.get(key)

        # Validate panel color (coerce string hex to int)
        if isinstance(panel, dict):
            color = panel.get("color")
            if not isinstance(color, int):
                try:
                    color_str = str(color).strip().lstrip("#").removeprefix("0x").removeprefix("0X")
                    panel["color"] = int(color_str, 16)
                except (ValueError, TypeError):
                    logger.warning(f"panel.color={color!r} invalid, using default")
                    panel["color"] = DEFAULT_SETTINGS["panel"]["color"]

        # Validate panel progress_update_interval (range 10-3600)
        if isinstance(panel, dict):
            interval = panel.get("progress_update_interval")
            try:
                v = int(interval)
                clamped = max(10, min(3600, v))
                if clamped != v:
                    logger.warning(f"panel.progress_update_interval={v} out of range, clamped to {clamped} (valid: 10-3600)")
                panel["progress_update_interval"] = clamped
            except (ValueError, TypeError):
                logger.warning(f"panel.progress_update_interval={interval!r} invalid, using default")
                panel["progress_update_interval"] = DEFAULT_SETTINGS["panel"]["progress_update_interval"]

        # Validate panel update_debounce_ms (minimum 300ms to prevent rate limiting)
        if isinstance(panel, dict):
            debounce = panel.get("update_debounce_ms")
            try:
                v = int(debounce)
                if v < 300:
                    logger.warning(f"panel.update_debounce_ms={v} below minimum, clamped to 300")
                    v = 300
                panel["update_debounce_ms"] = v
            except (ValueError, TypeError):
                logger.warning(f"panel.update_debounce_ms={debounce!r} invalid, using default")
                panel["update_debounce_ms"] = DEFAULT_SETTINGS["panel"]["update_debounce_ms"]

        # Validate panel recreate_interval (non-negative integer)
        if isinstance(panel, dict):
            recreate = panel.get("recreate_interval")
            try:
                v = int(recreate)
                if v < 0:
                    logger.warning(f"panel.recreate_interval={v} negative, clamped to 0")
                    v = 0
                panel["recreate_interval"] = v
            except (ValueError, TypeError):
                logger.warning(f"panel.recreate_interval={recreate!r} invalid, using default")
                panel["recreate_interval"] = DEFAULT_SETTINGS["panel"]["recreate_interval"]

    def _apply_env_overrides(self) -> None:
        """Override settings with environment variables.

        Environment variables always win over YAML settings, enabling Docker users
        to configure the bot without editing files.

        The env_map dict maps ENV_VAR_NAME -> (setting_key, converter):
        - setting_key: Dot notation for nested keys (e.g., "panel.color")
        - converter: Function to transform string value (int, str, bool lambda, etc.)

        Validator factories:
        - non_negative(key): Ensures value >= 0, clamps and warns if negative
        - hex_color(key): Parses hex color from string, strips #/0x prefixes

        Boolean env vars use case-insensitive "true" check (any other value = False).

        Invalid env var values are logged as warnings and ignored (setting unchanged).
        """
        # Validator factories
        def non_negative(env_key: str) -> Callable[[str], int]:
            def validate(x: str) -> int:
                v = int(x)
                if v < 0:
                    logger.warning(f"{env_key}={v} out of range, clamped to 0 (valid: 0+)")
                    return 0
                return v
            return validate

        def hex_color(env_key: str) -> Callable[[str], int]:
            def validate(x: str) -> int:
                x = x.strip().lstrip("#").removeprefix("0x").removeprefix("0X")
                return int(x, 16)
            return validate

        env_map = {
            # Playback defaults (range validation handled by _validate_settings)
            "QUEUE_DISPLAY_SIZE": ("queue_display_size", int),
            "PLAYLISTS_DISPLAY_SIZE": ("playlists_display_size", int),
            "INACTIVITY_TIMEOUT": ("inactivity_timeout", non_negative("INACTIVITY_TIMEOUT")),
            "DEFAULT_VOLUME": ("default_volume", int),
            "AUTO_RESCAN": ("auto_rescan", lambda x: x.lower() == "true"),
            "DEFAULT_PLAYLIST": ("default_playlist", str),
            "PRESENCE_ENABLED": ("presence_enabled", lambda x: x.lower() == "true"),
            "LOG_LEVEL": ("logging.level", str),
            # Panel appearance
            "PANEL_ENABLED": ("panel.enabled", lambda x: x.lower() == "true"),
            "PANEL_COLOR": ("panel.color", hex_color("PANEL_COLOR")),
            "PROGRESS_BAR_ENABLED": ("panel.progress_bar_enabled", lambda x: x.lower() == "true"),
            "SHUFFLE_BUTTON": ("panel.shuffle_button", lambda x: x.lower() == "true"),
            "LOOP_BUTTON": ("panel.loop_button", lambda x: x.lower() == "true"),
            "PLAYLIST_BUTTON": ("panel.playlist_button", lambda x: x.lower() == "true"),
            # Panel performance
            "PROGRESS_UPDATE_INTERVAL": ("panel.progress_update_interval", non_negative("PROGRESS_UPDATE_INTERVAL")),
            "UPDATE_DEBOUNCE_MS": ("panel.update_debounce_ms", non_negative("UPDATE_DEBOUNCE_MS")),
            "RECREATE_INTERVAL": ("panel.recreate_interval", non_negative("RECREATE_INTERVAL")),
            # Panel customization
            "DRINK_EMOJIS_ENABLED": ("panel.drink_emojis_enabled", lambda x: x.lower() == "true"),
            "INFO_FALLBACK_MESSAGE": ("panel.info_fallback_message", str),
            "PROGRESS_BAR_FILLED": ("panel.progress_bar_filled", str),
            "PROGRESS_BAR_EMPTY": ("panel.progress_bar_empty", str),
            # Commands
            "SHUFFLE_COMMAND": ("commands.shuffle_command", lambda x: x.lower() == "true"),
            "LOOP_COMMAND": ("commands.loop_command", lambda x: x.lower() == "true"),
            "RESCAN_COMMAND": ("commands.rescan_command", lambda x: x.lower() == "true"),
            # UI timeouts
            "EXTENDED_AUTO_DELETE": ("ui.extended_auto_delete", non_negative("EXTENDED_AUTO_DELETE")),
            "BRIEF_AUTO_DELETE": ("ui.brief_auto_delete", non_negative("BRIEF_AUTO_DELETE")),
        }

        for env_key, (setting_key, converter) in env_map.items():
            if value := os.getenv(env_key):
                try:
                    converted = converter(value)
                    # Handle nested keys (e.g., "logging.level")
                    if "." in setting_key:
                        parts = setting_key.split(".")
                        target = self.settings
                        for part in parts[:-1]:
                            target = target.setdefault(part, {})
                            if not isinstance(target, dict):
                                # Corrupted YAML: expected dict but got scalar
                                logger.warning(f"invalid config structure for {setting_key}")
                                break
                        else:
                            target[parts[-1]] = converted
                    else:
                        self.settings[setting_key] = converted
                    logger.debug(f"{env_key} overrides {setting_key}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"invalid env var {env_key}: {e}")

    def get(self, key: str, default=None) -> Any:
        """Get a setting value from settings.yaml.

        Args:
            key: Top-level setting key (e.g., "default_volume", "panel")
            default: Value to return if key not found

        Returns:
            Setting value, or default if not found
        """
        return self.settings.get(key, default)

    def msg(self, key: str, **kwargs) -> str:
        """Get formatted message text from messages.yaml.

        Args:
            key: Message key (e.g., "not_in_vc", "volume_set")
            **kwargs: Variables to substitute in message template

        Returns:
            Formatted message string. Returns key itself if message not found.
        """
        entry = self.messages.get(key, DEFAULT_MESSAGES.get(key, {}))
        template = entry.get("text", key) if isinstance(entry, dict) else entry
        try:
            return template.format(**kwargs)
        except KeyError:
            return template

    def is_enabled(self, key: str) -> bool:
        """Check if a message should be shown to the user.

        Each message in messages.yaml has an "enabled" flag. When False,
        the respond() helper will acknowledge the interaction silently
        without showing text (prevents "interaction failed" errors).

        Args:
            key: Message key (e.g., "now_playing", "paused")

        Returns:
            True if message should be shown, False for silent acknowledgment
        """
        entry = self.messages.get(key, DEFAULT_MESSAGES.get(key, {}))
        return entry.get("enabled", True) if isinstance(entry, dict) else True

    def get_panel_color(self) -> int:
        """Get panel color, with holiday override if active.

        Returns holiday-themed color when a holiday is detected,
        otherwise returns the user-configured panel color.

        Returns:
            Hex color integer (e.g., 0xA03E72)
        """
        holiday = get_active_holiday()
        if holiday and "color" in holiday:
            return holiday["color"]

        return self.get("panel", {}).get("color", 0xA03E72)


async def validate_configuration() -> None:
    """Validate configuration before bot starts, exit on failure.

    Called in main() before bot.start(). This is a pre-flight check to catch
    common configuration errors before the bot tries to connect.

    Checks performed:
    - DISCORD_TOKEN is set and has valid format (3 dot-separated sections)
    - Music, config, and data directories exist (creates if missing)
    - Lavalink server is reachable and responding

    Also warns (non-fatal) if GUILD_ID is not set.

    On failure: Logs all errors and calls sys.exit(1). The user can fix the
    issues and restart - no recovery is attempted.

    On success: Logs Lavalink version and returns normally.
    """
    import aiohttp

    errors = []

    # Check required env vars with format validation
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        errors.append(
            "DISCORD_TOKEN not set - run setup script, "
            "or add to .env (windows/linux) or docker-compose.yml (docker)"
        )
    else:
        # Basic token format validation
        token = token.strip()
        parts = token.split(".")
        if len(parts) != 3:
            errors.append(
                "DISCORD_TOKEN format appears invalid.\n"
                "Token should have three dot-separated sections.\n"
                "Get a fresh token from: https://discord.com/developers/applications"
            )
        elif any(not part for part in parts):
            errors.append(
                "DISCORD_TOKEN has empty sections.\n"
                "Get a fresh token from: https://discord.com/developers/applications"
            )

    # Warn if GUILD_ID not set (not an error - bot works without it)
    if not os.getenv("GUILD_ID"):
        logger.warning(
            "GUILD_ID not set - commands may take up to 1 hour to show up"
        )

    # Ensure music directory exists
    music_path = Path(os.getenv("MUSIC_PATH", "./music"))
    if not music_path.exists():
        try:
            music_path.mkdir(parents=True)
            logger.warning(f"created missing music directory: {music_path}")
        except OSError as e:
            errors.append(f"cannot create music directory {music_path}: {e}")

    # Ensure config directory exists
    _default_config = Path(__file__).parent.parent / "config"
    config_path = Path(os.getenv("CONFIG_PATH") or str(_default_config))
    if not config_path.exists():
        try:
            config_path.mkdir(parents=True)
            logger.warning(f"created missing config directory: {config_path}")
        except OSError as e:
            errors.append(f"cannot create config directory {config_path}: {e}")

    # Ensure data directory exists
    _default_data = Path(__file__).parent.parent / "data"
    data_path = Path(os.getenv("DATA_PATH") or str(_default_data))
    if not data_path.exists():
        try:
            data_path.mkdir(parents=True)
            logger.warning(f"created missing data directory: {data_path}")
        except OSError as e:
            errors.append(f"cannot create data directory {data_path}: {e}")

    # Check Lavalink connectivity
    lavalink_host = os.getenv("LAVALINK_HOST", "127.0.0.1")
    lavalink_port = os.getenv("LAVALINK_PORT", "2333")
    lavalink_password = os.getenv("LAVALINK_PASSWORD", "timetomixdrinksandnotchangepasswords")

    # Check for duplicate ports (will definitely fail at runtime)
    http_port = os.getenv("HTTP_SERVER_PORT", "2334")
    if lavalink_port == http_port:
        errors.append(
            f"LAVALINK_PORT and HTTP_SERVER_PORT are both set to {lavalink_port} - they must be different"
        )

    try:
        async with aiohttp.ClientSession() as session:
            url = f"http://{lavalink_host}:{lavalink_port}/version"
            headers = {"Authorization": lavalink_password}
            async with session.get(url, headers=headers, timeout=30.0) as resp:
                if resp.status != 200:
                    errors.append(f"lavalink not responding at {url}")
                else:
                    version = await resp.text()
                    logger.log("NOTICE", f"lavalink version: {version}")
    except Exception as e:
        errors.append(f"cannot connect to lavalink at {lavalink_host}:{lavalink_port}: {e}")

    # Log all validation errors and exit if any found
    if errors:
        for error in errors:
            logger.error(error)
        sys.exit(1)
