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

Extracts title, album artist, album, disc number, and track number from audio files.
Uses album artist only (not track/contributing artist) for sorting and display.
Supports multiple tag formats (ID3, Vorbis, MP4, etc.) via Mutagen.

Key functions:
- extract_metadata(): Async wrapper for single-file extraction
- scan_playlist_metadata(): Scan playlist with caching and duplicate detection

Caching:
- Caches stored in data/metadata/<playlist_name>.json
- Cache keyed by "rel_path_mtime" to detect modified files (rel_path = relative POSIX path from playlist root)
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

# Shared across all concurrent scan_playlist_metadata calls.
# Limits total extraction concurrency to match thread pool capacity.
_extraction_semaphore = asyncio.Semaphore(16)


def extract_metadata_sync(filepath: Path) -> dict:
    """Extract metadata from audio file (synchronous).

    Tries multiple tag formats (ID3, Vorbis, MP4) to find title, artist, album.
    Falls back to filename if metadata is missing or unreadable.

    Returns:
        Dict with keys: filename, title, artist, album, disc, track.
        title defaults to filename stem; artist/album may be None; disc/track default to 0.
    """
    result = {
        "filename": filepath.name,
        "title": filepath.stem,
        "artist": None,
        "album": None,
        "disc": 0,
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

        # Album artist only (not track/contributing artist)
        result["artist"] = (
            _get_first(audio, "albumartist") or
            _get_first(audio, "album artist") or  # Some taggers use space
            _get_first(audio, "TPE2") or
            _get_first(audio, "aART")
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

        # Disc number
        disc_str = _get_first(audio, "discnumber") or _get_first(audio, "TPOS")
        disc_num = 0

        if disc_str:
            try:
                disc_num = int(str(disc_str).split('/')[0])
            except (ValueError, TypeError):
                pass

        # MP4/M4A uses disk tag with tuple format [(disc, total)]
        if disc_num == 0:
            disk = audio.get("disk")
            if disk and isinstance(disk, list) and disk:
                try:
                    disc_num = int(disk[0][0])
                except (TypeError, IndexError, ValueError):
                    pass

        result["disc"] = disc_num

    except MutagenError as e:
        logger.warning(f"error reading metadata from {filepath.name}: {e}")

    return result


def _get_first(audio, key: str) -> str | None:
    """Get first value from tag, handling list format."""
    try:
        value = audio.get(key)
        if value is None:
            return None
        if isinstance(value, list):
            raw = str(value[0]) if value else None
        else:
            raw = str(value)
        if raw is None:
            return None
        # Collapse control chars to spaces, strip — whitespace-only → None
        cleaned = re.sub(r'[\x00-\x1f\x7f]+', ' ', raw).strip()
        return cleaned or None
    except Exception:
        # Corrupt tag value, encoding error, str() conversion failure - treat as missing
        return None


def _natural_sort_key(s: str) -> list:
    """Split string into text/number chunks for natural ordering.

    'Disc 2' -> ['disc ', 2]  'Disc 10' -> ['disc ', 10]
    """
    return [int(p) if p.isdigit() else p for p in re.split(r'(\d+)', s.lower())]


def _normalize_filename(name: str) -> str:
    """Normalize filename (or relative path) for duplicate detection.

    Handles OS duplicate suffixes like "song (1).mp3" → "song".
    Preserves parent directory for subfolder-aware dedup.
    Per guidelines: helper functions must never raise.
    """
    p = Path(name)
    try:
        stem = p.stem.lower()
        normalized = re.sub(r'\s*\(\d+\)\s*$', '', stem)
        parent = p.parent.as_posix().lower()
        return f"{parent}/{normalized}" if parent != "." else normalized
    except Exception:
        return name.lower()


def _get_dedup_key(info: dict, filename: str) -> tuple:
    """Get deduplication key based on available metadata.

    Returns a tuple with type prefix for namespace separation:
    - ('metadata', title, artist, album) when title and artist exist
    - ('title_only', title, normalized_filename) when title only
    - ('filename', normalized_filename) when no metadata

    Internal only - never displayed to users.
    """
    title = info.get('title')
    artist = info.get('artist')
    album = info.get('album')

    if title and artist:
        # Full metadata available - album included to prevent false matches
        # when many tracks share a generic album artist like "Various Artists"
        return ('metadata', title.lower(), artist.lower(), (album or '').lower())
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
            "disc": 0,
            "track": 0
        }


def _make_fallback(audio_file: Path, file_id: str) -> dict:
    """Create minimal metadata entry for files that failed extraction or stat."""
    return {
        'filename': audio_file.name,
        'title': audio_file.stem.lower(),
        'artist': None,
        'album': None,
        'disc': 0,
        'track': 0,
        'file_id': file_id
    }


def _collect_file_info(
    file_list: list[Path],
    cache: dict,
    playlist_root: Path
) -> list[tuple[Path, str | None, dict | None]]:
    """Phase 1: stat files and check cache (blocking I/O, run in thread).

    Returns ordered list of (audio_file, file_id, info_or_None):
    - stat success + cache hit: (file, file_id, cached_info)
    - stat success + cache miss: (file, file_id, None)
    - stat failure: (file, None, fallback_info) — file_id=None is the sentinel
    """
    entries = []
    for audio_file in file_list:
        try:
            stat = audio_file.stat()
            rel = audio_file.relative_to(playlist_root).as_posix()
            file_id = f"{rel}_{stat.st_mtime}"
            cached = cache.get(file_id)
            entries.append((audio_file, file_id, cached))
        except OSError as e:
            rel = audio_file.relative_to(playlist_root).as_posix()
            logger.warning(f"error accessing {rel}: {e}")
            fallback = _make_fallback(audio_file, audio_file.name)
            entries.append((audio_file, None, fallback))
    return entries


async def _extract_one(audio_file: Path, file_id: str) -> tuple[str, dict | None]:
    """Extract metadata for a single file with semaphore throttling."""
    async with _extraction_semaphore:
        try:
            info = await extract_metadata(audio_file)
            info['file_id'] = file_id

            # Apply lowercase normalization
            if info.get("title"):
                info["title"] = info["title"].lower()
            if info.get("artist"):
                info["artist"] = info["artist"].lower()
            if info.get("album"):
                info["album"] = info["album"].lower()

            return (file_id, info)
        except Exception as e:
            logger.warning(f"error extracting {audio_file.name}: {e}")
            return (file_id, None)


async def scan_playlist_metadata(
    file_list: list[Path],
    cache_dir: Path,
    playlist_name: str,
    playlist_root: Path,
    force_rebuild: bool = False
) -> tuple[list[dict], int, list[Path], list[str]]:
    """Scan playlist files, extract metadata, and update cache.

    Three-phase design for parallel extraction:
    1. Collect: stat files and check cache (threaded, non-blocking)
    2. Extract: parallel metadata extraction for uncached files
    3. Merge: sequential dedup and cache update

    Args:
        file_list: Pre-filtered audio file paths from library
        cache_dir: Directory for cache files (data/metadata/)
        playlist_name: Name of the playlist (used for cache filename)
        playlist_root: Filesystem path for the playlist directory
        force_rebuild: If True, ignore existing cache and rescan everything

    Returns:
        Tuple of (metadata_list, new_count, filtered_paths, duplicate_names):
        - metadata_list: List of metadata dicts sorted by (subfolder, artist, album, disc number, track number, filename)
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
        except (UnicodeDecodeError, OSError):
            # Encoding or I/O error - regenerate
            logger.warning("cache read error, regenerating")

    original_cache = set(cache.keys())

    # Phase 1: stat files and check cache (threaded to avoid blocking event loop)
    entries = await asyncio.to_thread(_collect_file_info, file_list, cache, playlist_root)

    # Phase 2: extract metadata for uncached files in parallel
    uncached = [(f, fid) for f, fid, cached in entries if fid is not None and cached is None]

    if uncached:
        extract_results = await asyncio.gather(
            *[_extract_one(f, fid) for f, fid in uncached]
        )
        extracted = dict(extract_results)
    else:
        extracted = {}

    # Phase 3: merge results and deduplicate
    metadata = []
    updated = False
    seen_keys: set[tuple] = set()
    duplicates: list[str] = []

    for audio_file, file_id, cached_info in entries:
        if file_id is None:
            # stat-failed fallback from Phase 1
            info = cached_info
        elif cached_info is not None:
            # Cache hit from Phase 1
            info = cached_info
        elif file_id in extracted and extracted[file_id] is not None:
            # Phase 2 extraction succeeded
            info = extracted[file_id]
            cache[file_id] = info
            updated = True
        else:
            # Phase 2 extraction failed — create fallback (don't cache)
            info = _make_fallback(audio_file, file_id)

        # Set rel_path on every entry (overwrites stale values from old caches)
        info['rel_path'] = audio_file.relative_to(playlist_root).as_posix()

        # Duplicate detection using tiered key strategy
        dup_key = _get_dedup_key(info, info['rel_path'])

        if dup_key in seen_keys:
            duplicates.append(info['rel_path'])
            continue

        seen_keys.add(dup_key)
        metadata.append(info)

    # Sort by subfolder (natural), artist, album, disc, track number (untagged last), filename (natural)
    metadata.sort(key=lambda m: (
        _natural_sort_key(str(Path(m.get('rel_path', m.get('filename', ''))).parent)),
        (0, _natural_sort_key(m['artist'])) if m.get('artist') else (1,),
        (0, _natural_sort_key(m['album'])) if m.get('album') else (1,),
        (0, m.get('disc', 0)) if m.get('disc', 0) > 0 else (1, 0),
        (0, m.get('track', 0)) if m.get('track', 0) > 0 else (1, 0),
        _natural_sort_key(m.get('filename', ''))
    ))

    # Count new unique songs (in final metadata list, not in original cache)
    new_count = sum(1 for m in metadata if m['file_id'] not in original_cache)

    # Remove duplicates from cache and reorder to match canonical sort
    # (cache dict order flows to empty-input autocomplete via metadata_cache.values())
    filtered_file_ids = {entry['file_id'] for entry in metadata}
    cache = {fid: info for fid, info in cache.items() if fid in filtered_file_ids}
    cache = {m['file_id']: cache[m['file_id']] for m in metadata if m['file_id'] in cache}

    # Save cache if updated (now contains only non-duplicates)
    if updated or len(cache) < len(original_cache):
        try:
            await asyncio.to_thread(_save_json, cache_file, cache)
        except Exception as e:
            logger.warning(f"failed to save cache: {e}")

    # Build filtered file paths from metadata (non-duplicates only)
    filtered_paths = [playlist_root / entry['rel_path'] for entry in metadata]

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
