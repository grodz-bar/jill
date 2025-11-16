"""
Slash Mode Messages Configuration
"""

# Command responses
MESSAGES = {
    # Slash-specific errors
    # (Most errors are now in common/messages.py and shared with prefix mode)
    'error_occurred': "❌ An error occurred while processing your request",
    'button_on_cooldown': "⏱️ Slow down! Please wait a moment before clicking again",

    # Control panel display
    'now_playing_title': "🎵 **Now Playing**",
    'nothing_playing': "Nothing to serve",
    'queue_empty_message': "*Queue is empty*",
    'up_next': "**Up Next:**",
    'and_more': "... and {count} more",
    'track_info': "Track #{index} - **{name}**",
    'status_playing': "▶️ *Playing*",
    'status_paused': "⏸️ *Paused*",

    # Command embeds
    'queue_title': "📋 Current Queue",
    'tracks_title': "📚 Track Library",
    'playlists_title': "📂 Available Playlists",
    'page_info': "Page {current}/{total}",

    # Help command
    'help_title': "🍸 Jill - Music Bot Commands",
    'help_description': "Your cyberpunk bartender, now serving beats!",
}

# Button labels (control panel buttons)
BUTTON_LABELS = {
    'previous': '⏮️',
    'pause': '⏸️',
    'play': '▶️',
    'skip': '⏭️',
    'shuffle': '🔀',
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

# Control panel settings
# Fallback playlist name when no playlist structure exists (flat folder)
FALLBACK_PLAYLIST_NAME = "jukebox"

# Embed color scheme
BOT_COLORS = {
    'primary': 0xE91E63,    # Pink
    'success': 0x00E676,    # Green
    'warning': 0xFFD600,    # Yellow
    'error': 0xFF5252,      # Red
    'info': 0x2196F3,       # Blue
}

__all__ = [
    'MESSAGES',
    'BUTTON_LABELS',
    'COMMAND_DESCRIPTIONS',
    'FALLBACK_PLAYLIST_NAME',
    'BOT_COLORS',
]
