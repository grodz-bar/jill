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

"""Fuzzy search for music tracks using RapidFuzz.

Best practices from:
- RapidFuzz: WRatio for general-purpose, token_set_ratio for word order independence
- Spotify: Combine "title artist" into searchable field
- Thresholds: 75% for auto-play, 51% for picker, 61% for autocomplete
"""

from rapidfuzz import fuzz
from rapidfuzz.utils import default_process


def fuzzy_search(query: str, tracks: list[dict], max_results: int = 25) -> list[tuple[dict, float]]:
    """
    Search tracks with fuzzy matching using RapidFuzz.

    Uses multiple strategies and takes the best score:
    1. WRatio on "artist - title" (handles most cases well)
    2. token_set_ratio on "artist title" (word order independence)
    3. WRatio on title only (for title-focused searches)
    4. partial_ratio on title (for substring matches like "drum" → "Drum Show")

    Args:
        query: Search string (truncated to 100 chars)
        tracks: List of dicts with keys: title, artist (optional), track
        max_results: Maximum results to return (default 25)

    Returns:
        List of (track, confidence) tuples sorted by confidence (0-100, or 101 for exact title match).
    """
    if not query or not tracks:
        return []

    # Truncate absurdly long queries (no song title is 100+ chars)
    query = query[:100]

    # Normalize query (lowercase, strip whitespace)
    query_processed = default_process(query)
    if not query_processed:
        return []

    results = []

    for track in tracks:
        title = track.get('title', '')
        artist = track.get('artist')
        filename = track.get('filename', '')

        # Build searchable strings (omit artist if missing)
        title_artist = f"{artist} - {title}" if artist else title
        title_artist_combined = f"{artist} {title}" if artist else title

        # Strategy 1: WRatio on "artist - title" (best general-purpose)
        # Handles partial matches, different lengths, some word reordering
        score_wratio = fuzz.WRatio(query, title_artist, processor=default_process)

        # Strategy 2: token_set_ratio on combined (word order independence)
        # "Garoad Dawn Approaches" matches "Dawn Approaches Garoad" perfectly
        # Length penalty: short queries shouldn't get 100% on long targets
        score_token_set_raw = fuzz.token_set_ratio(query, title_artist_combined, processor=default_process)
        target_len = len(default_process(title_artist_combined))
        length_ratio = min(len(query_processed) / max(target_len, 1), 1.0)
        score_token_set = score_token_set_raw * (0.7 + 0.3 * length_ratio)

        # Strategy 3: WRatio on title only (for title-focused searches)
        score_title = fuzz.WRatio(query, title, processor=default_process)

        # Strategy 4: partial_ratio on title (substring matching)
        # "drum" matches "Drum Show" well
        # Length penalty: if query is longer than title, title is just a fragment
        score_partial_raw = fuzz.partial_ratio(query, title, processor=default_process)
        title_len = len(default_process(title))
        if len(query_processed) > title_len:
            title_ratio = title_len / len(query_processed)
            score_partial = score_partial_raw * (0.5 + 0.5 * title_ratio)
        else:
            score_partial = score_partial_raw

        # Take best score from all strategies
        final_score = max(score_wratio, score_token_set, score_title, score_partial)

        # Boost exact matches by 1 point to ensure they win ties
        # Example: "Date 2" query vs "Date 2" title gets 101, vs "Date" title gets 100
        if default_process(title) == query_processed:
            final_score += 1

        results.append((track, final_score))

    # Sort by score descending, then by track number for tie-breaker
    results.sort(key=lambda x: (-x[1], x[0].get('track', 0)))

    return results[:max_results]


def get_best_match(query: str, tracks: list[dict]) -> tuple[dict | None, float, list[tuple[dict, float]]]:
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
    results = fuzzy_search(query, tracks)

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


def autocomplete_search(query: str, tracks: list[dict], max_results: int = 25) -> list[tuple[dict, float]]:
    """Search for Discord autocomplete dropdown.

    Filters results to 61%+ confidence. Default max_results=25 matches Discord's autocomplete limit.
    """
    results = fuzzy_search(query, tracks, max_results=max_results)
    return [(t, s) for t, s in results if s >= 61]
