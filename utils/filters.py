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

from mafic import Equalizer, Filter, Karaoke, LowPass, Rotation, Timescale, Tremolo, Vibrato

FILTER_LABEL = "preset"

# name -> (Filter, description)
FILTER_PRESETS: dict[str, tuple[Filter, str]] = {
    "bass boosted": (
        Filter(equalizer=Equalizer([0.10, 0.09, 0.08, 0.06, 0.03, 0, -0.05, -0.07, -0.07, -0.05, 0, 0, 0, 0, 0]), volume=0.88),
        "heavier low end",
    ),
    "nightcore": (
        Filter(timescale=Timescale(rate=1.25)),
        "sped up, high pitch",
    ),
    "slowed": (
        Filter(equalizer=Equalizer([-0.13, -0.13, -0.10, -0.06, -0.03, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]), timescale=Timescale(speed=0.88, pitch=0.92), low_pass=LowPass(smoothing=18.0), volume=1.40),
        "slowed down, muffled",
    ),
    "spatial": (
        Filter(rotation=Rotation(rotation_hz=0.07)),
        "rotating stereo",
    ),
    "karaoke": (
        Filter(equalizer=Equalizer([0.12, 0.11, 0.10, 0.08, 0.05, 0.08, 0.10, 0.08, 0.03, 0, 0, 0, 0, 0, 0]), karaoke=Karaoke(level=0.8, mono_level=1.0, filter_band=220.0, filter_width=100.0)),
        "vocal removal (mixed results)",
    ),
    "lo-fi": (
        Filter(
            equalizer=Equalizer([-0.05, -0.05, -0.03, 0, 0, 0.1, 0.1, 0.05, 0, -0.05, -0.1, -0.1, -0.15, -0.2, -0.25]),
            low_pass=LowPass(smoothing=14.0),
            tremolo=Tremolo(frequency=3.0, depth=0.15),
            vibrato=Vibrato(frequency=3.0, depth=0.1),
            volume=1.1,
        ),
        "muffled highs, warm mids",
    ),
}

PRESET_NAMES = list(FILTER_PRESETS.keys())


def get_filter(name: str) -> Filter | None:
    """Get a Filter by preset name. Returns None if not found."""
    preset = FILTER_PRESETS.get(name)
    return preset[0] if preset else None
