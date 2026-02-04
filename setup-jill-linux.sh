#!/usr/bin/env bash
# Jill - Linux Setup

set -e
cd "$(dirname "$0")" || exit 1

echo "=== jill setup ==="
echo

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
    echo "[x] python 3 is required."
    echo "    install with: sudo apt install python3 python3-venv"
    exit 1
fi
echo "[+] python found"

# Check Java
if ! command -v java >/dev/null 2>&1; then
    echo "[x] java 17+ is required for lavalink."
    echo ""
    echo "    Ubuntu/Debian/Pi: sudo apt install openjdk-17-jre"
    echo "    Fedora:          sudo dnf install java-17-openjdk"
    echo "    Arch:            sudo pacman -S jre17-openjdk"
    exit 1
fi
echo "[+] java found"

# Check if existing venv is broken (e.g., system Python was upgraded)
if [[ -d "venv" ]]; then
    if [[ ! -f "venv/bin/activate" ]] || [[ ! -e "venv/bin/python" ]] || ! "venv/bin/python" -c "import sys" 2>/dev/null; then
        echo "rebuilding virtual environment..."
        rm -rf venv
    fi
fi

# Create virtual environment
if [[ ! -d "venv" ]]; then
    echo "creating virtual environment..."
    python3 -m venv venv
else
    echo "[+] virtual environment exists"
fi

# Install dependencies
echo "installing dependencies..."
if ! source venv/bin/activate 2>/dev/null; then
    echo "[x] failed to activate virtual environment."
    echo "    run: rm -rf venv && ./setup-jill-linux.sh"
    exit 1
fi
python -m pip install -q -r requirements.txt

# Run Python setup wizard (handles Lavalink download, .env config, etc.)
echo
python -m setup
