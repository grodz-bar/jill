"""
Track Class and Library Loading

Represents individual music tracks and provides library loading functionality.
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

# Import from config
from config.paths import MUSIC_FOLDER


class Track:
    """
    Represents a single music track with unique identity.

    Attributes:
        track_id: Unique identifier (auto-incremented)
        opus_path: Full path to .opus file
        library_index: Position in master library (immutable)
        display_name: Formatted name for display (without number prefix/extension)

    Design notes:
        - Each track gets a unique ID to prevent object reference bugs
        - library_index is the track's position in the sorted library (never changes)
        - display_name strips "01 - " prefix and ".opus" extension for clean display
        - Equality based on track_id, not file path (survives file moves)
    """

    _next_id = 0  # Class variable: auto-incrementing ID counter
    _prefix_pattern = re.compile(r'^\d+\s*-\s*')  # Precompiled regex for numeric prefix removal

    def __init__(self, opus_path: Path, library_index: int):
        """
        Create a new track.

        Args:
            opus_path: Full path to the .opus file
            library_index: Position in sorted library (0-based)
        """
        self.track_id = Track._next_id
        Track._next_id += 1
        self.opus_path = opus_path
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
        """
        name = self.opus_path.stem  # Filename without extension
        name = Track._prefix_pattern.sub('', name)  # Remove "01 - " using precompiled regex
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


def load_library(guild_id: int = 0) -> Tuple[List[Track], Dict[int, Track]]:
    """
    Load all music files from disk into library.

    Files are sorted numerically by leading digits in filename:
    - "01 - Track.opus" comes before "02 - Track.opus"
    - "10 - Track.opus" comes after "9 - Track.opus" (numeric, not lexical)

    Args:
        guild_id: Guild ID for logging purposes (optional)

    Returns:
        Tuple of (library list, track_by_index dict):
            - library: List of Track objects sorted by filename number
            - track_by_index: Dict mapping library_index → Track for O(1) lookups

    Example:
        library, track_index = load_library(guild_id=123456)
        track_5 = track_index[4]  # Get 5th track (0-indexed)
    """
    music_path = Path(MUSIC_FOLDER)
    if not music_path.exists():
        logger.warning(f"Music folder not found: {MUSIC_FOLDER}")
        return [], {}

    files = [f for f in music_path.glob("*") if f.is_file() and f.suffix.lower() == '.opus']
    if not files:
        logger.warning(f"No .opus files found in {MUSIC_FOLDER}")
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

    sorted_files = sorted(files, key=get_sort_key)
    library = [Track(filepath, idx) for idx, filepath in enumerate(sorted_files)]

    # Build fast lookup index
    track_by_index = {track.library_index: track for track in library}

    logger.info("Guild %s: Loaded %d tracks", guild_id, len(library))
    return library, track_by_index
