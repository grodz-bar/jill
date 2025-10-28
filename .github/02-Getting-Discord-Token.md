# How to Get a Discord Bot Token

A step-by-step guide for creating your Discord bot and getting your token.

---

## Step 1: Create Application

1. Go to: [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"**
3. Name it (e.g., "jill music")
4. Click **"Create"**

---

## Step 2: Create Bot User

1. Click **"Bot"** in left sidebar
2. Click **"Add Bot"**
3. Confirm **"Yes, do it!"**

> **Note:** Sometimes it's auto-created.

---

## Step 3: Configure Bot

Under **"Privileged Gateway Intents"**, enable:

- ✅ **SERVER MEMBERS INTENT** (for auto-pause and disconnect)
- ✅ **MESSAGE CONTENT INTENT** (to read command messages)

---

## Step 4: Get Token

1. Under **"Token"** section, click **"Reset Token"**
2. Confirm, then copy the token
3. Save it somewhere safe (you'll need it later)

> **IMPORTANT:** NEVER share your token! It's like a password. If your token is leaked, reset it immediately in the developer portal.

---

## Step 5: Invite Bot to Server

1. Click **"OAuth2"** in left sidebar
2. Find **"OAuth2 URL Generator"** and under **"Scopes"**, select:
   - `bot`
   - `applications.commands`

3. Under **"Bot Permissions"**, select:
   - `Read Messages/View Channels`
   - `Send Messages`
   - `Manage Messages`
   - `Connect`
   - `Speak`
   - `Use Voice Activity`

4. Copy the generated URL at bottom
5. Paste into browser
6. Select your server
7. Click **"Authorize"**

---

## Step 6: Continue with Platform Setup

If you're following a platform setup guide ([Windows Setup](03-SETUP-Windows.md) or [Linux Setup](03-SETUP-Linux.md)), continue from it. You will need this token in the setup wizard.

---

## Troubleshooting

For troubleshooting, see [Troubleshooting](06-troubleshooting.md)
