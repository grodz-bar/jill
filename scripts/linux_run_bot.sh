#!/bin/bash
# Navigate to parent directory (project root)
cd "$(dirname "$0")/.." || exit 1
 
# Activate virtual environment (located at ~/jill-env as per setup guide)
source "$HOME/jill-env/bin/activate"
 
# Run the bot
exec python3 bot.py