# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

r"""
========================================================================================================
JILL MUSIC BOT - AUDIO & VOICE SETTINGS
========================================================================================================

This file contains audio playback and voice connection settings.
These settings work in BOTH prefix mode (!play) and slash mode (/play).

Most users won't need to change these unless experiencing audio quality or connection issues.

HOW TO CUSTOMIZE:
  1. Find the setting you want to change below
  2. Change 'None' to your desired value (see examples in comments)
  3. Save the file and restart the bot

DOCKER USERS:
  Leave settings as 'None' and create a .env file instead (see .env.example)

PRIORITY:
  Python setting (if not None) > .env file > built-in default

RESTART REQUIRED:
  All changes require restarting the bot to take effect.
  - Linux: sudo systemctl restart jill.service
  - Windows: Stop bot (Ctrl+C) and restart

FOR OTHER SETTINGS:
  - Common settings: See basic_settings.py
  - Internal constants: See advanced.py

========================================================================================================
"""

import os
from typing import Final

# =========================================================================================================
# Internal helper functions (used by settings below)
# =========================================================================================================

def _str_to_bool(value):
    """Convert string to boolean (for environment variables)."""
    if isinstance(value, bool):
        return value
    return str(value).lower() in ('true', '1', 'yes', 'on')

def _get_config(python_value, env_name, default, converter=None):
    """Get configuration value using priority system (Python > .env > default)."""
    if python_value is not None:
        return python_value
    env_value = os.getenv(env_name)
    if env_value is not None:
        return converter(env_value) if converter else env_value
    return default

# =========================================================================================================
# AUDIO FORMAT SETTINGS
# =========================================================================================================

# ----------------------------------------
# Audio Format Support
# ----------------------------------------
# What audio formats can the bot play?
#
# ALLOW_TRANSCODING:
#   True = Play MP3, FLAC, WAV, M4A, OGG, OPUS (uses more CPU)
#   False = Only play .opus files (best performance, Discord's native format)
#
# RECOMMENDATION: Convert your music to .opus format for best results
# See README/04-Converting-To-Opus.txt for instructions
#
ALLOW_TRANSCODING = None  # Leave as None to use .env or default (True)
ALLOW_TRANSCODING = _get_config(ALLOW_TRANSCODING, 'ALLOW_TRANSCODING', True, _str_to_bool)

# ----------------------------------------
# Supported Audio Formats
# ----------------------------------------
# Supported formats (in preference order - .opus is always preferred)
# Don't change this unless you know what you're doing
#
SUPPORTED_AUDIO_FORMATS = ('.opus', '.mp3', '.flac', '.wav', '.m4a', '.ogg')

# =========================================================================================================
# FFMPEG SETTINGS
# =========================================================================================================

# ----------------------------------------
# FFmpeg Options
# ----------------------------------------
# Command-line options passed to FFmpeg when playing audio
# These are optimized for low latency and real-time playback
#
# Options explained:
#   -hide_banner = Don't show FFmpeg's startup banner
#   -loglevel error = Only show errors (quieter console)
#   -nostdin = Don't read from stdin (prevents hangs)
#   -re = Read input at native frame rate (real-time playback)
#   -fflags +nobuffer = Minimize buffering for lower latency
#
FFMPEG_BEFORE_OPTIONS: Final[str] = '-hide_banner -loglevel error -nostdin -re -fflags +nobuffer'

# =========================================================================================================
# VOICE CONNECTION TIMING
# =========================================================================================================
#
# Low-level timing for Discord voice connections
# These control voice handshakes, reconnections, and connection checks
# DON'T CHANGE THESE unless experiencing specific voice connection issues

# ----------------------------------------
# Connection Timing
# ----------------------------------------
VOICE_CONNECT_DELAY = 0.25  # Wait for Discord handshake after connecting (250ms)
VOICE_SETTLE_DELAY = 0.2  # Let voice settle between tracks (200ms)
VOICE_RECONNECT_DELAY = 0.30  # Wait during reconnection (300ms)
VOICE_CONNECTION_MAX_WAIT = 0.5  # Max wait time for connection check (500ms)
VOICE_CONNECTION_CHECK_INTERVAL = 0.05  # Check connection every 50ms

# =========================================================================================================
# PLAYBACK TIMING
# =========================================================================================================
#
# Audio playback timing constants to prevent glitches and artifacts
# DON'T CHANGE THESE unless experiencing audio quality issues

# ----------------------------------------
# Playback Timing
# ----------------------------------------
TRACK_CHANGE_SETTLE_DELAY = 1.0  # Wait after stopping before new track (prevents crackling)
MESSAGE_SETTLE_DELAY = 0.5  # Wait for new messages to settle (500ms)
CALLBACK_MIN_INTERVAL = 1.0  # Minimum time between callback-triggered track changes (1 second)
FRAME_DURATION = 0.02  # Opus frame duration (20ms) for graceful stops

# =========================================================================================================
# VOICE CONNECTION HEALTH MONITORING
# =========================================================================================================
#
# Auto-fix stuttering audio from network issues
# The bot checks voice connection health and reconnects if needed
# This fixes stuttering caused by high latency or dead WebSocket connections

# ----------------------------------------
# Voice Health Check
# ----------------------------------------
# Should the bot monitor voice connection health and auto-reconnect?
#
# True = Auto-reconnects when latency is too high (fixes stuttering)
# False = No monitoring (may stutter if connection degrades)
#
VOICE_HEALTH_CHECK_ENABLED = None  # Leave as None to use .env or default (True)
VOICE_HEALTH_CHECK_ENABLED = _get_config(VOICE_HEALTH_CHECK_ENABLED, 'VOICE_HEALTH_CHECK', True, _str_to_bool)

# ----------------------------------------
# Technical Constants for Voice Health Monitoring
# ----------------------------------------
# (Don't change unless you're experiencing specific issues)

# Basic monitoring
VOICE_HEALTH_CHECK_IN_WATCHDOG = True  # Monitor during playback
VOICE_HEALTH_LATENCY_THRESHOLD = 250.0  # Milliseconds before reconnect
VOICE_HEALTH_CHECK_INTERVAL = 10.0  # Seconds between checks
VOICE_HEALTH_RECONNECT_COOLDOWN = 30.0  # Seconds before retry

# Adaptive health check intervals - monitoring frequency adapts to connection state
VOICE_HEALTH_NORMAL_INTERVAL: Final[float] = 35.0  # Healthy connection - relaxed monitoring
VOICE_HEALTH_SUSPICIOUS_INTERVAL: Final[float] = 10.0  # Marginal latency detected - watch closely
VOICE_HEALTH_POST_RECONNECT_INTERVAL: Final[float] = 8.0  # Just reconnected - verify it worked
VOICE_HEALTH_RECOVERY_INTERVAL: Final[float] = 20.0  # Connection recovering - stay vigilant

# Latency thresholds for adaptive behavior
VOICE_HEALTH_MARGINAL_LATENCY: Final[float] = 0.150  # 150ms = start watching closely
VOICE_HEALTH_BAD_LATENCY: Final[float] = 0.250  # 250ms = reconnect immediately

# Recovery behavior
VOICE_HEALTH_GOOD_CHECKS_FOR_NORMAL: Final[int] = 3  # 3 good checks before returning to normal interval

# =========================================================================================================
# Export Configuration
# =========================================================================================================

__all__ = [
    # Audio Format
    'ALLOW_TRANSCODING',
    'SUPPORTED_AUDIO_FORMATS',
    # FFmpeg
    'FFMPEG_BEFORE_OPTIONS',
    # Voice Connection Timing
    'VOICE_CONNECT_DELAY',
    'VOICE_SETTLE_DELAY',
    'VOICE_RECONNECT_DELAY',
    'VOICE_CONNECTION_MAX_WAIT',
    'VOICE_CONNECTION_CHECK_INTERVAL',
    # Playback Timing
    'TRACK_CHANGE_SETTLE_DELAY',
    'MESSAGE_SETTLE_DELAY',
    'CALLBACK_MIN_INTERVAL',
    'FRAME_DURATION',
    # Voice Health Monitoring
    'VOICE_HEALTH_CHECK_ENABLED',
    'VOICE_HEALTH_CHECK_IN_WATCHDOG',
    'VOICE_HEALTH_LATENCY_THRESHOLD',
    'VOICE_HEALTH_CHECK_INTERVAL',
    'VOICE_HEALTH_RECONNECT_COOLDOWN',
    'VOICE_HEALTH_NORMAL_INTERVAL',
    'VOICE_HEALTH_SUSPICIOUS_INTERVAL',
    'VOICE_HEALTH_POST_RECONNECT_INTERVAL',
    'VOICE_HEALTH_RECOVERY_INTERVAL',
    'VOICE_HEALTH_MARGINAL_LATENCY',
    'VOICE_HEALTH_BAD_LATENCY',
    'VOICE_HEALTH_GOOD_CHECKS_FOR_NORMAL',
]
