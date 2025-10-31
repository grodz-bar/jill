"""
Filename Pattern Configuration - Shared Between All Modes

Patterns for parsing track numbers from filenames.
"""

import re

# Patterns to strip track numbers from filenames
# Each pattern should capture the number prefix to remove
FILENAME_PATTERNS = [
    r'^\d+\s*[-_.]?\s*',  # "01 - ", "01. ", "01_", "01 "
    r'^\[\d+\]\s*',       # "[01] "
    r'^\(\d+\)\s*',       # "(01) "
    r'^\d+\)',            # "01)"
    r'^#\d+\s*',          # "#01 "
]

# Compiled patterns for efficiency
COMPILED_PATTERNS = [re.compile(pattern) for pattern in FILENAME_PATTERNS]

def clean_filename(filename: str) -> str:
    """
    Remove track number prefixes from filename.

    Args:
        filename: Original filename

    Returns:
        Cleaned filename without number prefix
    """
    for pattern in COMPILED_PATTERNS:
        filename = pattern.sub('', filename)
    return filename.strip()

__all__ = [
    'FILENAME_PATTERNS',
    'COMPILED_PATTERNS',
    'clean_filename',
]
