#!/usr/bin/env bash
# Jill - Linux Setup

set -e
cd "$(dirname "$0")" || exit 1

echo "=== Jill Setup ==="
echo

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "[x] Python 3 is required."
    echo "    Install with: sudo apt install python3 python3-venv"
    exit 1
fi
echo "[+] Python found"

# Check Java
if ! command -v java >/dev/null 2>&1; then
    echo "[x] Java 17+ is required for Lavalink."
    echo ""
    echo "    Ubuntu/Debian/Pi: sudo apt install openjdk-17-jre"
    echo "    Fedora:          sudo dnf install java-17-openjdk"
    echo "    Arch:            sudo pacman -S jre17-openjdk"
    exit 1
fi
echo "[+] Java found"

# Create virtual environment
if [[ ! -d "venv" ]]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "[+] Virtual environment exists"
fi

# Install dependencies
echo "Installing dependencies..."
if ! source venv/bin/activate 2>/dev/null; then
    echo "[x] Failed to activate virtual environment."
    echo "    Try: rm -rf venv && ./setup-jill-linux.sh"
    exit 1
fi
python -m pip install -q -r requirements.txt

# Run Python setup wizard (handles Lavalink download, .env config, etc.)
echo
python -m setup
