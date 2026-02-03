FROM python:3.13.1-slim

LABEL org.opencontainers.image.source=https://github.com/grodz-bar/jill
LABEL org.opencontainers.image.description="Jill - Discord music bot with bartender vibes"
LABEL org.opencontainers.image.licenses=GPL-3.0-or-later

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application (see .dockerignore for excluded files)
COPY . .

# Create mount points for volumes
RUN mkdir -p /music /config /data

# Run bot
CMD ["python", "bot.py"]
