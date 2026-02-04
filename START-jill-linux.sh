#!/usr/bin/env bash
# Jill Launcher - Linux

cd "$(dirname "$0")" || exit 1

# Colors
BLUE='\e[34m'
RED='\e[31m'
YELLOW='\e[2;33m'
CYAN='\e[36m'
MAGENTA='\e[35m'
NC='\e[0m'  # No Color

# Track Lavalink PID for cleanup
LAVALINK_PID=""

cleanup() {
    if [[ -n "$LAVALINK_PID" ]] && kill -0 "$LAVALINK_PID" 2>/dev/null; then
        echo "stopping lavalink..."
        kill "$LAVALINK_PID" 2>/dev/null
        wait "$LAVALINK_PID" 2>/dev/null
    fi
}
trap cleanup EXIT

echo -e "${MAGENTA}=== jill startup ===${NC}"
echo

# Check venv
if [[ ! -f "venv/bin/activate" ]]; then
    echo -e "${RED}[x] virtual environment not found.${NC}"
    echo "    run: ./setup-jill-linux.sh"
    exit 1
fi
echo -e "${CYAN}[+] virtual environment found${NC}"

# Check venv Python is functional
if [[ ! -e "venv/bin/python" ]] || ! "venv/bin/python" -c "import sys" 2>/dev/null; then
    echo -e "${RED}[x] virtual environment is broken.${NC}"
    echo "    run: ./setup-jill-linux.sh"
    exit 1
fi

# Check Java version
if ! command -v java >/dev/null 2>&1; then
    echo -e "${RED}[x] java 17+ required for lavalink.${NC}"
    echo ""
    echo "    Ubuntu/Debian/Pi: sudo apt install openjdk-17-jre"
    echo "    Fedora:          sudo dnf install java-17-openjdk"
    echo "    Arch:            sudo pacman -S jre17-openjdk"
    exit 1
fi

java_version=$(java -version 2>&1 | grep -o 'version "[0-9]*' | grep -o '[0-9]*' | head -1)
if [[ -z "$java_version" ]]; then
    echo -e "${YELLOW}[!] could not determine java version${NC}"
elif [[ "$java_version" -lt 17 ]]; then
    echo -e "${RED}[x] java 17+ required, found java $java_version${NC}"
    echo ""
    echo "    Ubuntu/Debian/Pi: sudo apt install openjdk-17-jre"
    echo "    Fedora:          sudo dnf install java-17-openjdk"
    echo "    Arch:            sudo pacman -S jre17-openjdk"
    exit 1
else
    echo -e "${CYAN}[+] java $java_version${NC}"
fi

# Check Lavalink files
if [[ ! -f "lavalink/Lavalink.jar" ]]; then
    echo -e "${RED}[x] lavalink/Lavalink.jar not found.${NC}"
    echo "    download from: https://github.com/lavalink-devs/Lavalink/releases"
    exit 1
fi
echo -e "${CYAN}[+] lavalink.jar found${NC}"

if [[ ! -f "lavalink/application.yml" ]]; then
    echo -e "${RED}[x] lavalink/application.yml not found.${NC}"
    exit 1
fi
echo -e "${CYAN}[+] application.yml found${NC}"

# Load password from .env if present (exported so Python can read it)
export LAVALINK_PASSWORD="${LAVALINK_PASSWORD:-timetomixdrinksandnotchangepasswords}"
if [[ -f ".env" ]]; then
    env_password=$(grep -E "^LAVALINK_PASSWORD=" .env 2>/dev/null | cut -d'=' -f2- | sed 's/[[:space:]][[:space:]]*#.*//')
    if [[ -n "$env_password" ]]; then
        export LAVALINK_PASSWORD="$env_password"
    fi
fi

# Load port from .env if present
export LAVALINK_PORT="${LAVALINK_PORT:-4440}"
if [[ -f ".env" ]]; then
    env_port=$(grep -E "^LAVALINK_PORT=" .env 2>/dev/null | cut -d'=' -f2- | sed 's/[[:space:]][[:space:]]*#.*//')
    if [[ -n "$env_port" ]]; then
        export LAVALINK_PORT="$env_port"
    fi
fi

# Health check using Python (no curl dependency, reads password from env to avoid injection)
is_lavalink_ready() {
    venv/bin/python -c "
import urllib.request
import os
import sys
password = os.environ.get('LAVALINK_PASSWORD', 'timetomixdrinksandnotchangepasswords')
port = os.environ.get('LAVALINK_PORT', '4440')
try:
    req = urllib.request.Request(f'http://127.0.0.1:{port}/version', headers={'Authorization': password})
    urllib.request.urlopen(req, timeout=2)
    sys.exit(0)
except urllib.error.HTTPError as e:
    print(f'HTTP {e.code}: {e.reason}', file=sys.stderr)
    sys.exit(1)
except urllib.error.URLError as e:
    # Connection refused is expected during startup, don't print
    sys.exit(1)
except Exception as e:
    print(f'Unexpected: {type(e).__name__}: {e}', file=sys.stderr)
    sys.exit(1)
"
}

if is_lavalink_ready; then
    echo -e "${CYAN}[+] lavalink already running${NC}"
else
    echo -e "${CYAN}[.] starting lavalink...${NC}"

    # Log to file instead of /dev/null so we can diagnose failures
    LAVALINK_LOG="lavalink/lavalink-startup.log"
    pushd lavalink >/dev/null || exit 1
    java -jar Lavalink.jar > lavalink-startup.log 2>&1 &
    LAVALINK_PID=$!
    popd >/dev/null || exit 1

    echo -ne "${CYAN}[.] waiting for lavalink${NC}"
    elapsed=0
    timeout=90  # Longer timeout for slower devices (Pi)
    while ! is_lavalink_ready && [[ $elapsed -lt $timeout ]]; do
        # Check if process died
        if ! kill -0 "$LAVALINK_PID" 2>/dev/null; then
            echo
            echo -e "${RED}[x] lavalink process died${NC}"
            if [[ -f "$LAVALINK_LOG" ]]; then
                echo "    last 10 lines of log:"
                tail -10 "$LAVALINK_LOG" | sed 's/^/    /'
            fi
            exit 1
        fi
        echo -n "."
        sleep 1
        ((elapsed++))
    done
    echo

    if is_lavalink_ready; then
        echo -e "${CYAN}[+] lavalink ready${NC}"
    else
        echo -e "${RED}[x] lavalink failed to start within $timeout seconds${NC}"
        if [[ -f "$LAVALINK_LOG" ]]; then
            echo "    last 10 lines of log:"
            tail -10 "$LAVALINK_LOG" | sed 's/^/    /'
        fi
        exit 1
    fi
fi

echo

# Start the bot
echo -e "${MAGENTA}[.] starting jill...${NC}"
echo
source venv/bin/activate
python bot.py
