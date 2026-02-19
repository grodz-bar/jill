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

"""Fuzzy search for music tracks and playlists using RapidFuzz.

Best practices from:
- RapidFuzz: WRatio for general-purpose, token_set_ratio for word order independence
- Spotify: Combine "title artist" into searchable field
- Thresholds: 75% for auto-play, 51% for picker, 61% for autocomplete

Search index: build_search_index() pre-computes processed strings once per playlist
load. fuzzy_search() uses pre-processed data with processor=None, eliminating
redundant default_process() calls on every autocomplete keystroke.
"""

from dataclasses import dataclass

from rapidfuzz import fuzz, process
from rapidfuzz.utils import default_process


@dataclass(slots=True)
class SearchEntry:
    """Pre-processed search data for one track.

    Built once per playlist load via build_search_index().
    Reused across every autocomplete keystroke and /play search.
    """
    track: dict                      # Original metadata dict
    proc_title: str                  # default_process(title)
    proc_title_artist: str           # default_process("artist - title")
    proc_title_artist_combined: str  # default_process("artist title")
    title_len: int                   # len(proc_title)
    combined_len: int                # len(proc_title_artist_combined)


def build_search_index(tracks: list[dict]) -> list[SearchEntry]:
    """Pre-process track strings for fast fuzzy search.

    Call once when metadata_cache is populated. Returns one SearchEntry per track.
    """
    entries = []
    for track in tracks:
        title = track.get('title', '') or ''
        artist = track.get('artist') or ''

        title_artist = f"{artist} - {title}" if artist else title
        title_artist_combined = f"{artist} {title}" if artist else title

        proc_title = default_process(title) or ''
        proc_ta = default_process(title_artist) or proc_title
        proc_tac = default_process(title_artist_combined) or proc_title

        entries.append(SearchEntry(
            track=track,
            proc_title=proc_title,
            proc_title_artist=proc_ta,
            proc_title_artist_combined=proc_tac,
            title_len=len(proc_title),
            combined_len=len(proc_tac),
        ))
    return entries


def fuzzy_search(query: str, index: list[SearchEntry], max_results: int = 25) -> list[tuple[dict, float]]:
    """
    Search tracks with fuzzy matching using RapidFuzz.

    Uses multiple strategies and takes the best score:
    1. WRatio on "artist - title" (handles most cases well)
    2. token_set_ratio on "artist title" (word order independence)
    3. WRatio on title only (for title-focused searches)
    4. partial_ratio on title (for substring matches like "drum" → "Drum Show")

    Args:
        query: Search string (truncated to 100 chars)
        index: Pre-built search index from build_search_index()
        max_results: Maximum results to return (default 25)

    Returns:
        List of (track, confidence) tuples sorted by confidence (0-100, or 101 for exact title match).
    """
    if not query or not index:
        return []

    # Truncate absurdly long queries (no song title is 100+ chars)
    query = query[:100]

    # Normalize query (lowercase, strip whitespace)
    query_processed = default_process(query)
    if not query_processed:
        return []

    query_len = len(query_processed)
    results = []

    for entry in index:
        # Strategy 1: WRatio on "artist - title" (best general-purpose)
        # Handles partial matches, different lengths, some word reordering
        score_wratio = fuzz.WRatio(query_processed, entry.proc_title_artist, processor=None)

        # Strategy 2: token_set_ratio on combined (word order independence)
        # "Garoad Dawn Approaches" matches "Dawn Approaches Garoad" perfectly
        # Length penalty: short queries shouldn't get 100% on long targets
        score_token_set_raw = fuzz.token_set_ratio(query_processed, entry.proc_title_artist_combined, processor=None)
        length_ratio = min(query_len / max(entry.combined_len, 1), 1.0)
        score_token_set = score_token_set_raw * (0.7 + 0.3 * length_ratio)

        # Strategy 3: WRatio on title only (for title-focused searches)
        score_title = fuzz.WRatio(query_processed, entry.proc_title, processor=None)

        # Strategy 4: partial_ratio on title (substring matching)
        # "drum" matches "Drum Show" well
        # Length penalty: if query is longer than title, title is just a fragment
        score_partial_raw = fuzz.partial_ratio(query_processed, entry.proc_title, processor=None)
        if query_len > entry.title_len:
            title_ratio = entry.title_len / query_len
            score_partial = score_partial_raw * (0.5 + 0.5 * title_ratio)
        else:
            score_partial = score_partial_raw

        # Take best score from all strategies
        final_score = max(score_wratio, score_token_set, score_title, score_partial)

        # Boost exact matches by 1 point to ensure they win ties
        # Example: "Date 2" query vs "Date 2" title gets 101, vs "Date" title gets 100
        if entry.proc_title == query_processed:
            final_score += 1

        results.append((entry.track, final_score))

    # Sort by score descending, then by track number for tie-breaker
    results.sort(key=lambda x: (-x[1], x[0].get('track', 0)))

    return results[:max_results]


def get_best_match(query: str, index: list[SearchEntry]) -> tuple[dict | None, float, list[tuple[dict, float]]]:
    """
    Get best match with confidence handling.

    Thresholds based on industry standards (Microsoft Power Query, Algolia):
    - >100: Exact title match, always auto-play (bypasses ambiguity check)
    - >75: High confidence, auto-play unless ambiguous (2nd result within 10 points)
    - 51-75: Medium confidence, show selection menu
    - <51: Too uncertain, no match

    Returns: (best_track, confidence, alternatives)
    - If confidence > 75 and unambiguous: returns (track, conf, [])
    - If confidence 51-75 or ambiguous: returns (None, 0, alternatives)
    - If confidence < 51: returns (None, 0, [])
    """
    results = fuzzy_search(query, index)

    if not results:
        return None, 0, []

    best_track, best_score = results[0]

    # High confidence - auto-play
    if best_score > 75:
        # Exact title match (101%+) - user typed the exact title, no ambiguity
        if best_score > 100:
            return best_track, best_score, []

        # Check for ambiguity: if 2nd result is within 10 points, show menu
        if len(results) > 1 and results[1][1] > best_score - 10:
            alternatives = [(t, s) for t, s in results if s >= 51]
            return None, 0, alternatives[:25]

        return best_track, best_score, []

    # Medium confidence - show options
    if best_score >= 51:
        # Filter to only show tracks above threshold
        alternatives = [(t, s) for t, s in results if s >= 51]
        return None, 0, alternatives[:25]

    # Low confidence - no match
    return None, 0, []


def autocomplete_search(query: str, index: list[SearchEntry], max_results: int = 25) -> list[tuple[dict, float]]:
    """Search for Discord autocomplete dropdown.

    Filters results to 61%+ confidence. Default max_results=25 matches Discord's autocomplete limit.
    """
    results = fuzzy_search(query, index, max_results=max_results)
    return [(t, s) for t, s in results if s >= 61]


def playlist_search(query: str, names: list[str], max_results: int = 25,
                    score_cutoff: float = 0) -> list[tuple[str, float]]:
    """Fuzzy search for playlist names using WRatio.

    Args:
        query: Search string
        names: List of playlist names
        max_results: Maximum results to return
        score_cutoff: Minimum score threshold (0-100)

    Returns:
        List of (name, score) tuples sorted by score descending.
    """
    if not query or not names:
        return []

    query = query[:100]

    results = process.extract(query, names, scorer=fuzz.WRatio,
                              limit=max_results, score_cutoff=score_cutoff)
    return [(name, score) for name, score, idx in results]
