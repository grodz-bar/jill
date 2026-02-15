# Music Library

Jill plays from the `music/` folder. Top-level subfolders become playlists.
> Supported formats: MP3, FLAC, OGG, OPUS, M4A, M4B, WAV, AAC, WebM, MKA
```
music/
├── synthwave/            ← playlist
│   ├── song1.mp3
│   ├── song2.mp3
│   └── ...
└── lofi/                 ← playlist
    ├── cloudly-day.opus
    ├── midnight.opus
    └── ...
```

You can also use subfolders to organize tracks within a playlist — they all count as one playlist:

```
music/
└── frieren-OST/          ← playlist
    ├── Disc 1/
    │   ├── 01-main theme.flac
    │   ├── 02-end of one journey.flac
    │   └── ...
    └── Disc 2/
        ├── 01-zoltraak.flac
        ├── 02-the slayer.flac
        └── ...
```

Jill scans folders up to 5 levels deep. If you use subfolders (like Disc 1, Disc 2), each subfolder plays through before the next. Within each subfolder, tracks are sorted by metadata track number, with filename as fallback.

> [!IMPORTANT]
> If you don't need playlists, just put files directly in `music/` with **no** subfolders. If you **do** have playlists (subfolders), any files ***not*** inside one will be ignored.

> [!TIP]
> After adding or removing files, run `/rescan` in Discord or restart Jill.

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

Jill reads **title**, **album artist**, **album**, and **track number** from your files' metadata. No title? She'll use the filename. For artist, she prefers album artist but falls back to track artist if it's missing or generic (like "Various Artists").

### Duplicates

If two files have the same title and artist, only the first is kept.

Having issues? See [Troubleshooting](../troubleshooting.md#playback).
