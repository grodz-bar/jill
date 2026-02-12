# Music Library

Jill plays from the `music/` folder. Top-level subfolders become playlists.
> Supported formats: MP3, FLAC, OGG, OPUS, M4A, M4B, WAV, AAC, WebM, MKA
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

You can also organize files within a playlist using subfolders:

```
music/
└── ost-collection/
    ├── Disc 1/
    │   ├── 01-opening.flac
    │   └── 02-theme.flac
    └── Disc 2/
        ├── 01-finale.flac
        └── 02-credits.flac
```

All files in subfolders are included in the playlist, up to 5 levels deep. Tracks are grouped by subfolder, then sorted by track number.

> [!TIP]
> Don't need playlists? Put files directly in `music/` with no subfolders.
>
> After adding or removing files, run `/rescan` in Discord or restart Jill.

> [!NOTE]
> Files in root are ignored if subfolders exist.

### Using Your Existing Library

You don't *need* to copy files, you can just point Jill to your collection:

- **Windows:** Set `MUSIC_PATH` in `.env`: `MUSIC_PATH=C:\Users\YourName\Music`
- **Linux:** Set `MUSIC_PATH` in `.env`: `MUSIC_PATH=/home/user/Music`
- **Docker:** Edit the music volume in `docker-compose.yml`: `/your/music/folder:/music:ro`

Jill only **reads** your music files, she'll never modify or delete them.

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

Jill reads **title**, **artist**, **album**, and **track number** from your files. Missing title falls back to filename. Tracks are sorted by subfolder first, then track number, then alphabetically.

### Duplicates

If two files have the same title and artist, only the first is kept.

Having issues? See [Troubleshooting](../troubleshooting.md#playback).
