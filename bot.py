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

"""Jill Discord Music Bot - Main Entry Point."""

__version__ = "2.0.1"

import asyncio
import colorsys
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import logging

from dotenv import load_dotenv

# Load .env from jill folder
load_dotenv(Path(__file__).parent / ".env")


def _sanitize_env_vars() -> None:
    """Strip trailing comments from environment variables.

    Handles: LAVALINK_PORT=4440 # my port  →  4440

    Pattern requires space before # to protect values like 'playlist#1'.
    Must run before module-level constants that use int(os.getenv(...)).
    """
    pattern = re.compile(r'\s+#.*$')

    env_vars = [
        # Critical (module-level constants with int() conversion)
        "DISCORD_TOKEN", "GUILD_ID",
        "HTTP_SERVER_HOST", "HTTP_SERVER_PORT",
        "LAVALINK_HOST", "LAVALINK_PORT", "LAVALINK_PASSWORD",
        "MUSIC_PATH", "DATA_PATH", "CONFIG_PATH",
        # Config overrides (int conversions)
        "QUEUE_DISPLAY_SIZE", "PLAYLISTS_DISPLAY_SIZE",
        "INACTIVITY_TIMEOUT", "DEFAULT_VOLUME",
        "PROGRESS_UPDATE_INTERVAL", "UPDATE_DEBOUNCE_MS",
        "RECREATE_INTERVAL", "EXTENDED_AUTO_DELETE", "BRIEF_AUTO_DELETE",
        # Config overrides (booleans - "true # comment" != "true")
        "AUTO_RESCAN", "PANEL_ENABLED", "PROGRESS_BAR_ENABLED",
        "SHUFFLE_BUTTON", "LOOP_BUTTON", "PLAYLIST_BUTTON",
        "DRINK_EMOJIS_ENABLED", "SHUFFLE_COMMAND", "LOOP_COMMAND",
        "RESCAN_COMMAND", "KILL_LAVALINK_ON_SHUTDOWN",
        # Config overrides (strings - strip for consistency)
        "DEFAULT_PLAYLIST", "LOG_LEVEL", "INFO_FALLBACK_MESSAGE",
        "PROGRESS_BAR_FILLED", "PROGRESS_BAR_EMPTY", "PANEL_COLOR",
        # Permissions
        "ENABLE_PERMISSIONS", "BARTENDER_ROLE_ID",
    ]

    for key in env_vars:
        if value := os.getenv(key):
            cleaned = pattern.sub('', value).strip()
            if cleaned != value:
                os.environ[key] = cleaned


_sanitize_env_vars()

import warnings

import aiohttp
import discord
import mafic
from aiohttp import web
from discord import app_commands
from discord.ext import commands
from loguru import logger
from mafic import UnsupportedVersionWarning

# Suppress mafic version warning (Lavalink 4.1.1 works fine)
warnings.filterwarnings("ignore", category=UnsupportedVersionWarning)

# Suppress mafic's traceback.print_exc() calls during reconnection
# Mafic has no config option for this - monkey-patch is the only solution
from mafic import node as mafic_node
mafic_node.print_exc = lambda: None

from ui.control_panel import ControlPanelLayout, PanelManager, DrinkCounter
from utils.config import ConfigManager, validate_configuration
from utils.library import MusicLibrary, ROOT_PLAYLIST_NAME
from utils.permissions import PermissionManager
from utils.state import StateManager


# ANSI true color helpers (for startup banner gradient)
RESET = "\033[0m"


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Parse #RRGGBB to (r, g, b)."""
    h = hex_color.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _rgb_to_ansi(r: int, g: int, b: int) -> str:
    """RGB to ANSI true color escape code."""
    return f"\033[38;2;{r};{g};{b}m"


def _interpolate_hsv(color1: tuple[int, int, int], color2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Interpolate between two RGB colors in HSV space for smooth gradients."""
    r1, g1, b1 = [c / 255 for c in color1]
    r2, g2, b2 = [c / 255 for c in color2]

    h1, s1, v1 = colorsys.rgb_to_hsv(r1, g1, b1)
    h2, s2, v2 = colorsys.rgb_to_hsv(r2, g2, b2)

    # Handle hue wraparound (take shortest path)
    if abs(h2 - h1) > 0.5:
        if h1 < h2:
            h1 += 1
        else:
            h2 += 1

    h = (h1 + (h2 - h1) * t) % 1.0
    s = s1 + (s2 - s1) * t
    v = v1 + (v2 - v1) * t

    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def _generate_gradient(colors: list[str], steps: int) -> list[tuple[int, int, int]]:
    """Generate gradient across multiple color stops."""
    if len(colors) < 2:
        return [_hex_to_rgb(colors[0])] * steps

    result = []
    segments = len(colors) - 1
    steps_per_segment = steps / segments

    for i in range(steps):
        segment = min(int(i / steps_per_segment), segments - 1)
        t = (i - segment * steps_per_segment) / steps_per_segment
        color1 = _hex_to_rgb(colors[segment])
        color2 = _hex_to_rgb(colors[segment + 1])
        result.append(_interpolate_hsv(color1, color2, t))

    return result


def _colorize_banner(text: str, colors: list[str]) -> str:
    """Apply vertical gradient to multi-line ASCII art."""
    lines = text.strip('\n').split('\n')
    gradient = _generate_gradient(colors, len(lines))

    colored_lines = []
    for i, line in enumerate(lines):
        r, g, b = gradient[i]
        colored_lines.append(f"{_rgb_to_ansi(r, g, b)}{line}{RESET}")

    return '\n'.join(colored_lines)


# VA-11 Hall-A gradient: pink → magenta → cyan
BANNER_COLORS = ["#ff6b9d", "#c77dff", "#00d4ff"]

BANNER_TEXT = """
            ▀     ▀    ▀▀█    ▀▀█
          ▄▄▄   ▄▄▄      █      █
            █     █      █      █
            █     █      █      █
            █   ▄▄█▄▄    ▀▄▄    ▀▄▄
            █
          ▀▀           CYBERPUNK
                                 BARTENDER
                                           MUSIC
                       .|                        BOT
                       | |
                       |'|            ._____
               ___    |  |            |.   |' .---"|
       _    .-'   '-. |  |     .--'|  ||   | _|    |
    .-'|  _.|  |    ||   '-__  |   |  |    ||      |
    |' | |.    |    ||       | |   |  |    ||      |
 ___|  '-'     '    ""       '-'   '-.'    '`      |____
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"""


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
# User-configurable log levels (settings.yaml: logging.level)
# These friendly names map to Loguru's internal levels.
#
# Log verbosity options:
#   minimal - Errors and milestones only (NOTICE + WARNING + ERROR)
#   verbose - Normal operation (INFO + above)
#   debug   - Everything including internal state (DEBUG + above)
# =============================================================================

LOG_LEVELS = {
    "minimal": "WARNING",
    "verbose": "INFO",
    "debug": "DEBUG",
}

# Icons shown instead of level names in log output.
# Makes logs cleaner and easier to scan visually.
LEVEL_ICONS = {
    "NOTICE": "[-]",    # Milestones (startup, shutdown, connected)
    "INFO": "[-]",      # Normal operations
    "WARNING": "[!]",   # Recoverable issues
    "ERROR": "[x]",     # Failures
    "CRITICAL": "[X]",  # Severe (unused in practice)
    "DEBUG": "[~]",     # Internal state
}


def log_format(record) -> str:
    """Custom log format with level icons."""
    icon = LEVEL_ICONS.get(record["level"].name, "[?]")
    return "{time:HH:mm:ss} | <level>" + icon + "</level> | {message}\n"


# Configure logging - bootstrap with INFO for startup visibility
# Reconfigured in setup_hook() after config loads
logger.remove()

# VA-11 Hall-A themed log colors (moody purple aesthetic)
logger.level("NOTICE", no=25, color="<fg #c77dff>")  # Magenta - milestones
logger.level("INFO", color="<fg #7c3aed>")           # Deep purple - info
logger.level("DEBUG", color="<fg #64748b>")          # Slate - subtle
logger.level("WARNING", color="<fg #fbbf24>")        # Amber - caution
logger.level("ERROR", color="<fg #ff6b9d>")          # Pink-red - danger
logger.level("CRITICAL", color="<bold><fg #cc0000>") # Blood red - severe

logger.add(
    sys.stderr,
    level="INFO",
    format=log_format,
    colorize=True
)

# Suppress Mafic's internal exception logging (we handle reconnection ourselves)
logging.getLogger("mafic").setLevel(logging.CRITICAL)


def configure_logger(level_name: str) -> None:
    """Configure logger with the specified level.

    Args:
        level_name: "minimal", "verbose", or "debug"
    """
    loguru_level = LOG_LEVELS.get(level_name.lower(), "WARNING")

    def log_filter(record) -> bool:
        # At WARNING level, also allow NOTICE through (milestones)
        if loguru_level == "WARNING" and record["level"].name == "NOTICE":
            return True
        return record["level"].no >= logger.level(loguru_level).no

    logger.remove()
    logger.add(
        sys.stderr,
        filter=log_filter,
        format=log_format,
        colorize=True
    )

# Configuration
_bot_dir = Path(__file__).parent
MUSIC_PATH = Path(os.getenv("MUSIC_PATH", "./music"))
DATA_PATH = Path(os.getenv("DATA_PATH") or str(_bot_dir / "data"))
METADATA_CACHE_PATH = DATA_PATH / "metadata"
CONFIG_PATH = Path(os.getenv("CONFIG_PATH") or str(_bot_dir / "config"))
HTTP_HOST = os.getenv("HTTP_SERVER_HOST", "127.0.0.1")
HTTP_PORT = int(os.getenv("HTTP_SERVER_PORT", "4444"))
LAVALINK_HOST = os.getenv("LAVALINK_HOST", "127.0.0.1")
LAVALINK_PORT = int(os.getenv("LAVALINK_PORT", "4440"))
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "timetomixdrinksandnotchangepasswords")

# Track last served file to deduplicate Lavalink's multiple requests per track
# (safe: check-write is after yield point, no await between them)
_last_served_path: str | None = None


@web.middleware
async def logging_middleware(request: web.Request, handler) -> web.Response:
    """Log HTTP requests with deduplication for Lavalink file requests."""
    global _last_served_path
    start = time.perf_counter()
    try:
        response = await handler(request)
        duration = time.perf_counter() - start

        # Clean logging for file serving (deduplicated)
        if request.path.startswith("/files/"):
            if request.path != _last_served_path:
                _last_served_path = request.path
                filename = request.path.split("/")[-1]
                logger.debug(f"playing {filename}")
        else:
            logger.debug(f"{request.method} {request.path} {response.status} ({duration:.3f}s)")

        return response
    except web.HTTPException as ex:
        duration = time.perf_counter() - start
        logger.warning(f"{request.method} {request.path} {ex.status} ({duration:.3f}s)")
        raise


# Track fire-and-forget cleanup tasks to prevent GC warnings
_cleanup_tasks: set[asyncio.Task] = set()


async def _delete_followup(msg: discord.Message, delay: float) -> None:
    """Delete followup message after delay (webhook doesn't support delete_after)."""
    try:
        await asyncio.sleep(delay)
        await msg.delete()
    except (asyncio.CancelledError, discord.NotFound, discord.HTTPException):
        pass


class CustomTree(app_commands.CommandTree):
    """Custom command tree with global error handling."""

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError
    ) -> None:
        """Handle global slash command errors. Logs with traceback and sends error_generic message (respects enabled flag and auto-delete)."""
        config = interaction.client.config_manager

        logger.opt(exception=True).error(f"command error: {error}")
        msg_key = "error_generic"
        msg = config.msg(msg_key)

        # Check if message is disabled - silent acknowledgment
        if not config.is_enabled(msg_key):
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True)
            try:
                await interaction.delete_original_response()
            except discord.NotFound:
                pass
            return

        # Get auto-delete timeout
        ui_config = config.get("ui", {})
        timeout = ui_config.get("brief_auto_delete", 10)
        delete_after = timeout if timeout > 0 else None

        if not interaction.response.is_done():
            await interaction.response.send_message(msg, ephemeral=True, delete_after=delete_after)
        else:
            followup_msg = await interaction.followup.send(msg, ephemeral=True)
            if delete_after:
                task = asyncio.create_task(_delete_followup(followup_msg, delete_after))
                _cleanup_tasks.add(task)
                task.add_done_callback(_cleanup_tasks.discard)


class MusicBot(commands.Bot):
    """Main bot class for Jill - a Discord music bot.

    Handles Discord connection, Lavalink audio streaming, and coordinates
    between cogs (Music, Queue, Settings) and UI components (control panel).

    Instantiation (in __init__):
        Creates unloaded managers: ConfigManager, StateManager, PermissionManager,
        PanelManager. These are instantiated but not yet loaded from disk.

    Initialization (in setup_hook):
        1. ConfigManager.load() - settings.yaml, messages.yaml, env overrides
        2. Logger reconfiguration - applies log level from settings
        3. MusicLibrary.scan() - discover playlists and audio files
        4. Metadata scan - auto_rescan triggers scan_playlist_metadata if enabled
        5. StateManager.load() - volume, shuffle, last_playlist
        6. PermissionManager.load() - role-based access control
        7. aiohttp session - for HTTP client operations
        8. HTTP server - serves audio files to Lavalink
        9. Panel setup - registers persistent view, loads panel.json, recovers existing panel
        10. Mafic pool creation (node connects in on_ready)
        11. Cogs - Music, Queue, Settings
        12. preload_playlist - loads last playlist into queue

    Shutdown (in close):
        1. Unload cogs - triggers cog_unload for cleanup
        2. Save state - persist volume, shuffle, queue position
        3. Disconnect voice clients (Mafic players)
        4. Brief delay (0.1s) for Mafic event processing
        5. Close Mafic pool (2s timeout)
        6. Stop HTTP server
        7. Close aiohttp session
        8. super().close() - Discord.py cleanup
        9. Kill Lavalink process (if managed by bot)

    Key attributes:
        config_manager: Settings and messages access
        state_manager: Persistent runtime state
        library: Music file discovery and playlists
        panel_manager: Control panel message tracking
        pool: Mafic NodePool for Lavalink connection
        drink_counters: Per-guild emoji rotation state
        session_ids: Tracks Lavalink session IDs for duplicate event detection
        _lavalink_init_lock: Serializes node creation in on_ready
        _lavalink_disconnect_lock: Serializes disconnect handling
    """

    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.guilds = True
        intents.voice_states = True
        intents.message_content = False

        super().__init__(
            command_prefix="",  # Unused but required
            intents=intents,
            tree_cls=CustomTree
        )

        self.session_ids: dict[str, str] = {}
        self.pool: mafic.NodePool | None = None
        # Serializes Lavalink node creation in on_ready() - prevents duplicate
        # nodes if Discord fires multiple ready events during connection
        self._lavalink_init_lock = asyncio.Lock()
        self._lavalink_disconnect_lock = asyncio.Lock()
        self._presence_task: asyncio.Task | None = None
        # Store config as instance attributes for cog access
        self.http_host = HTTP_HOST
        self.http_port = HTTP_PORT
        self.metadata_cache_path = METADATA_CACHE_PATH

        # Phase 7: Control panel
        self.panel_manager = PanelManager(DATA_PATH)
        # Single-guild bot: This dict will only ever have one entry.
        self.drink_counters: dict[int, DrinkCounter] = {}

        # Phase 8: State persistence
        self.state_manager = StateManager(DATA_PATH)

        # Phase 10: Permission system
        self.permission_manager = PermissionManager(CONFIG_PATH)

        # Phase 11: Configuration management
        self.config_manager = ConfigManager(CONFIG_PATH)

    async def serve_file(self, request: web.Request) -> web.Response:
        """Serve audio files to Lavalink. Validates path is within music directory."""
        playlist = request.match_info['playlist']
        filename = request.match_info['filename']

        # Security: Reject path traversal
        if '..' in playlist or '..' in filename:
            logger.debug("blocked path traversal attempt")
            raise web.HTTPForbidden()

        # Handle root playlist (files directly in music folder)
        if playlist == ROOT_PLAYLIST_NAME:
            filepath = (MUSIC_PATH / filename).resolve()
        else:
            filepath = (MUSIC_PATH / playlist / filename).resolve()

        music_root = MUSIC_PATH.resolve()

        # Security check BEFORE existence check
        if not filepath.is_relative_to(music_root):
            raise web.HTTPForbidden()

        if not filepath.is_file():
            logger.debug(f"file not found: {request.path}")
            raise web.HTTPNotFound()

        return web.FileResponse(filepath)

    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint for container orchestration."""
        return web.Response(text="ok", status=200)

    async def setup_hook(self) -> None:
        """Async initialization - runs before bot connects to Discord."""
        logger.debug("setup started")

        # Ensure music directory exists
        MUSIC_PATH.mkdir(parents=True, exist_ok=True)

        # Ensure metadata cache directory exists
        METADATA_CACHE_PATH.mkdir(parents=True, exist_ok=True)

        # Load configuration first (Phase 11)
        await self.config_manager.load()

        # Reconfigure logger with config settings
        log_config = self.config_manager.get("logging", {})
        log_level = log_config.get("level", "minimal")
        configure_logger(log_level)
        logger.log("NOTICE", f"log level: {log_level}")

        # Initialize music library
        self.library = MusicLibrary(MUSIC_PATH)
        await self.library.scan()

        # Auto-rescan if enabled (handles first-run implicitly via cache creation)
        all_duplicates: list[str] = []
        if self.config_manager.get("auto_rescan", True):  # default changed to True
            from utils.metadata import scan_playlist_metadata
            playlist_names = self.library.get_playlist_names()
            results = await asyncio.gather(
                *[scan_playlist_metadata(
                    self.library.get_playlist_path(name),
                    self.metadata_cache_path,
                    name
                ) for name in playlist_names],
                return_exceptions=True
            )

            total_new = 0
            for i, result in enumerate(results):
                if not isinstance(result, Exception):
                    _, new_count, filtered_paths, duplicates = result
                    total_new += new_count
                    all_duplicates.extend(duplicates)

                    # Apply metadata-based filtering to library playlists
                    self.library.update_playlist_files(playlist_names[i], filtered_paths)

            # Log per-playlist counts (after metadata filtering applied)
            for name, tracks in self.library.playlists.items():
                if name == ROOT_PLAYLIST_NAME:
                    track_word = "track" if len(tracks) == 1 else "tracks"
                    logger.debug(f"{len(tracks)} {track_word} in music root")
                else:
                    track_word = "track" if len(tracks) == 1 else "tracks"
                    logger.debug(f"playlist '{name}' has {len(tracks)} {track_word}")

            # Summary at INFO level
            total_tracks = sum(len(tracks) for tracks in self.library.playlists.values())
            track_word = "track" if total_tracks == 1 else "tracks"
            playlist_word = "playlist" if len(self.library.playlists) == 1 else "playlists"
            logger.info(f"found {total_tracks} {track_word} in {len(self.library.playlists)} {playlist_word}")

            # New songs logging
            if total_new > 0:
                song_word = "song" if total_new == 1 else "songs"
                playlist_word = "playlist" if len(playlist_names) == 1 else "playlists"
                logger.info(f"found {total_new} new {song_word} in {len(playlist_names)} {playlist_word}")
            elif total_new == 0:
                logger.debug("no new songs")

        # Log duplicates (deduplicated to avoid repeats in log)
        unique_duplicates = list(dict.fromkeys(all_duplicates))  # Preserve order, remove dupes
        if unique_duplicates:
            dup_word = "duplicate" if len(unique_duplicates) == 1 else "duplicates"
            logger.warning(f"skipped {len(unique_duplicates)} {dup_word}")
            for filename in unique_duplicates[:5]:
                logger.warning(f"  - {filename}")
            if len(unique_duplicates) > 5:
                logger.warning(f"  ...and {len(unique_duplicates) - 5} more")

        # Load persistent state (Phase 8)
        await self.state_manager.load()

        # Load permissions (Phase 10)
        await self.permission_manager.load()

        # Create aiohttp session FIRST (used by session resumption)
        connector = aiohttp.TCPConnector(
            limit=20,
            limit_per_host=10,
            ttl_dns_cache=300,
            enable_cleanup_closed=True
        )
        self.session = aiohttp.ClientSession(connector=connector)

        # HTTP Server
        self.web_app = web.Application(middlewares=[logging_middleware])
        self.web_app.router.add_get('/files/{playlist}/{filename}', self.serve_file)
        self.web_app.router.add_get('/health', self.health_check)

        self.runner = web.AppRunner(self.web_app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, host=HTTP_HOST, port=HTTP_PORT)
        try:
            await self.site.start()
        except OSError as e:
            if e.errno in (98, 10048):  # EADDRINUSE on Linux/Windows
                logger.error(f"port {HTTP_PORT} already in use - is another instance running?")
            raise
        logger.debug(f"http server started on {HTTP_HOST}:{HTTP_PORT}")

        # Control panel initialization (skip if disabled)
        panel_config = self.config_manager.get("panel", {})
        if panel_config.get("enabled", True):
            # Register persistent view FIRST (before loading panel)
            self.add_view(ControlPanelLayout(self))
            logger.log("NOTICE", "control panel enabled")

            # Load panel tracking
            await self.panel_manager.load()

            # Re-attach to existing panel if it exists (for restart recovery)
            existing_panel = await self.panel_manager.get_message(self)
            if existing_panel:
                logger.debug(f"found control panel in #{existing_panel.channel.name}")
                # Refresh to idle state (no voice connection after restart)
                layout = ControlPanelLayout(self)
                layout.header_display.content = "### now serving:\n[nothing]"
                layout.body_display.content = "press `▶️play` to start"
                try:
                    # CRITICAL: embed=None, content=None for transition from old embed
                    await existing_panel.edit(view=layout, embed=None, content=None)
                    logger.debug("refreshed control panel to idle")
                except discord.HTTPException as e:
                    logger.warning(f"failed to refresh control panel: {e}")
            else:
                logger.debug("no existing control panel found")
        else:
            logger.log("NOTICE", "control panel disabled")

        # Initialize Mafic NodePool (node created in on_ready after Discord connection)
        self.pool = mafic.NodePool(self)

        # Load cogs
        await self.load_extension("cogs.music")
        logger.debug("loaded music cog")

        await self.load_extension("cogs.queue")
        logger.debug("loaded queue cog")

        await self.load_extension("cogs.settings")
        logger.debug("loaded settings cog")

        # Preload playlist for autocomplete (if GUILD_ID configured)
        guild_id_str = os.getenv("GUILD_ID")
        if guild_id_str:
            try:
                guild_id = int(guild_id_str)
                music_cog = self.get_cog("Music")
                if music_cog:
                    await music_cog.preload_playlist(guild_id)
            except ValueError:
                pass  # Invalid GUILD_ID - will be caught in on_ready

    async def close(self) -> None:
        """Cleanup on shutdown."""
        logger.info("cleaning up")

        # Unload cogs first - cancels pending tasks, removes event listeners
        # Must happen before voice disconnect (which triggers events)
        for ext in list(self.extensions):
            try:
                await self.unload_extension(ext)
            except Exception:
                pass  # Best effort

        # Save state (safety net - usually already saved during operation)
        try:
            await asyncio.wait_for(self.state_manager.save(), timeout=2.0)
        except asyncio.TimeoutError:
            logger.error("state save timed out")

        # Disconnect all Mafic players (handles Lavalink cleanup + Discord disconnect)
        for vc in list(self.voice_clients):
            try:
                await vc.disconnect(force=True)
            except Exception:
                pass  # Best effort

        # Brief delay for Mafic to finish processing disconnect events
        await asyncio.sleep(0.1)

        # Close Mafic pool (should be quick now - no active players)
        if self.pool:
            try:
                await asyncio.wait_for(self.pool.close(), timeout=2.0)
            except asyncio.TimeoutError:
                logger.warning("mafic pool close timed out")

        # Now HTTP server cleanup is instant (no active connections)
        if hasattr(self, 'site'):
            await self.site.stop()
        if hasattr(self, 'runner'):
            await self.runner.cleanup()
        if hasattr(self, 'session'):
            await self.session.close()

        await super().close()

        # Kill Lavalink if enabled (default: true, set to false for shared Lavalink)
        # Blocking subprocess is intentional - event loop has no work after super().close()
        kill_lavalink = self.config_manager.get("kill_lavalink_on_shutdown", True)

        if kill_lavalink:
            lavalink_port = LAVALINK_PORT
            lavalink_killed = False
            try:
                if sys.platform == "win32":
                    result = subprocess.run(
                        ['powershell', '-Command',
                         f"$p = (Get-NetTCPConnection -LocalPort {lavalink_port} -State Listen -ErrorAction SilentlyContinue).OwningProcess; "
                         f"if ($p) {{ Stop-Process -Id $p -Force; exit 0 }} else {{ exit 1 }}"],
                        capture_output=True
                    )
                    lavalink_killed = result.returncode == 0
                else:
                    result = subprocess.run(['fuser', '-k', f'{lavalink_port}/tcp'],
                                           capture_output=True)
                    lavalink_killed = result.returncode == 0
            except Exception:
                pass

            if lavalink_killed:
                logger.log("NOTICE", "it's now safe to exit")
            else:
                logger.log("NOTICE", "it's now safe to exit (lavalink may still be running)")
        else:
            logger.log("NOTICE", "it's now safe to exit (lavalink left running)")

    async def on_ready(self) -> None:
        """Called when bot is connected and ready."""
        logger.info(f"logged in as {self.user} (ID: {self.user.id})")

        # Connect to Lavalink (requires bot to be ready for user.id)
        # Lock prevents race if on_ready fires multiple times during reconnection
        async with self._lavalink_init_lock:
            if "MAIN" not in self.pool.label_to_node:
                try:
                    await self.pool.create_node(
                        host=LAVALINK_HOST,
                        port=LAVALINK_PORT,
                        label="MAIN",
                        password=LAVALINK_PASSWORD,
                        timeout=30
                    )
                except Exception as e:
                    logger.error(f"lavalink connection failed: {e}")
                    await self.close()
                    return

        # Sync commands and validate guild access
        guild_id_str = os.getenv("GUILD_ID")
        if guild_id_str:
            try:
                guild_id = int(guild_id_str)
                guild = self.get_guild(guild_id)
                if guild is None:
                    logger.error(f"guild {guild_id} not found: bot not a member or ID incorrect")
                    await self.close()
                    return
                logger.log("NOTICE", f"connected to {guild.name}")
                guild_obj = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild_obj)
                logger.debug("syncing commands")
                await self.tree.sync(guild=guild_obj)
                logger.debug(f"commands synced to guild {guild_id}")
            except ValueError:
                logger.error(f"guild_id '{guild_id_str}' is not a valid integer")
                await self.close()
                return
        else:
            logger.debug("syncing commands globally")
            await self.tree.sync()
            logger.debug("commands synced globally")

        print()
        print("jill copyright (c) 2026 grodz - licensed under gpl 3.0\n")
        print(_colorize_banner(BANNER_TEXT, BANNER_COLORS))
        logger.log("NOTICE", f"v{__version__} - time to mix drinks and change lives")

    # Mafic event listeners (Bot class auto-registers on_<event> methods)
    async def on_node_ready(self, node: mafic.Node) -> None:
        """Handle Lavalink node connection.

        Called by Mafic when a node becomes available. Skips duplicate ready
        events during reconnection. Stores session ID and enables extended
        timeout for playback resumption after brief disconnections.
        """
        # Skip duplicate ready events (Mafic may dispatch multiple during reconnection)
        if self.session_ids.get(node.label) == node.session_id:
            return
        self.session_ids[node.label] = node.session_id
        logger.log("NOTICE", "lavalink connected")
        await self._enable_session_resumption(node)

    async def _enable_session_resumption(self, node: mafic.Node, timeout: int = 300) -> None:
        """Enable Lavalink session resumption. Timeout (default 300s) is how long Lavalink preserves playback state during reconnection."""
        url = f"http://{node.host}:{node.port}/v4/sessions/{node.session_id}"
        # Access internal password attribute (Python name-mangled as _Node__password)
        headers = {"Authorization": node._Node__password}
        payload = {"resuming": True, "timeout": timeout}

        try:
            async with self.session.patch(url, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    logger.debug(f"lavalink session resume enabled ({timeout}s)")
                else:
                    logger.error(f"lavalink session resumption failed: HTTP {resp.status}")
        except Exception:
            logger.debug("lavalink session resume failed")

    async def on_node_unavailable(self, node: mafic.Node) -> None:
        """Handle Lavalink node disconnection.

        Called by Mafic when the Lavalink connection drops. Disconnects voice
        clients so the panel returns to idle state. Mafic handles reconnection
        internally - we just need to clean up our side.

        Note: We can't use player.disconnect() because Mafic tries to HTTP to
        Lavalink first (to destroy the session), which fails when Lavalink is down.
        Instead we use change_voice_state + cleanup (what Discord.py does internally).
        """
        logger.warning("lavalink disconnected")

        # Disconnect from voice (gateway message + local cleanup)
        # on_voice_state_update will handle state cleanup and panel update
        for guild in self.guilds:
            vc = guild.voice_client
            if vc:
                try:
                    await guild.change_voice_state(channel=None)
                except Exception as e:
                    logger.debug(f"voice disconnect failed: {e}")
                finally:
                    vc.cleanup()

    async def handle_lavalink_connection_error(self) -> None:
        """Handle Lavalink disconnect detected via connection errors.

        Called when playback fails because Lavalink is unreachable.
        Triggers voice cleanup and forces Mafic to reconnect.
        """
        if self._lavalink_disconnect_lock.locked():
            return

        async with self._lavalink_disconnect_lock:
            if not self.pool or not self.pool.nodes:
                return
            node = list(self.pool.nodes)[0]

            # Voice cleanup (mirrors on_node_unavailable)
            logger.warning("lavalink disconnected")
            for guild in self.guilds:
                vc = guild.voice_client
                if vc:
                    try:
                        await guild.change_voice_state(channel=None)
                    except Exception as e:
                        logger.debug(f"voice disconnect failed: {e}")
                    finally:
                        vc.cleanup()

            # Force reconnection (Mafic has built-in exponential backoff)
            try:
                await node.close()
            except Exception:
                pass
            asyncio.create_task(node.connect())

    async def update_presence(self, title: str | None = None, artist: str | None = None) -> None:
        """Update bot presence to show current song.

        Args:
            title: Song title to display. None clears presence.
            artist: Optional artist name (shown as "artist - title").

        Non-critical: Errors are logged but don't interrupt playback.
        Debounced: waits 4s for rapid skipping to settle before updating.
        """
        if not self.config_manager.get("presence_enabled", True):
            return

        # Cancel existing pending update (task cleanup pattern - music.py:456-460)
        if self._presence_task and not self._presence_task.done():
            self._presence_task.cancel()

        # Clear presence immediately (stop/disconnect shouldn't wait)
        if title is None:
            try:
                await self.change_presence(activity=None)
            except Exception as e:
                logger.debug(f"presence update failed: {e}")
            return

        # Schedule debounced update for song changes
        self._presence_task = asyncio.create_task(
            self._debounced_presence_update(title, artist)
        )

    async def _debounced_presence_update(self, title: str, artist: str | None) -> None:
        """Debounced presence update - coalesces rapid track changes into one.

        Waits 4 seconds for rapid skipping to settle. If a newer track starts
        during the wait, this task is cancelled (preventing stale updates).

        4s matches Discord's rate limit (~5 updates per 20 seconds).
        """
        try:
            await asyncio.sleep(4)

            # Format: "artist - title" or just "title"
            display = f"{artist} - {title}" if artist else title

            # Discord limit: 128 characters
            if len(display) > 128:
                display = display[:125] + "..."

            activity = discord.Activity(
                type=discord.ActivityType.listening,
                name=display
            )
            await self.change_presence(activity=activity)
        except asyncio.CancelledError:
            pass  # Superseded by a newer update
        except Exception as e:
            logger.debug(f"presence update failed: {e}")


# Create bot instance
bot = MusicBot()


async def main() -> None:
    """Main entry point."""
    # Phase 1: Validate configuration before bot starts
    await validate_configuration()

    # Suppress harmless asyncio task exceptions (mafic internal errors during reconnection)
    def _silence_library_exceptions(loop, context) -> None:
        if "exception" in context:
            exc = context["exception"]
            # Silence mafic's internal errors: connection resets, websocket listener, player sync, orphaned reconnects
            if isinstance(exc, (ConnectionResetError, RuntimeError, KeyError, TimeoutError)):
                return  # Silently ignore
        loop.default_exception_handler(context)

    asyncio.get_running_loop().set_exception_handler(_silence_library_exceptions)

    # Validated by validate_configuration() above - exits if missing
    token = os.getenv("DISCORD_TOKEN")

    # SIGTERM handler only on Unix (Windows doesn't support add_signal_handler)
    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        shutdown_event = asyncio.Event()

        def handle_sigterm() -> None:
            logger.info("received sigterm")
            shutdown_event.set()

        loop.add_signal_handler(signal.SIGTERM, handle_sigterm)

        async with bot:
            start_task = asyncio.create_task(bot.start(token))
            shutdown_task = asyncio.create_task(shutdown_event.wait())

            done, pending = await asyncio.wait(
                [start_task, shutdown_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            # Re-raise any startup error (network, auth, etc)
            if start_task in done:
                start_task.result()
    else:
        # Windows: simple startup (Ctrl+C still works via KeyboardInterrupt)
        async with bot:
            await bot.start(token)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # Clean shutdown via Ctrl+C
    except discord.errors.LoginFailure:
        logger.error("invalid token - check DISCORD_TOKEN in .env (windows/linux) or docker-compose.yml (docker)")
        sys.exit(1)
    except aiohttp.ClientConnectionError:
        logger.error("cannot connect to discord - check your network connection")
        sys.exit(1)
