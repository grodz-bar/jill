"""
VA-11 Hall-A Discord Music Bot - Refactored Architecture
========================================================
VERSION: 1.0.0 - Modular architecture with composition pattern
========================================================

A Discord music bot built with clean, modular architecture.
See AGENTS.md for development guidelines.
"""

import disnake
from disnake.ext import commands
import asyncio
import logging
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

    logger.info(f'Bot connected as {bot.user}')

    # Start watchdogs
    _playback_watchdog_task = bot.loop.create_task(playback_watchdog(bot, players))
    _alone_watchdog_task = bot.loop.create_task(alone_watchdog(bot, players))

@bot.event
async def on_disconnect():
    """Bot disconnected from Discord."""
    # Cancel watchdogs
    if _playback_watchdog_task and not _playback_watchdog_task.done():
        _playback_watchdog_task.cancel()
    if _alone_watchdog_task and not _alone_watchdog_task.done():
        _alone_watchdog_task.cancel()

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

    logger.info("Starting bot...")
    try:
        bot.run(token)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
