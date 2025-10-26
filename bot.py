# Copyright (C) 2025 grodz-bar
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
VERSION: 0.9.5
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

# =============================================================================
# LOGGING SETUP
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('jill')

# Reduce disnake noise
logging.getLogger('disnake').setLevel(logging.WARNING)
logging.getLogger('disnake.player').setLevel(logging.WARNING)
logging.getLogger('disnake.voice_state').setLevel(logging.WARNING)

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

bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None
)

# Import our modules
from core.player import get_player, players
from systems.watchdog import playback_watchdog, alone_watchdog
from utils.discord_helpers import safe_disconnect, update_presence
from utils.persistence import load_last_channels

# Global watchdog tasks
_playback_watchdog_task = None
_alone_watchdog_task = None

# =============================================================================
# BOT EVENTS
# =============================================================================

@bot.event
async def on_ready():
    """Bot connected to Discord."""
    global _playback_watchdog_task, _alone_watchdog_task

    # Print banner
    print("\n" + "="*60)
    print("""
                          
            ▀     ▀    ▀▀█    ▀▀█   
          ▄▄▄   ▄▄▄      █      █   
            █     █      █      █   
            █     █      █      █   
            █   ▄▄█▄▄    ▀▄▄    ▀▄▄ 
            █                       
          ▀▀           A CYBERPUNK            
                                  BARTENDER
                                            MUSIC BOT
                       .|
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
    
    logger.info(f'Bot connected as {bot.user}')
    logger.info('Jill v0.9.5 - Copyright (C) 2025 grodz-bar')
    logger.info('Licensed under GPL 3.0 - See LICENSE.md for details')
    logger.info("Press Ctrl+C or send SIGTERM to shutdown gracefully")

    # Restore players for guilds with saved channels
    # This ensures cleanup workers resume automatically on restart
    saved_channels = load_last_channels()
    for guild_id, channel_id in saved_channels.items():
        try:
            # Get the guild
            guild = bot.get_guild(guild_id)
            if not guild:
                logger.debug(f"Guild {guild_id} not found (bot may have been removed)")
                continue

            # Get the text channel
            text_channel = guild.get_channel(channel_id)
            if not text_channel:
                logger.debug(f"Guild {guild_id}: Saved channel {channel_id} no longer exists")
                continue

            # Create/restore player (this starts cleanup workers automatically)
            player = await get_player(guild_id, bot, bot.user.id)
            player.text_channel = text_channel
            player.cleanup_manager.text_channel = text_channel

            logger.info(f"Guild {guild_id}: Restored cleanup on channel #{text_channel.name}")

        except Exception as e:
            logger.warning(f"Guild {guild_id}: Failed to restore player: {e}")

    # Start watchdogs
    _playback_watchdog_task = bot.loop.create_task(playback_watchdog(bot, players))
    _alone_watchdog_task = bot.loop.create_task(alone_watchdog(bot, players))

@bot.event
async def on_disconnect():
    """
    Bot disconnected from Discord - graceful shutdown.

    Properly cancels and awaits all watchdog tasks to prevent race conditions
    where watchdogs might try to queue commands during shutdown. This ensures
    clean task cancellation with no dangling references.

    Side effects:
        - Cancels playback_watchdog and alone_watchdog tasks
        - Awaits task completion to prevent race conditions
        - Disconnects from all voice channels
        - Clears bot presence status
    """
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
    if guild.id in players:
        player = players[guild.id]
        if player.voice_client:
            await safe_disconnect(player.voice_client, force=True)
        await player.shutdown()
        del players[guild.id]

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

    # Cancel and await watchdog tasks
    global _playback_watchdog_task, _alone_watchdog_task

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
            logger.error(f"Guild {guild_id}: Error during shutdown: {e}")

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
from handlers.commands import setup as setup_commands
setup_commands(bot)

logger.info("All commands registered")

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("DISCORD_BOT_TOKEN not found in environment!")
        exit(1)

    # Register signal handlers for graceful shutdown
    # SIGINT = Ctrl+C, SIGTERM = systemd stop / kill
    signal.signal(signal.SIGINT, handle_shutdown_signal)
    signal.signal(signal.SIGTERM, handle_shutdown_signal)

    # Set custom exception handler to suppress aiohttp shutdown warnings
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(custom_exception_handler)

    logger.info("Starting bot...")

    try:
        bot.run(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
