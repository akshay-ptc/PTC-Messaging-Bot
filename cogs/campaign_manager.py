import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from database.db import db
from utils.permissions import founder_or_admin_only

class CampaignManagerCog(commands.Cog, name="Campaigns"):
    """CRUD operations to monitor and control DM broadcast campaigns."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    campaign_group = app_commands.Group(
        name="campaign",
        description="Manage and monitor DM campaigns (Founder & Admin only)",
        default_permissions=discord.Permissions(administrator=True)
    )

    # 1. READ: List Campaigns
    @campaign_group.command(name="list", description="List recent DM campaigns and their progress")
    @founder_or_admin_only()
    async def campaign_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        campaigns = await db.list_campaigns(interaction.guild_id, limit=8)

        if not campaigns:
            await interaction.followup.send("ℹ️ No DM campaigns found for this server.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📋 DM Campaigns (Recent History)",
            color=0x3498DB
        )

        for c in campaigns:
            status_emoji = {
                "running": "⚡ Running",
                "pending": "⏳ Pending",
                "completed": "✅ Completed",
                "paused": "⏸️ Paused",
                "cancelled": "🛑 Cancelled"
            }.get(c["status"], c["status"])

            progress_pct = round((c["sent_count"] + c["blocked_count"] + c["failed_count"]) / max(c["total_targets"], 1) * 100, 1)

            embed.add_field(
                name=f"Campaign #{c['id']} — {c['title'][:30]}",
                value=(
                    f"**Status:** {status_emoji}\n"
                    f"**Target:** `{c['target_type']}` | **Total:** {c['total_targets']}\n"
                    f"**Progress:** {progress_pct}% (✅ {c['sent_count']} sent | 🚫 {c['blocked_count']} blocked | ❌ {c['failed_count']} failed)\n"
                    f"**Date:** {c['created_at'][:16]}"
                ),
                inline=False
            )

        embed.set_footer(text="Use /campaign status <id> for in-depth breakdown.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # 2. READ: Campaign Status
    @campaign_group.command(name="status", description="Get real-time details and statistics of a DM campaign")
    @app_commands.describe(campaign_id="The ID of the campaign to check")
    @founder_or_admin_only()
    async def campaign_status(self, interaction: discord.Interaction, campaign_id: int):
        await interaction.response.defer(ephemeral=True)
        c = await db.get_campaign(campaign_id)

        if not c or c["guild_id"] != interaction.guild_id:
            await interaction.followup.send(f"❌ Campaign #{campaign_id} not found.", ephemeral=True)
            return

        processed = c["sent_count"] + c["blocked_count"] + c["failed_count"]
        remaining = max(0, c["total_targets"] - processed)

        embed = discord.Embed(
            title=f"📊 Campaign #{c['id']} Overview",
            color=0x00FF88 if c["status"] == "completed" else 0x3498DB
        )
        embed.add_field(name="Title", value=c["title"], inline=False)
        embed.add_field(name="Status", value=f"**{c['status'].upper()}**", inline=True)
        embed.add_field(name="Target Type", value=f"`{c['target_type']}`", inline=True)
        embed.add_field(name="Total Audience", value=str(c["total_targets"]), inline=True)
        
        embed.add_field(name="✅ Successfully Delivered", value=f"**{c['sent_count']}**", inline=True)
        embed.add_field(name="🚫 Closed DMs (Blocked)", value=f"**{c['blocked_count']}**", inline=True)
        embed.add_field(name="❌ Errors / Failed", value=f"**{c['failed_count']}**", inline=True)
        embed.add_field(name="⏳ Remaining in Queue", value=f"**{remaining}**", inline=True)

        embed.set_footer(text="PTC Anti-Spam Queue Engine")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # 3. UPDATE: Pause Campaign
    @campaign_group.command(name="pause", description="Pause an ongoing DM campaign")
    @app_commands.describe(campaign_id="The ID of the campaign to pause")
    @founder_or_admin_only()
    async def campaign_pause(self, interaction: discord.Interaction, campaign_id: int):
        await interaction.response.defer(ephemeral=True)
        c = await db.get_campaign(campaign_id)
        if not c or c["guild_id"] != interaction.guild_id:
            await interaction.followup.send(f"❌ Campaign #{campaign_id} not found.", ephemeral=True)
            return

        await db.update_campaign_status(campaign_id, "paused")
        await interaction.followup.send(f"⏸️ **Campaign #{campaign_id} has been PAUSED.** No more DMs will be sent until resumed.", ephemeral=True)

    # 4. UPDATE: Resume Campaign
    @campaign_group.command(name="resume", description="Resume a paused DM campaign")
    @app_commands.describe(campaign_id="The ID of the campaign to resume")
    @founder_or_admin_only()
    async def campaign_resume(self, interaction: discord.Interaction, campaign_id: int):
        await interaction.response.defer(ephemeral=True)
        c = await db.get_campaign(campaign_id)
        if not c or c["guild_id"] != interaction.guild_id:
            await interaction.followup.send(f"❌ Campaign #{campaign_id} not found.", ephemeral=True)
            return

        await db.update_campaign_status(campaign_id, "running")
        await interaction.followup.send(f"▶️ **Campaign #{campaign_id} has been RESUMED.** Dispatching continues safely.", ephemeral=True)

    # 5. DELETE: Cancel / Remove Campaign
    @campaign_group.command(name="cancel", description="Cancel and purge an active or pending DM campaign")
    @app_commands.describe(campaign_id="The ID of the campaign to cancel")
    @founder_or_admin_only()
    async def campaign_cancel(self, interaction: discord.Interaction, campaign_id: int):
        await interaction.response.defer(ephemeral=True)
        c = await db.get_campaign(campaign_id)
        if not c or c["guild_id"] != interaction.guild_id:
            await interaction.followup.send(f"❌ Campaign #{campaign_id} not found.", ephemeral=True)
            return

        await db.delete_campaign(campaign_id)
        await interaction.followup.send(f"🛑 **Campaign #{campaign_id} was CANCELLED and deleted.** Queue purged.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(CampaignManagerCog(bot))

