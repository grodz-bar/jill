# Windows Setup

This guide covers Windows installation.

**Need to create a bot first?** Complete the [Discord Setup](discord-setup.md) first, then come back here.

---

### Requirements

- Windows 10 or 11 (64-bit)
- Python 3.11+ (3.13+ recommended)
- Java 17+ (21+ recommended)

---

### Quick Start

> [!TIP]
> This section is for experienced users who want to get running fast. If you're new to this, skip to [Step-by-Step Setup](#step-by-step-setup).

1. Install [Python 3.11+](https://www.python.org/downloads/) and [Java 17+](https://adoptium.net/temurin/releases/?version=25&os=windows&arch=x64) (Select ***JRE***, download the ***.msi***)
2. Download and extract Jill from the [releases page](https://github.com/grodz-bar/jill/releases)
3. Double-click `setup-jill-win.bat`
4. Add music to `music\` subfolders, or [link your existing library](../usage/music-library.md)
5. Double-click `START-jill-win.bat`
6. Once you see "time to mix drinks and change lives," head to Discord and type `/play`

---

### Step-by-Step Setup

**1. Install Python**

1. Go to [python.org/downloads](https://www.python.org/downloads/) and click the big download button
2. Run the installer (default options are fine)

**Verify installation** - open Command Prompt and run:
```batch
py --version
```
> You should see `Python 3.11.x` or higher. If `py` isn't recognized, try `python --version` instead.

<br>

**2. Install Java**

Jill uses Lavalink for audio streaming, which requires Java 17 or newer.

1. Go to [Adoptium Temurin releases](https://adoptium.net/temurin/releases/?version=21&os=windows&arch=x64)
2. Select **JRE** (not JDK - you only need the runtime)
3. Download the `.msi` installer
4. Run the installer with default options

> [!TIP]
> The `.msi` installer automatically adds Java to your PATH. If you use a `.zip` instead, you'll need to configure PATH manually.

**Verify installation** - open a **new** Command Prompt and run:
```batch
java -version
```
> You should see `openjdk version "17.x.x"` or higher.

<br>

**3. Get Jill**

1. Go to the [releases page](https://github.com/grodz-bar/jill/releases)
2. Download the latest `.zip` file
3. Extract to a folder of your choice (e.g., `C:\Jill`)

<br>

**4. Run the Setup Wizard**

1. Open the Jill folder in File Explorer
2. Double-click `setup-jill-win.bat`

> The wizard runs 5 phases:
> 1. **Prerequisites** - checks Python, Java, disk space
> 2. **Lavalink** - downloads the audio server (~85MB)
> 3. **Discord** - prompts for token and Guild ID
> 4. **Ports** - verifies 4440/4444 are available
> 5. **Directories** - creates music/, config/, data/

<br>

**5. Add Your Music**

Create folders in `music\` for your playlists, or use your existing library. See [Music Library](../usage/music-library.md) for options.

<br>

**6. Start Jill**

1. Double-click `START-jill-win.bat`
2. A command window opens showing startup progress:

```
=== JILL STARTUP ===

[+] virtual environment found
[+] java 25
[+] lavalink.jar found
[+] application.yml found
[.] starting lavalink...
[.] waiting for lavalink.
[+] lavalink ready

[.] starting jill...
```

3. When you see `time to mix drinks and change lives`, Jill is ready
4. Keep this window open while using Jill
5. Head to Discord and summon Jill with `/play`

---

### Managing Jill

Once Jill's running, here's how to control things:

| Task | How |
|------|-----|
| Stop | Close the command window, or press <kbd>Ctrl</kbd>+<kbd>C</kbd> |
| Restart | Close the window, run `START-jill-win.bat` again |
| View logs | Watch the command window (live activity) |
| Update music | Add files to `music/`, then `/rescan` in Discord |

---

### Configuration

Config files in `config\` are auto-generated on first run. To edit `.env`, right-click it and choose **Open with** → **Notepad**. See [Settings Reference](../configuration/settings.md).

---

### Next Steps

- **Explore commands:** Type `/` in Discord to see all available commands
- **Customize and configure:** [Settings](../configuration/settings.md), [Messages](../configuration/messages.md)
- **Control access:** Set up [Permissions](../configuration/permissions.md) for role-based control
- **Learn more:** [Commands](../usage/commands.md), [Control Panel](../usage/control-panel.md), [Music Library](../usage/music-library.md)

---

### Troubleshooting

<details>
<summary><strong>"Python is not recognized" or "'py' is not recognized"</strong></summary>

**Try logging off and back on** (or restart your PC).

**Try the standalone installer:**
1. Go to [python.org/downloads/windows](https://www.python.org/downloads/windows/)
2. Download the **Windows installer (64-bit)** under the latest release
3. Run it and check **"Install py.exe launcher"** and **"Add python.exe to PATH"**
4. Run `setup-jill-win.bat` again

**Add Python to PATH manually:**
1. Find your Python folder (usually `C:\Users\YourName\AppData\Local\Programs\Python\Python313`)
2. Search **"environment variables"** in Start menu → **Edit the system environment variables**
3. Click **Environment Variables** → select **Path** under **User variables** → **Edit**
4. Click **New** and add your Python folder, then **New** again for the `Scripts` subfolder
5. Click **OK**, open a new terminal, and try again

</details>

<details>
<summary><strong>Lavalink won't start / "Port already in use"</strong></summary>

An old Lavalink process may still be running from a previous session.

1. Open Task Manager (<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>Esc</kbd>)
2. Go to the **Details** tab
3. Look for **OpenJDK Platform binary** (uses ~450MB RAM)
4. Right-click → **End task**
5. Try starting again

</details>

<details>
<summary><strong>Jill joins voice chat but no audio plays</strong></summary>

Windows Firewall may be blocking Java from sending audio.

1. Start menu → **Windows Security** → **Firewall & network protection**
2. Click **Allow an app through firewall**
3. Find **OpenJDK Platform binary** and check both Private and Public
4. If not listed, click **Allow another app** and browse to your Java installation

</details>

<details>
<summary><strong>Music not showing up</strong></summary>

Check your folder structure in `music\`:

**If using playlists** (subfolders), files must be inside them:
```
music\
  rock\           ← playlist
    song.mp3
  jazz\           ← playlist
    track.flac
```
Files directly in `music\` are ignored when subfolders exist.

**If not using playlists**, put files directly in `music\` with no subfolders.

Supported formats: MP3, FLAC, OGG, OPUS, M4A, WAV, AAC

</details>

<details>
<summary><strong>Antivirus blocks startup</strong></summary>

Some antivirus software flags Java or Python as suspicious.

**Fix:** Add the Jill folder to your antivirus exclusion list. The exact steps vary by antivirus - search for "exclusions" or "exceptions" in your antivirus settings.

</details>

For other issues, see [Troubleshooting](../troubleshooting.md).
