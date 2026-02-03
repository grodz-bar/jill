#!/usr/bin/env python3
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

"""Jill setup entry point - run with: python -m setup"""

import sys
from pathlib import Path

from .wizard import run_wizard

if __name__ == "__main__":
    # Handle --help flag
    if len(sys.argv) > 1 and sys.argv[1] in ("--help", "-h"):
        print("Usage: python -m setup")
        print()
        print("Interactive setup wizard for Jill.")
        print("Downloads Lavalink, configures .env, and validates prerequisites.")
        sys.exit(0)

    try:
        # Project root is parent of setup/ folder
        project_root = Path(__file__).parent.parent
        success = run_wizard(project_root)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
