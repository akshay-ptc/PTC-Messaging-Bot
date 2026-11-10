import asyncio
import logging
import sys
import discord
from discord.ext import commands

import config
from database.db import db
from utils.queue_worker import SafeDMQueueWorker
from utils.web_server import KeepAliveServer

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ptc_bot")

class PTCBot(commands.Bot):
    def __init__(self):
        # Configure Intents
        intents = discord.Intents.default()
        intents.members = True          # Required for join events & role targeting
        intents.message_content = True  # Required for message link cloning
        intents.guilds = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
        )

        self.queue_worker = SafeDMQueueWorker(self)
        self.web_server = KeepAliveServer(self)

    async def setup_hook(self):
        """Runs before the bot connects to Discord gateway."""
        # 1. Initialize SQLite Database Schema
        logger.info("Initializing SQLite database...")
        await db.init()

        # 2. Start Keep-Alive Web Server for Render & UptimeRobot
        logger.info("Starting Keep-Alive Web Server...")
        await self.web_server.start()

        # 3. Load Cogs
        cogs = [
            "cogs.verification",
            "cogs.broadcast",
            "cogs.campaign_manager",
            "cogs.settings",
            "cogs.admin_help"
        ]
        for cog in cogs:
            try:
                await self.load_extension(cog)
                logger.info(f"Loaded Cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog}: {e}", exc_info=True)

        # 4. Start Safe DM Queue Worker
        self.queue_worker.start()

    async def on_ready(self):
        logger.info(f"==================================================")
        logger.info(f"🚀 PTC Security & DM Bot is Online!")
        logger.info(f"Logged in as: {self.user} (ID: {self.user.id})")
        logger.info(f"Serving {len(self.guilds)} server(s)")
        logger.info(f"==================================================")

        # Sync Slash Commands
        try:
            if config.GUILD_ID:
                guild_obj = discord.Object(id=config.GUILD_ID)
                self.tree.copy_global_to(guild=guild_obj)
                synced = await self.tree.sync(guild=guild_obj)
                logger.info(f"Synced {len(synced)} slash commands directly to Guild ID {config.GUILD_ID}")
            else:
                synced = await self.tree.sync()
                logger.info(f"Synced {len(synced)} slash commands globally.")
        except Exception as e:
            logger.error(f"Failed to sync slash commands: {e}", exc_info=True)

        # Set rich presence
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="Prop Traders Community 🛡️"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

    async def close(self):
        logger.info("Shutting down bot...")
        self.queue_worker.stop()
        if self.web_server:
            await self.web_server.stop()
        await super().close()


async def main():
    if not config.DISCORD_TOKEN:
        logger.critical(
            "DISCORD_TOKEN is missing! Please provide your bot token in the .env file or environment variables."
        )
        sys.exit(1)

    bot = PTCBot()
    async with bot:
        await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot process interrupted by user. Exiting cleanly.")

