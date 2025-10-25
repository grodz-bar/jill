# Copyright (C) 2025 grodz-bar
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

"""
Context Managers for Safe State Management

Provides context managers that guarantee cleanup even when errors occur.
Replaces manual flag management patterns with safer, more Pythonic code.
"""

from contextlib import contextmanager
from typing import Any


@contextmanager
def suppress_callbacks(player: Any):
    """
    Temporarily suppress track callbacks during manual playback control.

    Usage:
        with suppress_callbacks(player):
            player.voice_client.stop()  # Won't trigger after_track callback

    This prevents race conditions when manually changing tracks. The callback
    will be blocked from triggering play_next(), preventing double-playback.

    Args:
        player: MusicPlayer instance with _suppress_callback attribute
    """
    player._suppress_callback = True
    try:
        yield
    finally:
        player._suppress_callback = False


@contextmanager
def reconnecting_state(player: Any):
    """
    Mark player as reconnecting during channel switches.

    Usage:
        with reconnecting_state(player):
            await voice_client.move_to(new_channel)

    Prevents callbacks and certain operations during voice channel transitions.

    Args:
        player: MusicPlayer instance with _is_reconnecting attribute
    """
    player._is_reconnecting = True
    try:
        yield
    finally:
        player._is_reconnecting = False
