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

"""Audio filter presets for Lavalink playback."""

from mafic import Equalizer, Filter, Karaoke, LowPass, Rotation, Timescale

FILTER_LABEL = "preset"

# name -> (Filter, description)
FILTER_PRESETS: dict[str, tuple[Filter, str]] = {
    "bass boost": (
        Filter(equalizer=Equalizer([0.6, 0.7, 0.8, 0.55, 0.25, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])),
        "heavy low end",
    ),
    "nightcore": (
        Filter(timescale=Timescale(speed=1.25, pitch=1.3)),
        "sped up, high pitch",
    ),
    "slowed": (
        Filter(timescale=Timescale(speed=0.85, pitch=0.9), low_pass=LowPass(smoothing=20.0)),
        "slowed down, muffled",
    ),
    "8d": (
        Filter(rotation=Rotation(rotation_hz=0.2)),
        "rotating stereo",
    ),
    "karaoke": (
        Filter(karaoke=Karaoke()),
        "vocal removal",
    ),
}

PRESET_NAMES = list(FILTER_PRESETS.keys())


def get_filter(name: str) -> Filter | None:
    """Get a Filter by preset name. Returns None if not found."""
    preset = FILTER_PRESETS.get(name)
    return preset[0] if preset else None
