"""
File Paths and Directory Settings

This file contains file path configurations for advanced users.
Most users should NOT modify these settings unless they have specific needs.

WARNING: Changing these paths incorrectly can break bot functionality.
Only modify if you understand the implications.
"""

import os
from pathlib import Path

# ==================================================================================
# USER-CONFIGURABLE PATHS
# ==================================================================================

# Anchor paths to bot root directory for CWD-independence
# This ensures paths work regardless of where the bot is run from
_BOT_ROOT = Path(__file__).resolve().parent.parent

# MUSIC_FOLDER can be set via:
#   1. .env file in bot directory: MUSIC_FOLDER=/path/to/music
#   2. System environment variable: export MUSIC_FOLDER=/path/to/music
#   3. Fallback default (if neither is set): bot_root/music/ (anchored to bot directory)
MUSIC_FOLDER = os.getenv('MUSIC_FOLDER') or str(_BOT_ROOT / 'music')  # Path to your music files

# ==================================================================================
# INTERNAL PATHS (DO NOT MODIFY)
# ==================================================================================

# CHANNEL_STORAGE_FILE stores the last used text channel per guild
# This allows cleanup features to resume in the same channel after bot restart
# Format: JSON file with guild_id -> channel_id mappings
# WARNING: Do not change this path unless you absolutely know what you're doing
CHANNEL_STORAGE_FILE = str(_BOT_ROOT / 'last_channels.json')  # Path to channel storage file

# PLAYLIST_STORAGE_FILE stores the last used playlist per guild
# This allows the bot to remember which playlist each guild was using after restart
# Format: JSON file with guild_id -> playlist_id mappings
# WARNING: Do not change this path unless you absolutely know what you're doing
PLAYLIST_STORAGE_FILE = str(_BOT_ROOT / 'last_playlists.json')  # Path to playlist storage file
