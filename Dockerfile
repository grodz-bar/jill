FROM python:3.13.1-slim

LABEL org.opencontainers.image.source=https://github.com/grodz-bar/jill
LABEL org.opencontainers.image.description="Jill - Discord music bot with bartender vibes"
LABEL org.opencontainers.image.licenses=GPL-3.0-or-later

WORKDIR /app

# Install util-linux for setpriv (privilege dropping)
# Required: setpriv is NOT included in python:slim by default
RUN apt-get update && apt-get install -y --no-install-recommends util-linux \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for running the bot
RUN groupadd -g 1000 jill && useradd -u 1000 -g jill -m jill

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application (see .dockerignore for excluded files)
COPY . .

# Create mount points with correct ownership
RUN mkdir -p /music /config /data && chown -R jill:jill /music /config /data

# Copy and enable entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Default UID/GID (can be overridden at runtime)
ENV PUID=1000
ENV PGID=1000

ENTRYPOINT ["/entrypoint.sh"]
