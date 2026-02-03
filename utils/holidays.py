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

"""Holiday theme definitions for seasonal easter eggs."""

from datetime import date

# Chinese New Year dates (first day only) - source: pinyin.info
CNY_DATES: dict[int, tuple[int, int]] = {
    # fmt: off
    2000: (2, 5),  2001: (1, 24), 2002: (2, 12), 2003: (2, 1),  2004: (1, 22),
    2005: (2, 9),  2006: (1, 29), 2007: (2, 18), 2008: (2, 7),  2009: (1, 26),
    2010: (2, 14), 2011: (2, 3),  2012: (1, 23), 2013: (2, 10), 2014: (1, 31),
    2015: (2, 19), 2016: (2, 8),  2017: (1, 28), 2018: (2, 16), 2019: (2, 5),
    2020: (1, 25), 2021: (2, 12), 2022: (2, 1),  2023: (1, 22), 2024: (2, 10),
    2025: (1, 29), 2026: (2, 17), 2027: (2, 6),  2028: (1, 26), 2029: (2, 13),
    2030: (2, 3),  2031: (1, 23), 2032: (2, 11), 2033: (1, 31), 2034: (2, 19),
    2035: (2, 8),  2036: (1, 28), 2037: (2, 15), 2038: (2, 4),  2039: (1, 24),
    2040: (2, 12), 2041: (2, 1),  2042: (1, 22), 2043: (2, 10), 2044: (1, 30),
    2045: (2, 17), 2046: (2, 6),  2047: (1, 26), 2048: (2, 14), 2049: (2, 2),
    2050: (1, 23), 2051: (2, 11), 2052: (2, 1),  2053: (2, 19), 2054: (2, 8),
    2055: (1, 28), 2056: (2, 15), 2057: (2, 4),  2058: (1, 24), 2059: (2, 12),
    2060: (2, 2),  2061: (1, 21), 2062: (2, 9),  2063: (1, 29), 2064: (2, 17),
    2065: (2, 5),  2066: (1, 26), 2067: (2, 14), 2068: (2, 3),  2069: (1, 23),
    2070: (2, 11), 2071: (1, 31), 2072: (2, 19), 2073: (2, 7),  2074: (1, 27),
    2075: (2, 15), 2076: (2, 5),  2077: (1, 24), 2078: (2, 12), 2079: (2, 2),
    2080: (1, 22), 2081: (2, 9),  2082: (1, 29), 2083: (2, 17), 2084: (2, 6),
    2085: (1, 26), 2086: (2, 14), 2087: (2, 3),  2088: (1, 24), 2089: (2, 10),
    2090: (1, 30), 2091: (2, 18), 2092: (2, 7),  2093: (1, 27), 2094: (2, 15),
    2095: (2, 5),  2096: (1, 25), 2097: (2, 12), 2098: (2, 1),  2099: (1, 21),
    # fmt: on
}


def _get_thanksgiving(year: int) -> tuple[int, int]:
    """Calculate US Thanksgiving (4th Thursday of November)."""
    # Nov 1 weekday: 0=Mon, 3=Thu
    nov1 = date(year, 11, 1).weekday()
    # Days until first Thursday (Thursday = 3)
    days_to_thu = (3 - nov1) % 7
    first_thu = 1 + days_to_thu
    fourth_thu = first_thu + 21
    return (11, fourth_thu)


# Chinese zodiac animals in order (12-year cycle)
# 2020 = Rat (index 0), 2021 = Ox, ..., 2024 = Dragon, 2025 = Snake, etc.
ZODIAC_EMOJIS: list[str] = [
    "🐀",  # Rat
    "🐂",  # Ox
    "🐅",  # Tiger
    "🐇",  # Rabbit
    "🐉",  # Dragon
    "🐍",  # Snake
    "🐎",  # Horse
    "🐐",  # Goat
    "🐒",  # Monkey
    "🐓",  # Rooster
    "🐕",  # Dog
    "🐖",  # Pig
]


def _get_cny_emojis(year: int) -> list[str]:
    """Get Chinese New Year emojis with correct zodiac animal for the year."""
    zodiac_index = (year - 2020) % 12
    zodiac_emoji = ZODIAC_EMOJIS[zodiac_index]
    # Base CNY emojis with dynamic zodiac animal
    return ["🧧", zodiac_emoji, "🏮", "🎆", "🧨", "🎊", "🍊", "🎋"]


HOLIDAYS: dict[str, dict] = {
    "new_year": {
        "dates": [(1, 1)],
        "color": 0xD4AF37,  # Metallic gold
        "emojis": ["🎉", "🥂", "🎊", "✨", "🎆", "🍾", "🕛", "🎇"],
        "progress_filled": "🟨",
    },
    "chinese_new_year": {
        "dates": "cny_lookup",  # Special handling
        "color": 0xE81A0A,  # Chinese red
        "emojis": "cny_dynamic",  # Special handling - uses _get_cny_emojis(year)
        "progress_filled": "🟥",
    },
    "valentines": {
        "dates": [(2, 14)],
        "color": 0xE84A8A,  # Rose pink
        "emojis": ["💕", "💖", "💌", "🌹", "💝", "💗", "💘", "🍫"],
        "progress_filled": "🟥",
    },
    "st_patricks": {
        "dates": [(3, 17)],
        "color": 0x139F38,  # Irish green
        "emojis": ["☘️", "🪙", "🎩", "🍀", "🍺", "💚", "🇮🇪", "🌈"],
        "progress_filled": "🟩",
    },
    "april_fools": {
        "dates": [(4, 1)],
        "color": 0xC4A484,  # Light coffee brown (soft drinks only today)
        "emojis": ["🥤", "🧃", "🥛", "☕", "🍵", "🧋", "🫖", "🍼"],
        "progress_filled": "⬜",
    },
    "halloween": {
        "dates": [(10, 31)],
        "color": 0xF06A10,  # Pumpkin orange
        "emojis": ["🎃", "👻", "🦇", "🕷️", "🕸️", "🍬", "💀", "🧙"],
        "progress_filled": "🟧",
    },
    "thanksgiving": {
        "dates": "thanksgiving_calc",  # Special handling
        "color": 0xC7745B,  # Autumn brown
        "emojis": ["🦃", "🍂", "🌽", "🥧", "🍁", "🌾", "🥖", "🍎"],
        "progress_filled": "🟫",
    },
    "christmas": {
        "dates": [(12, 24), (12, 25)],
        "color": 0xC41E3A,  # Christmas red
        "emojis": ["🎄", "🎅", "☃️", "⭐", "❄️", "🦌", "🔔", "🤶"],
        "progress_filled": "⬜",
    },
}


def get_active_holiday() -> dict | None:
    """Return active holiday theme, or None if no holiday today.

    Returns dict with 'color', 'emojis', 'progress_filled'. CNY includes
    year-specific zodiac emoji. Never raises (defensive for easter egg).
    """
    try:
        today = date.today()
        month, day = today.month, today.day

        for name, holiday in HOLIDAYS.items():
            dates = holiday["dates"]

            if dates == "cny_lookup":
                # Chinese New Year: check lookup table + dynamic emojis
                cny = CNY_DATES.get(today.year)
                if cny and (month, day) == cny:
                    # Return copy with year-specific zodiac emojis
                    return {
                        "color": holiday["color"],
                        "emojis": _get_cny_emojis(today.year),
                        "progress_filled": holiday["progress_filled"],
                    }
            elif dates == "thanksgiving_calc":
                # Thanksgiving: calculate 4th Thursday of November
                if (month, day) == _get_thanksgiving(today.year):
                    return holiday
            elif (month, day) in dates:
                return holiday

        return None
    except Exception:
        return None  # Fail silently - it's just an easter egg
