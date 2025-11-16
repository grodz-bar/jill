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
        title=MESSAGES['now_playing_title'],
        description=MESSAGES['track_info'].format(index=track_index, name=track_name),
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

    status = MESSAGES['status_paused'] if is_paused else MESSAGES['status_playing']
    embed.set_footer(text=status.replace('*', ''))

    return embed


def create_queue_embed(
    current_track: Optional[str],
    upcoming_tracks: List[str],
    shuffle_enabled: bool = False,
    last_played: Optional[str] = None
) -> disnake.Embed:
    """Create embed showing current queue."""
    from config import MESSAGES, BOT_COLORS

    embed = disnake.Embed(
        title=MESSAGES['queue_title'],
        color=BOT_COLORS['info']
    )

    if last_played:
        embed.add_field(
            name="Last Played",
            value=f"⏮️ {last_played}",
            inline=False
        )

    if current_track:
        embed.add_field(
            name=MESSAGES['now_playing_title'].replace('**', ''),
            value=f"▶️ {current_track}",
            inline=False
        )

    if upcoming_tracks:
        queue_text = "\n".join([f"{i+1}. {track}" for i, track in enumerate(upcoming_tracks[:10])])
        if len(upcoming_tracks) > 10:
            queue_text += "\n" + MESSAGES['and_more'].format(count=len(upcoming_tracks) - 10)
        embed.add_field(
            name=MESSAGES['up_next'].replace('**', ''),
            value=queue_text,
            inline=False
        )
    else:
        embed.add_field(
            name=MESSAGES['up_next'].replace('**', ''),
            value=MESSAGES['queue_empty_message'].replace('*', ''),
            inline=False
        )

    if shuffle_enabled:
        embed.set_footer(text="🔀 Shuffle is ON")

    return embed


def create_control_panel_embed(
    is_playing: bool = False,
    track_name: Optional[str] = None,
    track_index: Optional[int] = None,
    playlist_name: Optional[str] = None,
    is_paused: bool = False,
    upcoming_track_names: Optional[List[str]] = None,
    total_upcoming: int = 0,
    shuffle_enabled: bool = False,
    current_drink_emoji: Optional[str] = None,
    last_track_name: Optional[str] = None,
    last_drink_emoji: Optional[str] = None,
    next_drink_emoji: Optional[str] = None
) -> disnake.Embed:
    """Create control panel embed with boxed prefix-style layout."""
    from config import MESSAGES, BOT_COLORS, FALLBACK_PLAYLIST_NAME

    # Choose color based on state
    if is_paused:
        color = BOT_COLORS['warning']
    elif is_playing:
        color = BOT_COLORS['primary']
    else:
        color = BOT_COLORS['info']

    # Build boxed layout
    if track_name and track_index is not None:
        # Calculate total tracks (current index + remaining)
        total_tracks = track_index + total_upcoming

        # Header: 💿 1/14 - Breach TOP (or just 💿 1/14 if no playlist)
        if playlist_name:
            header = f"💿 {track_index}/{total_tracks} - {playlist_name}"
        else:
            # Use fallback name if no playlist structure
            header = f"💿 {track_index}/{total_tracks} - {FALLBACK_PLAYLIST_NAME}"

        # Build boxed content
        lines = [header, "╔════════════════════════════╗"]

        # Last Served (conditional - only if there's a previous track)
        if last_track_name:
            emoji = last_drink_emoji if last_drink_emoji else "🍷"
            lines.append(f"  {emoji} Last Served: {last_track_name}")

        # Now Serving (always shown when playing)
        emoji = current_drink_emoji if current_drink_emoji else "🍸"
        lines.append(f"  {emoji} Now Serving → {track_name}")

        # Coming Up (conditional - only if there are upcoming tracks)
        if upcoming_track_names and len(upcoming_track_names) > 0:
            emoji = next_drink_emoji if next_drink_emoji else "🍹"
            lines.append(f"  {emoji} Coming Up:")
            for track in upcoming_track_names[:3]:
                lines.append(f"      • {track}")

        lines.append("╚════════════════════════════╝")
        description = "\n".join(lines)
    else:
        description = f"{MESSAGES['nothing_playing']}\n{MESSAGES['queue_empty_message']}"

    # Create embed with no title
    embed = disnake.Embed(
        description=description,
        color=color
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

    title = MESSAGES['tracks_title']
    if playlist_name:
        title = f"{MESSAGES['tracks_title']} - {playlist_name}"

    embed = disnake.Embed(
        title=title,
        color=BOT_COLORS['info']
    )

    if tracks:
        embed.description = "\n".join(tracks)
    else:
        embed.description = MESSAGES['error_no_tracks']

    if total_pages > 1:
        embed.set_footer(text=MESSAGES['page_info'].format(current=page, total=total_pages))

    return embed


def create_playlists_embed(playlists: List[str]) -> disnake.Embed:
    """Create embed showing available playlists."""
    from config import MESSAGES, BOT_COLORS

    embed = disnake.Embed(
        title=MESSAGES['playlists_title'],
        color=BOT_COLORS['info']
    )

    if playlists:
        embed.description = "\n".join([f"• {p}" for p in playlists])
    else:
        embed.description = MESSAGES['error_no_playlists']

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
        title=MESSAGES['help_title'],
        description=MESSAGES['help_description'],
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
