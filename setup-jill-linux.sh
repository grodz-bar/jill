#!/usr/bin/env bash
# Jill - Linux Setup

set -e

# Colors
GREEN='\e[92m'
RED='\e[91m'
YELLOW='\e[93m'
LTBLUE='\e[94m'
NC='\e[0m'
cd "$(dirname "$0")" || exit 1

echo "=== jill setup ==="
echo

# Check Python
if ! command -v python3 >/dev/null 2>&1; then
    echo -e "${RED}[x] Python 3 is required.${NC}"
    echo "    install with: sudo apt install python3 python3-venv"
    exit 1
fi
echo -e "${GREEN}[+] Python found${NC}"

# Check Java
if ! command -v java >/dev/null 2>&1; then
    echo -e "${RED}[x] Java 17+ is required for Lavalink.${NC}"
    echo ""
    echo "    Ubuntu/Debian/Pi: sudo apt install openjdk-17-jre"
    echo "    Fedora:          sudo dnf install java-17-openjdk"
    echo "    Arch:            sudo pacman -S jre17-openjdk"
    exit 1
fi
echo -e "${GREEN}[+] Java found${NC}"

# Check if existing venv is broken (e.g., system Python was upgraded, pip missing)
if [[ -d "venv" ]]; then
    if [[ ! -f "venv/bin/activate" ]] || [[ ! -e "venv/bin/python" ]] || ! "venv/bin/python" -c "import pip" 2>/dev/null; then
        echo -e "${YELLOW}[!] Rebuilding virtual environment...${NC}"
        rm -rf venv
    fi
fi

# Create virtual environment
if [[ ! -d "venv" ]]; then
    echo -e "${LTBLUE}[.] Creating virtual environment...${NC}"
    python3 -m venv venv
else
    echo -e "${GREEN}[+] Virtual environment exists${NC}"
fi

# Bootstrap pip if missing (some minimal venvs need this)
if ! venv/bin/python -m pip --version >/dev/null 2>&1; then
    echo -e "${LTBLUE}[.] Bootstrapping pip...${NC}"
    if ! venv/bin/python -m ensurepip --default-pip 2>/dev/null; then
        echo -e "${RED}[x] Pip bootstrap failed. ensurepip may not be available.${NC}"
        echo "    install with: sudo apt install python3-venv"
        echo "    then run: rm -rf venv && ./setup-jill-linux.sh"
        exit 1
    fi
fi

# Install dependencies
echo -e "${LTBLUE}[.] Installing dependencies...${NC}"
if ! source venv/bin/activate 2>/dev/null; then
    echo -e "${RED}[x] Failed to activate virtual environment.${NC}"
    echo "    run: rm -rf venv && ./setup-jill-linux.sh"
    exit 1
fi
if ! python -m pip install -q -r requirements.txt; then
    echo -e "${RED}[x] Failed to install dependencies${NC}"
    echo "    check your internet connection and try again"
    exit 1
fi

# Run Python setup wizard (handles Lavalink download, .env config, etc.)
echo
if ! python -m setup; then
    echo
    echo -e "${RED}[x] Setup did not complete successfully.${NC}"
    exit 1
fi
