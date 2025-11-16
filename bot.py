# Copyright (C) 2025 grodz
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

"""
jill Music Bot
========================================================
VERSION: 1.0.0
========================================================

A Discord music bot built using the disnake API.
See AGENTS.md for development guidelines.
"""

import disnake
from disnake.ext import commands
import asyncio
import logging
import signal
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Import command mode and configuration early (needed for bot initialization)
from config import COMMAND_MODE, COMMAND_PREFIX, LOG_LEVEL, SUPPRESS_LIBRARY_LOGS, VOICE_RECONNECT_DELAY

# Conditional imports for slash mode
if COMMAND_MODE == 'slash':
    from systems.control_panel import get_control_panel_manager
    from handlers.buttons import setup as setup_buttons

# =============================================================================
# LOGGING SETUP
# =============================================================================

# Map string log level to logging constant
LOG_LEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL,
}

# Custom formatter for clean 4-char level names
class JillFormatter(logging.Formatter):
    """
    Custom formatter with 4-character level names for clean, aligned logs.

    Maps Python's standard log levels to 4-character names:
    - DEBUG    → [DBUG] - Technical details for debugging
    - INFO     → [INFO] - Normal operation messages
    - WARNING  → [WARN] - Issues that don't stop operation
    - ERROR    → [FAIL] - Recoverable failures
    - CRITICAL → [CRIT] - Catastrophic failures

    CAUTION: Changing LEVEL_NAMES may break log parsing or monitoring tools.
    Only modify if you know what you're doing.
    """

    LEVEL_NAMES = {
        'DEBUG': 'DBUG',
        'INFO': 'INFO',
        'WARNING': 'WARN',
        'ERROR': 'FAIL',
        'CRITICAL': 'CRIT',
    }

    def format(self, record):
        # Temporarily replace levelname for formatting, then restore original
        # This prevents mutation side effects if multiple handlers exist
        original_levelname = record.levelname
        record.levelname = self.LEVEL_NAMES.get(record.levelname, record.levelname)
        result = super().format(record)
        record.levelname = original_levelname
        return result

# Configure logging with custom formatter
handler = logging.StreamHandler()
handler.setFormatter(JillFormatter(
    fmt='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logging.basicConfig(
    level=LOG_LEVEL_MAP[LOG_LEVEL],
    handlers=[handler]
)
logger = logging.getLogger('jill')

# Reduce disnake noise (if enabled)
if SUPPRESS_LIBRARY_LOGS:
    logging.getLogger('disnake').setLevel(logging.WARNING)
    logging.getLogger('disnake.player').setLevel(logging.WARNING)
    logging.getLogger('disnake.voice_state').setLevel(logging.WARNING)
else:
    # Show disnake logs at configured level
    logging.getLogger('disnake').setLevel(LOG_LEVEL_MAP[LOG_LEVEL])
    logging.getLogger('disnake.player').setLevel(LOG_LEVEL_MAP[LOG_LEVEL])
    logging.getLogger('disnake.voice_state').setLevel(LOG_LEVEL_MAP[LOG_LEVEL])

# =============================================================================
# ASYNCIO EXCEPTION HANDLER
# =============================================================================

def custom_exception_handler(loop, context):
    """
    Custom asyncio exception handler to suppress cosmetic aiohttp warnings.
    
    Suppresses only:
    - "Unclosed client session" (from aiohttp during shutdown)
    - "Unclosed connector" (from aiohttp during shutdown)
    
    All other exceptions are passed to the default handler to preserve
    visibility of real errors.
    """
    message = context.get("message", "")
    
    # Suppress only specific aiohttp shutdown warnings
    if message in ["Unclosed client session", "Unclosed connector"]:
        return
    
    # Pass all other exceptions to default handler
    loop.default_exception_handler(context)

# =============================================================================
# BOT SETUP
# =============================================================================

intents = disnake.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True

# Command sync flags for slash mode
command_sync_flags = None
if COMMAND_MODE == 'slash':
    command_sync_flags = commands.CommandSyncFlags.default()

bot = commands.Bot(
    command_prefix=COMMAND_PREFIX if COMMAND_MODE == 'prefix' else commands.when_mentioned,
    intents=intents,
    help_command=None,
    command_sync_flags=command_sync_flags,
)

# Import our modules
from core.player import get_player, players
from core.track import discover_playlists, load_library, has_playlist_structure
from systems.watchdog import playback_watchdog, alone_watchdog
from systems.voice_manager import PlaybackState
from utils.discord_helpers import safe_disconnect, update_presence, format_guild_log, format_user_log, safe_voice_state_change
from utils.context_managers import reconnecting_state, suppress_callbacks
from utils.persistence import load_last_channels, flush_all_immediately

# Global watchdog tasks
_playback_watchdog_task = None
_alone_watchdog_task = None

# Shutdown flag to prevent on_disconnect from running during intentional shutdown
_is_shutting_down = False

# Initialization flag to prevent on_ready from running setup code on reconnects
_is_initialized = False

# =============================================================================
# BOT EVENTS
# =============================================================================

@bot.event
async def on_ready():
    """
    Bot connected to Discord.

    Handles both initial startup and gateway reconnects (full session restart).
    On reconnects, restores voice connections and skips initialization.
    """
    global _playback_watchdog_task, _alone_watchdog_task, _is_initialized

    # Check if this is a reconnect (not initial startup)
    if _is_initialized:
        logger.info("Gateway reconnected via on_ready")
        await _restore_voice_connections()
        return

    # Mark as initialized to prevent re-running on reconnects
    _is_initialized = True

    # Register persistent views (slash mode only)
    # Disnake doesn't have setup_hook, so we register here with flag protection
    if COMMAND_MODE == 'slash':
        from systems.persistent_view import MusicControlView
        bot.add_view(MusicControlView(bot))
        logger.debug("Registered persistent music control view")

    # Set custom exception handler on the actual bot loop
    # (Must be done here since bot.run() creates its own loop)
    bot.loop.set_exception_handler(custom_exception_handler)

    # Print banner
    print("\n" + "="*60)
    print("""
                          
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
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    """)
    print("="*60 + "\n")

    # Copyright and license info (as required by GPL 3.0)
    logger.info('Jill v1.0.0 - Copyright (C) 2025 grodz')
    logger.info('Licensed under GPL 3.0 - See LICENSE.md for details')
    print()  # Blank line without timestamp/level

    # Bot status
    logger.info(f'Bot connected as {bot.user}')
    logger.info(f'Command mode: {COMMAND_MODE}')

    # Display music library summary
    if has_playlist_structure():
        # Multi-playlist mode: count playlists and total songs
        playlists = discover_playlists(guild_id=0)
        total_songs = sum(playlist.track_count for playlist in playlists)
        logger.info(f"Discovered {len(playlists)} playlists with {total_songs} total songs")
    else:
        # Single-playlist mode: count songs in root folder
        library, _ = load_library(guild_id=0)
        if library:
            logger.info(f"Loaded {len(library)} songs from music folder")
        else:
            logger.error("No audio files found in music folder")

    # Show shutdown instruction last
    logger.info("Press Ctrl+C or send SIGTERM to shutdown")

    # Restore players for guilds with saved channels
    # This ensures cleanup workers resume automatically on restart
    saved_channels = load_last_channels()
    for guild_id, channel_id in saved_channels.items():
        try:
            # Get the guild
            guild = bot.get_guild(guild_id)
            if not guild:
                logger.debug(f"{format_guild_log(guild_id, bot)} not found (bot may have been removed)")
                continue

            # Get the text channel
            text_channel = guild.get_channel(channel_id)
            if not text_channel:
                logger.debug(f"{format_guild_log(guild, bot)}: Saved channel {channel_id} no longer exists")
                continue

            # Create/restore player (this starts cleanup workers automatically)
            player = await get_player(guild_id, bot, bot.user.id)
            player.set_text_channel(text_channel)

            logger.debug(f"{format_guild_log(guild, bot)}: Restored cleanup on channel #{text_channel.name}")

        except Exception as e:
            logger.warning(f"{format_guild_log(guild_id, bot)}: Failed to restore player: {e}")

    # Start watchdogs
    _playback_watchdog_task = bot.loop.create_task(playback_watchdog(bot, players))
    _alone_watchdog_task = bot.loop.create_task(alone_watchdog(bot, players))

    # Slash mode initialization
    if COMMAND_MODE == 'slash':
        # Initialize control panel manager
        control_panel = get_control_panel_manager(bot)
        logger.info("Control panel manager initialized")

        # Setup button handler
        setup_buttons(bot)
        logger.debug("Button handler registered")

        # Commands auto-synced via command_sync_flags (configured at bot initialization)
        logger.info("Slash command mode active (auto-sync enabled)")

@bot.event
async def on_disconnect():
    """
    Bot disconnected from Discord.

    Handles both temporary disconnects (network issues) and intentional shutdowns.
    On temporary disconnects, skips cleanup and lets Disnake auto-reconnect.
    On shutdown (Ctrl+C, SIGTERM), performs full cleanup.

    Cleanup side effects (shutdown only):
        - Cancels playback_watchdog and alone_watchdog tasks
        - Awaits task completion to prevent race conditions
        - Disconnects from all voice channels
        - Clears bot presence status
    """
    # Skip cleanup on temporary disconnects - let Disnake auto-reconnect handle it
    # Only cleanup during intentional shutdown (Ctrl+C, SIGTERM)
    if not _is_shutting_down:
        logger.info("Gateway disconnected, waiting for Disnake auto-reconnect...")
        return

    # Cancel and await watchdogs to prevent race conditions
    if _playback_watchdog_task and not _playback_watchdog_task.done():
        _playback_watchdog_task.cancel()
        try:
            await _playback_watchdog_task
        except asyncio.CancelledError:
            pass

    if _alone_watchdog_task and not _alone_watchdog_task.done():
        _alone_watchdog_task.cancel()
        try:
            await _alone_watchdog_task
        except asyncio.CancelledError:
            pass

    # Disconnect from all voice
    for player in list(players.values()):
        if player.voice_client:
            await safe_disconnect(player.voice_client, force=True)

    await update_presence(bot, None)

# =============================================================================
# VOICE RESTORATION
# =============================================================================

async def _restore_voice_connections():
    """
    Restore voice connections after gateway reconnects.

    Gateway reconnects (network drops, VPN changes) break the voice WebSocket,
    leaving clients in a stale "connected but not working" state. This function
    destroys stale clients and creates fresh connections with new sockets.

    Called by:
        - on_ready() — Full gateway reconnect (new session)
        - on_resumed() — Session resume (RESUME event)

    Note: This is distinct from voice health monitoring (discord_helpers.py)
    which handles stuttering/latency during normal operation.
    """
    logger.info("Gateway reconnected, checking voice connections...")

    for guild_id, player in list(players.items()):
        # Skip if no active playback
        if not player.now_playing:
            continue

        # Check if voice connection exists
        old_vc = player.voice_client
        if not old_vc:
            continue

        try:
            # Get channel before destroying old client
            channel = old_vc.channel
            if not channel:
                continue

            # Check if connection is broken
            if not old_vc.is_connected():
                logger.info(f"{format_guild_log(guild_id, bot)}: Voice broken after gateway reconnect, full reconnect needed")

                # FULL DISCONNECT+RECONNECT (same pattern as voice health monitoring)
                with reconnecting_state(player):
                    # Stop playback cleanly
                    try:
                        if old_vc.is_playing():
                            with suppress_callbacks(player):
                                old_vc.stop()
                    except Exception:
                        pass

                    # Disconnect - destroys stale client
                    try:
                        await old_vc.disconnect(force=True)
                    except Exception as e:
                        logger.debug(f"{format_guild_log(guild_id, bot)}: Disconnect error (continuing): {e}")

                    player.voice_client = None

                    # Wait for disconnect to settle
                    await asyncio.sleep(VOICE_RECONNECT_DELAY)

                    # Reconnect - creates fresh client with new sockets
                    try:
                        new_vc = await channel.connect(timeout=5.0, reconnect=True)
                        player.voice_client = new_vc
                        player.voice_manager.set_voice_client(new_vc)

                        # Self-deafen
                        guild = bot.get_guild(guild_id)
                        if guild:
                            await safe_voice_state_change(guild, channel, self_deaf=True)

                        logger.info(f"{format_guild_log(guild_id, bot)}: Voice reconnected after gateway recovery")

                        # Resume playback if was playing
                        if player.state == PlaybackState.PLAYING:
                            from core.playback import _play_current
                            await _play_current(guild_id, bot)

                    except asyncio.TimeoutError:
                        logger.error(f"{format_guild_log(guild_id, bot)}: Voice reconnect timed out after gateway recovery")
                        player.voice_client = None
                    except Exception as e:
                        logger.error(f"{format_guild_log(guild_id, bot)}: Voice reconnect failed after gateway recovery: {e}")
                        player.voice_client = None

        except Exception as e:
            logger.error(f"{format_guild_log(guild_id, bot)}: Failed to restore voice after reconnect: {e}")

@bot.event
async def on_resumed():
    """
    Gateway session resumed - restore voice connections if needed.

    Called when Disnake successfully resumes the gateway session after
    a temporary disconnect (RESUME event). Voice connections may need
    manual restoration.
    """
    await _restore_voice_connections()

@bot.event
async def on_voice_state_update(member, before, after):
    """Handle voice state changes for auto-pause."""
    # Bot disconnected
    if member.id == bot.user.id and before.channel and not after.channel:
        player = await get_player(member.guild.id, bot, bot.user.id)
        if not player._is_reconnecting:
            player.reset_state()
            return

    # User joined/left - check alone state
    if member.guild.id in players:
        player = await get_player(member.guild.id, bot, bot.user.id)
        if player.voice_client and player.voice_client.is_connected():
            bot_channel = player.voice_client.channel
            if before.channel == bot_channel or after.channel == bot_channel:
                current_state = player.voice_manager.get_playback_state()
                new_state = await player.voice_manager.handle_alone_state(
                    bot,
                    current_state,
                    player.now_playing
                )
                if new_state is not None:
                    player.state = new_state

@bot.event
async def on_guild_remove(guild):
    """Bot removed from guild - cleanup."""
    logger.info(f"Bot removed from {format_guild_log(guild)}")
    if guild.id in players:
        player = players[guild.id]
        if player.voice_client:
            await safe_disconnect(player.voice_client, force=True)
        await player.shutdown()
        del players[guild.id]

@bot.event
async def on_command_error(ctx, error):
    """Handle command errors gracefully."""
    # Silently ignore typos (CommandNotFound) - these are harmless user mistakes
    if isinstance(error, commands.CommandNotFound):
        logger.debug(f"{format_guild_log(ctx.guild)}: Unknown command from {format_user_log(ctx.author)}: {ctx.message.content}")
        return

    # Missing required arguments - user error, not code error (silently ignore like typos)
    if isinstance(error, commands.MissingRequiredArgument):
        logger.debug(f"{format_guild_log(ctx.guild)}: Missing argument for {ctx.command} from {format_user_log(ctx.author)}")
        return

    # For actual errors (code problems, API failures, etc.), log with full traceback
    logger.error(f"Command error in {ctx.command}: {error}", exc_info=error)

# =============================================================================
# GRACEFUL SHUTDOWN
# =============================================================================

async def shutdown_bot():
    """
    Gracefully shutdown the bot and all subsystems.

    This ensures all async tasks are properly cancelled and awaited,
    all players are shutdown cleanly, and all voice connections are closed.

    Called by signal handlers (SIGTERM, SIGINT) for clean shutdown.
    """
    logger.info("Initiating graceful shutdown...")

    # Set shutdown flag to prevent on_disconnect from running
    global _playback_watchdog_task, _alone_watchdog_task, _is_shutting_down
    _is_shutting_down = True

    # Cancel and await watchdog tasks

    if _playback_watchdog_task and not _playback_watchdog_task.done():
        logger.info("Stopping playback watchdog...")
        _playback_watchdog_task.cancel()
        try:
            await _playback_watchdog_task
        except asyncio.CancelledError:
            pass

    if _alone_watchdog_task and not _alone_watchdog_task.done():
        logger.info("Stopping alone watchdog...")
        _alone_watchdog_task.cancel()
        try:
            await _alone_watchdog_task
        except asyncio.CancelledError:
            pass

    # Shutdown all players (spam protectors, cleanup managers, etc.)
    logger.info(f"Shutting down {len(players)} player(s)...")
    for guild_id, player in list(players.items()):
        try:
            # Disconnect from voice
            if player.voice_client:
                await safe_disconnect(player.voice_client, force=True)

            # Shutdown player subsystems
            await player.shutdown()
        except Exception as e:
            logger.error(f"{format_guild_log(guild_id, bot)}: Error during shutdown: {e}")

    # Clean up control panels in slash mode
    if COMMAND_MODE == 'slash':
        logger.info("Cleaning up control panels...")
        try:
            control_panel = get_control_panel_manager(bot)
            if control_panel:
                # Shutdown control panel manager (cancels background tasks)
                await control_panel.shutdown()

                # Delete all panels
                for guild_id in list(control_panel.panels.keys()):
                    try:
                        await control_panel.delete_panel(guild_id)
                    except Exception as e:
                        logger.error(f"Error cleaning panel for {format_guild_log(guild_id, bot)}: {e}")
        except Exception as e:
            logger.error(f"Error during control panel cleanup: {e}")

    # Flush all pending persistence saves immediately
    logger.info("Flushing persistence to disk...")
    try:
        await flush_all_immediately()
    except Exception as e:
        logger.error(f"Error flushing persistence: {e}")

    # Clear bot presence
    await update_presence(bot, None)

    # Close bot connection
    logger.info("Closing bot connection...")
    logger.info("Shutdown complete")
    await bot.close()

def handle_shutdown_signal(signum, frame):
    """
    Signal handler for SIGTERM and SIGINT.

    Creates a task to run the async shutdown sequence.
    This allows Ctrl+C (SIGINT) and systemd stop (SIGTERM) to trigger clean shutdown.
    """
    signal_name = signal.Signals(signum).name
    logger.info(f"Received {signal_name} signal, shutting down...")

    # Schedule shutdown on the bot's event loop
    # Use bot.loop to ensure we're using the correct event loop
    if bot.loop and bot.loop.is_running():
        bot.loop.create_task(shutdown_bot())
    else:
        # Fallback: try to get the running loop
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(shutdown_bot())
        except RuntimeError:
            # No loop running, just log and exit
            logger.warning("No event loop running, forcing exit")
            os._exit(0)

# =============================================================================
# COMMANDS
# =============================================================================

# Import and register all commands
if COMMAND_MODE == 'slash':
    from handlers import slash_commands
    slash_commands.setup(bot)
    logger.info("Slash commands loaded")
else:
    from handlers.commands import setup as setup_commands
    setup_commands(bot)
    logger.info("Prefix commands loaded")

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.critical("DISCORD_BOT_TOKEN not found in environment - bot cannot start!")
        exit(1)

    # Register signal handlers for graceful shutdown
    # SIGINT = Ctrl+C, SIGTERM = systemd stop / kill
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    # Note: Custom exception handler is set in on_ready() where bot.loop exists
    logger.info("Starting bot...")

    try:
        bot.run(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
