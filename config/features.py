"""
Feature Toggles

This file contains feature switches and adjustments for the major bot behaviors.

QUICK GUIDE:
- Set to True = feature enabled, False = feature disabled
- Restart bot after changes:
  * Linux: sudo systemctl restart jill.service
  * Windows: Stop bot (Ctrl+C) and restart it
- Most features work independently (no dependencies)
- WARNING: Keep SPAM_PROTECTION_ENABLED = True (prevents API rate limits)

"""

# =========================================================================================================
# MESSAGE CLEANUP FEATURES
# =========================================================================================================

DELETE_OTHER_BOTS = True           # Delete other bots' messages during cleanup
                                   # False = only delete our messages (keeps other bots' spam)

AUTO_CLEANUP_ENABLED = True        # Enable automatic message cleanup (background worker)
                                   # False = manual cleanup only (chat gets cluttered)

TTL_CLEANUP_ENABLED = True         # Auto-delete messages after TTL expires
                                   # False = messages stay forever

# CLEANUP SYSTEMS EXPLAINED:
# --------------------------
# SCHEDULED CLEANUP (TTL-based): Messages get "expiration dates" and are deleted when time is up
# CHANNEL SWEEP (History scan): Scans channel history periodically + when spam detected
# 
# Why both? SCHEDULED CLEANUP is fast for known messages, CHANNEL SWEEP catches missed ones.
# Together they ensure clean chat with redundancy.
#
# IMPORTANT: Both cleanup systems work in the text channel where you first used !play.
# Cleanup features activate after the first !play command. The bot automatically remembers 
# which channel to clean up and restores it after restart. Channel data is stored in 
# last_channels.json and managed transparently.

# =========================================================================================================
# ANTI-SPAM FEATURES
# =========================================================================================================

# SPAM PROTECTION EXPLAINED:
# --------------------------
# The bot automatically prevents spam and abuse in multiple ways:
# - Bot ignores commands sent too quickly (prevents spam)
# - Bot checks permissions before doing expensive operations (fast errors)
# - Bot limits how many commands can run at once (protects Discord API)
# - Bot waits for spam to stop before executing commands (prevents flooding)
# - Bot processes commands one at a time (prevents conflicts)
# - Bot adds cooldowns after commands finish (prevents rapid re-execution)
#
# This keeps the bot stable and prevents abuse while being user-friendly.

SPAM_PROTECTION_ENABLED = True     # CRITICAL: Prevents API rate limits
                                   # False = NO PROTECTION (can break bot!)

SPAM_WARNING_ENABLED = True      # Show spam warning responses when users spam commands
                                   # False = silent (users won't know why commands don't work)

# =========================================================================================================
# AUTO-PAUSE FEATURES
# =========================================================================================================

AUTO_PAUSE_ENABLED = True          # Auto-pause when alone in voice channel (default: 10s)
                                   # False = keeps playing to empty channel

AUTO_DISCONNECT_ENABLED = True     # Auto-disconnect when alone too long (default: 10min)
                                   # False = stays connected forever

# =========================================================================================================
# PLAYBACK FEATURES
# =========================================================================================================

SHUFFLE_MODE_ENABLED = True        # Enable !shuffle and !unshuffle commands
                                   # False = commands return "feature disabled"

QUEUE_DISPLAY_ENABLED = True       # Enable !queue command (shows upcoming tracks)
                                   # False = command returns "feature disabled"

QUEUE_DISPLAY_COUNT = 3            # Number of upcoming tracks to show in !queue
                                   # Higher = more tracks shown (longer messages)

LIBRARY_DISPLAY_ENABLED = True     # Enable !library command (shows all tracks)
                                   # False = command returns "feature disabled"

LIBRARY_PAGE_SIZE = 20             # Number of tracks per page in !library
                                   # Higher = more tracks per page (longer messages)

# =========================================================================================================
# ADVANCED FEATURES
# =========================================================================================================

SMART_MESSAGE_MANAGEMENT = True    # Edit "now serving" messages instead of sending new ones
                                   # False = more messages in chat (uses more API calls)

BATCH_DELETE_ENABLED = True        # Delete messages in batches (faster cleanup)
                                   # False = slower cleanup (more API calls)

VOICE_RECONNECT_ENABLED = True     # Auto-reconnect on voice errors
                                   # False = manual reconnection required

# =========================================================================================================
# FUTURE FEATURES (WIP)
# =========================================================================================================

#PLAYLIST_MODE_ENABLED = False      # Enable playlist functionality  
#CROSS_SERVER_SYNC_ENABLED = False  # Enable cross-server synchronization
#VOLUME_CONTROL_ENABLED = False     # Enable volume control commands
#(Volume control unlikely since it causes so many freaking issues.)


