"""
Bot Messages - All text responses

This file contains all the bot's text output that users see.
Customize these messages to change Jill's personality and responses.

STRING FORMATTING GUIDE:
========================

APOSTROPHES:
❌ WRONG: 'It's broken'          # Apostrophe breaks things
✅ RIGHT: 'It\'s broken'         # Now it doesn't

SPECIAL CHARACTERS:
- \n = new line, \t = tab, \\ = backslash
- \' = apostrophe, \" = quote

DISCORD FORMATTING:
- **bold**, *italic*, `code`, ***bold italic***

EXAMPLE TEXT (with lots of formatting):
'**Jill\'s Bar** *is open* - Time to `mix drinks` and ***change lives***\n Hooray. 🍸'

CUSTOMIZATION TIPS:
- Change emojis to match your server's style
- Modify personality by changing the tone of messages
- Add your own custom responses for special events
"""

# =======================================================================================================================
# DRINK EMOJIS - Rotating drinks for "Now serving" messages
# =======================================================================================================================

DRINK_EMOJIS = ['🍸', '🥃', '🍺', '🍸', '🍷', '🍶']

MESSAGES = {
    # ===================================================================================================================
    # ERRORS - Error messages and validation responses
    # ===================================================================================================================
    'error_not_in_voice': "🤔 Are you hiding?",
    'error_no_permission': "🚫 **{channel}** is off-limits!",
    'error_not_playing': "😒 I'm not even playing anything.",
    'error_already_playing': "🙄 It's already playing?",
    'error_no_tracks': "🎵 No tracks in the jukebox!",
    'error_fight_me': "😤 Fight me.",
    'error_cant_connect': "❌ Can't join that channel: {error}",
    'error_invalid_track': "❌ Track #{number} doesn't exist. Library has {total} tracks.",
    
    # ===================================================================================================================
    # FEATURE DISABLED - Messages for disabled features
    # ===================================================================================================================
    'feature_shuffle_disabled': "🔒 Shuffle feature is currently disabled.",
    'feature_queue_disabled': "🔒 Queue display feature is currently disabled.",
    'feature_library_disabled': "🔒 Library display feature is currently disabled.",
    
    # ===================================================================================================================
    # PLAYBACK - Music playback and control messages
    # ===================================================================================================================
    'now_serving': '{drink} Now serving: **{track}**',
    'resume': '🍹 Back to work: **{track}**',
    'pause': '🌃 Taking a break.',
    'pause_on_break': '🌃 On a break.',
    'pause_auto': '🌙 Stopped serving (bar\'s empty)',
    'stop': '😴 I\'m heading out.',
    
    # ===================================================================================================================
    # NAVIGATION - Track navigation and queue messages
    # ===================================================================================================================
    'previous_at_start': '😑 Already at the beginning!',
    'skip_no_disc': '✖️ No disc in jukebox.',
    'nothing_playing': '✖️ Nothing\'s playing right now.',
    'queue_will_loop': '_(Queue will loop after this)_',
    'queue_now_playing': '**Now playing:**',
    'queue_last_played': '**Last played:**',
    'queue_up_next': '**Up next:**',
    
    # ===================================================================================================================
    # SHUFFLE - Shuffle mode and organization messages
    # ===================================================================================================================
    'shuffle_on': '🔀 **Shuffle ON** - Time to mix things up!',
    'shuffle_off': '📋 **Shuffle OFF** - Back to the classics.',
    'shuffle_already_off': '📋 Already done!',
    'unshuffle_organized': '📋 **Shuffle OFF** - All neat and organized.',
    
    # ===================================================================================================================
    # SPAM WARNINGS - Warning messages for spam protection
    # ===================================================================================================================
    'spam_skip': '😤 Easy there, hotshot. I\'ll skip when you stop button mashing.',
    'spam_pause': '😑 Alright, alright, I\'ll pause. Chill.',
    'spam_stop': '😑 Yeah yeah, I\'m leaving. Give me a second.',
    'spam_previous': '😑 Going back, going back...',
    'spam_shuffle': '😵‍💫 Shuffle, unshuffle, make up your mind!',
    'spam_unshuffle': '😑 Okay, okay, organizing...',
    'spam_play_jump': '😵‍💫 Hold on, let me find that track...',
    
    # ===================================================================================================================
    # LIBRARY - Music library and playlist messages
    # ===================================================================================================================
    'library_header': '**🎵 Library (Page {page}/{total_pages})**\n',
    'library_next_page': '\nUse `!list {next_page}` for next page.',
    'library_shuffle_note': '\n🔀 **Shuffle is ON** - The list above shows unshuffled order.',
    'library_shuffle_help': 'Use `!play [number]` to jump to a track | Use `!queue` to see shuffled playback order.',
    'library_normal_help': 'Use `!play [number]` to jump to a track.',
    
    # ===================================================================================================================
    # HELP TEXT - Command help and information
    # ===================================================================================================================
    # NOTE: Help text is dynamically generated based on which features are enabled
    # See HELP_TEXT dictionary below for customization options
        }

# =======================================================================================================================
# HELP TEXT - Customize everything here!
# =======================================================================================================================

HELP_TEXT = {
    # Always shown
    'header': '🍸 **jill\'s jukebox** 🍸',
    'volume_note': '***Volume control***: *Use Discord\'s user volume slider (right-click bot)*',
    'footer': '        Time to mix drinks and change lives. 🍹',
    
    # Section titles
    'playback_title': '**Playback:**',
    'queue_title': '**Queue & Library:**',
    'shuffle_title': '**Shuffle:**',
    'info_title': '**Info:**',
    
    # Command lists
    # Note: Each section only shows if the corresponding feature is enabled
    'playback_commands': [
        '`!play` / `!resume` / `!unpause` / `!start` - Start/resume music',
        '`!play [number]` / `!skipto [number]` - Jump to track (e.g., !play 32)',
        '`!pause` / `!break` - Pause playback',
        '`!skip` / `!next` / `!ns` - Skip track',
        '`!previous` / `!back` / `!ps` - Previous track',
        '`!stop` / `!leave` / `!dc` / `!bye` - Disconnect'
    ],
    
    # Queue section (only shows if QUEUE_DISPLAY_ENABLED = True)
    'queue_commands': [
        '`!queue` / `!q` / `!song` / `!name` / `!playing` - Show song queue'
    ],
    
    # Library section (only shows if LIBRARY_DISPLAY_ENABLED = True)
    'library_commands': [
        '`!list [page]` / `!playlist [page]` / `!all [page]` - Show entire song list'
    ],
    
    # Shuffle section (only shows if SHUFFLE_MODE_ENABLED = True)
    'shuffle_commands': [
        '`!shuffle` / `!mess` / `!scramble` - Toggle shuffle on/off',
        '`!unshuffle` / `!fix` / `!organize` - Turn shuffle off'
    ],
    
    # Info section (always shown)
    'info_commands': [
        '`!help` / `!commands` / `!jill` - Show this message'
    ],
    
    # Error message (shown if help generation fails)
    'generation_error': '❌ Help system error - contact server administrator'
}

