"""
Path Configuration - Shared Between All Modes

File and directory paths for the bot.
"""

import os
from pathlib import Path

# Music folder
MUSIC_FOLDER = os.getenv('MUSIC_FOLDER', 'music').strip()
if not Path(MUSIC_FOLDER).is_absolute():
    MUSIC_FOLDER = str(Path(MUSIC_FOLDER).resolve())

# Persistence/storage files
CHANNEL_STORAGE_FILE = 'last_channels.json'
PLAYLIST_STORAGE_FILE = 'last_playlists.json'
MESSAGE_PERSISTENCE_FILE = 'last_message_ids.json'  # Slash mode only

# Supported audio formats
SUPPORTED_FORMATS = ('.opus', '.mp3', '.flac', '.wav', '.m4a', '.ogg')

__all__ = [
    'MUSIC_FOLDER',
    'CHANNEL_STORAGE_FILE',
    'PLAYLIST_STORAGE_FILE',
    'MESSAGE_PERSISTENCE_FILE',
    'SUPPORTED_FORMATS',
]
