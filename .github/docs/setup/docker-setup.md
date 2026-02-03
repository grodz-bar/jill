# Docker Setup

Docker is the easiest way to run Jill. One file, two lines to edit, done.

**Need to create a bot first?** Complete the [Discord Setup](discord-setup.md) first, then come back here.

---

### Requirements

- 64-bit system (amd64/arm64)
- Docker Engine 25.0+ or Docker Desktop 4.27+
- Docker Compose 2.24.0+
- Discord bot token and guild ID from [Discord Setup](discord-setup.md)

---

### Setup

**1. Download**

Download [docker-compose.yml](https://raw.githubusercontent.com/grodz-bar/jill/main/docker-compose.yml) or copy from [GitHub](../../../docker-compose.yml).

<br>

**2. Configure** - Open `docker-compose.yml` and find:

```yaml
- DISCORD_TOKEN=paste_your_token_here
- GUILD_ID=paste_your_guild_id_here
```

Replace with your actual token and guild ID.

> [!TIP]
> `GUILD_ID` makes slash commands appear instantly instead of taking up to an hour.

> [!NOTE]
> Jill is single-server - run separate instances for multiple servers.

<br>

**3. Set Up Music**

Edit the music volume in `docker-compose.yml` to point to your library (pick one):

```yaml
- /home/user/Music:/music:ro    # existing library
- /mnt/nas/music:/music:ro      # NAS library
- ./music:/music:ro             # new folder (default)
```

Subfolders become playlists. Supported formats: MP3, FLAC, OGG, M4A, WAV, AAC.

<br>

**4. Run**

```bash
docker compose up -d
docker compose logs -f jill  # Watch for: "time to mix drinks and change lives"
```

> [!TIP]
> Using older Docker? Replace `docker compose` with `docker-compose` throughout.

> [!NOTE]
> Running without Compose? Use `docker run -e PUID=$(id -u) -e PGID=$(id -g) ...` to match your user.

---

### Managing Jill

| Task | Command |
|------|---------|
| View logs | `docker compose logs -f jill` |
| Restart Jill | `docker compose restart jill` |
| Stop everything | `docker compose down` |
| Update to latest | `docker compose pull && docker compose up -d` |

---

### Config and Data Directories

Docker Compose creates three folders:

| Folder | Purpose |
|--------|---------|
| `./music` | Your music library (read-only) |
| `./config` | Settings files (read-write) |
| `./data` | Runtime state (read-write) |

> **On first run**, config files are created automatically:
> - `settings.yaml` - Bot behavior settings
> - `permissions.yaml` - Role-based command access
> - `messages.yaml` - Customizable messages

---

### Next Steps

- **Explore commands:** Type `/` in Discord to see all available commands
- **Customize and configure:** [Environment](../configuration/environment.md), [Messages](../configuration/messages.md), [Settings](../configuration/settings.md)
- **Control access:** Set up [Permissions](../configuration/permissions.md) for role-based control
- **Learn more:** [Commands](../usage/commands.md), [Control Panel](../usage/control-panel.md), [Music Library](../usage/music-library.md)

---

### Troubleshooting

<details>
<summary><strong>"Cannot connect to Lavalink"</strong></summary>

Lavalink needs time to start. Try:

```bash
docker compose down && docker compose up -d
```

</details>

<details>
<summary><strong>"Permission denied" on volumes</strong></summary>

Jill defaults to user 1000:1000. Check your ID with `id -u` and `id -g`, then set PUID/PGID in docker-compose.yml to match:
```yaml
- PUID=1001
- PGID=1001
```

</details>

<details>
<summary><strong>Jill shows offline</strong></summary>

Verify token is correct, check logs (`docker compose logs jill`), ensure no quotes around token value.

</details>

<details>
<summary><strong>Slash commands not appearing</strong></summary>

If you didn't set your `GUILD_ID` it can take 1 hour.

</details>

<details>
<summary><strong>"Memory limit capabilities" warning (Raspberry Pi)</strong></summary>

Harmless. Your kernel doesn't support Docker memory limits, but Jill runs fine without them.

</details>

For other issues, see [Troubleshooting](../troubleshooting.md).
