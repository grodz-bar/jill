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

"""Music library and playlist management."""

import asyncio
from pathlib import Path

from loguru import logger


# Supported audio file suffixes — case-insensitive matching (Lavalink-compatible)
AUDIO_EXTENSIONS = {'.mp3', '.flac', '.ogg', '.opus', '.m4a', '.m4b', '.wav', '.aac', '.webm', '.mka'}

# Internal playlist name for audio files placed directly in the music root directory
# (used when no subdirectory playlists exist). Users see "root" in the UI.
ROOT_PLAYLIST_NAME = "_root"

# Maximum subdirectory depth for recursive playlist scanning
MAX_SCAN_DEPTH = 5


class MusicLibrary:
    """Manages playlists and music file discovery.

    Scans the music directory for playlists (subdirectories containing audio files).
    Each subdirectory becomes a playlist named after the folder. Subfolders within
    playlists are scanned recursively (up to MAX_SCAN_DEPTH levels).

    Directory structure:
        music/
        ├── Jazz/           -> "jazz" playlist
        │   ├── track1.mp3
        │   └── track2.flac
        ├── Rock/           -> "rock" playlist
        │   ├── song.ogg
        │   └── Disc 2/     -> files included in "rock" playlist
        │       └── bonus.mp3
        └── loose.mp3       -> Ignored if playlists exist, or "_root" playlist

    Scanning behavior:
    - Hidden folders (starting with .) are skipped
    - Playlist names are lowercased for case-insensitive lookups
    - Tracks sorted by relative path from playlist root (groups by subfolder)
    - Loose files in root: warned and ignored if playlists exist,
      otherwise become "_root" playlist (stays flat, not recursive)

    The library is scanned once on startup. Use /rescan to detect new files.

    Attributes:
        music_path: Root directory containing playlist subdirectories
        _playlists: Cached scan results (None until scan() is called)
        _playlist_paths: Maps lowercase playlist name to original-casing directory Path
    """

    def __init__(self, music_path: Path) -> None:
        self.music_path = music_path
        self._playlists: dict[str, list[Path]] | None = None
        self._playlist_paths: dict[str, Path] = {}

    async def scan(self) -> dict[str, list[Path]]:
        """Scan music directory for playlists.

        Updates internal _playlists cache. Logs warnings for loose files in root
        or empty directories.

        Returns:
            Playlists dict mapping name to list of file paths
        """
        logger.info("loading library...")

        playlists, loose_files, playlist_paths = await asyncio.to_thread(self._scan_sync)
        self._playlist_paths = playlist_paths

        # Warn about loose files in root (when playlists exist)
        if loose_files:
            logger.warning(
                f"{len(loose_files)} audio file(s) in root ignored, "
                "move them to a playlist subfolder"
            )
            for filename in loose_files[:5]:
                logger.warning(f"  - {filename}")
            if len(loose_files) > 5:
                logger.warning(f"  ...and {len(loose_files) - 5} more")

        if not playlists:
            logger.warning("no playlists found")
        else:
            file_count = sum(len(tracks) for tracks in playlists.values())
            playlist_count = len(playlists)
            file_word = "file" if file_count == 1 else "files"
            playlist_word = "playlist" if playlist_count == 1 else "playlists"
            logger.info(f"found {file_count} {file_word} in {playlist_count} {playlist_word}")

        self._playlists = playlists
        return playlists

    def _scan_audio_files(self, directory: Path, max_depth: int = MAX_SCAN_DEPTH) -> list[Path]:
        """Recursively find audio files up to max_depth. Skips hidden dirs."""
        if max_depth < 0:
            return []
        result = []
        try:
            children = list(directory.iterdir())
        except PermissionError:
            logger.warning(f"permission denied: {directory}")
            return []
        for entry in children:
            if entry.is_file() and entry.suffix.lower() in AUDIO_EXTENSIONS:
                result.append(entry)
            elif entry.is_dir() and not entry.name.startswith('.'):
                result.extend(self._scan_audio_files(entry, max_depth - 1))
        return result

    def _scan_sync(self) -> tuple[dict[str, list[Path]], list[str], dict[str, Path]]:
        """Synchronous directory scanning.

        Returns:
            Tuple of (playlists dict, list of loose filenames in root, playlist paths dict)
        """
        playlists = {}
        loose_files = []
        playlist_paths = {}

        if not self.music_path.exists():
            logger.warning(f"music path does not exist: {self.music_path}")
            return playlists, loose_files, playlist_paths

        # Scan subdirectories for playlists (recursive into subfolders)
        for playlist_dir in sorted(self.music_path.iterdir(), key=lambda p: p.name.lower()):
            if not playlist_dir.is_dir():
                continue
            if playlist_dir.name.startswith('.'):
                continue  # Skip hidden folders

            audio_files = self._scan_audio_files(playlist_dir)

            if audio_files:
                # Sort by relative path (groups files by subfolder)
                sorted_files = sorted(audio_files, key=lambda p: p.relative_to(playlist_dir).as_posix().lower())

                key = playlist_dir.name.lower()
                if key in playlists:
                    existing_dir = playlist_paths[key]
                    logger.warning(
                        f"folders '{existing_dir.name}' and '{playlist_dir.name}' "
                        f"have the same name, keeping '{playlist_dir.name}'"
                    )
                playlists[key] = sorted_files
                playlist_paths[key] = playlist_dir
            else:
                logger.warning(f"playlist '{playlist_dir.name}' is empty")

        # Check for audio files in root (stays flat — not recursive)
        root_audio = [f for f in self.music_path.iterdir()
                      if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS]

        if root_audio:
            if playlists:
                # Playlists exist AND root has files: collect for warning
                loose_files = [f.name for f in root_audio]
            else:
                # NO playlists but root has files: treat as root playlist
                sorted_files = sorted(root_audio, key=lambda p: p.name.lower())
                playlists[ROOT_PLAYLIST_NAME] = sorted_files

        return playlists, loose_files, playlist_paths

    @property
    def playlists(self) -> dict[str, list[Path]]:
        """Get cached playlists. Returns empty dict if scan() hasn't been called."""
        if self._playlists is None:
            return {}
        return self._playlists

    def get_playlist(self, name: str) -> list[Path] | None:
        """Get tracks for a playlist, or None if not found."""
        return self.playlists.get(name)

    def update_playlist_files(self, playlist_name: str, filtered_paths: list[Path]) -> int:
        """Replace playlist files with duplicate-filtered list.

        Args:
            playlist_name: Name of the playlist to update
            filtered_paths: File paths after duplicate detection

        Returns:
            Number of files removed. Returns 0 if playlist doesn't exist.
        """
        if playlist_name not in self.playlists:
            return 0

        original_count = len(self.playlists[playlist_name])
        self.playlists[playlist_name] = filtered_paths
        removed = original_count - len(filtered_paths)

        return removed

    def get_playlist_names(self) -> list[str]:
        """Get list of playlist names."""
        return list(self.playlists.keys())

    def get_playlist_path(self, playlist_name: str) -> Path:
        """Get filesystem path for a playlist.

        Handles root playlist specially - returns music_path directly
        instead of music_path / "_root".

        Uses _playlist_paths cache (built during scan) to preserve filesystem casing
        (playlist names are lowercase but directories may have mixed case).
        Returns constructed path as fallback if playlist not found.
        """
        if playlist_name == ROOT_PLAYLIST_NAME:
            return self.music_path
        path = self._playlist_paths.get(playlist_name)
        if path:
            return path
        return self.music_path / playlist_name  # fallback (shouldn't happen)

    def track_key(self, track: Path, playlist_name: str) -> str:
        """Relative POSIX path from playlist root."""
        playlist_path = self.get_playlist_path(playlist_name)
        try:
            return track.relative_to(playlist_path).as_posix()
        except ValueError:
            return track.name
