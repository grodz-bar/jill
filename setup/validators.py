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

"""Validation utilities for setup - stdlib only."""

import re
import shutil
import socket
import subprocess
import sys
from pathlib import Path


def check_python_version(min_version: tuple = (3, 11)) -> tuple[bool, str]:
    """Check if Python version meets minimum requirement.

    Args:
        min_version: Minimum required version as tuple (major, minor)

    Returns:
        (ok, message)
    """
    current = sys.version_info[:2]
    version_str = f"{current[0]}.{current[1]}"

    if current >= min_version:
        return True, f"Python {version_str}"
    else:
        min_str = f"{min_version[0]}.{min_version[1]}"
        return False, f"Python {min_str}+ required, found {version_str}"


def check_java_version(min_version: int = 17) -> tuple[bool, str]:
    """Check if Java version meets minimum requirement.

    Parses `java -version` output (which goes to stderr).

    Args:
        min_version: Minimum required major version

    Returns:
        (ok, message)
    """
    # Check if java is in PATH
    if not shutil.which("java"):
        return False, "Java not installed or not in PATH"

    try:
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        # Java outputs version to stderr
        output = result.stderr or result.stdout

        # Parse version from output like:
        # openjdk version "17.0.1" or java version "21.0.1"
        # Also handles legacy 1.x format: java version "1.8.0_321"
        match = re.search(r'(?:version|release) "(\d+)(?:\.(\d+))?', output)
        if match:
            major = int(match.group(1))
            # Java 8 and earlier used 1.x format (1.8 = Java 8)
            if major == 1 and match.group(2):
                major = int(match.group(2))
            if major >= min_version:
                return True, f"Java {major}"
            else:
                return False, f"Java {min_version}+ required, found Java {major}"

        return False, "Could not parse Java version"

    except subprocess.TimeoutExpired:
        return False, "Java version check timed out"
    except Exception as e:
        return False, f"Java check failed: {e}"


def validate_token_format(token: str) -> tuple[bool, str]:
    """Basic validation of Discord bot token format.

    Discord tokens have three dot-separated base64 sections. This check is
    lenient - better to let unexpected formats through than reject valid tokens.

    Args:
        token: The Discord bot token to validate

    Returns:
        (ok, message) - messages are user-friendly, not technical
    """
    if not token or not isinstance(token, str):
        return False, "Token is empty"

    token = token.strip()

    # Common mistakes with clear fixes
    if token.startswith('"') or token.startswith("'"):
        return False, "Remove the quotes around your token"

    if " " in token:
        return False, "Token contains spaces - make sure you copied it completely"

    if token == "your_token_here":
        return False, "Replace 'your_token_here' with your actual bot token"

    # Structure check: three dot-separated parts
    parts = token.split(".")
    if len(parts) != 3 or any(not part for part in parts):
        return False, (
            "That doesn't look like a valid token.\n"
            "Get a fresh one: Discord Developer Portal > Your App > Bot > Reset Token"
        )

    # Length sanity check (very lenient - just catch obvious mistakes)
    # Valid tokens are typically 59-72 chars but we use wide range for safety
    if len(token) < 50 or len(token) > 150:
        return False, (
            "Token appears incomplete or corrupted.\n"
            "Try copying it again from the Developer Portal"
        )

    return True, "Token format valid"


def check_port_available(port: int, host: str = "127.0.0.1") -> tuple[bool, str]:
    """Check if a port has nothing listening.

    Uses TCP connect to test if something is already bound to the port.

    Args:
        port: Port number to check
        host: Host to check on (default localhost)

    Returns:
        (available, message)
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            if result == 0:
                # Port is in use (connection succeeded)
                return False, f"Port {port} is already in use"
            else:
                # Port is available (connection refused)
                return True, f"Port {port} available"
    except socket.error as e:
        return False, f"Port check failed: {e}"


def check_disk_space(path: Path, min_mb: int = 300) -> tuple[bool, str]:
    """Check available disk space at path.

    Args:
        path: Path to check. Walks up to find existing parent if needed.
        min_mb: Minimum required MB (default 300 for Lavalink + headroom)

    Returns:
        (ok, message)
    """
    try:
        # Ensure path exists or use parent
        check_path = path if path.exists() else path.parent
        while not check_path.exists() and check_path.parent != check_path:
            check_path = check_path.parent

        stat = shutil.disk_usage(check_path)
        available_mb = stat.free // (1024 * 1024)

        if available_mb >= min_mb:
            return True, f"{available_mb}MB available"
        else:
            return False, f"Low disk space: {available_mb}MB (need {min_mb}MB)"

    except Exception as e:
        return False, f"Disk check failed: {e}"


def get_windows_excluded_port_ranges() -> list[tuple[int, int]]:
    """Get Windows reserved/excluded port ranges.

    Only runs on Windows - returns empty list on other platforms or errors.

    Returns:
        List of (start, end) tuples for reserved ranges
    """
    if sys.platform != "win32":
        return []

    try:
        result = subprocess.run(
            ["netsh", "interface", "ipv4", "show", "excludedportrange", "protocol=tcp"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return []

        ranges = []
        for line in result.stdout.splitlines():
            match = re.match(r'^\s*(\d+)\s+(\d+)', line)
            if match:
                ranges.append((int(match.group(1)), int(match.group(2))))
        return ranges

    except Exception:
        return []


def check_port_reserved(port: int, ranges: list[tuple[int, int]]) -> bool:
    """Check if port is in any of the given ranges.

    Args:
        port: Port to check
        ranges: List of (start, end) tuples (inclusive bounds)

    Returns:
        True if port is in a reserved range
    """
    return any(start <= port <= end for start, end in ranges)
