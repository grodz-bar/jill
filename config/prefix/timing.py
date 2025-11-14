# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

"""
Timing Settings - All timing and cooldown configurations

This file contains all timing-related settings organized by category.
These control how fast/slow the bot responds and manages various operations.

Changing some of these values can break things and make the bot more prone
to spam and Discord's API rate-limiting, be careful and test thoroughly.
"""

from typing import Final

# =========================================================================================================
# SPAM PROTECTION (4-LAYER SYSTEM)
# =========================================================================================================

# LAYER 1: PER-USER SPAM SESSIONS
# Detects and stops individual spammers (first filter), handles Discord drip-feed

# Number of commands to trigger spam session
USER_SPAM_SESSION_TRIGGER_COUNT = 3

# Time window to detect spam (seconds)
USER_SPAM_SESSION_TRIGGER_WINDOW = 1.5

# How long spam session lasts (drops commands for this duration)
USER_SPAM_SESSION_DURATION = 5.0

# Send warning messages to spammers
USER_SPAM_WARNINGS_ENABLED = True

# Warning messages (one randomly selected)
USER_SPAM_WARNINGS = [
    "Easy there. I'll do it when you stop button mashing.",
    "Whoa! One thing at a time, please.",
    "Take it easy... spamming won't make me work faster.",
    "Calm down, I heard you the first time.",
]


# ABUSER TIMEOUT SYSTEM (Optional)
# Timeout for heavy abusers

ABUSER_TIMEOUT_ENABLED = False  # Enable timeouts for heavy abusers

ABUSER_TIMEOUT_THRESHOLD = 10   # Commands during spam session to trigger timeout

ABUSER_TIMEOUT_DURATION = 60    # Timeout duration (seconds)

ABUSER_TIMEOUT_MESSAGE = "{user}, you've been timed out for {duration}s. Please don't spam."

ABUSER_TIMEOUT_ESCALATION = True  # Escalate timeout for repeat offenders

ABUSER_TIMEOUT_ESCALATION_MULTIPLIER = 2.0  # Each timeout doubles duration


# LAYER 2: PER-GUILD CIRCUIT BREAKER
# Guild isolation - bad guilds can't affect good guilds
# Commands counted AFTER Layer 1 filtering (single-user spam won't trip circuit)

CIRCUIT_BREAKER_ENABLED = True

# Maximum commands per second before tripping circuit
GUILD_MAX_COMMANDS_PER_SECOND = 3.0

# Maximum queue size per guild
GUILD_MAX_QUEUE_SIZE = 50

# How long circuit stays open after tripping (seconds)
CIRCUIT_BREAK_DURATION = 30.0

# Enable progressive penalties for repeat offenders
CIRCUIT_PROGRESSIVE_PENALTIES = True

# Penalties for repeat trips (multiplies CIRCUIT_BREAK_DURATION)
CIRCUIT_TRIP_PENALTIES = {
    1: 1.0,   # First trip: 30s
    2: 2.0,   # Second trip: 60s
    3: 4.0,   # Third trip: 120s
    4: 8.0,   # Fourth+: 240s (4 minutes)
}

# Reset penalty counter after this many seconds of good behavior
CIRCUIT_PENALTY_RESET_TIME = 300.0  # 5 minutes


# =========================================================================================================
# MESSAGE CLEANUP TIMING
# =========================================================================================================

TTL_CHECK_INTERVAL = 1.0           # Seconds between TTL expiry checks
                                   # IMPORTANT: Must be shorter than USER_COMMAND_TTL (8 seconds)
                                   # LOWER = more precise TTL timing, HIGHER = less CPU usage
                                   # Good rule: Set to 1/4 of your shortest TTL for responsive cleanup

USER_COMMAND_TTL = 8.0             # Seconds before user command messages are deleted
                                   # LOWER = cleaner chat, HIGHER = users can see their commands longer
                                   # Used for all user commands (!play, !skip, !tracks, etc.)

MESSAGE_SETTLE_DELAY = 0.5         # Seconds to wait for new messages to settle
                                   # LOWER = faster responses, HIGHER = more stable

HISTORY_CLEANUP_INTERVAL = 120     # Seconds between full channel history scans (2 min)
                                   # LOWER = more frequent cleanup, HIGHER = less CPU usage
                                   # This is independent of TTL-based cleanup

CLEANUP_HISTORY_LIMIT = 50         # How many recent messages to check during history scan
                                   # HIGHER = cleans more thoroughly, LOWER = faster

USER_COMMAND_MAX_LENGTH = 2000     # Max length of user commands to clean up
                                   # Discord message limit is 2000 characters
                                   # Used to identify user command messages during cleanup

CLEANUP_SAFE_AGE_THRESHOLD = 120   # Seconds - safe age for message deletion during history scan (2 min)
                                   # LOWER = deletes newer messages, HIGHER = keeps longer
                                   # Prevents deleting messages users might still be reading

CLEANUP_BATCH_SIZE = 75            # Messages grouped together for bulk deletion
                                   # Discord allows up to 100 messages per bulk delete operation
                                   # HIGHER = fewer API calls, faster cleanup, but larger failure batches
                                   # LOWER = more API calls, slower cleanup, but smaller failure batches

CLEANUP_BATCH_DELAY = 0.5          # Seconds delay between cleanup batches
                                   # LOWER = faster cleanup, HIGHER = safer for Discord API

MESSAGE_BURIAL_CHECK_LIMIT = 40    # How many messages to check after "now serving" message
                                   # HIGHER = checks more messages (more accurate but slower)
                                   # Used to decide if "now serving" message is buried by other messages

MESSAGE_BURIAL_THRESHOLD = 4       # How many messages = "buried" (bot resends "now serving")
                                   # LOWER = resends more often, HIGHER = keeps editing longer
                                   # If 4+ messages appear after "now serving", bot sends a new message

SPAM_CLEANUP_DELAY = 20            # Seconds to wait before cleaning up spam messages
                                   # LOWER = cleans faster, HIGHER = lets users see warning messages

# =========================================================================================================
# AUTO-PAUSE TIMING
# =========================================================================================================

ALONE_PAUSE_DELAY = 10             # Seconds alone before auto-pause
                                   # LOWER = pauses faster, HIGHER = waits longer

ALONE_DISCONNECT_DELAY = 600       # Seconds alone before auto-disconnect (10 min)
                                   # LOWER = disconnects faster, HIGHER = stays longer

# =========================================================================================================
# MESSAGE LIFETIMES (seconds) - How long each message type stays visible
# =========================================================================================================

# Used by systems.cleanup.CleanupManager to schedule deletions. Status embeds
# are edited in place, and these TTLs govern follow-up messages such as queue
# lists, shuffle toggles, and errors.

MESSAGE_TTL = {
    'now_serving': 600,            # Current track info - protected while playing
    'pause': 10,                   # "Paused" message
    'resume': 10,                  # "Resumed" message
    'stop': 20,                    # "Stopped" message
    'queue': 30,                   # !queue command output
    'tracks': 90,                  # !tracks command output (longer to read)
    'playlists': 90,               # !playlists command output (longer to read)
    'help': 120,                   # !help command output (wall of text)
    'shuffle': 30,                 # Shuffle mode confirmation
    'error_quick': 10,             # Quick error messages
    'error': 15,                   # Standard error messages
}

# =========================================================================================================
# LAYER 4: POST-EXECUTION COOLDOWNS (per command)
# =========================================================================================================
# Cooldowns prevent immediate re-execution after a command completes.
# These work WITH spam sessions (Layer 1) to provide comprehensive protection.
# Spam sessions handle rate limiting, cooldowns handle post-execution delays.

# Playback control commands
SKIP_COOLDOWN = 1.0                # Can't skip again for 1s after skip
PAUSE_COOLDOWN = 1.5               # Can't pause/resume again for 1.5s
STOP_COOLDOWN = 2.0                # Can't stop again for 2s
PREVIOUS_COOLDOWN = 1.5            # Can't go back again for 1.5s
PLAY_JUMP_COOLDOWN = 1.0           # Can't jump to track again for 1s

# Library/queue commands
QUEUE_COOLDOWN = 1.0               # Can't show queue again for 1s
TRACKS_COOLDOWN = 1.0              # Can't switch playlist again for 1s
PLAYLISTS_COOLDOWN = 1.0           # Can't list playlists again for 1s

# Other commands
SHUFFLE_COOLDOWN = 2.0             # Can't toggle shuffle again for 2s
HELP_COOLDOWN = 1.0                # Can't show help again for 1s


# =========================================================================================================
# ADVANCED TIMING SETTINGS (Don't change unless you know what you're doing)
# =========================================================================================================

VOICE_CONNECT_DELAY = 0.15               # Wait for Discord voice handshake (prevents crashes)
VOICE_SETTLE_DELAY = 0.15                # Let voice settle between tracks (prevents audio glitches)
VOICE_RECONNECT_DELAY = 0.30             # Wait during voice reconnection (prevents race conditions)
VOICE_CONNECTION_MAX_WAIT = 0.5          # Max wait for voice connection (500ms)
VOICE_CONNECTION_CHECK_INTERVAL = 0.05   # Check voice connection every 50ms
FRAME_DURATION = 0.02                    # Opus frame duration (20ms) for graceful stops

# Track Change Settling - Wait time after stopping before starting new track
# This delay allows Discord's audio buffers to fully drain after stop(), preventing
# pop and scratchiness artifacts when the next track starts playing.
# Based on testing: direct stop() + 1s delay = clean audio (matches manual pause workflow)
TRACK_CHANGE_SETTLE_DELAY = 1.0          # Wait after stop before playing next track (1000ms)
                                         # LOWER = faster track changes, HIGHER = cleaner audio transition
                                         # 1s prevents pop/scratchiness when next track starts

# FFmpeg Audio Options - Controls playback latency and buffering behavior
# Format: Space-separated command-line options passed to FFmpeg before reading input
# Default optimizes for low latency and real-time playback of opus files
FFMPEG_BEFORE_OPTIONS: Final[str] = '-hide_banner -loglevel error -nostdin -re -fflags +nobuffer'
# Breakdown of default options:
#   -hide_banner      : Suppress FFmpeg version banner (cleaner logs)
#   -loglevel error   : Only log errors (reduces noise)
#   -nostdin          : Don't read from stdin (prevents FFmpeg hanging)
#   -re               : Read input at native frame rate (real-time playback, prevents rushing)
#   -fflags +nobuffer : Reduce buffering delay (lower latency, faster start)
# Advanced tuning: Adjust -analyzeduration/-probesize for faster startup if needed
# Note: -vn flag (ignore video streams) not needed since we only play audio files

MAX_HISTORY = 100                        # Max tracks to remember (prevents memory bloat)
COMMAND_QUEUE_TIMEOUT = 0.5              # Max wait for queue operations (don't wait forever)

WATCHDOG_INTERVAL = 600                  # Check for stuck playback every 10 minutes
WATCHDOG_TIMEOUT = 660                   # Consider playback stuck after 11 minutes

CALLBACK_MIN_INTERVAL = 1.0              # Min time between callback-triggered track advances
ALONE_WATCHDOG_INTERVAL = 10             # Check alone status every 10 seconds

# =========================================================================================================
# VOICE HEALTH ADAPTIVE MONITORING
# =========================================================================================================

# Voice Health Adaptive Monitoring
# The bot adjusts check frequency based on connection quality:
# - Normal (35s): Everything is fine, relaxed monitoring
# - Suspicious (10s): Marginal latency detected, watching closely
# - Post-Reconnect (8s): Just reconnected, verify fix worked quickly
# - Recovery (20s): Fix is working but staying vigilant
#
# These are the default intervals used by the adaptive system:
VOICE_HEALTH_NORMAL_INTERVAL: Final[float] = 35.0      # Check interval when healthy
VOICE_HEALTH_SUSPICIOUS_INTERVAL: Final[float] = 10.0  # Check interval when issues detected
VOICE_HEALTH_POST_RECONNECT_INTERVAL: Final[float] = 8.0  # Check after reconnect
VOICE_HEALTH_RECOVERY_INTERVAL: Final[float] = 20.0    # Check during recovery phase

# Latency thresholds (in seconds)
VOICE_HEALTH_MARGINAL_LATENCY: Final[float] = 0.150   # 150ms - start watching closely
VOICE_HEALTH_BAD_LATENCY: Final[float] = 0.250       # 250ms - reconnect needed

# Recovery settings
VOICE_HEALTH_GOOD_CHECKS_FOR_NORMAL: Final[int] = 3  # Good checks before returning to normal
VOICE_HEALTH_RECONNECT_COOLDOWN: Final[float] = 30.0 # Minimum seconds between reconnects
