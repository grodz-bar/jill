# Music Library

Jill plays from the `music/` folder. Subfolders become playlists.

```
music/
├── chill-beats/           → "chill-beats" playlist
│   ├── track1.mp3
│   └── track2.flac
├── lofi/                  → "lofi" playlist
│   └── rainy-day.mp3
└── va-11-hall-a-ex/       → "va-11-hall-a-ex" playlist
    ├── 01-glitch-city.flac
    └── 02-shine-spark.flac
```

> [!TIP]
> Don't need playlists? Put files directly in `music/` with no subfolders.
>
> After adding or removing files, run `/rescan` in Discord or restart Jill.

> [!NOTE]
> Files in root are ignored if subfolders exist.

> Supported formats: MP3, FLAC, OGG, M4A, WAV, AAC

### Using Your Existing Library

You don't *need* to copy files, you can just point Jill to your collection:

- **Windows:** Set `MUSIC_PATH` in `.env`: `MUSIC_PATH=C:\Users\YourName\Music`
- **Linux:** Set `MUSIC_PATH` in `.env`: `MUSIC_PATH=/home/user/Music`
- **Docker:** Edit the music volume in `docker-compose.yml`: `/your/music/folder:/music:ro`

Jill only reads your music files, she'll never modify or delete them.

<details>
<summary><strong>Alternative: Link specific folders</strong></summary>

If you only want certain folders from your library, link them individually.

**Linux:**
```bash
ln -s /home/user/Music/jazz music/jazz
ln -s /home/user/Music/rock music/rock
```

**Windows** (run Command Prompt as Administrator):
```batch
mklink /d "music\jazz" "C:\Users\You\Music\Jazz"
mklink /d "music\rock" "C:\Users\You\Music\Rock"
```

</details>

### Metadata

Jill reads **title**, **artist**, **album**, and **track number** from your files. Missing title falls back to filename. Tracks sort by track number, then alphabetically.

### Limits

- **1000 tracks per playlist** - split larger collections into multiple folders
- **Duplicates** - detected by title+artist, only the first is kept

Having issues? See [Troubleshooting](../troubleshooting.md#playback).
