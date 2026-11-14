# 🛡️ PTC Enterprise Discord Security & Mass DM Bot
**Prop Traders Community (PTC) Official Operations System**

A robust, enterprise-grade Discord bot built with `discord.py`, SQLite, and an advanced **Anti-Spam & Rate-Limit Shield** designed specifically for high-volume trading communities.

---

## 🌟 Key Features

### 1. 🚀 Instant Verification & Automated Unverified Reminders
- **On Join DM**: Automatically dispatches a clean, formatted DM to every new member who joins the server, including the official verification banner instruction image and clickable link to `<#verification>`.
- **Scheduled Reminders**: Periodically checks for members holding the `@unverified` role.
  - Sends a reminder after **1 day (24 hours)**.
  - Automatically repeats every **24 hours** (or custom configured interval) until verified.
  - Automatically halts reminders the moment the user verifies and receives their member role.

### 2. 📬 Targeted Mass DM Broadcasts (With Interactive Yes/No Preview)
- Send announcements to:
  - **Every Member (`@everyone`)**
  - **Members with a Specific Role** (e.g. `@VIP`, `@Funded Trader`, `@unverified`)
  - **A Specific Member**
- Supports up to 3 custom image attachments per dispatch.
- **Safety Confirmation & Live Preview**: Before any DMs are sent, the bot shows a full preview of the message content and attachments, showing recipient count and delivery time, and requires clicking **`[ ✅ Confirm & Send DMs ]`** (Yes) or **`[ ❌ Cancel Broadcast ]`** (No).

### 3. 🔗 Clone & Forward Messages from Discord Links (With Yes/No Preview)
- Simply right-click any Discord announcement or update in your server, click **"Copy Message Link"**, and pass it to `/dm from_link`.
- The bot extracts the text, embeds, and downloads all original file attachments to forward them directly into members' DMs.
- Displays a confirmation preview with **`[ ✅ Confirm & Send DMs ]`** and **`[ ❌ Cancel Broadcast ]`** buttons before queuing.
*(Note: Automated welcome DMs for newly joined members and scheduled unverified reminders run automatically without requiring manual confirmation).*

### 4. 🛡️ Anti-Spam & Discord Rate-Limit Shield (Zero Bans / Zero Flags)
Discord strictly monitors bot DM velocity and bans bots that blast hundreds of DMs simultaneously. This bot includes a state-of-the-art protection engine:
- **Humanized Jitter Delay**: Waits randomized intervals (3.0s – 6.0s) between every DM.
- **Batch Cool-Down Breather**: Automatically takes a 25-second cool-down break after every 20 DMs to keep your bot’s trust score high.
- **HTTP 429 Exponential Backoff**: Detects Discord rate limits dynamically, reads `retry_after`, pauses safely, and resumes without dropping a single message.
- **Error 50007 Isolation (Closed DMs)**: When users disable direct messages or block the bot, it logs them as `blocked_dms` without crashing or spamming failed gateway sockets.
- **Circuit Breaker Fail-Safe**: Auto-pauses broadcasts if consecutive network errors exceed safe thresholds.

### 5. 🔒 Strict Security (Founder & Admin Only)
- All commands are protected by dual-layer security:
  - Discord Slash Command permissions: `administrator=True`.
  - Runtime decorator `@founder_or_admin_only()` ensuring only the **Server Founder/Owner** or members with Administrator permissions can trigger operations.

### 6. ⚡ Full CRUD Management & JSON Database
- **Pure JSON Database**: Stores all data in `bot_database.json` with thread-safe atomic writes (zero corruption, fully human-readable).
- **Campaign CRUD**: Create, view status, list history, pause, resume, or cancel active broadcasts.
- **Settings CRUD**: Update verification channels, role IDs, reminder delays, and custom message templates.
- **Template CRUD**: Save, read, list, and delete reusable announcement templates.
- **Blacklist CRUD**: Manage user opt-outs so compliant members are never messaged.

### 7. 💾 Instant Backup & Restore (Re-Add & Server Migration Protection)
- **`/backup download`**: Generates and sends a full `PTC_Bot_Backup_YYYYMMDD_HHMMSS.json` snapshot directly to the admin in Discord.
- **`/backup restore`**: Upload your `.json` backup file in Discord to restore 100% of your configurations, templates, reminders, and broadcast history. Perfect if you remove the bot, switch servers, or migrate hosts!

### 8. 📄 Official PDF Command Manual Exporter
- Run `/export_pdf` in Discord to receive a formatted, executive-style PDF manual directly in your server.

---

## 📋 Slash Command Reference

| Command | Parameters | Description |
| :--- | :--- | :--- |
| **`/verify preview`** | None | Sends a test verification DM to yourself to preview layout and banner. |
| **`/verify status`** | None | Displays current verification settings, target channel, and unverified count. |
| **`/verify trigger_reminders`** | None | Instantly triggers a reminder cycle across all unverified members. |
| **`/dm send`** | `target_type`, `message`, `[role]`, `[user]`, `[images 1-3]` | Send custom DM to Everyone, a Role, or a Member with attachments. |
| **`/dm from_link`** | `message_link`, `target_type`, `[role]`, `[user]` | Clones an existing message and forwards text + attachments to DMs. |
| **`/campaign list`** | None | **[READ]** Lists recent DM broadcasts and delivery completion percentages. |
| **`/campaign status`** | `campaign_id` | **[READ]** Real-time breakdown: Sent, Blocked DMs, Failed, Remaining. |
| **`/campaign pause`** | `campaign_id` | **[UPDATE]** Halts an active broadcast immediately. |
| **`/campaign resume`** | `campaign_id` | **[UPDATE]** Resumes a paused broadcast queue. |
| **`/campaign cancel`** | `campaign_id` | **[DELETE]** Cancels broadcast and purges pending queue entries. |
| **`/config view`** | None | **[READ]** View active server configuration. |
| **`/config set`** | `channel`, `unverified_role`, `delay`, `interval`, `enabled` | **[UPDATE]** Modify verification channel, roles, and reminder schedule. |
| **`/config set_message`** | `message` | **[UPDATE]** Edit verification reminder text template. |
| **`/template create`** | `name`, `content` | **[CREATE]** Save a reusable message template. |
| **`/template get`** | `name` | **[READ]** View saved template. |
| **`/template list`** | None | **[READ]** List all saved templates. |
| **`/template delete`** | `name` | **[DELETE]** Remove a template. |
| **`/blacklist add`** | `user`, `[reason]` | **[CREATE]** Opt-out/blacklist a member from receiving DMs. |
| **`/blacklist remove`** | `user` | **[DELETE]** Remove user from blacklist. |
| **`/blacklist list`** | None | **[READ]** List all blacklisted members. |
| **`/backup download`** | None | **[BACKUP]** Generates and sends full JSON database snapshot in Discord. |
| **`/backup restore`** | `backup_file` (.json) | **[RESTORE]** Upload JSON backup to restore all settings, reminders & templates. |
| **`/export_pdf`** | None | Exports and uploads `PTC_Bot_Command_Reference.pdf` directly into Discord. |
| **`/system_status`** | None | Real-time ping, uptime status, cached members, and keep-alive health. |

---

## 🛠️ Step-by-Step 24/7 Cloud Deployment Guide

Follow these steps to deploy your bot for free on **Render** and keep it running 24/7 using **UptimeRobot (Upbot)**.

### Step 1: Discord Developer Portal Setup
1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application** and name it `PTC Security Bot`.
3. Go to the **Bot** tab on the left:
   - Click **Reset Token** and copy your **Bot Token** (keep this secret).
   - Under **Privileged Gateway Intents**, turn **ON**:
     - ✅ **SERVER MEMBERS INTENT** *(Required to welcome new members & read unverified roles)*
     - ✅ **MESSAGE CONTENT INTENT** *(Required to clone messages from links)*
4. Go to **OAuth2 -> URL Generator**:
   - Scopes: Select `bot` and `applications.commands`.
   - Bot Permissions: Select `Administrator` (or *Send Messages, Manage Roles, Read Messages/View Channels, Attach Files, Read Message History*).
   - Copy the generated URL and open it in your browser to invite the bot to your server.

---

### Step 2: Push Bot Code to GitHub
1. Create a **Private Repository** on GitHub (e.g. `ptc-discord-bot`).
2. Push this folder to your repository:
   ```bash
   git init
   git add .
   git commit -m "PTC Bot initial release"
   git branch -M main
   git remote add origin https://github.com/<your-username>/ptc-discord-bot.git
   git push -u origin main
   ```

---

### Step 3: Deploy on Render (Free Web Service)
1. Sign in to [Render](https://render.com).
2. Click **New +** -> **Web Service**.
3. Connect your GitHub repository.
4. Fill in the service settings:
   - **Name**: `ptc-security-bot`
   - **Region**: Choose the closest region (e.g. Oregon or Frankfurt).
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: `Free`
5. Scroll down to **Environment Variables** and add:
   - `DISCORD_TOKEN`: *(Your Bot Token from Step 1)*
   - `GUILD_ID`: *(Your Discord Server ID)*
   - `FOUNDER_ID`: *(Your Discord User ID)*
   - `ADMIN_ROLE_ID`: *(Optional - Your Server Admin Role ID)*
   - `PORT`: `8080`
6. Click **Deploy Web Service**.
7. Render will build the environment and start the bot. When complete, you will see:
   ```
   🚀 PTC Security & DM Bot is Online!
   Keep-Alive HTTP Web Server started on port 8080.
   ```
8. Copy your Render service URL (e.g. `https://ptc-security-bot.onrender.com`).

---

### Step 4: Keep Bot Alive 24/7 with UptimeRobot (Upbot)
Render's free tier spins down web services after 15 minutes of inactivity if no HTTP requests are received. Our bot embeds an ultra-lightweight keep-alive server specifically designed to counter this.

1. Create a free account at [UptimeRobot](https://uptimerobot.com).
2. In the dashboard, click **+ Add New Monitor**.
3. Configure the monitor:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `PTC Discord Bot 24/7`
   - **URL (or IP)**: `https://your-app-name.onrender.com/health`
   - **Monitoring Interval**: `Every 5 minutes`
4. Click **Create Monitor**.
5. UptimeRobot will now ping your bot's `/health` endpoint every 5 minutes:
   - Render detects continuous incoming traffic and **never sleeps**.
   - Your Discord bot remains connected to the Discord gateway **24 hours a day, 7 days a week, 365 days a year**!

---

## 🔒 Security Best Practices
- Never commit your `.env` file or bot token to public repositories.
- Only Founders and Admins can invoke the bot commands.
- All DM campaigns log delivery status (`sent`, `blocked_dms`, `failed`), providing total auditability.

