# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

"""
Prefix Mode Spam Protection Configuration

All spam protection settings specific to prefix mode (!play, !skip, etc.).

Prefix mode requires more extensive spam protection because Discord provides NO built-in
rate limiting for text commands. This file contains:
- Command cooldowns: Prevent accidental double-clicks
- Layer 1: Individual user spam detection
- Layer 2: Guild-wide flood protection

Note: Layer 3 (serial queue) is in config/common/spam_protection.py (used by both modes)
"""

# =========================================================================================================
# COMMAND COOLDOWNS - Prevent accidental double-clicks on text commands
# =========================================================================================================
# After a command finishes executing, prevent the same command from running again
# for this many seconds. Helps prevent accidental double-clicks.

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
# LAYER 1: USER SPAM SESSIONS - Individual spam detection
# =========================================================================================================
# Tracks individual users who spam commands too quickly.
# When detected, the user enters a "spam session" with rate limiting.

USER_SPAM_SESSION_TRIGGER_WINDOW = 2.5  # 3 commands in 2.5s = spam detected
USER_SPAM_SESSION_DURATION = 8.0  # Cooldown period before session ends
USER_SPAM_WARNINGS_ENABLED = True  # Show warnings to spammers
USER_SPAM_SESSION_CLEANUP_TIMEOUT = 1800  # Remove inactive sessions after 30 min

# =========================================================================================================
# LAYER 2: CIRCUIT BREAKER - Guild-wide flood protection
# =========================================================================================================
# Protects against entire server flooding the bot with commands.
# If too many commands per second, temporarily locks out the entire guild.
# Progressive penalties increase for repeat offenders.

CIRCUIT_BREAKER_ENABLED = True  # Enable guild-wide rate limiting
GUILD_MAX_COMMANDS_PER_SECOND = 2.5  # Max commands/second for entire server
CIRCUIT_BREAK_DURATION = 20.0  # Lockout duration if limits exceeded
CIRCUIT_PROGRESSIVE_PENALTIES = True  # Increase penalties for repeat offenders
CIRCUIT_PENALTY_RESET_TIME = 180.0  # 3 min of good behavior resets penalty
CIRCUIT_BREAKER_HISTORY_SIZE = 100  # Commands to remember for rate calculation
CIRCUIT_RATE_CALCULATION_WINDOW = 1.0  # Time window for rate calculation

# =========================================================================================================
# EXPORTS
# =========================================================================================================

__all__ = [
    # Command Cooldowns
    'SKIP_COOLDOWN',
    'PAUSE_COOLDOWN',
    'STOP_COOLDOWN',
    'PREVIOUS_COOLDOWN',
    'PLAY_JUMP_COOLDOWN',
    'QUEUE_COOLDOWN',
    'TRACKS_COOLDOWN',
    'PLAYLISTS_COOLDOWN',
    'SHUFFLE_COOLDOWN',
    'HELP_COOLDOWN',
    # Layer 1: User Spam Sessions
    'USER_SPAM_SESSION_TRIGGER_WINDOW',
    'USER_SPAM_SESSION_DURATION',
    'USER_SPAM_WARNINGS_ENABLED',
    'USER_SPAM_SESSION_CLEANUP_TIMEOUT',
    # Layer 2: Circuit Breaker
    'CIRCUIT_BREAKER_ENABLED',
    'GUILD_MAX_COMMANDS_PER_SECOND',
    'CIRCUIT_BREAK_DURATION',
    'CIRCUIT_PROGRESSIVE_PENALTIES',
    'CIRCUIT_PENALTY_RESET_TIME',
    'CIRCUIT_BREAKER_HISTORY_SIZE',
    'CIRCUIT_RATE_CALCULATION_WINDOW',
]
