import os
import platform
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from utils.permissions import founder_or_admin_only
from utils.pdf_generator import generate_pdf
from database.db import db
import config

class AdminHelpCog(commands.Cog, name="Help & System"):
    """Command reference, PDF exporter, system health status, and JSON database backup/restore."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================
    # Group: /backup (JSON Database Backup & Restore)
    # ============================================================
    backup_group = app_commands.Group(
        name="backup",
        description="JSON Database Backup and Restore tools (Founder & Admin Only)",
        default_permissions=discord.Permissions(administrator=True)
    )

    @backup_group.command(name="download", description="Generate and download a full JSON backup of the database")
    @founder_or_admin_only()
    async def backup_download(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            backup_file_path = await db.create_backup_file()
            file = discord.File(backup_file_path, filename=os.path.basename(backup_file_path))

            embed = discord.Embed(
                title="💾 JSON Database Backup Created",
                description=(
                    "Here is your complete database backup snapshot.\n\n"
                    "**What is included:**\n"
                    "• Server verification settings & schedules\n"
                    "• Member join & reminder histories\n"
                    "• DM broadcast campaigns & queue stats\n"
                    "• Reusable message templates\n"
                    "• Opt-out blacklists\n\n"
                    "💡 *Save this `.json` file on your PC or cloud drive. If you ever remove the bot or redeploy, "
                    "simply run `/backup restore` with this file to restore everything instantly!*"
                ),
                color=0x2ECC71
            )
            embed.set_footer(text=f"Snapshot file: {os.path.basename(backup_file_path)}")
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to create backup: {e}", ephemeral=True)

    @backup_group.command(name="restore", description="Restore the bot database from a previously downloaded JSON backup file")
    @app_commands.describe(backup_file="Attach the .json backup file downloaded earlier")
    @founder_or_admin_only()
    async def backup_restore(self, interaction: discord.Interaction, backup_file: discord.Attachment):
        await interaction.response.defer(ephemeral=True)

        if not backup_file.filename.endswith(".json"):
            await interaction.followup.send("❌ Invalid file format! Please upload a valid `.json` backup file.", ephemeral=True)
            return

        temp_restore_path = config.BASE_DIR / "temp_attachments" / f"restore_{backup_file.filename}"
        os.makedirs(os.path.dirname(temp_restore_path), exist_ok=True)

        try:
            await backup_file.save(str(temp_restore_path))
            success = await db.restore_from_json(str(temp_restore_path))

            if os.path.exists(temp_restore_path):
                os.remove(temp_restore_path)

            if success:
                embed = discord.Embed(
                    title="✅ Database Restored Successfully!",
                    description=(
                        f"All configurations, templates, reminders, and broadcast data from **{backup_file.filename}** "
                        "have been successfully imported and applied to the bot."
                    ),
                    color=0x00FF88
                )
                embed.set_footer(text="PTC Security Bot • JSON Database Active")
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send("❌ Failed to restore database. The provided JSON file appears to be corrupted or invalid.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error restoring backup: {e}", ephemeral=True)

    # ============================================================
    # PDF Exporter
    # ============================================================
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
                    "CRUD features, JSON database backups, and 24/7 Render/UptimeRobot setup instructions."
                ),
                color=0x00A8FF
            )
            embed.set_footer(text="Prop Traders Community • Founder & Admin Clearance")
            await interaction.followup.send(embed=embed, file=file, ephemeral=True)
        else:
            await interaction.followup.send("❌ Error generating PDF documentation.", ephemeral=True)

    # ============================================================
    # Help Command
    # ============================================================
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
            name="2. 📬 Mass DM & Link Mirroring (With Preview & Yes/No)",
            value=(
                "• `/dm send` — Custom DM to Everyone, Role, or User with attachments + preview.\n"
                "• `/dm from_link` — Clones message text & attachments from a link into DMs."
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
            name="5. 💾 JSON Database Backup & Restore",
            value=(
                "• `/backup download` — Download full `.json` database snapshot directly in Discord.\n"
                "• `/backup restore` — Upload `.json` file to restore all settings and data instantly."
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
        embed.add_field(name="Database Engine", value="`Pure JSON (Atomic)`", inline=True)
        embed.add_field(name="Keep-Alive Web Port", value=f"`{config.PORT}` (HTTP 200 OK)", inline=True)
        embed.add_field(name="Python Runtime", value=f"`{platform.python_version()}`", inline=True)
        embed.set_footer(text="Enterprise 24/7 Readiness")

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminHelpCog(bot))
