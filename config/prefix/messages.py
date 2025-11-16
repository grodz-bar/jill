# Part of Jill - Licensed under GPL 3.0
# See LICENSE.md for details

r"""
=========================================================================================================================
Bot Messages
=========================================================================================================================

This file contains the bot's text output that users see.
Customize these messages to change jill's personality and responses.

=========================================================================================================================
STRING FORMATTING GUIDE:
=========================================================================================================================

APOSTROPHES:
WRONG: 'It's broken'          # Apostrophe breaks things
RIGHT: 'It\'s broken'         # Now it doesn't

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
- If you have your own custom server emojis, you can use them like this:

1. Find what emoji you want to use and what its name is; you can see the emoji's name by
hovering over it in the emoji selection menu.

2. Go to a text channel and type \:youremojiname: then hit Enter to send

3. Copy the output of the message, it should look like <:emojiname:1628512340528825422>

4. Replace or add below with your custom emoji code; for example, I use:

    'spam_skip': '<:jillgun:1428564230588827442> Easy there, hotshot. I\'ll skip when you stop button mashing.',
    
    instead of the default
    
    'spam_skip': '😒 Easy there. I\'ll skip when you stop button mashing.',
    
5. Now your bot is extra special and unique, just like you.
=========================================================================================================================
"""

MESSAGES = {
    # ===================================================================================================================
    # PLAYBACK ANNOUNCEMENTS - Prefix mode only (slash mode is silent, uses visual control panel)
    # ===================================================================================================================
    'now_serving': '{drink} Now serving: **{track}**',
    'paused_auto': "🌙 Auto-paused (no one listening)",
    'resumed_auto': "▶️ Auto-resumed: **{track}**",
    'stop': "😴 I'm heading out.",

    # ===================================================================================================================
    # PLAYBACK CONTROLS - User-initiated actions
    # ===================================================================================================================
    'resume': '🍹 Back to work: **{track}**',
    'pause': '🌃 Taking a break.',
    
    # ===================================================================================================================
    # NAVIGATION - Track navigation and queue messages
    # ===================================================================================================================
    # I use invisible characters to align text when needed, here's one if you want to use it: "⠀"
    # To customize "upcoming tracks" indentation/spacing, see /handlers/commands.py (queue formatting)

    'previous_at_start': '😑 Already at the beginning!',
    'skip_no_disc': '✖️ No disc in jukebox.',
    'nothing_playing': '✖️ Nothing\'s playing right now.',
    'queue_header': '╔════════════════════════════╗',
    'queue_footer': '╚════════════════════════════╝',
    'queue_now_playing': '⠀⠀🍸 Now Serving →',
    'queue_last_played': '⠀⠀🍷 Last Served: ',
    'queue_up_next': '⠀⠀🍹 Coming Up: ',

    # ===================================================================================================================
    # SHUFFLE - Shuffle mode messages
    # ===================================================================================================================
    'shuffle_on': '🔀 **Shuffle ON** - Time to mix things up!',
    'shuffle_off': '🎼 **Shuffle OFF** - Back to the classics.',
    
    # ===================================================================================================================
    # SPAM WARNINGS - Warning messages for spam protection
    # ===================================================================================================================
    # Spam session warnings (Layer 1: Per-User Spam Sessions)
    # One is randomly selected when a spam session is triggered
    'spam_warning_1': "Easy there. I'll do it when you stop button mashing.",
    'spam_warning_2': "Whoa! One thing at a time, please.",
    'spam_warning_3': "Take it easy... spamming won't make me work faster.",
    'spam_warning_4': "Calm down, I heard you the first time.",

    # ===================================================================================================================
    # TRACKS - Track list and playlist management messages
    # ===================================================================================================================
    'tracks_header': '**🎵 Tracks (Page {page}/{total_pages})**\n',
    'tracks_next_page': '\nUse `!tracks {next_page}` for next page.',
    'tracks_shuffle_note': '\n🔀 **Shuffle is ON** - The list above shows unshuffled order.',
    'tracks_shuffle_help': 'Use `!play [number or name]` to jump to a track | Use `!queue` to see shuffled playback order.',
    'tracks_normal_help': 'Use `!play [number or name]` to jump to a track.',

    # ===================================================================================================================
    # PLAYLISTS - Playlist browsing and switching messages
    # ===================================================================================================================
    'playlists_header': '**🎵 Playlists (Page {page}/{total_pages})**\n',
    'playlists_next_page': '\nUse `!playlists {next_page}` for next page.',
    'playlists_help': '\nUse `!playlist [name or number]` to switch playlists.',
    'playlist_switched': '✅ {message}',

    # ===================================================================================================================
    # ALIASES - Command alias information messages
    # ===================================================================================================================
    'aliases_header': '**🔤 Command Aliases**\n',
    'aliases_for': '**Aliases for `{command}`:** {aliases}',
    'aliases_none': '`{command}` has no aliases.',
    'aliases_unknown': '❌ Unknown command: `{command}`. Use `{prefix}help` to see all commands.',
    'aliases_footer': '\n💡 _All aliases work exactly like their main command_',
        }

# =======================================================================================================================
# HELP TEXT - Customize all the !help text here!
# =======================================================================================================================

HELP_TEXT = {
    # Always shown
    'header': '🍸 **jill\'s jukebox** 🍸',
    'volume_note': '**Volume control**: Use Discord\'s user volume slider (right-click bot)',
    'footer': 'Time to mix drinks and change lives. 🍹',
    
    # Section titles
    'playback_title': '**Playback:**',
    'queue_title': '**Queue:**',
    'tracks_title': '**Tracks:**',
    'playlist_title': '**Playlists:**',
    'shuffle_title': '**Shuffle:**',
    'info_title': '**Info:**',
    
    # Command lists
    # Note: Each section only shows if the corresponding feature is enabled
    'playback_commands': [
        '`!play` - Start/resume music',
        '`!play [track]` - Jump to track by number or name',
        '`!pause` - Pause playback',
        '`!skip` - Next track',
        '`!previous` - Previous track',
        '`!stop` - Disconnect'
    ],
    
    # Queue section (only shows if QUEUE_DISPLAY_ENABLED = True)
    'queue_commands': [
        '`!queue` - Show current song queue',
        '`!tracks` - Show all tracks in current playlist'
    ],
 
    # Playlists section (only shows if has_playlist_structure() = True)
    'playlist_commands': [
        '`!playlists` - Show all available playlists',
        '`!playlist <name>` - Switch to different playlist'
    ],
    
    # Tracks section (only shows if LIBRARY_DISPLAY_ENABLED = True)
    'tracks_commands': [
        # Empty - track/playlist commands are in the playlists section
    ],

    # Shuffle section (only shows if SHUFFLE_MODE_ENABLED = True)
    'shuffle_commands': [
        '`!shuffle` - Toggle shuffle mode'
    ],
    
    # Info section (always shown)
    'info_commands': [
        '`!help` - Show this message'
    ],
}

