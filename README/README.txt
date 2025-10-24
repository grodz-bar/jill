================================================================================
JILL - A CYBERPUNK BARTENDER DISCORD MUSIC BOT
================================================================================

A simple yet robust Discord music bot built with disnake that plays local .opus
files with queue navigation, shuffle modes, and automated message cleanup.


QUICK START:
1. Get a Discord bot token (see 'Getting-Discord-Token.txt')
2. Convert your music to .opus format (see 'Converting-To-Opus.txt')
3. Follow setup guide (see SETUP-Linux.txt or SETUP-Windows.txt)
4. Serve drinks.


BASIC COMMANDS:
!play [track#]  - Start playing or jump to track
!pause          - Pause playback
!play           - Resume playback
!stop           - Stop and reset queue
!skip           - Skip to next track
!previous       - Go to previous track
!queue          - Show current queue
!list [page]    - Browse available tracks
!shuffle        - Enable/disable shuffle mode
!help           - Show help message


FEATURES:
- Music Control: Play, pause, skip, queue navigation
- Smart Automation: Auto-pause when alone, dual message cleanup systems
- Shuffle Mode: Randomize track order and auto-reshuffles
- Multi-Layer Spam Protection: Prevents abuse and rate-limiting
- Customizable: Command aliases, bot messages, feature toggles
- Channel Persistence: Remembers which channel to clean up after restart


CONFIGURATION:
All settings are in the /config/ folder. The most important files:
- config/messages.py - Customize bot responses
- config/features.py - Turn features on/off
- config/timing.py   - Adjust cooldowns and timing


For troubleshooting, see troubleshooting.txt
