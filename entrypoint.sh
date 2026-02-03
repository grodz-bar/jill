#!/bin/sh
set -e

# Default to UID/GID 1000 if not specified
PUID=${PUID:-1000}
PGID=${PGID:-1000}

# Guard against running as root (PUID=0)
if [ "$PUID" -eq 0 ]; then
    echo "Warning: Running as root (PUID=0) is not recommended"
    exec python bot.py
fi

# Verify jill user exists (should be created in Dockerfile)
if ! id jill > /dev/null 2>&1; then
    echo "Error: jill user not found"
    exit 1
fi

# Adjust jill user/group to match requested UID/GID
# -o allows non-unique IDs so container can match host user/group
groupmod -o -g "$PGID" jill
usermod -o -u "$PUID" -g "$PGID" jill

# Fix ownership of data directories
chown -R jill:jill /data /config

# Drop to non-root user and run bot
# setpriv maintains PID 1 for proper signal handling (SIGTERM, etc.)
exec setpriv --reuid="$PUID" --regid="$PGID" --init-groups python bot.py
