# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

"""
Timing Settings - All timing and cooldown configurations

This file contains all timing-related settings organized by category.
These control how fast/slow the bot responds and manages various operations.

Settings are organized from most common (top) to most advanced (bottom).
Only change advanced settings if you know what you're doing.
"""

from typing import Final

# =========================================================================================================
# SPAM PROTECTION - Prevents command spam
# =========================================================================================================

# How fast can someone send commands before being warned?
# The bot allows 2 quick commands (like checking !help then using a command)
# If 3 commands arrive within the detection window, spam protection activates
#
# Detection window: How close together commands need to be to count as spam
USER_SPAM_SESSION_TRIGGER_WINDOW = 2.5  # seconds (3 commands in 2.5s = spam)

# Cooldown period: How long spammer must be silent before session ends
USER_SPAM_SESSION_DURATION = 8.0  # seconds (timer resets if they keep spamming)

# Show warning messages when spam is detected?
USER_SPAM_WARNINGS_ENABLED = True  # Set to False to silently block spam


# Advanced: Server-wide protection (rarely needs adjustment)

CIRCUIT_BREAKER_ENABLED = True
# Circuit breaker temporarily locks out entire server if command rate is too high
# Protects against multiple users spamming simultaneously
GUILD_MAX_COMMANDS_PER_SECOND = 2.5  # Max commands/second for entire server
GUILD_MAX_QUEUE_SIZE = 30  # Max queued commands
CIRCUIT_BREAK_DURATION = 20.0  # Lockout duration if limits exceeded


# =========================================================================================================
# MESSAGE CLEANUP - Auto-delete old bot messages to keep chat clean
# =========================================================================================================

# How long to keep user command messages before deleting them (!play, !skip, etc.)
USER_COMMAND_TTL = 8.0  # seconds (lower = cleaner chat, higher = visible longer)

# How long to keep spam warning messages visible
SPAM_CLEANUP_DELAY = 15  # seconds (lets users read the warning)

# How often to check for expired messages
TTL_CHECK_INTERVAL = 1.0  # seconds (should be less than USER_COMMAND_TTL)

# Small delay to let Discord finish sending all related messages
MESSAGE_SETTLE_DELAY = 0.5  # seconds

# Deep cleanup: Scan entire chat history periodically
HISTORY_CLEANUP_INTERVAL = 180  # seconds (3 minutes between full scans)
CLEANUP_HISTORY_LIMIT = 50  # how many recent messages to check
CLEANUP_SAFE_AGE_THRESHOLD = 120  # only delete messages older than 2 minutes

# Bulk delete settings (Discord allows up to 100 messages at once)
CLEANUP_BATCH_SIZE = 95  # messages per batch (near Discord's limit for max efficiency)
CLEANUP_BATCH_DELAY = 1.2  # seconds between batches (respects Discord's 1/sec bulk delete limit)

# "Now playing" message handling
MESSAGE_BURIAL_CHECK_LIMIT = 40  # how many messages to check
MESSAGE_BURIAL_THRESHOLD = 4  # if 4+ messages after "now playing", send new one

# Advanced (don't change)
USER_COMMAND_MAX_LENGTH = 2000  # Discord's max message length

# =========================================================================================================
# AUTO-PAUSE - What happens when bot is alone in voice channel
# =========================================================================================================

ALONE_PAUSE_DELAY = 10  # Seconds to wait before pausing music
ALONE_DISCONNECT_DELAY = 600  # Seconds to wait before leaving channel (10 minutes)

# =========================================================================================================
# MESSAGE LIFETIMES - How long different bot messages stay before being deleted
# =========================================================================================================

MESSAGE_TTL = {
    'now_serving': 600,    # 10 minutes - current track info
    'pause': 10,           # Quick confirmation messages
    'resume': 10,
    'stop': 20,
    'queue': 30,           # 30 seconds - queue list
    'tracks': 90,          # 90 seconds - track list (longer to read)
    'playlists': 90,       # 90 seconds - playlist list
    'help': 120,           # 2 minutes - help text
    'shuffle': 30,         # 30 seconds - shuffle toggle
    'error_quick': 10,     # Quick errors
    'error': 15,           # Standard errors
}

# =========================================================================================================
# COMMAND COOLDOWNS - Prevent accidental double-clicks
# =========================================================================================================
# Prevents the same command from being used again immediately after it finishes

SKIP_COOLDOWN = 1.0         # seconds
PAUSE_COOLDOWN = 1.5
STOP_COOLDOWN = 2.0
PREVIOUS_COOLDOWN = 1.5
PLAY_JUMP_COOLDOWN = 1.0
QUEUE_COOLDOWN = 1.0
TRACKS_COOLDOWN = 1.0
PLAYLISTS_COOLDOWN = 1.0
SHUFFLE_COOLDOWN = 2.0
HELP_COOLDOWN = 1.0


# =========================================================================================================
# ADVANCED SPAM PROTECTION - Internal behavior (default values work well)
# =========================================================================================================

# Progressive penalties: Guilds that spam repeatedly get longer lockouts
# First offense: 30s lockout, Second: 60s, Third: 90s, Fourth+: 120s (max)
CIRCUIT_PROGRESSIVE_PENALTIES = True
CIRCUIT_PENALTY_RESET_TIME = 180.0  # 3 minutes of good behavior resets the penalty counter

# Memory management: Clean up old tracking data to prevent memory leaks
USER_SPAM_SESSION_CLEANUP_TIMEOUT = 1800  # Remove inactive user sessions after 30 minutes

# Rate calculation: How many commands to remember for rate limiting
CIRCUIT_BREAKER_HISTORY_SIZE = 100  # commands (higher = more accurate, uses more memory)
CIRCUIT_RATE_CALCULATION_WINDOW = 1.0  # seconds to calculate rate over

# Command queue: How commands wait to be executed
COMMAND_QUEUE_TIMEOUT = 1.0  # seconds to wait for queue slot
QUEUE_SIZE_WARNING_THRESHOLD = 0.9  # warn when queue is 90% full
PRIORITY_COMMAND_TIMEOUT_MULTIPLIER = 0.5  # critical commands wait half as long


# =========================================================================================================
# ADVANCED PLAYBACK SETTINGS - Fine-tuning for audio quality
# =========================================================================================================

# Voice connection timing (prevents crashes and race conditions)
VOICE_CONNECT_DELAY = 0.25  # wait for Discord handshake
VOICE_SETTLE_DELAY = 0.2  # let voice settle between tracks
VOICE_RECONNECT_DELAY = 0.30  # wait during reconnection
VOICE_CONNECTION_MAX_WAIT = 0.75  # max wait time (750ms)
VOICE_CONNECTION_CHECK_INTERVAL = 0.05  # check every 50ms
FRAME_DURATION = 0.02  # Opus frame duration (20ms)

# Track change delay: Prevents popping/crackling when switching songs
# Discord's audio buffers need time to drain after stopping
TRACK_CHANGE_SETTLE_DELAY = 1.0  # 1 second (lower = faster changes, higher = cleaner audio)

# FFmpeg settings: Controls how audio files are processed
# Optimized for low latency and real-time playback of opus files
FFMPEG_BEFORE_OPTIONS: Final[str] = '-hide_banner -loglevel error -nostdin -re -fflags +nobuffer'

# Playback history and monitoring
MAX_HISTORY = 100  # max tracks to remember in history
WATCHDOG_INTERVAL = 600  # check for stuck playback every 10 minutes
WATCHDOG_TIMEOUT = 660  # consider stuck after 11 minutes
CALLBACK_MIN_INTERVAL = 1.0  # min time between track changes
ALONE_WATCHDOG_INTERVAL = 10  # check if alone every 10 seconds

# =========================================================================================================
# VOICE HEALTH MONITORING - Auto-reconnect when connection quality drops
# =========================================================================================================
# The bot monitors voice latency and reconnects automatically if quality degrades.
# Check frequency adapts based on connection state:
#   - Normal (35s): Everything working fine, relaxed monitoring
#   - Suspicious (10s): Latency getting high, watching closely
#   - Post-Reconnect (8s): Just reconnected, verify it worked
#   - Recovery (20s): Connection improving, stay vigilant

# Adaptive check intervals
VOICE_HEALTH_NORMAL_INTERVAL: Final[float] = 35.0  # healthy connection
VOICE_HEALTH_SUSPICIOUS_INTERVAL: Final[float] = 10.0  # marginal latency detected
VOICE_HEALTH_POST_RECONNECT_INTERVAL: Final[float] = 8.0  # right after reconnecting
VOICE_HEALTH_RECOVERY_INTERVAL: Final[float] = 20.0  # connection recovering

# Latency thresholds: When to take action
VOICE_HEALTH_MARGINAL_LATENCY: Final[float] = 0.150  # 150ms = start watching closely
VOICE_HEALTH_BAD_LATENCY: Final[float] = 0.250  # 250ms = reconnect immediately

# Recovery behavior
VOICE_HEALTH_GOOD_CHECKS_FOR_NORMAL: Final[int] = 3  # 3 good checks before returning to normal
VOICE_HEALTH_RECONNECT_COOLDOWN: Final[float] = 30.0  # minimum 30s between reconnect attempts
