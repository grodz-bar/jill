# Slash Commands

Type `/` in Discord to see all available commands.

| Command | What it does | Permission |
|---------|--------------|------------|
| `/play [song]` | Search for a song or resume | bartender |
| `/pause` | Pause playback | bartender |
| `/skip` | Next track (restarts if looping) | bartender |
| `/previous` | Previous track (restarts if looping) | bartender |
| `/stop` | Stop and disconnect | bartender |
| `/seek <position>` | Jump to position in track (0-100%) | bartender |
| `/playlist [name]` | Switch to a playlist (has autocomplete) | bartender |
| `/shuffle <on/off>` | Toggle shuffle on or off | bartender |
| `/loop <on/off>` | Toggle track loop on or off | bartender |
| `/volume <0-100>` | Adjust music volume | bartender |
| `/panel [remove]` | Create, move, or remove the control panel | bartender |
| `/filter [preset]` | Apply an audio filter | bartender |
| `/queue` | Show current queue | customer |
| `/playlists` | List all available playlists | customer |
| `/np` | Show current song details | customer |
| `/rescan` | Fully rebuilds metadata cache | owner |

> `[brackets]` = optional, `<brackets>` = required.

> [!IMPORTANT]
> By default, everyone can use all commands. The "Permission" column only applies if you [enable permissions](../configuration/permissions.md).

### Behavior Notes

> [!NOTE]
> Playback commands require you to be in Jill's voice channel. When Jill isn't in a voice channel, `/shuffle`, `/loop`, `/filter`, and `/playlist` still work.
>
> **Filters**: Use with `/filter`, pick "clear" to return to normal playback.
>
> **Loop**: Repeats current track, resets when you switch playlists or restart Jill.
>
> **Saved across restarts**: Volume, shuffle mode, last playlist, filter selection.
>
> **`/playlists`**: Disabled if you only have one playlist.

### Disabling Commands

**Docker** (in [`docker-compose.yml`](../configuration/environment.md)):
```yaml
- SHUFFLE_COMMAND=false
- LOOP_COMMAND=false
- FILTER_COMMAND=false
- PANEL_COMMAND=false
```

**Windows/Linux** (in [`settings.yaml`](../configuration/settings.md#commands)):
```yaml
# settings.yaml
commands:
  shuffle_command: false
  loop_command: false
  filter_command: false
  panel_command: false
```

> Disabled commands still appear in Discord but respond with "command disabled" when used.
