"""
Slash Mode Timing Configuration

Timing and delay settings specific to slash mode.
"""

# Control panel update settings
UPDATE_THROTTLE_TIME = 2.0  # Minimum seconds between panel updates
CONTROL_PANEL_TIMEOUT = 300  # Button interaction timeout (5 minutes)

# Startup delays
STARTUP_MESSAGE_DELAY = 5.0  # Wait before initializing panels on startup

# Response timeouts
INTERACTION_TIMEOUT = 15.0  # Discord interaction timeout
DEFER_TIMEOUT = 3.0  # How long before deferring response

# Message update delays
MESSAGE_UPDATE_COOLDOWN = 1.0  # Cooldown between message edits
MESSAGE_SETTLE_DELAY = 0.5  # Seconds to wait for new messages to settle

# Connection delays (shared with prefix but may differ)
VOICE_CONNECT_DELAY = 0.5  # Delay after connecting to voice

# Track Change Settling - Wait time after stopping before starting new track
# This delay allows Discord's audio buffers to fully drain after stop(), preventing
# pop and scratchiness artifacts when the next track starts playing.
TRACK_CHANGE_SETTLE_DELAY = 1.0  # Wait after stop before playing next track (1000ms)

# Core playback timing (shared with playback.py)
VOICE_SETTLE_DELAY = 0.05  # Let voice settle between tracks (prevents audio glitches)
VOICE_RECONNECT_DELAY = 0.30  # Wait during voice reconnection (prevents race conditions)
VOICE_CONNECTION_MAX_WAIT = 0.5  # Max wait for voice connection (500ms)
VOICE_CONNECTION_CHECK_INTERVAL = 0.05  # Check voice connection every 50ms
CALLBACK_MIN_INTERVAL = 1.0  # Min time between callback-triggered track advances
FRAME_DURATION = 0.02  # Opus frame duration (20ms) for graceful stops

# Button interaction throttling (control panel updates)
DEBOUNCE_WINDOW = 0.5  # Debounce window for rapid button clicks
COMMAND_COOLDOWN = 1.0  # Cooldown for button interactions

__all__ = [
    'UPDATE_THROTTLE_TIME',
    'CONTROL_PANEL_TIMEOUT',
    'STARTUP_MESSAGE_DELAY',
    'INTERACTION_TIMEOUT',
    'DEFER_TIMEOUT',
    'MESSAGE_UPDATE_COOLDOWN',
    'MESSAGE_SETTLE_DELAY',
    'VOICE_CONNECT_DELAY',
    'TRACK_CHANGE_SETTLE_DELAY',
    'VOICE_SETTLE_DELAY',
    'VOICE_RECONNECT_DELAY',
    'VOICE_CONNECTION_MAX_WAIT',
    'VOICE_CONNECTION_CHECK_INTERVAL',
    'CALLBACK_MIN_INTERVAL',
    'FRAME_DURATION',
    'DEBOUNCE_WINDOW',
    'COMMAND_COOLDOWN',
]
