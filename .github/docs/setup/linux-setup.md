# Linux Setup

This guide walks you through setting up Jill on Linux.

**Need to create a bot first?** Complete the [Discord Setup](discord-setup.md) first, then come back here.

---

### Requirements

- 64-bit system (amd64/arm64)
- Python 3.11+ (3.13+ recommended)
- Java 17+ (21+ recommended)

---

### Installing Dependencies

- **Debian / Ubuntu / Raspberry Pi:** `sudo apt install python3 python3-venv default-jre-headless unzip curl nano`
- **Arch Linux:** `sudo pacman -Syu python jre-openjdk unzip curl nano`
- **Fedora:** `sudo dnf install python3 java-latest-openjdk-headless unzip nano`

> **Verify:** `python3 --version` and `java -version`

---

### Quick Start

> [!TIP]
> This section is for experienced users who want to get running fast. If you're new to this, skip to [Step-by-Step Setup](#step-by-step-setup).

1. Install Python 3.11+ and Java 17+ (see [Installing Dependencies](#installing-dependencies))
2. Download [jill-linux.zip](https://github.com/grodz-bar/jill/releases/latest/download/jill-linux.zip): `unzip jill-linux.zip -d jill && cd jill`
3. Make scripts executable: `chmod +x setup-jill-linux.sh START-jill-linux.sh`
4. Run setup: `./setup-jill-linux.sh`
5. Add music to `music/` subfolders, or [link your existing library](../usage/music-library.md)
6. Start: `./START-jill-linux.sh`
7. Once you see "time to mix drinks and change lives," head to Discord and type `/play`

---

### Step-by-Step Setup

**1. Get the Files**

- Download [jill-linux.zip](https://github.com/grodz-bar/jill/releases/latest/download/jill-linux.zip)

> **Terminal:** `curl -LO https://github.com/grodz-bar/jill/releases/latest/download/jill-linux.zip`

- Extract it: `unzip jill-linux.zip -d jill && cd jill`

<br>

**2. Run the Setup Wizard**

Make the scripts executable and run setup:

```bash
chmod +x setup-jill-linux.sh START-jill-linux.sh
./setup-jill-linux.sh
```

> The wizard runs 5 phases:
> 1. **Prerequisites** - checks Python, Java, disk space
> 2. **Lavalink** - downloads the audio server (~85MB)
> 3. **Discord** - prompts for token and Guild ID
> 4. **Ports** - verifies 2333/2334 are available
> 5. **Directories** - creates music/, config/, data/

<br>

**3. Add Your Music**

Create folders in `music/` for your playlists, or use your existing library. See [Music Library](../usage/music-library.md) for options.

> **Example:** `mkdir music/fez-ost music/celeste-ost`

<br>

**4. Start Jill**

```bash
./START-jill-linux.sh
```

The terminal shows startup progress:
```
=== jill startup ===

[+] virtual environment found
[+] java 25
[+] lavalink.jar found
[+] application.yml found
[.] starting lavalink...
[.] waiting for lavalink
[+] lavalink ready

[.] starting jill...
```

When you see `time to mix drinks and change lives`, Jill is ready.

Head to Discord and summon Jill with `/play`.

---

### Configuration

Config files in `config/` are auto-generated on first run. See [Settings Reference](../configuration/settings.md).

> **Example:** `nano config/settings.yaml`

---

### Running as a Service (Optional)

To run Jill automatically on boot, create a systemd service:

`sudo nano /etc/systemd/system/jill.service`

Paste the following (adjust paths and username):

```ini
[Unit]
Description=Jill Discord Music Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/home/youruser/jill
EnvironmentFile=-/home/youruser/jill/.env
ExecStart=/home/youruser/jill/START-jill-linux.sh
Restart=on-failure
RestartSec=10
KillMode=mixed
TimeoutStopSec=15

[Install]
WantedBy=multi-user.target
```

Then enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable jill
sudo systemctl start jill
```

> Check status with `sudo systemctl status jill`.

---

### Managing Jill

| Task | Manual | As Service |
|------|--------|------------|
| **Start** | `./START-jill-linux.sh` | `sudo systemctl start jill` |
| **Stop** | <kbd>Ctrl</kbd>+<kbd>C</kbd> in terminal | `sudo systemctl stop jill` |
| **Restart** | Stop and start again | `sudo systemctl restart jill` |
| **View logs** | Terminal output | `journalctl -u jill -f` |
| **Update music** | Add files, then `/rescan` in Discord | Same |

---

### Updating

1. Download the latest [jill-linux.zip](https://github.com/grodz-bar/jill/releases/latest/download/jill-linux.zip)
2. Extract over your existing Jill folder: `unzip -o jill-linux.zip -d /path/to/jill`
3. Run `./setup-jill-linux.sh` to update dependencies and Lavalink

> [!TIP]
> Jill will let you know in the console when a new version is available.

> Your `config/`, `data/`, `music/`, and `.env` are preserved. New settings added in updates will show after a restart.

---

### Next Steps

- **Explore commands:** Type `/` in Discord to see all available commands
- **Customize and configure:** [Settings](../configuration/settings.md), [Messages](../configuration/messages.md)
- **Control access:** Set up [Permissions](../configuration/permissions.md) for role-based control
- **Learn more:** [Commands](../usage/commands.md), [Control Panel](../usage/control-panel.md), [Music Library](../usage/music-library.md)

---

### Troubleshooting

<details>
<summary><strong>Lavalink won't start / "Port already in use"</strong></summary>

An old Lavalink process may still be running from a previous session.

```bash
pkill -f Lavalink.jar
./START-jill-linux.sh
```

</details>

<details>
<summary><strong>"[x] failed to activate virtual environment."</strong></summary>

On Debian, Ubuntu, and Raspberry Pi, the `python3-venv` package isn't installed by default.

```bash
sudo apt install python3-venv
rm -rf venv
./setup-jill-linux.sh
```

Arch and Fedora include venv with Python, so this error shouldn't occur there.

</details>

<details>
<summary><strong>Jill joins voice chat but no audio plays</strong></summary>

Restart Jill to check if Lavalink comes up:

```bash
./START-jill-linux.sh
```

If it says "lavalink ready", the issue is elsewhere. If it fails or times out, check `lavalink/logs/` for errors.

</details>

<details>
<summary><strong>Music not showing up</strong></summary>

Check your folder structure in `music/`:

**If using playlists** (subfolders), files must be inside them:
```
music/
  rock/           ← playlist
    song.mp3
  jazz/           ← playlist
    track.flac
```
Files directly in `music/` are ignored when subfolders exist.

**If not using playlists**, put files directly in `music/` with no subfolders.

Supported formats: MP3, FLAC, OGG, OPUS, M4A, WAV, AAC

</details>

For other issues, see [Troubleshooting](../troubleshooting.md).
