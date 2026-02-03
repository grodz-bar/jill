# Copyright (C) 2026 grodz
#
# This file is part of Jill.
#
# Jill is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""Interactive setup wizard - stdlib only."""

import shutil
import stat
import sys
from pathlib import Path

from .validators import (
    check_python_version,
    check_java_version,
    validate_token_format,
    check_port_available,
    check_disk_space,
)
from .download import download_lavalink


def run_wizard(project_root: Path = None) -> bool:
    """Run the interactive setup wizard.

    Phases:
        1. Check prerequisites (Python, Java, disk space)
        2. Download Lavalink.jar if missing or incomplete
        3. Configure .env (create from template, prompt for token/guild ID)
        4. Check port availability (4440, 4444)
        5. Create required directories (music/, config/, data/)

    Args:
        project_root: Root directory of the project. Defaults to parent of setup module.

    Returns:
        True if completed, False if any check failed. Raises KeyboardInterrupt if cancelled.
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent

    project_root = Path(project_root)

    print("=" * 50)
    print("Jill Setup Wizard")
    print("=" * 50)
    print()

    # Phase 1: Check prerequisites
    print("Checking prerequisites...")
    print()

    ok, msg = check_python_version()
    _print_status(ok, msg)
    if not ok:
        print("\nSetup cannot continue without Python 3.11+")
        return False

    ok, msg = check_java_version()
    _print_status(ok, msg)
    if not ok:
        print("\nJava 17+ is required to run Lavalink.")
        print("Download from: https://adoptium.net/")
        return False

    ok, msg = check_disk_space(project_root)
    _print_status(ok, msg, warning_only=True)

    print()

    # Phase 2: Check/download Lavalink (download_lavalink handles "already exists" case)
    lavalink_dir = project_root / "lavalink"

    ok, msg = download_lavalink(lavalink_dir)
    _print_status(ok, msg)
    if not ok:
        print("\n" + msg)
        return False

    print()

    # Phase 3: Configure .env
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"

    needs_token = True
    needs_guild = True

    if env_file.exists():
        _print_status(True, ".env file exists")
        # Check if token is set
        env_content = env_file.read_text(encoding='utf-8')
        if "DISCORD_TOKEN=" in env_content:
            for line in env_content.splitlines():
                if line.startswith("DISCORD_TOKEN="):
                    value = line.split("=", 1)[1].split("#", 1)[0].strip()
                    if value:
                        needs_token = False
                        _print_status(True, "Using existing DISCORD_TOKEN from .env")
                    break
        if "GUILD_ID=" in env_content:
            for line in env_content.splitlines():
                if line.startswith("GUILD_ID="):
                    value = line.split("=", 1)[1].split("#", 1)[0].strip()
                    if value:
                        needs_guild = False
                        _print_status(True, "Using existing GUILD_ID from .env")
                    break
    else:
        if env_example.exists():
            shutil.copy(env_example, env_file)
            _print_status(True, "Created .env from template")
        else:
            env_file.touch()
            _print_status(True, "Created empty .env file")
        # Restrict .env permissions on Linux (contains token)
        if sys.platform != "win32":
            env_file.chmod(stat.S_IRUSR | stat.S_IWUSR)  # 0600

    print()

    if needs_token:
        print("Discord Token")
        print("-" * 40)
        print("Your bot token from Discord Developer Portal.")
        print("Get it from: https://discord.com/developers/applications")
        print()

        while True:
            try:
                token = input("Paste token: ").strip()
            except EOFError:
                print("\nInput cancelled.")
                return False

            if not token:
                print("Token cannot be empty. Try again.")
                continue

            ok, msg = validate_token_format(token)
            if ok:
                _print_status(True, "Token format valid")
                _update_env_value(env_file, "DISCORD_TOKEN", token)
                break
            else:
                print(f"[!] {msg}")
                print("Try again or Ctrl+C to cancel.")

        print()

    if needs_guild:
        print("Guild ID (STRONGLY RECOMMENDED)")
        print("-" * 40)
        print("Without Guild ID: Slash commands take UP TO 1 HOUR to appear")
        print("With Guild ID:    Commands appear INSTANTLY")
        print()
        print("To get your Guild ID:")
        print("  1. Discord Settings > Advanced > Enable Developer Mode")
        print("  2. Right-click your server icon > Copy Server ID")
        print()

        try:
            guild_id = input("Enter Guild ID (or press Enter to skip): ").strip()
        except EOFError:
            guild_id = ""  # Treat EOF as skip

        if guild_id:
            # Discord snowflake IDs are 16-20 digits (16 for pre-2015, 19-20 for 2022+)
            if guild_id.isdigit() and 16 <= len(guild_id) <= 20:
                _update_env_value(env_file, "GUILD_ID", guild_id)
                _print_status(True, "Guild ID saved")
            elif guild_id.isdigit():
                _print_status(False, "Guild ID should be 16-20 digits, skipped", warning_only=True)
            else:
                _print_status(False, "Invalid Guild ID (must be a number), skipped", warning_only=True)
        else:
            _print_status(False, "Guild ID skipped - commands may take up to 1 hour", warning_only=True)

        print()

    # Phase 4: Check ports
    print("Checking ports...")

    ok, msg = check_port_available(4440)
    _print_status(ok, msg, warning_only=True)

    ok, msg = check_port_available(4444)
    _print_status(ok, msg, warning_only=True)

    print()

    # Phase 5: Create directories
    music_dir = project_root / "music"
    if not music_dir.exists():
        music_dir.mkdir(parents=True)
        _print_status(True, "Created music/ folder")
    else:
        _print_status(True, "music/ folder exists")

    config_dir = project_root / "config"
    if not config_dir.exists():
        config_dir.mkdir(parents=True)
        _print_status(True, "Created config/ folder")
    else:
        _print_status(True, "config/ folder exists")

    data_dir = project_root / "data"
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
        _print_status(True, "Created data/ folder")
    else:
        _print_status(True, "data/ folder exists")

    print()
    print("=" * 50)
    print("Setup Complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Add music to the music/ folder (subfolders become playlists)")
    if sys.platform == "win32":
        print("  2. Run: START-jill-win.bat")
    else:
        print("  2. Run: ./START-jill-linux.sh")
    print()

    return True


def _print_status(ok: bool, msg: str, warning_only: bool = False):
    """Print a status line with [+], [!], or [x] prefix.

    Args:
        ok: Whether the check passed
        msg: Message to display
        warning_only: If True and ok is False, prints [!] instead of [x]
    """
    if ok:
        print(f"[+] {msg}")
    elif warning_only:
        print(f"[!] {msg}")
    else:
        print(f"[x] {msg}")


def _update_env_value(env_file: Path, key: str, value: str):
    """Update or add a value in .env file. Creates file if missing.

    Uncomments commented keys (strips leading '#' chars) or appends if not found.

    Args:
        env_file: Path to .env file
        key: Environment variable name
        value: Value to set
    """
    if not env_file.exists():
        env_file.write_text(f"{key}={value}\n", encoding='utf-8')
        return

    lines = env_file.read_text(encoding='utf-8').splitlines()
    found = False

    for i, line in enumerate(lines):
        # Check for active key
        if line.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break
        # Check for commented key (various formats)
        stripped = line.lstrip('#').lstrip()
        if stripped.startswith(f"{key}="):
            lines[i] = f"{key}={value}"
            found = True
            break

    if not found:
        lines.append(f"{key}={value}")

    env_file.write_text("\n".join(lines) + "\n", encoding='utf-8')


if __name__ == "__main__":
    try:
        success = run_wizard()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
