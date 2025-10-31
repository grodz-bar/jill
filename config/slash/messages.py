"""
Slash Mode Messages Configuration

ALL user-facing text for slash command mode.
NO HARDCODED STRINGS in implementation files!
"""

# Command responses
MESSAGES = {
    # Playback
    'RESUMED': "▶️ Resuming playback",
    'PAUSED': "⏸️ Playback paused",
    'SKIPPED': "⏭️ Skipped to next track",
    'PREVIOUS': "⏮️ Returned to previous track",
    'STOPPED': "⏹️ Playback stopped and queue cleared",
    'CONNECTED': "🔊 Connected to voice channel",
    'STARTING_PLAYBACK': "▶️ Starting playback",

    # Shuffle
    'SHUFFLED': "🔀 Queue shuffled",
    'SHUFFLE_ON': "🔀 Shuffle mode enabled",
    'SHUFFLE_OFF': "➡️ Shuffle mode disabled",
    'NOTHING_TO_SHUFFLE': "❌ Nothing to shuffle",

    # Errors
    'USER_NOT_IN_VOICE': "❌ You need to be in a voice channel",
    'WRONG_VOICE_CHANNEL': "❌ You need to be in the same voice channel as the bot",
    'BOT_NOT_PLAYING': "❌ Nothing is currently playing",
    'CANNOT_CONNECT': "❌ Cannot connect to your voice channel",
    'NO_TRACKS': "❌ No tracks available in the library",
    'TRACK_NOT_FOUND': "❌ Track not found: **{query}**",
    'PLAYLIST_NOT_FOUND': "❌ Playlist not found: **{name}**",
    'INVALID_NUMBER': "❌ Please provide a valid track number",
    'EMPTY_QUEUE': "📭 The queue is empty",
    'NO_PLAYLISTS': "❌ No playlists available",
    'PLAYLIST_EMPTY': "❌ This playlist has no tracks",
    'NO_PREVIOUS_TRACK': "❌ No previous track available",
    'PERMISSION_DENIED': "❌ You don't have permission to use this command",
    'ERROR_OCCURRED': "❌ An error occurred while processing your request",

    # Success
    'PLAYLIST_SWITCHED': "📂 Switched to playlist: **{playlist}**",
    'JUMPED_TO_TRACK': "⏩ Jumped to track #{number}: **{name}**",

    # Panel
    'CONTROL_PANEL_TITLE': "🎵 Music Controls",
    'CONTROL_PANEL_DESC': "Use the buttons below to control playback",
    'NOW_PLAYING_TITLE': "🎵 **Now Playing**",
    'NOTHING_PLAYING': "Nothing to serve",
    'QUEUE_EMPTY_MESSAGE': "*Queue is empty*",
    'UP_NEXT': "**Up Next:**",
    'AND_MORE': "... and {count} more",
    'TRACK_INFO': "Track #{index} - **{name}**",
    'PLAYLIST_INFO': "📂 Playlist: {name}",
    'STATUS_PLAYING': "▶️ *Playing*",
    'STATUS_PAUSED': "⏸️ *Paused*",

    # Lists
    'QUEUE_TITLE': "📋 Current Queue",
    'TRACKS_TITLE': "📚 Track Library",
    'PLAYLISTS_TITLE': "📂 Available Playlists",
    'PAGE_INFO': "Page {current}/{total}",

    # Help
    'HELP_TITLE': "🍸 Jill - Music Bot Commands",
    'HELP_DESCRIPTION': "Your cyberpunk bartender, now serving beats!",
}

# Button labels
BUTTON_LABELS = {
    'previous': '⏮️',
    'pause': '⏸️',
    'play': '▶️',
    'skip': '⏭️',
    'shuffle': '🔀',
    'stop': '⏹️',
    'page_prev': '◀️ Previous',
    'page_next': 'Next ▶️',
    'page_info': '{current}/{total}',
}

# Command descriptions
COMMAND_DESCRIPTIONS = {
    'play': 'Start playback or jump to a specific track',
    'pause': 'Pause the current track',
    'skip': 'Skip to the next track',
    'stop': 'Stop playback and clear the queue',
    'previous': 'Go back to the previous track',
    'shuffle': 'Toggle shuffle mode',
    'queue': 'Show the current queue',
    'tracks': 'List all available tracks',
    'playlist': 'Switch to a different playlist',
    'playlists': 'Show all available playlists',
    'help': 'Show help information',
}

__all__ = [
    'MESSAGES',
    'BUTTON_LABELS',
    'COMMAND_DESCRIPTIONS',
]
