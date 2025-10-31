"""
Slash Mode Button Configuration

Discord button components using configuration values.
"""

import disnake

def create_control_buttons(is_playing: bool = False, is_paused: bool = False) -> list:
    """Create button components for the control panel."""
    from config import BUTTON_LABELS

    buttons = []

    # Previous
    buttons.append(
        disnake.ui.Button(
            style=disnake.ButtonStyle.secondary,
            label=BUTTON_LABELS['previous'],
            custom_id="music_previous",
            disabled=not is_playing
        )
    )

    # Play/Pause toggle
    if is_paused or not is_playing:
        buttons.append(
            disnake.ui.Button(
                style=disnake.ButtonStyle.success,
                label=BUTTON_LABELS['play'],
                custom_id="music_play",
                disabled=False
            )
        )
    else:
        buttons.append(
            disnake.ui.Button(
                style=disnake.ButtonStyle.primary,
                label=BUTTON_LABELS['pause'],
                custom_id="music_pause",
                disabled=not is_playing
            )
        )

    # Skip
    buttons.append(
        disnake.ui.Button(
            style=disnake.ButtonStyle.secondary,
            label=BUTTON_LABELS['skip'],
            custom_id="music_skip",
            disabled=not is_playing
        )
    )

    # Shuffle
    buttons.append(
        disnake.ui.Button(
            style=disnake.ButtonStyle.secondary,
            label=BUTTON_LABELS['shuffle'],
            custom_id="music_shuffle",
            disabled=not is_playing
        )
    )

    # Stop
    buttons.append(
        disnake.ui.Button(
            style=disnake.ButtonStyle.danger,
            label=BUTTON_LABELS['stop'],
            custom_id="music_stop",
            disabled=not is_playing
        )
    )

    return [disnake.ui.ActionRow(*buttons)]


def create_pagination_buttons(current_page: int, total_pages: int) -> list:
    """Create pagination buttons for list displays."""
    from config import BUTTON_LABELS

    buttons = []

    # Previous page
    buttons.append(
        disnake.ui.Button(
            style=disnake.ButtonStyle.secondary,
            label=BUTTON_LABELS['page_prev'],
            custom_id="page_previous",
            disabled=current_page <= 1
        )
    )

    # Page indicator
    buttons.append(
        disnake.ui.Button(
            style=disnake.ButtonStyle.secondary,
            label=BUTTON_LABELS['page_info'].format(current=current_page, total=total_pages),
            custom_id="page_info",
            disabled=True
        )
    )

    # Next page
    buttons.append(
        disnake.ui.Button(
            style=disnake.ButtonStyle.secondary,
            label=BUTTON_LABELS['page_next'],
            custom_id="page_next",
            disabled=current_page >= total_pages
        )
    )

    return [disnake.ui.ActionRow(*buttons)]


__all__ = [
    'create_control_buttons',
    'create_pagination_buttons',
]
