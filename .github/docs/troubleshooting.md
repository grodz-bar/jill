# Troubleshooting

### Quick Fixes

1. **Restart Jill** - Fixes most transient issues
2. **Check the logs** - `docker-compose logs jill` or terminal output
3. **Verify your token** - No quotes, correct value
4. **Run `/rescan`** - After adding or removing music

---

### Installation

- **Python not found**: Install Python 3.11+ and ensure it's in PATH. Windows: reinstall with "Add to PATH" checked.

- **Java not found**: Install Java 17+ from [adoptium.net](https://adoptium.net).

- **Lavalink.jar not found**: Download from [Lavalink releases](https://github.com/lavalink-devs/Lavalink/releases) and place in `lavalink/` folder.

- **Permission denied (Linux)**: Run `chmod +x *.sh`

- **Can't edit `.env` (Windows)**: Right-click → **Open with** → **Notepad**.

- **`.env` change not working**: Remove the `#` at the start.

- **Config value cut off**: In `.env` and `docker-compose.yml`, text after ` #` (space + hash) is treated as a comment:
  ```env
  # Won't work - becomes "lofi"
  DEFAULT_PLAYLIST=lofi #444

  # Works
  DEFAULT_PLAYLIST=lofi#444
  DEFAULT_PLAYLIST=lofi-444
  ```

---

### Connection

- **Multiple servers**: Jill is single-server. Run separate instances for each server.

- **Jill shows offline**: Check token is correct, no quotes around the value, internet works, [Discord status](https://discordstatus.com) is OK.

- **Cannot connect to Lavalink**:
  - Wait for healthcheck (Docker shows "healthy")
  - Check host setting: `lavalink` (Docker) or `127.0.0.1` (native)
  - Check ports 4440/4444 aren't in use

- **Lavalink keeps restarting**: Check logs for Java errors (need 17+), YAML syntax errors, or out of memory.
  > To see Lavalink errors directly: `cd lavalink && java -jar Lavalink.jar`

- **Lavalink disconnected**: Jill reconnects automatically once Lavalink is back up. If she seems stuck, press any playback button to nudge her.
  > Jill can't restart Lavalink on her own. If you're not sure how to fix it, try restarting Jill - the start script should bring Lavalink back too.

- **Lavalink closes when Jill stops**: This is intentional - Jill kills Lavalink on shutdown by default. To keep Lavalink running:
  ```yaml
  # settings.yaml
  kill_lavalink_on_shutdown: false
  ```
  > Docker: `KILL_LAVALINK_ON_SHUTDOWN=false`

---

### Playback

- **Audio sounds weird**: Check the host's internet connection. If stable, check [Discord status](https://discordstatus.com).

- **No audio**: Check logs show "lavalink connected", music folder has files, Jill has read access. Also check if her volume, both in Discord and with /volume is not set too low.

- **"Shelves are empty"**: No playlists found. See [Music Library](usage/music-library.md) for folder structure.

- **Songs not appearing**: Run `/rescan`. Check format is supported (MP3, FLAC, OGG, M4A, WAV, AAC) and file isn't corrupted.

- **Wrong track order**: Tracks sort by track number tag, then alphabetically. Check your files have track numbers set.

- **Playback stops**: Check inactivity timeout (Jill leaves when alone), Lavalink logs, network stability.

- **"Playback failed... fault error"**: A leftover Lavalink process may be running. Kill any **OpenJDK Platform binary** (~450MB RAM) in Task Manager or `pkill -f Lavalink`, then restart.

- **Metadata not showing**: Check file has embedded tags, run `/rescan`. Raw WAV has limited tag support.

- **Duplicates appearing**: Files have slightly different metadata. Check title/artist spelling matches exactly.

- **Slow startup**: First run scans all files. Later startups use cache. For large libraries that rarely change:
  ```yaml
  # settings.yaml
  auto_rescan: false
  ```
  > Docker: `AUTO_RESCAN=false`

---

### Commands

- **Slash commands not appearing**: Commands show up instantly with `GUILD_ID` set. Without it, Discord can take up to an hour to sync them. Restart Jill after permission changes.

- **"That's for staff only"**: Check your role ID in `permissions.yaml` is correct.

- **Command says disabled**: Command is turned off in config:
  ```yaml
  # settings.yaml
  commands:
    shuffle_command: true
    loop_command: true
    rescan_command: true
  ```
  > Docker: `SHUFFLE_COMMAND=true`, `LOOP_COMMAND=true`, `RESCAN_COMMAND=true`

---

### Panel

- **"Panel's gone"**: Message was deleted. Run `/play` to create a new one.

- **"That panel's outdated"**: You clicked an old panel. Scroll down or run `/play`.

- **Buttons not responding**: You're not in the same voice channel as Jill, you lack the required role (check `permissions.yaml`), Lavalink isn't connected, or [Discord is having issues](https://discordstatus.com).

- **Panel not updating**: Check Jill has "Send Messages" and "Embed Links" permissions. Run `/stop` then `/play` to recreate.

- **Panel laggy**: Discord limits edits. Panel auto-recreates periodically. Manual fix: `/stop` then `/play`.

- **Everything is lowercase!**: It sure is. Jill lowercases text so the control panel doesn't look goofy when songs have inconsistent capitalization. Plus, it fits her vibe.

---

### Docker

- **Container won't start**: Check `docker-compose logs jill`, verify token in docker-compose.yml, ensure Docker daemon is running.

- **Permission denied on volumes**: Jill defaults to user 1000:1000. Check your IDs with `id -u` and `id -g`, then set PUID/PGID in docker-compose.yml to match. Or: `chmod -R 755 music/ config/ data/`

- **Config changes not working**:
  - Code changes: `docker-compose up -d --build`
  - Config changes: `docker-compose restart jill`

- **"Your kernel does not support memory limit capabilities..." warning (Raspberry Pi)**: Harmless, safe to ignore.

---

### Logs

Set log level for more detail:

```yaml
# settings.yaml
logging:
  level: verbose  # minimal, verbose, or debug
```
> Docker: `LOG_LEVEL=verbose`

| Level | Shows |
|-------|-------|
| minimal | Errors and milestones |
| verbose | + voice events, auto-pause/resume (default) |
| debug | + HTTP requests, internal state |
