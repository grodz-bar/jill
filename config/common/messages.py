# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

"""
Common Messages - Shared Between Both Modes

Mode-specific messages stay in:
- config/prefix/messages.py (prefix mode only)
- config/slash/messages.py (slash mode only)

Architecture:
- Common messages loaded first (this file)
- Mode-specific messages loaded second (can override if needed)
- Final MESSAGES dict = {**COMMON_MESSAGES, **MODE_MESSAGES} (merged at runtime)
"""

COMMON_MESSAGES = {
    # ===================================================================
    # SHARED ERRORS - Used by both prefix and slash modes
    # ===================================================================
    # These errors have consistent behavior across both command modes.
    # Prefix personality (playful, emoji-rich) is used for better UX.

    # Voice channel validation
    'error_not_in_voice': "🤔 Are you hiding?",
    'error_no_permission': "🚫 **{channel}** is off-limits!",
    'error_not_connected': "❌ I'm not connected to voice!",
    'error_cant_connect': "❌ Can't join that channel: {error}",

    # Playback state errors
    'error_not_playing': "😒 I'm not even playing anything.",
    'error_no_previous': "❌ No previous track available.",

    # Library/track errors
    'error_no_tracks': "🎵 No tracks in the jukebox!",
    'error_invalid_track': "❌ Track #{number} doesn't exist. Current playlist has {total} tracks.",
    'error_track_not_found': "❌ '{query}'? Try `{prefix}tracks` to see what we have.",

    # Playlist errors
    'error_no_playlists': "❌ No playlists found. Music must be in subfolders.",
    'error_playlist_not_found': "❌ I ran out of '{query}'. Try `{prefix}playlists` to see the menu.",
}

# ===================================================================
# DRINK EMOJIS - Rotating drinks for "Now Serving" messages
# ===================================================================
# Used by core/player.py for rotating drink emojis in 'now_serving' message
# Each emoji is used in rotation when displaying track changes
#
DRINK_EMOJIS = ['🍸', '🍹', '🍻', '🍸', '🍷', '🧉', '🍶', '🥃']

__all__ = ['COMMON_MESSAGES', 'DRINK_EMOJIS']
