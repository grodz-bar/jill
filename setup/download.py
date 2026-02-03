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

"""Lavalink downloader - stdlib only, with progress bar."""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

# Direct download URL (avoids GitHub API rate limits)
LAVALINK_DIRECT_URL = "https://github.com/lavalink-devs/Lavalink/releases/latest/download/Lavalink.jar"

# GitHub API fallback
LAVALINK_API_URL = "https://api.github.com/repos/lavalink-devs/Lavalink/releases/latest"

# Minimum valid file size (catches partial downloads)
MIN_JAR_SIZE = 45 * 1024 * 1024  # 45MB (actual Lavalink.jar is ~85MB)


def download_lavalink(dest_dir: Path, verbose: bool = True) -> tuple[bool, str]:
    """Download Lavalink.jar if missing or incomplete.

    Returns early if valid Lavalink.jar exists. Re-downloads if file is undersized.
    Creates dest_dir if needed.

    Fallback order: direct URL, GitHub API, manual instructions.

    Args:
        dest_dir: Directory to save Lavalink.jar
        verbose: Print progress messages

    Returns:
        (success, message)
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "Lavalink.jar"

    # Check if already exists and valid
    if dest_file.exists():
        size = dest_file.stat().st_size
        if size >= MIN_JAR_SIZE:
            return True, f"Lavalink.jar already exists ({size // (1024*1024)}MB)"
        else:
            if verbose:
                print(f"Existing Lavalink.jar too small ({size} bytes), re-downloading...")
            dest_file.unlink()

    # Try direct URL first
    if verbose:
        print("Getting Lavalink.jar from github.com/lavalink-devs...")

    success, msg = _download_with_direct_url(dest_file, verbose)
    if success:
        return True, msg

    # Try GitHub API fallback
    if verbose:
        print("Direct download failed, trying GitHub API...")

    success, msg = _download_with_github_api(dest_file, verbose)
    if success:
        return True, msg

    # Both failed - provide manual instructions
    return False, _get_manual_instructions()


def _download_with_direct_url(dest_file: Path, verbose: bool) -> tuple[bool, str]:
    """Download from direct GitHub URL with up to 3 attempts (2s, 4s backoff)."""
    last_error = ""
    for attempt in range(3):
        if attempt > 0:
            if verbose:
                print(f"Retry {attempt}/2...")
            time.sleep(2 ** attempt)  # Exponential backoff: 2s, 4s
        success, msg = _do_download(LAVALINK_DIRECT_URL, dest_file, verbose)
        if success:
            return True, msg
        last_error = msg
    return False, last_error


def _download_with_github_api(dest_file: Path, verbose: bool) -> tuple[bool, str]:
    """Try downloading using GitHub API to find asset URL."""
    try:
        req = urllib.request.Request(
            LAVALINK_API_URL,
            headers={"User-Agent": "Jill-Setup"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())

        for asset in data.get("assets", []):
            if asset.get("name") == "Lavalink.jar":
                download_url = asset.get("browser_download_url")
                # Validate URL is from expected GitHub domain
                if download_url and download_url.startswith("https://github.com/lavalink-devs/"):
                    return _do_download(download_url, dest_file, verbose)

        return False, "Lavalink.jar not found in release assets"

    except json.JSONDecodeError:
        return False, "Invalid JSON from GitHub API"
    except urllib.error.URLError as e:
        return False, f"GitHub API error: {e.reason}"
    except Exception as e:
        return False, f"GitHub API error: {e}"


def _do_download(url: str, dest_file: Path, verbose: bool) -> tuple[bool, str]:
    """Download file to dest_file with optional progress bar.

    Downloads to .tmp first, validates size, then renames. Cleans up .tmp on failure.

    Args:
        url: URL to download from
        dest_file: Destination path for the file
        verbose: Show progress bar (only if server provides Content-Length)

    Returns:
        (success, message)
    """
    temp_file = dest_file.with_suffix('.tmp')
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Jill-Setup"})

        with urllib.request.urlopen(req, timeout=300) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 65536  # 64KB chunks

            with open(temp_file, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)

                    if verbose and total_size:
                        _print_progress(downloaded, total_size)

        if verbose and total_size:
            print()  # Newline after progress bar

        # Verify file size
        if not temp_file.exists():
            return False, "Download completed but file not found"

        size = temp_file.stat().st_size
        if size < MIN_JAR_SIZE:
            temp_file.unlink()
            return False, f"Downloaded file too small ({size} bytes), may be corrupted"

        # Atomic rename to final destination
        temp_file.rename(dest_file)
        return True, f"Downloaded Lavalink.jar ({size // (1024*1024)}MB)"

    except urllib.error.URLError as e:
        if temp_file.exists():
            temp_file.unlink()
        return False, f"Download failed: {e.reason}"
    except KeyboardInterrupt:
        if temp_file.exists():
            temp_file.unlink()
        raise
    except Exception as e:
        if temp_file.exists():
            temp_file.unlink()
        return False, f"Download error: {e}"


def _print_progress(downloaded: int, total: int):
    """Print a progress bar to stdout."""
    percent = downloaded / total
    bar_width = 30
    filled = int(bar_width * percent)
    bar = "=" * filled + "-" * (bar_width - filled)
    mb_done = downloaded // (1024 * 1024)
    mb_total = total // (1024 * 1024)
    print(f"\r[{bar}] {mb_done}/{mb_total}MB", end="", flush=True)


def _get_manual_instructions() -> str:
    """Return manual download instructions when auto-download fails."""
    return """
Could not auto-download Lavalink. Please download manually:

1. Go to: https://github.com/lavalink-devs/Lavalink/releases/latest
2. Download Lavalink.jar from the Assets section
3. Place it in the lavalink/ folder

This may have failed due to:
- No internet connection
- GitHub rate limiting (try again in a few minutes)
- Firewall blocking the download
""".strip()
