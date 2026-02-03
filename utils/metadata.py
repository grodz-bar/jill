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

"""Metadata extraction using Mutagen.

Extracts title, artist, album, and track number from audio files.
Supports multiple tag formats (ID3, Vorbis, MP4, etc.) via Mutagen.

Key functions:
- extract_metadata(): Async wrapper for single-file extraction
- scan_playlist_metadata(): Scan playlist with caching and duplicate detection

Caching:
- Caches stored in data/metadata/<playlist_name>.json
- Cache keyed by "filename_mtime" to detect modified files
- Duplicates are detected and excluded from playback

All metadata is lowercased for consistent display and search.
"""

import asyncio
import json
import os
import re
from pathlib import Path

from loguru import logger

try:
    from mutagen import File, MutagenError
except ImportError:
    File = None
    MutagenError = Exception
    logger.warning("mutagen not installed, metadata extraction disabled")


def extract_metadata_sync(filepath: Path) -> dict:
    """Extract metadata from audio file (synchronous).

    Tries multiple tag formats (ID3, Vorbis, MP4) to find title, artist, album.
    Falls back to filename if metadata is missing or unreadable.

    Returns:
        Dict with keys: filename, title, artist, album, track.
        title defaults to filename stem; artist/album may be None; track defaults to 0.
    """
    result = {
        "filename": filepath.name,
        "title": filepath.stem,
        "artist": None,
        "album": None,
        "track": 0
    }

    if File is None:
        return result

    try:
        audio = File(filepath)
        if audio is None:
            return result

        # Try different tag formats
        result["title"] = (
            _get_first(audio, "title") or
            _get_first(audio, "TIT2") or
            _get_first(audio, "\xa9nam") or
            filepath.stem
        )

        result["artist"] = (
            _get_first(audio, "artist") or
            _get_first(audio, "TPE1") or
            _get_first(audio, "\xa9ART") or
            None
        )

        # Album (support multiple formats)
        result["album"] = (
            _get_first(audio, "album") or
            _get_first(audio, "TALB") or
            _get_first(audio, "\xa9alb") or
            None
        )

        # Track number
        track_str = _get_first(audio, "tracknumber") or _get_first(audio, "TRCK")
        track_num = 0

        if track_str:
            try:
                track_num = int(str(track_str).split('/')[0])
            except (ValueError, TypeError):
                pass

        # MP4/M4A uses trkn tag with tuple format [(track, total)]
        if track_num == 0:
            trkn = audio.get("trkn")
            if trkn and isinstance(trkn, list) and trkn:
                try:
                    track_num = int(trkn[0][0])
                except (TypeError, IndexError, ValueError):
                    pass

        result["track"] = track_num

    except MutagenError:
        logger.warning(f"error reading metadata from {filepath.name}")

    return result


def _get_first(audio, key: str) -> str | None:
    """Get first value from tag, handling list format."""
    try:
        value = audio.get(key)
        if value is None:
            return None
        if isinstance(value, list):
            return str(value[0]) if value else None
        return str(value)
    except Exception:
        # Corrupt tag value, encoding error, str() conversion failure - treat as missing
        return None


def _normalize_filename(name: str) -> str:
    """Normalize filename for duplicate detection.

    Handles OS duplicate suffixes like "song (1).mp3" → "song".
    Per guidelines: helper functions must never raise.
    """
    try:
        stem = Path(name).stem.lower()
        return re.sub(r'\s*\(\d+\)\s*$', '', stem)
    except Exception:
        return name.lower()


def _get_dedup_key(info: dict, filename: str) -> tuple:
    """Get deduplication key based on available metadata.

    Returns a tuple with type prefix for namespace separation:
    - ('metadata', title, artist) when both exist
    - ('title_only', title, normalized_filename) when title only
    - ('filename', normalized_filename) when no metadata

    Internal only - never displayed to users.
    """
    title = info.get('title')
    artist = info.get('artist')

    if title and artist:
        # Full metadata available - standard dedup
        return ('metadata', title.lower(), artist.lower())
    elif title:
        # Title only - combine with filename to distinguish different songs
        return ('title_only', title.lower(), _normalize_filename(filename))
    else:
        # No metadata - use normalized filename
        return ('filename', _normalize_filename(filename))


async def extract_metadata(filepath: Path, timeout: float = 15.0) -> dict:
    """Extract metadata asynchronously with timeout.

    If extraction takes longer than timeout (hung filesystem, corrupt file),
    returns fallback dict with filename as title. The background thread
    continues running until Mutagen completes, but the scan proceeds.
    """
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(extract_metadata_sync, filepath),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.warning(f"metadata extraction timed out: {filepath.name}")
        return {
            "filename": filepath.name,
            "title": filepath.stem,
            "artist": None,
            "album": None,
            "track": 0
        }


async def scan_playlist_metadata(
    playlist_path: Path,
    cache_dir: Path,
    playlist_name: str,
    force_rebuild: bool = False
) -> tuple[list[dict], int, list[Path], list[str]]:
    """Scan playlist directory, extract metadata, and update cache.

    Reads existing cache from cache_dir/<playlist_name>.json if available,
    extracts metadata from new/modified files, removes duplicates, and saves
    updated cache.

    Args:
        playlist_path: Directory containing audio files
        cache_dir: Directory for cache files (data/metadata/)
        playlist_name: Name of the playlist (used for cache filename)
        force_rebuild: If True, ignore existing cache and rescan everything

    Returns:
        Tuple of (metadata_list, new_count, filtered_paths, duplicate_names):
        - metadata_list: List of metadata dicts sorted by (track number, filename)
        - new_count: Number of new non-duplicate files added to playlist
        - filtered_paths: File paths after duplicate removal
        - duplicate_names: Filenames that were skipped as duplicates
    """
    cache_file = cache_dir / f'{playlist_name}.json'
    cache = {}

    # Load existing cache with corruption handling
    if cache_file.exists() and not force_rebuild:
        try:
            cache = await asyncio.to_thread(_load_json, cache_file)
        except json.JSONDecodeError as e:
            # Corrupt JSON - delete and regenerate
            logger.warning(f"cache corrupted at line {e.lineno}, regenerating")
            try:
                await asyncio.to_thread(cache_file.unlink, missing_ok=True)
            except OSError:
                # File locked by another process (Windows) - continue without delete
                pass
        except (UnicodeDecodeError, OSError) as e:
            # Encoding or I/O error - regenerate
            logger.warning("cache read error, regenerating")

    original_cache = set(cache.keys())
    metadata = []
    updated = False
    seen_keys: set[tuple] = set()  # Track duplicates by dedup key
    duplicates: list[str] = []  # Collect duplicate filenames for grouped logging
    extensions = ['*.mp3', '*.flac', '*.ogg', '*.opus', '*.m4a', '*.wav', '*.aac']

    for ext in extensions:
        for audio_file in playlist_path.glob(ext):
            try:
                stat = audio_file.stat()
                file_id = f"{audio_file.name}_{stat.st_mtime}"

                if file_id in cache:
                    info = cache[file_id]
                else:
                    # Extract new
                    info = await extract_metadata(audio_file)
                    info['file_id'] = file_id
                    info['path'] = str(audio_file)

                    # Apply lowercase
                    if info.get("title"):
                        info["title"] = info["title"].lower()
                    if info.get("artist"):
                        info["artist"] = info["artist"].lower()
                    if info.get("album"):
                        info["album"] = info["album"].lower()

                    cache[file_id] = info
                    updated = True

                # Duplicate detection using tiered key strategy
                dup_key = _get_dedup_key(info, audio_file.name)

                if dup_key in seen_keys:
                    duplicates.append(audio_file.name)
                    continue

                seen_keys.add(dup_key)
                metadata.append(info)

            except Exception as e:
                logger.warning(f"error processing {audio_file.name}")

                # Create minimal entry with filename fallback
                # This ensures files with metadata errors still appear in playlist
                # Use filename-only file_id (stat() could fail if file deleted)
                try:
                    stat = audio_file.stat()
                    file_id = f"{audio_file.name}_{stat.st_mtime}"
                except OSError:
                    # File deleted or inaccessible - use filename only
                    file_id = audio_file.name
                info = {
                    'filename': audio_file.name,
                    'title': audio_file.stem,  # Fallback to filename stem
                    'artist': None,
                    'album': None,
                    'track': 0,
                    'file_id': file_id,
                    'path': str(audio_file)
                }

                # Apply lowercase to fallback title
                info["title"] = info["title"].lower()

                # Don't add to cache (it's corrupt), but do add to metadata for playlist inclusion
                # Duplicate check using same tiered key strategy
                dup_key = _get_dedup_key(info, audio_file.name)

                if dup_key not in seen_keys:
                    seen_keys.add(dup_key)
                    metadata.append(info)

    # Sort by track number, then filename
    metadata.sort(key=lambda m: (m.get('track', 0), m.get('filename', '')))

    # Count new unique songs (in final metadata list, not in original cache)
    new_count = sum(1 for m in metadata if m['file_id'] not in original_cache)

    # Remove duplicates from cache (for autocomplete)
    # Keep only file IDs that are in the filtered metadata list
    filtered_file_ids = {entry['file_id'] for entry in metadata}
    cache = {fid: info for fid, info in cache.items() if fid in filtered_file_ids}

    # Save cache if updated (now contains only non-duplicates)
    if updated:
        try:
            await asyncio.to_thread(_save_json, cache_file, cache)
        except Exception as e:
            logger.warning("failed to save cache")

    # Build filtered file paths from metadata (non-duplicates only)
    filtered_paths = [Path(entry['path']) for entry in metadata]

    return metadata, new_count, filtered_paths, duplicates


def _load_json(path: Path) -> dict:
    """Load JSON file (caller handles decode/IO errors)."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _save_json(path: Path, data: dict) -> None:
    """Save JSON file atomically to prevent corruption."""
    import tempfile

    # Create parent directory if needed
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file first
    temp_fd, temp_path = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        try:
            f = os.fdopen(temp_fd, 'w', encoding='utf-8')
        except Exception:
            os.close(temp_fd)
            raise
        with f:
            json.dump(data, f, indent=2)
        # Atomic rename (works on Windows + Linux)
        Path(temp_path).replace(path)
    except Exception:
        Path(temp_path).unlink(missing_ok=True)
        raise
