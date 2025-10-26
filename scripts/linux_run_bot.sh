#!/bin/bash
# Navigate to parent directory (project root)
cd "$(dirname "$0")/.."

# Activate virtual environment
source venv/bin/activate

# Run the bot
exec python3 bot.py

