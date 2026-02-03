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
from itertools import chain
from pathlib import Path

from loguru import logger


# Glob patterns for supported audio formats (Lavalink-compatible)
AUDIO_EXTENSIONS = ['*.mp3', '*.flac', '*.ogg', '*.m4a', '*.wav', '*.aac']

# Maximum tracks per playlist to prevent memory issues with very large libraries
MAX_PLAYLIST_SIZE = 1000

# Internal playlist name for audio files placed directly in the music root directory
# (used when no subdirectory playlists exist). Users see "root" in the UI.
ROOT_PLAYLIST_NAME = "_root"


class MusicLibrary:
    """Manages playlists and music file discovery.

    Scans the music directory for playlists (subdirectories containing audio files).
    Each subdirectory becomes a playlist named after the folder.

    Directory structure:
        music/
        ├── Jazz/           -> "jazz" playlist
        │   ├── track1.mp3
        │   └── track2.flac
        ├── Rock/           -> "rock" playlist
        │   └── song.ogg
        └── loose.mp3       -> Ignored if playlists exist, or "_root" playlist

    Scanning behavior:
    - Hidden folders (starting with .) are skipped
    - Playlist names are lowercased for case-insensitive lookups
    - Tracks sorted alphabetically by filename
    - Playlists capped at MAX_PLAYLIST_SIZE tracks
    - Loose files in root: warned and ignored if playlists exist,
      otherwise become "_root" playlist

    The library is scanned once on startup. Use /rescan to detect new files.

    Attributes:
        music_path: Root directory containing playlist subdirectories
        _playlists: Cached scan results (None until scan() is called)
    """

    def __init__(self, music_path: Path) -> None:
        self.music_path = music_path
        self._playlists: dict[str, list[Path]] | None = None

    async def scan(self) -> dict[str, list[Path]]:
        """Scan music directory for playlists.

        Updates internal _playlists cache. Logs warnings for loose files in root
        or empty directories.

        Returns:
            Playlists dict mapping name to list of file paths
        """
        logger.info("library scan started")

        playlists, loose_files = await asyncio.to_thread(self._scan_sync)

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
            folder_count = len(playlists)
            file_word = "file" if file_count == 1 else "files"
            folder_word = "folder" if folder_count == 1 else "folders"
            logger.info(f"scanned {file_count} {file_word} in {folder_count} {folder_word}")

        self._playlists = playlists
        return playlists

    def _scan_sync(self) -> tuple[dict[str, list[Path]], list[str]]:
        """Synchronous directory scanning.

        Returns:
            Tuple of (playlists dict, list of loose filenames in root)
        """
        playlists = {}
        loose_files = []

        if not self.music_path.exists():
            logger.warning(f"music path does not exist: {self.music_path}")
            return playlists, loose_files

        # Scan subdirectories for playlists
        for playlist_dir in self.music_path.iterdir():
            if not playlist_dir.is_dir():
                continue
            if playlist_dir.name.startswith('.'):
                continue  # Skip hidden folders

            audio_files = list(chain.from_iterable(
                playlist_dir.glob(ext) for ext in AUDIO_EXTENSIONS
            ))

            if audio_files:
                # Sort by filename (canonical order for now)
                sorted_files = sorted(audio_files, key=lambda p: p.name.lower())

                # Enforce playlist size limit
                if len(sorted_files) > MAX_PLAYLIST_SIZE:
                    track_word = "track" if len(sorted_files) == 1 else "tracks"
                    logger.warning(
                        f"playlist '{playlist_dir.name}' has {len(sorted_files)} {track_word}, "
                        f"truncating to {MAX_PLAYLIST_SIZE}"
                    )
                    sorted_files = sorted_files[:MAX_PLAYLIST_SIZE]

                playlists[playlist_dir.name.lower()] = sorted_files
            else:
                logger.warning(f"playlist '{playlist_dir.name}' is empty")

        # Check for audio files in root
        root_audio = list(chain.from_iterable(
            self.music_path.glob(ext) for ext in AUDIO_EXTENSIONS
        ))

        if root_audio:
            if playlists:
                # Playlists exist AND root has files: collect for warning
                loose_files = [f.name for f in root_audio]
            else:
                # NO playlists but root has files: treat as root playlist
                sorted_files = sorted(root_audio, key=lambda p: p.name.lower())

                if len(sorted_files) > MAX_PLAYLIST_SIZE:
                    track_word = "track" if len(sorted_files) == 1 else "tracks"
                    logger.warning(
                        f"library: root folder has {len(sorted_files)} {track_word}, "
                        f"truncating to {MAX_PLAYLIST_SIZE}"
                    )
                    sorted_files = sorted_files[:MAX_PLAYLIST_SIZE]

                playlists[ROOT_PLAYLIST_NAME] = sorted_files

        return playlists, loose_files

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

        Derives path from first track's parent to preserve filesystem casing
        (playlist names are lowercase but directories may have mixed case).
        Returns constructed path as fallback if playlist not found.
        """
        if playlist_name == ROOT_PLAYLIST_NAME:
            return self.music_path
        tracks = self.get_playlist(playlist_name)
        if tracks:
            return tracks[0].parent
        return self.music_path / playlist_name  # fallback (shouldn't happen)
