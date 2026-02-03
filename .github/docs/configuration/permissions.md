# Permissions

`/jill/config/permissions.yaml`

Restrict playback control to specific users. By default, everyone can use all commands.

> [!NOTE]
> Docker users: edit this file in your mounted `config/` folder.

#### Default Permission Tiers

| Tier | Requirement | Commands |
|------|-------------|----------|
| **customer** | None | `/queue`, `/playlists`, `/np` |
| **bartender** | Specific Discord role | `/play`, `/pause`, `/skip`, `/previous`,<br>`/stop`, `/seek`, `/shuffle`, `/loop`,<br>`/playlist`, `/volume` |
| **owner** | Manage Guild permission | `/rescan` |

### Enabling Permissions

**1. Pick a Role** - Create one or use an existing role for users who should control playback.

**2. Get the Role ID** - Discord Settings > Advanced > Enable Developer Mode. Then Server Settings > Roles > Right-click role > Copy Role ID.

**3. Configure:**

```yaml
# permissions.yaml
enabled: true
bartender_role_id: 1234567890123456789
```

> Docker: `ENABLE_PERMISSIONS=true` and `BARTENDER_ROLE_ID=1234567890123456789`

**4. Restart Jill** - Permission changes require a restart.

### Customizing Tiers

Move commands between tiers in `permissions.yaml`:

> [!NOTE]
> Users with `Manage Guild` or `Administrator` automatically pass bartender checks without needing the role.

```yaml
# permissions.yaml
tiers:
  customer:
    - queue
    - playlists
    - np
  bartender:
    - play
    - pause
    - skip
    - previous
    - stop
    - seek
    - shuffle
    - loop
    - playlist
    - volume
  owner:
    - rescan
```

> **Example - let everyone control volume:** Move `volume` from `bartender` to `customer`.
>
> **Example - admin-only playback:** Move playback commands from `bartender` to `owner`.

> [!TIP]
> Panel buttons use the same permissions as their equivalent slash commands.

### Troubleshooting

**"No permission" with role assigned:**
1. Verify role ID is numeric (not the role name)
2. Make sure you used your actual role ID, not the example
3. Check `enabled: true` is set
4. Restart after changes

**Owner commands not working:** Owner tier requires Discord's "Manage Guild" permission, not a role.
