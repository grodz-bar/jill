"""
Slash Mode Embed Configuration

Embed builders that use configuration values, no hardcoded strings.
"""

import disnake
from typing import Optional, List

def create_now_playing_embed(
    track_name: str,
    track_index: int,
    total_tracks: int,
    playlist_name: Optional[str] = None,
    is_paused: bool = False
) -> disnake.Embed:
    """Create embed for currently playing track."""
    from config import MESSAGES, BOT_COLORS

    color = BOT_COLORS['warning'] if is_paused else BOT_COLORS['success']

    embed = disnake.Embed(
        title=MESSAGES['NOW_PLAYING_TITLE'],
        description=MESSAGES['TRACK_INFO'].format(index=track_index, name=track_name),
        color=color
    )

    if playlist_name:
        embed.add_field(
            name="Playlist",
            value=playlist_name,
            inline=True
        )

    embed.add_field(
        name="Progress",
        value=f"{track_index}/{total_tracks}",
        inline=True
    )

    status = MESSAGES['STATUS_PAUSED'] if is_paused else MESSAGES['STATUS_PLAYING']
    embed.set_footer(text=status.replace('*', ''))

    return embed


def create_queue_embed(
    current_track: Optional[str],
    upcoming_tracks: List[str],
    shuffle_enabled: bool = False
) -> disnake.Embed:
    """Create embed showing current queue."""
    from config import MESSAGES, BOT_COLORS

    embed = disnake.Embed(
        title=MESSAGES['QUEUE_TITLE'],
        color=BOT_COLORS['info']
    )

    if current_track:
        embed.add_field(
            name=MESSAGES['NOW_PLAYING_TITLE'].replace('**', ''),
            value=f"▶️ {current_track}",
            inline=False
        )

    if upcoming_tracks:
        queue_text = "\n".join([f"{i+1}. {track}" for i, track in enumerate(upcoming_tracks[:10])])
        if len(upcoming_tracks) > 10:
            queue_text += "\n" + MESSAGES['AND_MORE'].format(count=len(upcoming_tracks) - 10)
        embed.add_field(
            name=MESSAGES['UP_NEXT'].replace('**', ''),
            value=queue_text,
            inline=False
        )
    else:
        embed.add_field(
            name=MESSAGES['UP_NEXT'].replace('**', ''),
            value=MESSAGES['QUEUE_EMPTY_MESSAGE'].replace('*', ''),
            inline=False
        )

    if shuffle_enabled:
        embed.set_footer(text="🔀 Shuffle is ON")

    return embed


def create_control_panel_embed(is_playing: bool = False) -> disnake.Embed:
    """Create embed for the control panel."""
    from config import MESSAGES, BOT_COLORS

    embed = disnake.Embed(
        title=MESSAGES['CONTROL_PANEL_TITLE'],
        description=MESSAGES['CONTROL_PANEL_DESC'],
        color=BOT_COLORS['primary'] if is_playing else BOT_COLORS['info']
    )

    return embed


def create_tracks_embed(
    tracks: List[str],
    page: int = 1,
    total_pages: int = 1,
    playlist_name: Optional[str] = None
) -> disnake.Embed:
    """Create embed showing track list."""
    from config import MESSAGES, BOT_COLORS

    title = MESSAGES['TRACKS_TITLE']
    if playlist_name:
        title = f"{MESSAGES['TRACKS_TITLE']} - {playlist_name}"

    embed = disnake.Embed(
        title=title,
        color=BOT_COLORS['info']
    )

    if tracks:
        embed.description = "\n".join(tracks)
    else:
        embed.description = MESSAGES['NO_TRACKS']

    if total_pages > 1:
        embed.set_footer(text=MESSAGES['PAGE_INFO'].format(current=page, total=total_pages))

    return embed


def create_playlists_embed(playlists: List[str]) -> disnake.Embed:
    """Create embed showing available playlists."""
    from config import MESSAGES, BOT_COLORS

    embed = disnake.Embed(
        title=MESSAGES['PLAYLISTS_TITLE'],
        color=BOT_COLORS['info']
    )

    if playlists:
        embed.description = "\n".join([f"• {p}" for p in playlists])
    else:
        embed.description = MESSAGES['NO_PLAYLISTS']

    return embed


def create_error_embed(error_message: str) -> disnake.Embed:
    """Create embed for error messages."""
    from config import BOT_COLORS

    embed = disnake.Embed(
        title="❌ Error",
        description=error_message,
        color=BOT_COLORS['error']
    )

    return embed


def create_help_embed() -> disnake.Embed:
    """Create help embed."""
    from config import MESSAGES, BOT_COLORS, COMMAND_DESCRIPTIONS

    embed = disnake.Embed(
        title=MESSAGES['HELP_TITLE'],
        description=MESSAGES['HELP_DESCRIPTION'],
        color=BOT_COLORS['primary']
    )

    for cmd, desc in COMMAND_DESCRIPTIONS.items():
        embed.add_field(
            name=f"/{cmd}",
            value=desc,
            inline=False
        )

    return embed


__all__ = [
    'create_now_playing_embed',
    'create_queue_embed',
    'create_control_panel_embed',
    'create_tracks_embed',
    'create_playlists_embed',
    'create_error_embed',
    'create_help_embed',
]
