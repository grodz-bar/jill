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

# Button interaction cooldowns (spam protection Layer 4)
# Prevents users from spam-clicking control panel buttons
BUTTON_PLAY_PAUSE_COOLDOWN = 0.5  # Play/pause toggle (fast response)
BUTTON_SKIP_COOLDOWN = 1.5  # Skip to next track
BUTTON_PREVIOUS_COOLDOWN = 1.5  # Return to previous track
BUTTON_SHUFFLE_COOLDOWN = 2.0  # Toggle shuffle mode (less frequent)
BUTTON_STOP_COOLDOWN = 1.0  # Stop playback

# Controls whether to show "slow down" message when button cooldown triggered
# False = silent (recommended), True = show ephemeral message to user
BUTTON_SHOW_COOLDOWN_MESSAGE = False

__all__ = [
    'UPDATE_THROTTLE_TIME',
    'CONTROL_PANEL_TIMEOUT',
    'STARTUP_MESSAGE_DELAY',
    'INTERACTION_TIMEOUT',
    'DEFER_TIMEOUT',
    'MESSAGE_UPDATE_COOLDOWN',
    'BUTTON_PLAY_PAUSE_COOLDOWN',
    'BUTTON_SKIP_COOLDOWN',
    'BUTTON_PREVIOUS_COOLDOWN',
    'BUTTON_SHUFFLE_COOLDOWN',
    'BUTTON_STOP_COOLDOWN',
    'BUTTON_SHOW_COOLDOWN_MESSAGE',
]
