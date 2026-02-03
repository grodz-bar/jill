# Discord Setup

Before Jill can tend bar, you'll need to register the bot with Discord. This guide walks you through creating the bot and inviting it to your server.

### 1. Create a Discord Application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **New Application** in the top right
3. Enter a name (this is just the application name, not what users see in your server)
4. Accept the Terms of Service and click **Create**

> [!NOTE]
> The application name is for your reference in the Developer Portal. The bot's display name in Discord is set separately in the Bot section.

### 2. Create the Bot User

1. In the left sidebar, click **Bot**
2. Click **Add Bot** (or **Reset Token** if one already exists)
3. A confirmation dialog appears - click **Yes, do it!**
4. Click **Copy** in the Token section and save it somewhere safe - you can only see it once

> [!WARNING]
> Treat your bot token like a password. If exposed, click **Reset Token** immediately.

### 3. Configure Bot Settings

1. Go to **Installation** tab and set **Install Link** to "None"
2. Go to **Bot** tab and disable **Public Bot** and **Requires OAuth2 Code Grant**
3. Scroll down and leave all **Privileged Gateway Intents** OFF - Jill doesn't need any

### 4. Generate the Invite Link

Now you'll create a URL to invite Jill to your server.

1. In the left sidebar, click **OAuth2** → **URL Generator**
2. Under **Scopes**, check both: `bot` and `applications.commands`
3. Under **Bot Permissions**, check exactly these four:
   - `View Channels`
   - `Send Messages`
   - `Connect`
   - `Speak`
4. Copy the generated URL from the bottom of the page

### 5. Invite to Your Server

1. Paste the invite URL into your browser
2. Select the server you want to add Jill to (you need "Manage Server" permission)
3. Click **Authorize**
4. Complete the CAPTCHA if prompted

> Jill will now appear in your server's member list, but she'll show as **offline** until you run her.

### 6. Get Your Guild ID (Recommended)

> [!TIP]
> Without a Guild ID, slash commands can take up to an hour to appear.

1. Enable **Developer Mode** - Discord Settings > App Settings > Advanced > Developer Mode ON
2. Right-click your server's icon > **Copy Server ID** - this is your `GUILD_ID`

### Next Steps

Choose your platform setup:

- [Docker Setup](docker-setup.md)
- [Linux Setup](linux-setup.md)
- [Windows Setup](windows-setup.md)
