# Copyright (C) 2026 grodz
#
# This file is part of Jill.
#
# Jill is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Config file templates for first-run generation.

These templates are written when config files don't exist yet.

Maintenance: When adding new settings or messages, update BOTH the
DEFAULT_* dict in config.py AND the corresponding template here.
"""

import os
import tempfile
from pathlib import Path


# =============================================================================
# SETTINGS TEMPLATE (settings.yaml)
# =============================================================================

SETTINGS_TEMPLATE = """\
# Jill Bot Settings
# Edit these values to customize behavior

# Playback
default_volume: 50          # 0-100: volume on startup/reconnect
default_playlist: null      # Playlist to auto-load on startup (null = none)
inactivity_timeout: 10      # 0+: minutes before auto-disconnect (0 to disable)
presence_enabled: true      # Show "Listening to [song]" in bot status

# Panel appearance
panel:
  enabled: true             # Set false to disable control panel entirely

  color: 0xA03E72           # Hex value (A03E72 or 0xA03E72, use quotes for "#A03E72")

  # Decorative emojis that cycle with each track (must be non-empty list)
  drink_emojis: ['\U0001f378', '\U0001f379', '\U0001f37b', '\U0001f378', '\U0001f377', '\U0001f9c9', '\U0001f376', '\U0001f943']
  drink_emojis_enabled: true  # Set false to hide

  # Progress bar
  progress_bar_enabled: true
  progress_bar_filled: "\U0001f7ea"
  progress_bar_empty: "\u2b1b"

  # Message shown when no album/artist/playlist info available
  info_fallback_message: "mixing drinks and changing lives"

  # Button visibility (set false to hide from panel)
  shuffle_button: true
  loop_button: true
  playlist_button: true     # Auto-hidden if only 1 playlist exists

  # Panel performance
  progress_update_interval: 15  # seconds between progress bar updates (10-3600)
  update_debounce_ms: 500       # wait time (ms) before updating after actions
                                # higher = less flicker, slower response
  recreate_interval: 30         # minutes before auto-recreating panel (0 to disable)
                                # recreating prevents Discord lag from many edits

# UI timing
ui:
  extended_auto_delete: 90  # seconds before /queue, /playlists, /np auto-delete (0 = never)
  brief_auto_delete: 10     # seconds before error/confirmation messages auto-delete (0 = never)

# Slash command availability (set false to disable)
commands:
  shuffle_command: true
  loop_command: true
  rescan_command: true

# Queue/playlist display
queue_display_size: 15      # 1-50: tracks shown per page in /queue
playlists_display_size: 15  # 1-50: playlists shown per page in /playlists

# Library scanning
auto_rescan: true           # Check for new/changed music files on startup
# Logging (LOG_LEVEL env var overrides this)
logging:
  level: "verbose"          # minimal, verbose, or debug
"""


# =============================================================================
# MESSAGES TEMPLATE (messages.yaml)
# =============================================================================

MESSAGES_TEMPLATE = """\
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
# Jill's Responses
# Customize her personality here
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#
# FORMATTING GUIDE:
#
#   Each message has two fields:
#     text: The message content (supports Discord markdown)
#     enabled: Whether to show this message (true/false)
#
#   Discord markdown:
#     **bold**  *italic*  `code`  ***bold italic***
#
#   Variables (keep these exactly as shown):
#     {title}  {name}  {level}  {position}  {playlist}  {playlists}  {tracks}  {channel}  {command}
#
#   Custom emojis:
#     1. In Discord, type \\:youremojiname: and hit send
#     2. Copy the output (should look like <:name:123456789>)
#     3. Paste it in your message
#
#   Example:
#     not_in_vc:
#       text: "<:jillgun:1234567890> Try that again."
#       enabled: true
#
# TIPS:
#   - enabled: false = action happens, no message shown
#   - enabled: true = action happens, message shown
#   - Errors are enabled by default (you need to know why something failed)
#   - Confirmations are disabled by default (you can see/hear the result)
#   - Delete this file to reset to defaults
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550

# Voice channel errors
not_in_vc:
  text: "hey, come sit at the bar first"
  enabled: true
wrong_vc:
  text: "wrong bar, i'm at {channel}"
  enabled: true
voice_error:
  text: "voice hiccup, hit me again"
  enabled: true
need_vc_permissions:
  text: "don't have access to that channel"
  enabled: true
failed_join_vc:
  text: "can't get in there"
  enabled: true

# Permissions
no_permission:
  text: "sorry, that's for staff only"
  enabled: true
command_disabled:
  text: "`/{command}` isn't available"
  enabled: true

# Playback
nothing_playing:
  text: "bar's quiet right now"
  enabled: true
now_playing:
  text: "now serving: **{title}**"
  enabled: false
paused:
  text: "taking a break"
  enabled: false
resumed:
  text: "back at it"
  enabled: false
stopped:
  text: "shift's over, heading out"
  enabled: false
already_playing:
  text: "already serving that"
  enabled: false

# Search/tracks
song_not_found:
  text: "don't have that one in stock"
  enabled: true
track_load_failed:
  text: "can't load that"
  enabled: true
track_play_error:
  text: "that broke, try again"
  enabled: true

# Queue/playlist
queue_empty:
  text: "nothing in the queue"
  enabled: true
no_playlists:
  text: "shelves are empty"
  enabled: true
playlist_empty:
  text: "that one's empty"
  enabled: true
no_playlist_loaded:
  text: "no menu set"
  enabled: false
playlist_not_found:
  text: "can't find '{name}'"
  enabled: true
playlist_not_found_pick:
  text: "can't find '{name}', pick from available:"
  enabled: true
playlist_switched:
  text: "switching to **{playlist}** menu"
  enabled: false

# Settings
volume_set:
  text: "volume set to {level}%"
  enabled: false
shuffle_on:
  text: "mixing it up"
  enabled: false
shuffle_off:
  text: "keeping it neat"
  enabled: false
loop_on:
  text: "i'll keep this one going"
  enabled: false
loop_off:
  text: "last pour for this one"
  enabled: false

# Seek
seek_to:
  text: "jumped to {position}% of **{title}**"
  enabled: false
cant_seek:
  text: "can't do that for this drink"
  enabled: true

# Previous track
history_empty:
  text: "nothing before this"
  enabled: false

# Admin
rescan_complete:
  text: "found {playlists} playlists and {tracks} songs"
  enabled: true
rescan_in_progress:
  text: "a rescan is already running, please wait"
  enabled: true
rescan_failed:
  text: "rescan failed, check the logs"
  enabled: true
music_unavailable:
  text: "music system's down"
  enabled: true

# Errors
error_generic:
  text: "something broke, try again"
  enabled: true

# Control panel
panel_deleted:
  text: "panel's gone"
  enabled: true
panel_orphaned:
  text: "that panel's outdated"
  enabled: true
library_unavailable:
  text: "music library's offline"
  enabled: true
select_playlist:
  text: "pick a playlist:"
  enabled: true

# Hints
shuffle_hint:
  text: "try `/shuffle on` or `/shuffle off`"
  enabled: false
loop_hint:
  text: "try `/loop on` or `/loop off`"
  enabled: false

# Search UI
track_selected:
  text: "got it, **{title}** coming up"
  enabled: false
"""


# =============================================================================
# PERMISSIONS TEMPLATE (permissions.yaml)
# =============================================================================

PERMISSIONS_TEMPLATE = """\
# Jill Permission System
# Set enabled: true to activate role-based permissions

enabled: false

# Discord role ID for Bartender tier
# Get this by enabling Developer Mode and right-clicking the role
# This value should look something like this:
# bartender_role_id: 1947232103103759351

bartender_role_id:

# Environment variable overrides (optional):
# ENABLE_PERMISSIONS=true     - enable permission system
# BARTENDER_ROLE_ID=123...    - set bartender role ID

# Note: Control panel buttons use the same permission system.
# Users without required tier see "no permission" messages.

# Command tier assignments (only these 3 tiers are supported)
# customer: Available to everyone
# bartender: Requires bartender role
# owner: Requires admin/manage_guild permission
# Move commands between tiers as needed
tiers:
  customer:
    - queue
    - playlists
    - np
  bartender:
    - play
    - pause
    - skip
    - previous
    - stop
    - seek
    - shuffle
    - loop
    - playlist
    - volume
  owner:
    - rescan
"""


def write_template(path: Path, content: str) -> None:
    """Write a config file template atomically.

    Uses temp-file-then-rename pattern to prevent corruption.
    Creates parent directories if they don't exist.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_fd, temp_path = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        f = os.fdopen(temp_fd, 'w', encoding='utf-8')
    except Exception:
        os.close(temp_fd)
        raise
    try:
        with f:
            f.write(content)
        Path(temp_path).replace(path)
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        raise
