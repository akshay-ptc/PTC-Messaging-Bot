import os
import logging
from aiohttp import web
import config

logger = logging.getLogger("ptc_bot.web")

class KeepAliveServer:
    def __init__(self, bot):
        self.bot = bot
        self.app = web.Application()
        self.app.router.add_get("/", self.handle_root)
        self.app.router.add_get("/health", self.handle_health)
        self.app.router.add_get("/status", self.handle_status)
        self.runner = None
        self.site = None

    async def handle_root(self, request):
        return web.Response(
            text="🚀 PTC Message Bot is LIVE and running 24/7!\nProp Traders Community Discord Guard",
            content_type="text/plain"
        )

    async def handle_health(self, request):
        status = "online" if self.bot.is_ready() else "starting"
        return web.json_response({
            "status": status,
            "bot_user": str(self.bot.user) if self.bot.user else None,
            "latency_ms": round(self.bot.latency * 1000, 2) if self.bot.is_ready() else None,
            "guilds_count": len(self.bot.guilds) if self.bot.is_ready() else 0
        })

    async def handle_status(self, request):
        return web.json_response({
            "service": "PTC Message & Security Bot",
            "uptime_target": "24/7 via UptimeRobot Ping",
            "version": "2.0.0-enterprise"
        })

    async def start(self):
        port = int(os.getenv("PORT", config.PORT))
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "0.0.0.0", port)
        await self.site.start()
        logger.info(f"Keep-Alive HTTP Web Server started on port {port}. Ready for Render & UptimeRobot.")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
            logger.info("Keep-Alive HTTP Web Server stopped.")

