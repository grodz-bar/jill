#!/usr/bin/env bash
# Jill Launcher - Linux

cd "$(dirname "$0")" || exit 1

# Colors
BLUE='\e[34m'
RED='\e[31m'
YELLOW='\e[2;33m'
CYAN='\e[36m'
MAGENTA='\e[35m'
LTBLUE='\e[94m'
NC='\e[0m'  # No Color

# Track Lavalink PID for cleanup
LAVALINK_PID=""

cleanup() {
    if [[ -n "$LAVALINK_PID" ]] && kill -0 "$LAVALINK_PID" 2>/dev/null; then
        echo -e "${LTBLUE}[.] stopping lavalink...${NC}"
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

# Check venv Python is functional (test pip - if missing, packages won't be installed)
if [[ ! -e "venv/bin/python" ]] || ! "venv/bin/python" -c "import pip" 2>/dev/null; then
    echo -e "${RED}[x] virtual environment is broken.${NC}"
    echo "    run: ./setup-jill-linux.sh"
    exit 1
fi

# Check Java version
if ! command -v java >/dev/null 2>&1; then
    echo -e "${RED}[x] java 17+ is required for lavalink.${NC}"
    echo ""
    echo "    Ubuntu/Debian/Pi: sudo apt install openjdk-17-jre"
    echo "    Fedora:          sudo dnf install java-17-openjdk"
    echo "    Arch:            sudo pacman -S jre17-openjdk"
    exit 1
fi

java_version=$(java -version 2>&1 | grep -oE '(version|release) "[0-9]+' | grep -o '[0-9]*' | head -1)
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
    # Strip trailing comment (space + # + anything) - matches .env.example format
    env_password=$(grep -E "^LAVALINK_PASSWORD=" .env 2>/dev/null | cut -d'=' -f2- | sed "s/[[:space:]][[:space:]]*#.*//; s/^[\"']//; s/[\"']$//")
    if [[ -n "$env_password" ]]; then
        export LAVALINK_PASSWORD="$env_password"
    fi
fi

# Load port from .env if present
export LAVALINK_PORT="${LAVALINK_PORT:-2333}"
if [[ -f ".env" ]]; then
    # Strip trailing comment (space + # + anything) - matches .env.example format
    env_port=$(grep -E "^LAVALINK_PORT=" .env 2>/dev/null | cut -d'=' -f2- | sed "s/[[:space:]][[:space:]]*#.*//; s/^[\"']//; s/[\"']$//")
    if [[ -n "$env_port" ]]; then
        export LAVALINK_PORT="$env_port"
    fi
fi

# Load MANAGE_LAVALINK from .env if present (default: true)
# When true, kills stale Lavalink on startup. Set false if sharing Lavalink with other bots.
export MANAGE_LAVALINK="${MANAGE_LAVALINK:-true}"
if [[ -f ".env" ]]; then
    env_manage=$(grep -E "^MANAGE_LAVALINK=" .env 2>/dev/null | cut -d'=' -f2- | sed "s/[[:space:]][[:space:]]*#.*//; s/^[\"']//; s/[\"']$//")
    if [[ -n "$env_manage" ]]; then
        export MANAGE_LAVALINK="$env_manage"
    fi
fi

# Load HTTP port from .env if present
export HTTP_SERVER_PORT="${HTTP_SERVER_PORT:-2334}"
if [[ -f ".env" ]]; then
    env_http_port=$(grep -E "^HTTP_SERVER_PORT=" .env 2>/dev/null | cut -d'=' -f2- | sed "s/[[:space:]][[:space:]]*#.*//; s/^[\"']//; s/[\"']$//")
    if [[ -n "$env_http_port" ]]; then
        export HTTP_SERVER_PORT="$env_http_port"
    fi
fi

# Check for duplicate ports
if [[ "$LAVALINK_PORT" == "$HTTP_SERVER_PORT" ]]; then
    echo -e "${RED}[x] LAVALINK_PORT and HTTP_SERVER_PORT are both set to $LAVALINK_PORT${NC}"
    echo "    they must be different - fix in .env"
    exit 1
fi

# Validate application.yml matches .env (local installs only)
if [[ -f "lavalink/application.yml" ]]; then
    venv/bin/python -c "
import yaml, os, sys

def clean_env(key, default):
    '''Strip trailing comments from env vars (requires space before #).'''
    val = os.environ.get(key, default)
    return val.split(' #')[0].strip() if ' #' in val else val.strip()

env_port = clean_env('LAVALINK_PORT', '2333')
env_pass = clean_env('LAVALINK_PASSWORD', 'timetomixdrinksandnotchangepasswords')

try:
    with open('lavalink/application.yml', encoding='utf-8') as f:
        cfg = yaml.safe_load(f)

    yml_port = cfg.get('server', {}).get('port')
    yml_pass = cfg.get('lavalink', {}).get('server', {}).get('password')

    if yml_port is not None and str(yml_port).strip() != env_port:
        print(f'\033[91m[x] port mismatch: LAVALINK_PORT={env_port} but application.yml has port: {yml_port}\033[0m')
        print('    fix in .env or lavalink/application.yml')
        sys.exit(1)
    if yml_pass is not None and yml_pass.strip() != env_pass:
        print('\033[91m[x] password mismatch: LAVALINK_PASSWORD does not match application.yml\033[0m')
        print('    fix in .env or lavalink/application.yml')
        sys.exit(1)
except yaml.YAMLError:
    print('\033[93m[!] warning: could not parse application.yml\033[0m')
except FileNotFoundError:
    pass
except Exception:
    pass
" || exit 1
fi

# Check if a port is in use (returns 0 if in use, 1 if available)
is_port_in_use() {
    local port=$1
    # Try ss first (modern), fall back to netstat
    if command -v ss >/dev/null 2>&1; then
        ss -tuln | grep -q ":${port} "
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tuln | grep -q ":${port} "
    else
        return 1  # Can't check - proceed and let Lavalink fail if needed
    fi
}

# Health check using Python (no curl dependency, reads password from env to avoid injection)
# Returns: "ready", "auth_failed", or "waiting" on stdout; exit 0 for ready, 1 otherwise
is_lavalink_ready() {
    venv/bin/python -c "
import urllib.request
import os
import sys
password = os.environ.get('LAVALINK_PASSWORD', 'timetomixdrinksandnotchangepasswords')
port = os.environ.get('LAVALINK_PORT', '2333')
try:
    req = urllib.request.Request(f'http://127.0.0.1:{port}/version', headers={'Authorization': password})
    urllib.request.urlopen(req, timeout=2)
    print('ready')
    sys.exit(0)
except urllib.error.HTTPError as e:
    if e.code == 401:
        print('auth_failed')
    else:
        print('waiting')
    sys.exit(1)
except urllib.error.URLError as e:
    # Connection refused is expected during startup
    print('waiting')
    sys.exit(1)
except Exception as e:
    print('waiting')
    sys.exit(1)
"
}

# Check if port is already in use (informational - fuser may fix it)
if is_port_in_use "$LAVALINK_PORT"; then
    echo -e "${YELLOW}[!] port $LAVALINK_PORT may be in use by another process${NC}"
fi

status=$(is_lavalink_ready 2>/dev/null) || true
: "${status:=waiting}"
if [[ "$status" == "ready" ]]; then
    echo -e "${CYAN}[+] lavalink already running${NC}"
elif [[ "$status" == "auth_failed" ]]; then
    echo -e "${RED}[x] existing lavalink has wrong password${NC}"
    echo "    password in .env must match lavalink/application.yml"
    exit 1
else
    # Kill any stale Lavalink process on our port (may be unresponsive zombie)
    # Respects MANAGE_LAVALINK setting - skip if sharing Lavalink with other bots
    if [[ "${MANAGE_LAVALINK,,}" != "false" ]]; then
        if command -v fuser >/dev/null 2>&1; then
            stale_pid=$(fuser "$LAVALINK_PORT/tcp" 2>/dev/null)
            if [[ -n "$stale_pid" ]]; then
                echo -e "${YELLOW}[.] killing stale process on port $LAVALINK_PORT...${NC}"
                fuser -k "$LAVALINK_PORT/tcp" 2>/dev/null
                sleep 2
            fi
        fi
    fi

    echo -e "${CYAN}[.] starting lavalink...${NC}"

    # Log to file instead of /dev/null so we can diagnose failures
    LAVALINK_LOG="lavalink/lavalink-startup.log"
    pushd lavalink >/dev/null || exit 1
    # JVM args: limit heap to 512MB, use G1GC for better memory management
    java -Xmx512m -Xms256m -XX:+UseG1GC -jar Lavalink.jar > lavalink-startup.log 2>&1 &
    LAVALINK_PID=$!
    popd >/dev/null || exit 1

    echo -ne "${CYAN}[.] waiting for lavalink${NC}"
    elapsed=0
    timeout=90  # Longer timeout for slower devices (Pi)
    while [[ $elapsed -lt $timeout ]]; do
        status=$(is_lavalink_ready 2>/dev/null) || true
        : "${status:=waiting}"
        if [[ "$status" == "ready" ]]; then
            break
        fi
        if [[ "$status" == "auth_failed" ]]; then
            echo
            echo -e "${RED}[x] lavalink auth failed - check LAVALINK_PASSWORD${NC}"
            echo "    password in .env must match lavalink/application.yml"
            exit 1
        fi
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
venv/bin/python bot.py
