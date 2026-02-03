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

"""Lavalink health check utilities - stdlib only."""

import time
import urllib.request
import urllib.error


DEFAULT_PASSWORD = "timetomixdrinksandnotchangepasswords"


def is_lavalink_running(
    host: str = "127.0.0.1",
    port: int = 4440,
    password: str = DEFAULT_PASSWORD
) -> bool:
    """Quick check if Lavalink is responding.

    Args:
        host: Lavalink host
        port: Lavalink port
        password: Lavalink password for Authorization header

    Returns:
        True if Lavalink responds to version endpoint
    """
    try:
        url = f"http://{host}:{port}/version"
        req = urllib.request.Request(url, headers={"Authorization": password})
        with urllib.request.urlopen(req, timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def wait_for_lavalink(
    host: str = "127.0.0.1",
    port: int = 4440,
    password: str = DEFAULT_PASSWORD,
    timeout: int = 60,
    verbose: bool = True
) -> tuple[bool, str]:
    """Wait for Lavalink to become ready.

    Polls /version endpoint until success or timeout. Exits early on auth error.

    Args:
        host: Lavalink host
        port: Lavalink port
        password: Lavalink password for Authorization header
        timeout: Maximum seconds to wait
        verbose: Print progress to stdout

    Returns:
        (success, version_string_or_error)
    """
    url = f"http://{host}:{port}/version"
    start_time = time.time()

    if verbose:
        print("Waiting for Lavalink", end="", flush=True)

    while time.time() - start_time < timeout:
        try:
            req = urllib.request.Request(url, headers={"Authorization": password})
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    version = response.read().decode().strip()
                    if verbose:
                        print(f" ready (v{version})")
                    return True, version
        except urllib.error.HTTPError as e:
            if e.code == 401:
                if verbose:
                    print(" auth error")
                return False, "Lavalink password incorrect"
        except Exception:
            pass

        if verbose:
            print(".", end="", flush=True)
        time.sleep(1)

    if verbose:
        print(" timeout")

    return False, f"Lavalink not ready after {timeout} seconds"
