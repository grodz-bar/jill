# Environment Variables

`docker-compose.yml`

Docker configuration reference. Set these in the `environment:` section.

> [!NOTE]
> Native Windows/Linux users: configure via [settings.yaml](settings.md) instead.

### Quick Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_TOKEN` | — | **Required.** Bot token |
| `GUILD_ID` | — | Server ID for instant slash commands |
| `PUID` | 1000 | User ID for file permissions |
| `PGID` | 1000 | Group ID for file permissions |
| `DEFAULT_VOLUME` | 50 | Initial volume (0-100) |
| `DEFAULT_PLAYLIST` | — | Playlist folder name to auto-load |
| `AUTO_RESCAN` | true | Scan for new music on startup |
| `INACTIVITY_TIMEOUT` | 10 | Minutes before auto-disconnect (0 = never) |
| `PRESENCE_ENABLED` | true | Show "Listening to [song]" in bot status |
| `QUEUE_DISPLAY_SIZE` | 15 | Tracks per page (1-50) |
| `PLAYLISTS_DISPLAY_SIZE` | 15 | Playlists per page (1-50) |
| `LOG_LEVEL` | verbose | `minimal`, `verbose`, or `debug` |
| `PANEL_ENABLED` | true | Show the control panel |
| `PANEL_COLOR` | A03E72 | Hex color for panel accent |
| `PROGRESS_BAR_ENABLED` | true | Show progress bar |
| `PROGRESS_BAR_FILLED` | 🟪 | Filled portion emoji |
| `PROGRESS_BAR_EMPTY` | ⬛ | Empty portion emoji |
| `DRINK_EMOJIS_ENABLED` | true | Cycling drink emojis per track |
| `INFO_FALLBACK_MESSAGE` | mixing drinks and changing lives | Shown when no artist/album |
| `SHUFFLE_BUTTON` | true | Show shuffle button |
| `LOOP_BUTTON` | true | Show loop button |
| `PLAYLIST_BUTTON` | true | Show playlist button |
| `PROGRESS_UPDATE_INTERVAL` | 15 | Seconds between updates (10-3600) |
| `UPDATE_DEBOUNCE_MS` | 500 | Wait before panel update (ms) |
| `RECREATE_INTERVAL` | 30 | Minutes before panel recreate (0 = never) |
| `SHUFFLE_COMMAND` | true | Enable /shuffle command |
| `LOOP_COMMAND` | true | Enable /loop command |
| `RESCAN_COMMAND` | true | Enable /rescan command |
| `EXTENDED_AUTO_DELETE` | 90 | Seconds for /queue, /np messages (0 = never) |
| `BRIEF_AUTO_DELETE` | 10 | Seconds for feedback messages (0 = never) |
| `ENABLE_PERMISSIONS` | false | Enable role-based restrictions |
| `BARTENDER_ROLE_ID` | — | Role ID for playback commands |

### Notes

> [!IMPORTANT]
> Hiding a button doesn't disable its command, and disabling a command doesn't hide its button.

> [!TIP]
> `GUILD_ID` makes slash commands appear instantly instead of taking up to an hour.

> [!WARNING]
> Never share your `DISCORD_TOKEN` or commit it to version control.

> [!TIP]
> **PUID/PGID**: Find your IDs with `id -u` and `id -g`. Most Linux users are 1000:1000 (the default).

> [!NOTE]
> **Playlist name**: `DEFAULT_PLAYLIST` uses the folder name from `music/`, not a display name.
>
> **Color formats**: `A03E72`, `#A03E72`, and `0xA03E72` all work.
>
> **Custom emoji**: `PROGRESS_BAR_FILLED`/`EMPTY` accept custom server emoji.
>
> **Debounce**: `UPDATE_DEBOUNCE_MS` - higher = less flicker, slower feel. Lower = snappier but may flicker.
>
> **Recreation**: `RECREATE_INTERVAL` - Discord gets sluggish after many edits. Recreating keeps it responsive.
>
> **Drink emojis**: Customize via `panel.drink_emojis` in [settings.yaml](settings.md#panel-appearance).
>
> **Comments**: A `space` followed by `#` starts a comment: `playlist #1` is treated as `playlist`.

### Tips

**No quotes around values:**
```yaml
# Correct
- DISCORD_TOKEN=MTIz...

# Wrong
- DISCORD_TOKEN="MTIz..."
```

**Empty value uses default:**
```yaml
- DEFAULT_VOLUME=     # Uses 50
- DEFAULT_VOLUME=75   # Uses 75
```

<details>
<summary><strong>Paths (Advanced)</strong></summary>

Docker Compose sets these automatically. Only change for custom deployments.

| Variable | Default | Docker Default | Purpose |
|----------|---------|----------------|---------|
| `MUSIC_PATH` | ./music | /music | Music library location |
| `CONFIG_PATH` | ./config | /config | YAML config files |
| `DATA_PATH` | ./data | /data | Runtime state files |

</details>

<details>
<summary><strong>Infrastructure (Advanced)</strong></summary>

Lavalink connection settings. Defaults work for standard deployments.

| Variable | Default | Docker Default | Purpose |
|----------|---------|----------------|---------|
| `LAVALINK_HOST` | 127.0.0.1 | lavalink | Lavalink server address |
| `LAVALINK_PORT` | 2333 | 2333 | Lavalink port |
| `LAVALINK_PASSWORD` | timetomixdrinksandnotchangepasswords | (same) | Lavalink auth |
| `HTTP_SERVER_HOST` | 127.0.0.1 | 0.0.0.0 | Bot's audio server bind |
| `HTTP_SERVER_URL_HOST` | (HTTP_SERVER_HOST) | jill | Hostname in audio URLs |
| `HTTP_SERVER_PORT` | 2334 | 2334 | Bot's audio server port |
| `MANAGE_LAVALINK` | true | true | Kill stale Lavalink on startup/shutdown |

</details>
