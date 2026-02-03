# Slash Commands

Type `/` in Discord to see all available commands.

| Command | What it does | Permission |
|---------|--------------|------------|
| `/play [song]` | Play a song, or resume if no song specified | bartender |
| `/pause` | Pause playback | bartender |
| `/skip` | Next track (with loop on, replays current track) | bartender |
| `/previous` | Previous track (with loop on, replays current track) | bartender |
| `/stop` | Stop and disconnect | bartender |
| `/seek <position>` | Jump to position in track (0-100%) | bartender |
| `/playlist <name>` | Switch playlist (has autocomplete) | bartender |
| `/shuffle <on/off>` | Toggle shuffle mode | bartender |
| `/loop <on/off>` | Toggle single-track repeat | bartender |
| `/volume <0-100>` | Set volume | bartender |
| `/queue` | Show current queue | customer |
| `/playlists` | List available playlists | customer |
| `/np` | Show now playing info | customer |
| `/rescan` | Fully rebuilds metadata cache | owner |

> [!IMPORTANT]
> By default, everyone can use all commands. The "Permission" column only applies if you [enable permissions](../configuration/permissions.md).

### Behavior Notes

> [!NOTE]
> Playback commands require you to be in Jill's voice channel. When Jill isn't in a voice channel, `/shuffle`, `/loop`, and `/playlist` still work.
>
> **Pause vs auto-pause**: Manual `/pause` stays paused. Auto-pause (when channel empties) auto-resumes when someone joins.
>
> **Shuffle**: Randomizes the entire playlist. Reshuffles when it loops.
>
> **Loop**: Repeats current track. Resets when you switch playlists or restart the bot.
>
> **Saved across restarts**: Volume, shuffle mode, last playlist.
>
> **`/playlists`**: Hidden if you only have one playlist.

### Disabling Commands

**Docker** (in [`docker-compose.yml`](../configuration/environment.md)):
```yaml
- SHUFFLE_COMMAND=false
- LOOP_COMMAND=false
```

**Windows/Linux** (in [`settings.yaml`](../configuration/settings.md#commands)):
```yaml
# settings.yaml
commands:
  shuffle_command: false
  loop_command: false
```

> Disabled commands still appear in Discord but respond with "command disabled" when used.
