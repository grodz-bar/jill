# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

"""
Filename Pattern Configuration

Configure how the bot removes numeric prefixes from track and playlist names.

QUICK GUIDE:
- Choose a pattern from the list below that matches your file naming style
- Set SELECTED_PATTERN to the pattern name you want to use
- Restart bot after changes

PATTERN EXAMPLES:
- 'default'      → "01 - Song Name.opus"  becomes "Song Name"
- 'underscore'   → "01_Song_Name.opus"    becomes "Song_Name"
- 'period'       → "01. Song Name.opus"   becomes "Song Name"
- 'dash_compact' → "01-Song Name.opus"    becomes "Song Name"
- 'space_only'   → "01 Song Name.opus"    becomes "Song Name"
- 'track_disc'   → "1-05 Song Name.opus"  becomes "Song Name"
- 'none'         → "01 - Song Name.opus"  stays "01 - Song Name"

ADDING CUSTOM PATTERNS:
1. Add a new entry to FILENAME_PATTERNS below with your regex pattern
2. Set SELECTED_PATTERN to your new pattern name
3. Test with your music files

NOTE: All patterns work for both track filenames and playlist folder names.
"""

import logging
import re

logger = logging.getLogger(__name__)

# =========================================================================================================
# FILENAME PATTERNS (Add your own patterns here!)
# =========================================================================================================

FILENAME_PATTERNS = {
    # Standard formats
    'default': r'^\d+\s*-\s*',           # "01 - Song Name" or "1 - Song Name"
    'underscore': r'^\d+_',               # "01_Song_Name" or "1_Song_Name"
    'period': r'^\d+\.\s*',               # "01. Song Name" or "1. Song Name"
    'dash_compact': r'^\d+-',             # "01-Song Name" or "1-Song Name"
    'space_only': r'^\d+\s+',             # "01 Song Name" (must have space after number)

    # Special formats
    'track_disc': r'^\d+-\d+\s*',         # "1-05 Song Name" (disc-track format)

    # No removal (keeps original filename)
    'none': r'^(?!x)x',                   # Pattern that never matches (keeps full name)
}

# =========================================================================================================
# USER CONFIGURATION
# =========================================================================================================

# Which pattern to use for your files
# Change this to match your file naming convention
SELECTED_PATTERN = 'default'

# =========================================================================================================
# VALIDATION (DO NOT MODIFY)
# =========================================================================================================

if SELECTED_PATTERN not in FILENAME_PATTERNS:
    available = ', '.join(sorted(FILENAME_PATTERNS.keys()))
    error_msg = (
        f"Invalid SELECTED_PATTERN '{SELECTED_PATTERN}'. "
        f"Available patterns: {available}"
    )
    logger.critical(error_msg)
    raise ValueError(error_msg)

logger.info(f"Filename pattern selected: '{SELECTED_PATTERN}'")

# Compile the regex pattern for use by track.py
COMPILED_PATTERN = re.compile(FILENAME_PATTERNS[SELECTED_PATTERN])
