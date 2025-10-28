# Copyright (C) 2025 grodz
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

"""
Track Class and Library Loading

Represents individual music tracks and provides library loading functionality.
Also handles playlist discovery and organization.
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# Import from config
from config.paths import MUSIC_FOLDER
from config.features import ALLOW_TRANSCODING, SUPPORTED_AUDIO_FORMATS

# Module-level regex pattern for numeric prefix removal (DRY - used by both Playlist and Track)
_PREFIX_PATTERN = re.compile(r'^\d+\s*-\s*')


def _collect_audio_files(target_path: Path, guild_id: int = 0) -> List[Path]:
    """
    Collect audio files from path, respecting ALLOW_TRANSCODING setting.

    When multiple formats of the same file exist (e.g., song.opus and song.mp3),
    prefers .opus format (first in SUPPORTED_AUDIO_FORMATS list).

    Args:
        target_path: Directory to scan for audio files
        guild_id: Guild ID for logging purposes

    Returns:
        List of Path objects for audio files (deduplicated, .opus preferred)

    Examples:
        ALLOW_TRANSCODING=True, files: [song.opus, song.mp3, track.flac]
        Returns: [song.opus, track.flac]  (song.opus preferred over song.mp3)

        ALLOW_TRANSCODING=False, files: [song.opus, song.mp3, track.flac]
        Returns: [song.opus]  (only .opus files)
    """
    if not target_path.exists():
        return []

    # Determine which extensions to accept
    if ALLOW_TRANSCODING:
        allowed_extensions = set(ext.lower() for ext in SUPPORTED_AUDIO_FORMATS)
    else:
        allowed_extensions = {'.opus'}

    # Collect all files with allowed extensions
    all_files = [f for f in target_path.glob("*")
                 if f.is_file() and f.suffix.lower() in allowed_extensions]

    if not all_files:
        return []

    # Group files by stem (filename without extension)
    # This allows us to prefer .opus when multiple formats exist
    files_by_stem = {}
    for filepath in all_files:
        stem = filepath.stem
        if stem not in files_by_stem:
            files_by_stem[stem] = []
        files_by_stem[stem].append(filepath)

    # For each stem, select the preferred format
    selected_files = []
    for stem, file_group in files_by_stem.items():
        if len(file_group) == 1:
            # Only one format exists, use it
            selected_files.append(file_group[0])
        else:
            # Multiple formats exist - prefer based on SUPPORTED_AUDIO_FORMATS order
            # (opus is first, so it will be preferred)
            preferred = None
            for ext in SUPPORTED_AUDIO_FORMATS:
                ext_lower = ext.lower()  # Normalize extension for case-insensitive comparison
                for filepath in file_group:
                    if filepath.suffix.lower() == ext_lower:
                        preferred = filepath
                        break
                if preferred:
                    break

            if preferred:
                selected_files.append(preferred)
                # Log if we're preferring one format over another
                other_formats = [f.suffix for f in file_group if f != preferred]
                if other_formats:
                    logger.debug(
                        f"Guild {guild_id}: Multiple formats found for '{stem}', "
                        f"preferring {preferred.suffix} over {other_formats}"
                    )

    return selected_files


class Playlist:
    """
    Represents a music playlist (subfolder in music directory).

    Attributes:
        playlist_id: Unique identifier (folder name)
        playlist_path: Full path to playlist folder
        display_name: Formatted name for display (without number prefix)
        track_count: Number of .opus tracks in this playlist

    Design notes:
        - Playlists are sorted numerically by leading digits (like tracks)
        - display_name strips "01 - " prefix for clean display
        - Equality based on playlist_id
    """

    def __init__(self, playlist_path: Path, track_count: int = 0):
        """
        Create a new playlist.

        Args:
            playlist_path: Full path to the playlist folder
            track_count: Number of tracks in this playlist
        """
        self.playlist_id = playlist_path.name
        self.playlist_path = playlist_path
        self.track_count = track_count
        self.display_name = self._get_display_name()

    def _get_display_name(self) -> str:
        """
        Format folder name for display.

        Removes leading numbers and dash ("01 - ")

        Example:
            "01 - Album Name" → "Album Name"
        """
        name = self.playlist_id
        name = _PREFIX_PATTERN.sub('', name)  # Remove "01 - " using module-level regex
        return name

    def __eq__(self, other) -> bool:
        """Playlists are equal if they have the same ID."""
        return isinstance(other, Playlist) and self.playlist_id == other.playlist_id

    def __hash__(self) -> int:
        """Hash based on ID allows playlists to be used in sets/dicts."""
        return hash(self.playlist_id)

    def __repr__(self) -> str:
        """Debug representation."""
        return f"Playlist(id={self.playlist_id}, name={self.display_name}, tracks={self.track_count})"


class Track:
    """
    Represents a single music track with unique identity.

    Attributes:
        track_id: Unique identifier (auto-incremented)
        file_path: Full path to audio file (supports multiple formats)
        library_index: Position in master library (immutable)
        display_name: Formatted name for display (without number prefix/extension)

    Design notes:
        - Each track gets a unique ID to prevent object reference bugs
        - library_index is the track's position in the sorted library (never changes)
        - display_name strips "01 - " prefix and file extension for clean display
        - Equality based on track_id, not file path (survives file moves)
        - Supports multiple audio formats when ALLOW_TRANSCODING=True
    """

    _next_id = 0  # Class variable: auto-incrementing ID counter

    def __init__(self, file_path: Path, library_index: int):
        """
        Create a new track.

        Args:
            file_path: Full path to the audio file (any supported format)
            library_index: Position in sorted library (0-based)
        """
        self.track_id = Track._next_id
        Track._next_id += 1
        self.file_path = file_path
        self.library_index = library_index
        self.display_name = self._get_display_name()

    def _get_display_name(self) -> str:
        """
        Format filename for display.

        Removes:
            - Leading numbers and dash ("01 - ")
            - File extension (case-insensitive)

        Example:
            "01 - Hopes and Dreams.opus" → "Hopes and Dreams"
            "02 - Track.mp3" → "Track"
        """
        name = self.file_path.stem  # Filename without extension
        name = _PREFIX_PATTERN.sub('', name)  # Remove "01 - " using module-level regex
        return name

    def __eq__(self, other) -> bool:
        """Tracks are equal if they have the same ID."""
        return isinstance(other, Track) and self.track_id == other.track_id

    def __hash__(self) -> int:
        """Hash based on ID allows tracks to be used in sets/dicts."""
        return hash(self.track_id)

    def __repr__(self) -> str:
        """Debug representation."""
        return f"Track(id={self.track_id}, name={self.display_name})"


def discover_playlists(guild_id: int = 0) -> List[Playlist]:
    """
    Discover all playlists (subfolders with .opus files) in music directory.

    Scans MUSIC_FOLDER for subdirectories containing .opus files.
    Sorts playlists numerically by leading digits in folder name.

    Args:
        guild_id: Guild ID for logging purposes (optional)

    Returns:
        List of Playlist objects sorted by folder number

    Example:
        playlists = discover_playlists(guild_id=123456)
        # [Playlist(01 - Album), Playlist(02 - OST), ...]
    """
    music_path = Path(MUSIC_FOLDER)
    if not music_path.exists():
        logger.warning(f"Guild {guild_id}: Music folder not found: {MUSIC_FOLDER}")
        return []

    playlists = []

    # Scan for subdirectories
    for folder in music_path.iterdir():
        if not folder.is_dir():
            continue

        # Count audio files in this folder using the multi-format helper
        audio_files = _collect_audio_files(folder, guild_id)
        if audio_files:
            playlists.append(Playlist(folder, track_count=len(audio_files)))

    if not playlists:
        logger.debug(f"Guild {guild_id}: No playlist subfolders found in {MUSIC_FOLDER}")
        return []

    def get_sort_key(playlist: Playlist) -> int:
        """Extract leading number from folder name for sorting."""
        match = re.match(r'^(\d+)', playlist.playlist_id)
        if match:
            return int(match.group(1))
        else:
            # Unnumbered folders sort to end
            logger.warning(f"Guild {guild_id}: Playlist folder missing numeric prefix (will sort last): {playlist.playlist_id}")
            return 999999

    # Sort by number first, then by name (casefold for case-insensitive sorting)
    # This provides stable, deterministic sorting even for unnumbered playlists
    sorted_playlists = sorted(
        playlists,
        key=lambda p: (get_sort_key(p), p.display_name.casefold())
    )
    logger.info(f"Guild {guild_id}: Discovered {len(sorted_playlists)} playlists")

    return sorted_playlists


def has_playlist_structure() -> bool:
    """
    Check if music folder has playlist structure (subfolders with tracks).

    Returns:
        True if subfolders with audio files exist, False otherwise

    Use this to determine whether to enable multi-playlist features.
    """
    music_path = Path(MUSIC_FOLDER)
    if not music_path.exists():
        return False

    # Check if any subdirectories contain audio files
    for folder in music_path.iterdir():
        if folder.is_dir():
            audio_files = _collect_audio_files(folder)
            if audio_files:
                return True

    return False


def load_library(guild_id: int = 0, playlist_path: Optional[Path] = None) -> Tuple[List[Track], Dict[int, Track]]:
    """
    Load all music files from disk into library.

    Supports multiple audio formats when ALLOW_TRANSCODING=True (MP3, FLAC, WAV, M4A, OGG).
    Always prefers .opus format when multiple versions of the same file exist.

    Files are sorted numerically by leading digits in filename:
    - "01 - Track.opus" comes before "02 - Track.opus"
    - "10 - Track.opus" comes after "9 - Track.opus" (numeric, not lexical)

    Args:
        guild_id: Guild ID for logging purposes (optional)
        playlist_path: Path to playlist folder (if None, uses MUSIC_FOLDER root)

    Returns:
        Tuple of (library list, track_by_index dict):
            - library: List of Track objects sorted by filename number
            - track_by_index: Dict mapping library_index → Track for O(1) lookups

    Example:
        library, track_index = load_library(guild_id=123456)
        track_5 = track_index[4]  # Get 5th track (0-indexed)
    """
    # Use playlist path if provided, otherwise use root music folder
    target_path = playlist_path if playlist_path else Path(MUSIC_FOLDER)

    if not target_path.exists():
        logger.warning(f"Guild {guild_id}: Music path not found: {target_path}")
        return [], {}

    # Collect audio files using the new multi-format helper
    files = _collect_audio_files(target_path, guild_id)
    if not files:
        format_msg = "audio files" if ALLOW_TRANSCODING else ".opus files"
        logger.warning(f"Guild {guild_id}: No {format_msg} found in {target_path}")
        return [], {}

    def get_sort_key(filepath: Path) -> int:
        """Extract leading number from filename for sorting."""
        filename = filepath.name
        match = re.match(r'^(\d+)', filename)
        if match:
            return int(match.group(1))
        else:
            # Unnumbered files sort to end and trigger warning
            logger.warning(f"Guild {guild_id}: File missing numeric prefix (will sort last): {filename}")
            return 999999

    # Sort by number first, then by name (casefold for case-insensitive sorting)
    # This provides stable, deterministic sorting even for unnumbered files
    sorted_files = sorted(files, key=lambda f: (get_sort_key(f), f.name.casefold()))
    library = [Track(filepath, idx) for idx, filepath in enumerate(sorted_files)]

    # Build fast lookup index
    track_by_index = {track.library_index: track for track in library}

    logger.info("Guild %s: Loaded %d tracks from %s", guild_id, len(library), target_path)
    return library, track_by_index
