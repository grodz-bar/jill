# Settings

`/jill/config/settings.yaml` - created after first run

Customize Jill's panel appearance, playback behavior, and commands.

> [!NOTE]
> **Docker users**: configure via [Environment Variables](environment.md) instead.

> [!IMPORTANT]
> Buttons and commands are independent: disabling one doesn't affect the other.

> **Priority** (highest wins): Environment variables > settings.yaml > Built-in defaults

### Panel Appearance

| Setting | Default | Description |
|---------|---------|-------------|
| `panel.enabled` | `true` | Show the control panel. `false` = slash commands only |
| `panel.color` | `0xA03E72` | Embed accent color. Formats: `A03E72`, `0xA03E72`, `"#A03E72"` |
| `panel.info_fallback_message` | `"mixing drinks`<br>`and changing lives"` | Shown when track has no artist/album/playlist |
| `panel.drink_emojis` | `['🍸', '🍹', '🍻',`<br>`'🍸', '🍷', '🧉',`<br>`'🍶', '🥃']` | Emojis that cycle in panel header |
| `panel.drink_emojis_enabled` | `true` | Show drink emojis |
| `panel.progress_bar_enabled` | `true` | Show the progress bar |
| `panel.progress_bar_filled` | `🟪` | Progress bar filled emoji |
| `panel.progress_bar_empty` | `⬛` | Progress bar empty emoji |
| `panel.shuffle_button` | `true` | Show shuffle button |
| `panel.loop_button` | `true` | Show loop button |
| `panel.playlist_button` | `true` | Show playlist button (auto-hidden if only 1 playlist) |

### Playback

| Setting | Default | Description |
|---------|---------|-------------|
| `default_volume` | `50` | Startup volume (0-100) |
| `default_playlist` | — | Playlist to auto-load (overrides remembered playlist) |
| `inactivity_timeout` | `10` | Minutes before auto-disconnect when alone. `0` = never |
| `presence_enabled` | `true` | Show "Listening to [song]" in bot status |

> Jill remembers volume and last playlist between restarts. `default_playlist` overrides the remembered playlist if set.

### Display

| Setting | Default | Description |
|---------|---------|-------------|
| `queue_display_size` | `15` | Tracks per page in `/queue` (1-50) |
| `playlists_display_size` | `15` | Playlists per page in `/playlists` (1-50) |

### Commands

| Setting | Default | Description |
|---------|---------|-------------|
| `commands.shuffle_command` | `true` | Enable `/shuffle` |
| `commands.loop_command` | `true` | Enable `/loop` |
| `commands.rescan_command` | `true` | Enable `/rescan` (admin) |

### Library

| Setting | Default | Description |
|---------|---------|-------------|
| `auto_rescan` | `true` | Scan for new/changed files on startup |

> Auto-rescan only reads tags from new or modified files. Use `/rescan` for a full rebuild.

### Logging

| Setting | Default | Description |
|---------|---------|-------------|
| `logging.level` | `verbose` | Log verbosity |

> - `minimal`: errors + milestones
> - `verbose`: + voice events, track changes
> - `debug`: + HTTP, internal state

<details>
<summary><strong>Advanced</strong></summary>

<br>

### UI Timing

| Setting | Default | Description |
|---------|---------|-------------|
| `ui.extended_auto_delete` | `90` | Seconds before `/queue`, `/playlists`, `/np` auto-delete. `0` = never |
| `ui.brief_auto_delete` | `10` | Seconds before feedback/error messages auto-delete. `0` = never |

### Panel Performance

| Setting | Default | Description |
|---------|---------|-------------|
| `panel.progress_update_interval` | `15` | Seconds between progress bar updates (10-3600) |
| `panel.update_debounce_ms` | `500` | Wait before updating. Higher = less flicker, slower feel (300+) |
| `panel.recreate_interval` | `30` | Minutes before recreating panel. `0` = never |

Discord embeds get sluggish after many edits. Periodic recreation keeps things responsive.

</details>

> For setting up who can do what, see [Permissions](permissions.md).

<details>
<summary><strong>Environment-Only Settings</strong></summary>

<br>

These settings are configured in `.env`, not settings.yaml. See [.env.example](../../../.env.example) for details.

#### Paths

| Variable | Default | Description |
|----------|---------|-------------|
| `MUSIC_PATH` | `./music` | Music library location |
| `CONFIG_PATH` | `./config` | YAML config files |
| `DATA_PATH` | `./data` | Runtime state files |

#### Infrastructure

| Variable | Default | Description |
|----------|---------|-------------|
| `LAVALINK_HOST` | `127.0.0.1` | Lavalink server address |
| `LAVALINK_PORT` | `2333` | Lavalink port |
| `LAVALINK_PASSWORD` | (see .env.example) | Lavalink auth |
| `HTTP_SERVER_HOST` | `127.0.0.1` | Bot's audio server bind |
| `HTTP_SERVER_PORT` | `2334` | Bot's audio server port |
| `MANAGE_LAVALINK` | `true` | Kill stale Lavalink on startup/shutdown |

</details>
