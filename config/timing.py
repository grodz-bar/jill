"""
Timing Settings - All timing and cooldown configurations

This file contains all timing-related settings organized by category.
These control how fast/slow the bot responds and manages various operations.
"""

# =========================================================================================================
# SPAM PROTECTION TIMING
# =========================================================================================================

USER_COMMAND_SPAM_THRESHOLD = 0.5  # Min seconds between commands from same user
                                   # LOWER = more lenient (allows faster commands)
                                   # HIGHER = stricter (forces longer wait)

GLOBAL_RATE_LIMIT = 0.15           # Min seconds between ANY commands (allows max 6.7 commands per second)
                                   # LOWER = more lenient (allows faster commands)
                                   # HIGHER = stricter (forces longer wait)

USER_SPAM_WARNING_THRESHOLD = 3    # Show spam warning message after N rapid attempts
                                   # LOWER = warns sooner, HIGHER = more tolerant

USER_SPAM_RESET_COOLDOWN = 2.0     # Seconds of no spam before resetting spam count
                                   # LOWER = resets faster, HIGHER = remembers longer

SPAM_WARNING_COOLDOWN = 19        # Seconds between spam warning messages
                                   # LOWER = more warning messages, HIGHER = less spam warnings

USER_COMMAND_MAX_LENGTH = 2000     # Max length of user commands to clean up
                                   # LOWER = cleans shorter commands, HIGHER = cleans longer commands
                                   # Discord message limit is 2000 characters

# =========================================================================================================
# MESSAGE CLEANUP TIMING
# =========================================================================================================

TTL_CHECK_INTERVAL = 1.0           # Seconds between TTL expiry checks
                                   # IMPORTANT: Must be shorter than USER_COMMAND_TTL (8 seconds)
                                   # LOWER = more precise TTL timing, HIGHER = less CPU usage
                                   # Good rule: Set to 1/4 of your shortest TTL for responsive cleanup

USER_COMMAND_TTL = 8.0             # Seconds before user command messages are deleted
                                   # LOWER = cleaner chat, HIGHER = users can see their commands longer
                                   # Used for all user commands (!play, !skip, !library, etc.)

MESSAGE_SETTLE_DELAY = 0.5         # Seconds to wait for new messages to settle
                                   # LOWER = faster responses, HIGHER = more stable

HISTORY_CLEANUP_INTERVAL = 120     # Seconds between full channel history scans (2 min)
                                   # LOWER = more frequent cleanup, HIGHER = less CPU usage
                                   # This is independent of TTL-based cleanup

CLEANUP_HISTORY_LIMIT = 50         # How many recent messages to check during history scan
                                   # HIGHER = cleans more thoroughly, LOWER = faster

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
# COMMAND COOLDOWNS
# =========================================================================================================

SKIP_COOLDOWN = 2.0                # Time after !skip before another !skip works
PLAY_COOLDOWN = 2.0                # Time after !play before another !play works  
STOP_COOLDOWN = 2.0                # Time after !stop before another !stop works
RECONNECT_COOLDOWN = 3.0           # Time after channel switch before commands work

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

MESSAGE_TTL = {
    'now_serving': 600,            # Current track info - protected while playing
    'pause': 10,                   # "Paused" message
    'resume': 10,                  # "Resumed" message  
    'stop': 20,                    # "Stopped" message
    'queue': 30,                   # !queue command output
    'library': 90,                 # !library command output (longer to read)
    'help': 120,                   # !help command output (wall of text)
    'shuffle': 30,                 # Shuffle mode confirmation
    'error_quick': 10,             # Quick error messages
    'error': 15,                   # Standard error messages
}

# =========================================================================================================
# COMMAND DEBOUNCING SETTINGS (per command)
# =========================================================================================================

# Queue command debouncing
QUEUE_DEBOUNCE_WINDOW = 2.0        # Wait time for spam to stop (seconds)
QUEUE_COOLDOWN = 1.0               # Cooldown after execution (seconds)
QUEUE_SPAM_THRESHOLD = 5           # Times user can spam before warning

# Library command debouncing
LIBRARY_DEBOUNCE_WINDOW = 1.5      # Wait time for spam to stop (seconds)
LIBRARY_COOLDOWN = 0.5             # Cooldown after execution (seconds)
LIBRARY_SPAM_THRESHOLD = 5         # Times user can spam before warning

# Play jump command debouncing (!play [number])
# Note: Normal !play (join/resume) doesn't use debouncing - only track jumping does
PLAY_JUMP_DEBOUNCE_WINDOW = 1.0    # Wait time for spam to stop (seconds)
PLAY_JUMP_COOLDOWN = 1.0           # Cooldown after execution (seconds)
PLAY_JUMP_SPAM_THRESHOLD = 5       # Times user can spam before warning

# Pause command debouncing
PAUSE_DEBOUNCE_WINDOW = 2.0        # Wait time for spam to stop (seconds)
PAUSE_COOLDOWN = 2.0               # Cooldown after execution (seconds)
PAUSE_SPAM_THRESHOLD = 5           # Times user can spam before warning

# Skip command debouncing
SKIP_DEBOUNCE_WINDOW = 1.0         # Wait time for spam to stop (seconds)
SKIP_COOLDOWN = 1.0                # Cooldown after execution (seconds)
SKIP_SPAM_THRESHOLD = 10           # Times user can spam before warning

# Stop command debouncing
STOP_DEBOUNCE_WINDOW = 2.0         # Wait time for spam to stop (seconds)
STOP_COOLDOWN = 2.0                # Cooldown after execution (seconds)
STOP_SPAM_THRESHOLD = 5            # Times user can spam before warning

# Previous command debouncing
PREVIOUS_DEBOUNCE_WINDOW = 2.5     # Wait time for spam to stop (seconds)
PREVIOUS_COOLDOWN = 2.0            # Cooldown after execution (seconds)
PREVIOUS_SPAM_THRESHOLD = 5        # Times user can spam before warning

# Shuffle command debouncing
SHUFFLE_DEBOUNCE_WINDOW = 2.5      # Wait time for spam to stop (seconds)
SHUFFLE_COOLDOWN = 2.0             # Cooldown after execution (seconds)
SHUFFLE_SPAM_THRESHOLD = 5         # Times user can spam before warning

# Unshuffle command debouncing
UNSHUFFLE_DEBOUNCE_WINDOW = 2.5    # Wait time for spam to stop (seconds)
UNSHUFFLE_COOLDOWN = 2.0           # Cooldown after execution (seconds)
UNSHUFFLE_SPAM_THRESHOLD = 5       # Times user can spam before warning

# Help command debouncing
HELP_DEBOUNCE_WINDOW = 1.0         # Wait time for spam to stop (seconds)
HELP_COOLDOWN = 1.0                # Cooldown after execution (seconds)
HELP_SPAM_THRESHOLD = 4            # Times user can spam before warning

# =========================================================================================================
# ADVANCED TIMING SETTINGS (Don't change unless you know what you're doing)
# =========================================================================================================

VOICE_CONNECT_DELAY = 0.15               # Wait for Discord voice handshake (prevents crashes)
VOICE_SETTLE_DELAY = 0.05                # Let voice settle between tracks (prevents audio glitches)
VOICE_RECONNECT_DELAY = 0.30             # Wait during voice reconnection (prevents race conditions)
                                         # Slightly higher delay (0.30) = safer reconnect on slower networks.
VOICE_CONNECTION_MAX_WAIT = 0.5          # Max wait for voice connection (500ms)
VOICE_CONNECTION_CHECK_INTERVAL = 0.05   # Check voice connection every 50ms
FRAME_DURATION = 0.02                    # Opus frame duration (20ms) for graceful stops

MAX_HISTORY = 100                        # Max tracks to remember (prevents memory bloat)
COMMAND_QUEUE_MAXSIZE = 100              # Max commands in queue (prevents memory exhaustion)
COMMAND_QUEUE_TIMEOUT = 0.5              # Max wait for queue operations (don't wait forever)

WATCHDOG_INTERVAL = 600                  # Check for stuck playback every 10 minutes
WATCHDOG_TIMEOUT = 660                   # Consider playback stuck after 11 minutes

# Legacy constants (kept for compatibility)
CALLBACK_MIN_INTERVAL = 1.0              # Min time between callback-triggered track advances
ALONE_WATCHDOG_INTERVAL = 10             # Check alone status every 10 seconds

