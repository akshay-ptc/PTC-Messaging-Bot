import os
import platform
import discord
from discord import app_commands
from discord.ext import commands

from utils.permissions import founder_or_admin_only
from utils.pdf_generator import generate_pdf
import config

class AdminHelpCog(commands.Cog, name="Help & System"):
    """Command reference, PDF exporter, and system health status."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="export_pdf", description="Export the official PDF Command & Operations Reference")
    @founder_or_admin_only()
    async def export_pdf(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        pdf_path = config.BASE_DIR / "PTC_Bot_Command_Reference.pdf"

        # Regenerate fresh copy
        generate_pdf(str(pdf_path))

        if os.path.exists(pdf_path):
            file = discord.File(str(pdf_path), filename="PTC_Bot_Command_Reference.pdf")
            embed = discord.Embed(
                title="📄 PTC Bot Operations & Command Reference Manual",
                description=(
                    "Here is your official PDF manual covering all bot commands, anti-spam protections, "
                    "CRUD features, and 24/7 Render/UptimeRobot setup instructions."
                ),
                color=0x00A8FF
            )
            embed.set_footer(text="Prop Traders Community • Founder & Admin Clearance")
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        else:
            await interaction.followup.send("❌ Error generating PDF documentation.", ephemeral=True)

    @app_commands.command(name="help", description="Display all available bot commands and administrative usage")
    @founder_or_admin_only()
    async def help_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        embed = discord.Embed(
            title="🛡️ PTC Discord Bot Command Directory",
            description="All commands are restricted to **Server Founder** and **Administrators**.",
            color=0x1F51FF
        )

        embed.add_field(
            name="1. 🚀 Verification & Auto-Reminders",
            value=(
                "• `/verify preview` — Send a test verification DM to yourself.\n"
                "• `/verify status` — Check current unverified member count & cadence.\n"
                "• `/verify trigger_reminders` — Force-run a reminder pass now."
            ),
            inline=False
        )

        embed.add_field(
            name="2. 📬 Mass DM & Link Mirroring",
            value=(
                "• `/dm send` — Send custom DM to Everyone, Role, or User with up to 3 attachments.\n"
                "• `/dm from_link` — Copy a Discord message URL; the bot clones text & all attachments to DMs."
            ),
            inline=False
        )

        embed.add_field(
            name="3. ⚡ Campaign Queue Controls (CRUD)",
            value=(
                "• `/campaign list` — View recent broadcast campaigns & progress %.\n"
                "• `/campaign status <id>` — Detailed stats (Sent, Blocked, Failed, Remaining).\n"
                "• `/campaign pause <id>` — Pause an ongoing broadcast.\n"
                "• `/campaign resume <id>` — Resume a paused broadcast.\n"
                "• `/campaign cancel <id>` — Abort campaign and clear queue."
            ),
            inline=False
        )

        embed.add_field(
            name="4. ⚙️ Configuration & Templates (CRUD)",
            value=(
                "• `/config view` / `/config set` — Manage verification channel, roles, delays.\n"
                "• `/config set_message` — Update verification DM template.\n"
                "• `/template create` / `list` / `get` / `delete` — Reusable announcement templates.\n"
                "• `/blacklist add` / `remove` / `list` — Member opt-out management.\n"
                "• `/export_pdf` — Download the PDF manual right here in Discord."
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ Anti-Spam Safety Shield",
            value="Active: 3-6s jitter delay • 25s cool-off every 20 DMs • 429 auto-backoff • 50007 closed DM handler.",
            inline=False
        )

        embed.set_footer(text="PTC Security Bot • Prop Traders Community")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="system_status", description="Check bot latency, server resources, and health")
    @founder_or_admin_only()
    async def system_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        latency = round(self.bot.latency * 1000, 2)
        guilds = len(self.bot.guilds)
        users = sum(g.member_count for g in self.bot.guilds)

        embed = discord.Embed(
            title="🖥️ PTC Bot System & 24/7 Service Health",
            color=0x2ECC71
        )
        embed.add_field(name="Gateway Latency", value=f"`{latency} ms`", inline=True)
        embed.add_field(name="Connected Guilds", value=f"`{guilds}`", inline=True)
        embed.add_field(name="Cached Members", value=f"`{users}`", inline=True)
        embed.add_field(name="Keep-Alive Web Port", value=f"`{config.PORT}` (HTTP 200 OK)", inline=True)
        embed.add_field(name="Python Runtime", value=f"`{platform.python_version()}`", inline=True)
        embed.add_field(name="Uptime Monitor", value="`UptimeRobot / Upbot Active`", inline=True)
        embed.set_footer(text="Enterprise 24/7 Readiness")

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminHelpCog(bot))

