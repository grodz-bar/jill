# Messages

`/jill/config/messages.yaml`

Customize most messages Jill sends.

> [!NOTE]
> Docker users: edit this file in your mounted `config/` folder.

### How Messages Work

```yaml
# messages.yaml
not_in_vc:
  text: "hey, come sit at the bar first"
  enabled: true
```

- `text` - Message content (supports markdown and variables)
- `enabled` - `true` shows the message, `false` performs the action silently

> Errors default to enabled, confirmations default to disabled. Jill stays quiet when things work, speaks up when something goes wrong.

### Formatting

**Variables** - Dynamic content in curly braces:

| Variable | Contains |
|----------|----------|
| `{title}` | Track title |
| `{name}` | Item name (playlist, track, etc.) |
| `{playlist}` | Current playlist name |
| `{level}` | Volume percentage (0-100) |
| `{position}` | Seek position as percentage |
| `{playlists}` | Number of playlists |
| `{tracks}` | Number of tracks |
| `{channel}` | Voice channel mention |
| `{command}` | Command name (without the slash) |

**Discord markdown** works in messages: `**bold**` → **bold**, `*italic*` → *italic*, `` `code` `` → `code`, `~~strike~~` → ~~strike~~

### Custom Emojis

You can add your server's custom emojis to messages:

1. In Discord, type `\:youremojiname:` (with the backslash) and send
2. Copy the output - it looks like `<:name:123456789012345678>`
3. Paste the whole thing into your message text

**Example:**
```yaml
# messages.yaml
not_in_vc:
  text: "<:jillgun:1234567890123456> hey, come sit at the bar first"
  enabled: true
```

> [!NOTE]
> Custom emojis must be from the server Jill is in, or uploaded to your [Application's Emoji tab](https://discord.com/developers/applications).

### All Messages

| Key | Message | When Used | Default |
|-----|---------|-----------|---------|
| **Voice Channel Errors** |  |  |  |
| `not_in_vc` | "hey, come sit at the bar first" | User isn't in any voice channel | enabled |
| `wrong_vc` | "wrong bar, i'm at {channel}" | User is in a different channel than Jill | enabled |
| `voice_error` | "voice hiccup, hit me again" | Generic voice connection issue | enabled |
| `need_vc_permissions` | "don't have access to that channel" | Jill lacks Connect/Speak permissions | enabled |
| `failed_join_vc` | "can't get in there" | Failed to join voice channel | enabled |
| | | | |
| **Permission Errors** |  |  |  |
| `no_permission` | "sorry, that's for staff only" | User lacks role for restricted command | enabled |
| `command_disabled` | "`/{command}` isn't available" | Command disabled in settings | enabled |
| | | | |
| **Playback** |  |  |  |
| `nothing_playing` | "bar's quiet right now" | Tried to control playback with nothing queued | enabled |
| `now_playing` | "now serving: **{title}**" | Track starts playing | disabled |
| `paused` | "taking a break" | Playback paused | disabled |
| `resumed` | "back at it" | Playback resumed | disabled |
| `stopped` | "shift's over, heading out" | Playback stopped, Jill leaves voice | disabled |
| `already_playing` | "already serving that" | Tried to play a track already playing | disabled |
| | | | |
| **Search and Tracks** |  |  |  |
| `song_not_found` | "don't have that one in stock" | Search returned no results | enabled |
| `track_load_failed` | "can't load that" | Failed to load audio file | enabled |
| `track_play_error` | "that broke, try again" | Playback error mid-track | enabled |
| | | | |
| **Queue and Playlists** |  |  |  |
| `queue_empty` | "nothing in the queue" | Queue is empty | enabled |
| `no_playlists` | "shelves are empty" | No playlists in music library | enabled |
| `playlist_empty` | "that one's empty" | Selected playlist has no tracks | enabled |
| `no_playlist_loaded` | "no menu set" | No playlist currently selected | disabled |
| `playlist_not_found` | "can't find '{name}'" | Playlist name doesn't exist | enabled |
| `playlist_not_found_pick` | "can't find '{name}', pick from available:" | Partial match, showing alternatives | enabled |
| `playlist_switched` | "switching to **{playlist}** menu" | Playlist changed | disabled |
| | | | |
| **Settings** |  |  |  |
| `volume_set` | "volume set to {level}%" | Volume changed | disabled |
| `shuffle_on` | "mixing it up" | Shuffle enabled | disabled |
| `shuffle_off` | "keeping it neat" | Shuffle disabled | disabled |
| `loop_on` | "i'll keep this one going" | Loop enabled | disabled |
| `loop_off` | "last pour for this one" | Loop disabled | disabled |
| | | | |
| **Seek and Navigation** |  |  |  |
| `seek_to` | "jumped to {position}% of **{title}**" | Seeked to position | disabled |
| `cant_seek` | "can't do that for this drink" | Track doesn't support seeking | enabled |
| `history_empty` | "nothing before this" | Tried to go back with no history | disabled |
| | | | |
| **Admin** |  |  |  |
| `rescan_complete` | "found {playlists} playlists and {tracks} songs" | Library rescan finished | enabled |
| `rescan_in_progress` | "a rescan is already running, please wait" | Rescan attempted while one is running | enabled |
| `rescan_failed` | "rescan failed, check the logs" | Library rescan failed | enabled |
| `music_unavailable` | "music system's down" | Lavalink not connected | enabled |
| | | | |
| **Errors** |  |  |  |
| `error_generic` | "something broke, try again" | Unexpected error occurred | enabled |
| | | | |
| **Control Panel** |  |  |  |
| `panel_deleted` | "panel's gone" | Panel message was deleted | enabled |
| `panel_orphaned` | "that panel's outdated" | Interacted with an old panel | enabled |
| `library_unavailable` | "music library's offline" | Library not loaded | enabled |
| `select_playlist` | "pick a playlist:" | Prompt for playlist picker | enabled |
| | | | |
| **Hints** |  |  |  |
| `shuffle_hint` | "try `/shuffle on` or `/shuffle off`" | Hint about shuffle command | disabled |
| `loop_hint` | "try `/loop on` or `/loop off`" | Hint about loop command | disabled |
| | | | |
| **Search UI** |  |  |  |
| `track_selected` | "got it, **{title}** coming up" | User selected a track | disabled |

### Tips

**Keep messages short.** Discord embeds have character limits, and brief messages are easier to read.

**Test custom emojis.** Make sure Jill can access the emoji (it must be from a server Jill is in).

**Leave errors enabled.** If a user tries something that fails, they need to know why. Silencing errors creates confusion.

**Reset to defaults.** Delete the file entirely and restart Jill. A fresh file will be generated with all defaults.

**Check your syntax.** YAML is sensitive to indentation. Use spaces (not tabs) and keep the two-space indent consistent.

### Related

- **[Settings Reference](settings.md)** - Configure behavior, UI, and commands
- **[Permissions Reference](permissions.md)** - Control who can use what
