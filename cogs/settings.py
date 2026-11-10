import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

from database.db import db
from utils.permissions import founder_or_admin_only
import config

class SettingsCog(commands.Cog, name="Settings"):
    """CRUD operations for Verification Settings, Message Templates, and Opt-out Blacklist."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ============================================================
    # Group 1: /config (Verification Settings CRUD)
    # ============================================================
    config_group = app_commands.Group(
        name="config",
        description="Configure bot settings and verification schedule (Founder & Admin Only)",
        default_permissions=discord.Permissions(administrator=True)
    )

    @config_group.command(name="view", description="View current server configuration and reminder rules")
    @founder_or_admin_only()
    async def config_view(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        s = await db.get_settings(interaction.guild_id)

        v_chan = f"<#{s['verification_channel_id']}>" if s.get('verification_channel_id') else "*Not Set*"
        unverified_r = f"<@&{s['unverified_role_id']}>" if s.get('unverified_role_id') else "*Not Set*"
        verified_r = f"<@&{s['verified_role_id']}>" if s.get('verified_role_id') else "*Not Set*"

        embed = discord.Embed(
            title="⚙️ PTC Bot Server Configuration",
            color=0x00A8FF
        )
        embed.add_field(name="Auto-Reminders", value="✅ **Enabled**" if s.get("reminder_enabled") else "❌ **Disabled**", inline=True)
        embed.add_field(name="Verification Channel", value=v_chan, inline=True)
        embed.add_field(name="Unverified Role", value=unverified_r, inline=True)
        embed.add_field(name="Verified Role", value=verified_r, inline=True)
        embed.add_field(name="Initial Delay", value=f"**{s.get('initial_delay_hours')} Hours** (1 day)", inline=True)
        embed.add_field(name="Repeat Interval", value=f"**{s.get('repeat_interval_hours')} Hours** (everyday)", inline=True)
        embed.add_field(name="Banner Image", value=f"`{s.get('verify_image_path', 'Default')}`", inline=False)
        embed.add_field(name="Verification Message", value=f"```{s.get('verify_message_template')[:350]}...```", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @config_group.command(name="set", description="Update server verification settings and schedule intervals")
    @app_commands.describe(
        verification_channel="Channel where members verify (e.g. #verification)",
        unverified_role="Role given to unverified members",
        verified_role="Role given to verified members (removes reminders once granted)",
        initial_delay_hours="Hours after joining before first reminder (Default: 24h = 1 day)",
        repeat_interval_hours="Hours between subsequent reminders (Default: 24h = everyday)",
        reminder_enabled="Enable (True) or Disable (False) automatic reminders"
    )
    @founder_or_admin_only()
    async def config_set(
        self,
        interaction: discord.Interaction,
        verification_channel: Optional[discord.TextChannel] = None,
        unverified_role: Optional[discord.Role] = None,
        verified_role: Optional[discord.Role] = None,
        initial_delay_hours: Optional[float] = None,
        repeat_interval_hours: Optional[float] = None,
        reminder_enabled: Optional[bool] = None,
    ):
        await interaction.response.defer(ephemeral=True)
        updates = {}

        if verification_channel is not None:
            updates["verification_channel_id"] = verification_channel.id
        if unverified_role is not None:
            updates["unverified_role_id"] = unverified_role.id
        if verified_role is not None:
            updates["verified_role_id"] = verified_role.id
        if initial_delay_hours is not None:
            updates["initial_delay_hours"] = max(0.5, initial_delay_hours)
        if repeat_interval_hours is not None:
            updates["repeat_interval_hours"] = max(1.0, repeat_interval_hours)
        if reminder_enabled is not None:
            updates["reminder_enabled"] = 1 if reminder_enabled else 0

        if not updates:
            await interaction.followup.send("⚠️ No settings were provided to update.", ephemeral=True)
            return

        await db.update_settings(interaction.guild_id, **updates)
        await interaction.followup.send("✅ **Settings updated successfully!** Use `/config view` to see the new values.", ephemeral=True)

    @config_group.command(name="set_message", description="Update the custom text used in the verification DM")
    @app_commands.describe(message="The new template text. Use {channel_id} to mention the verification channel.")
    @founder_or_admin_only()
    async def config_set_message(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=True)
        await db.update_settings(interaction.guild_id, verify_message_template=message)
        await interaction.followup.send("✅ **Verification message template updated!**", ephemeral=True)

    # ============================================================
    # Group 2: /blacklist (Opt-out / Excluded List CRUD)
    # ============================================================
    blacklist_group = app_commands.Group(
        name="blacklist",
        description="Opt-out blacklist management (Founder & Admin Only)",
        default_permissions=discord.Permissions(administrator=True)
    )

    @blacklist_group.command(name="add", description="Add a user to the DM blacklist so they never receive DMs")
    @app_commands.describe(user="The member to blacklist", reason="Optional reason")
    @founder_or_admin_only()
    async def blacklist_add(self, interaction: discord.Interaction, user: discord.Member, reason: Optional[str] = "Admin excluded"):
        await interaction.response.defer(ephemeral=True)
        await db.add_to_blacklist(user.id, interaction.guild_id, reason, interaction.user.id)
        await interaction.followup.send(f"🛡️ **{user.mention}** has been added to the DM Blacklist. They will not receive automated DMs.", ephemeral=True)

    @blacklist_group.command(name="remove", description="Remove a user from the DM blacklist")
    @app_commands.describe(user="The member to unblacklist")
    @founder_or_admin_only()
    async def blacklist_remove(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        removed = await db.remove_from_blacklist(user.id, interaction.guild_id)
        if removed:
            await interaction.followup.send(f"✅ **{user.mention}** removed from blacklist.", ephemeral=True)
        else:
            await interaction.followup.send(f"ℹ️ **{user.mention}** was not in the blacklist.", ephemeral=True)

    @blacklist_group.command(name="list", description="List members on the DM blacklist")
    @founder_or_admin_only()
    async def blacklist_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        items = await db.list_blacklist(interaction.guild_id)

        if not items:
            await interaction.followup.send("ℹ️ No users are currently blacklisted.", ephemeral=True)
            return

        lines = [f"• <@{it['user_id']}> — *{it['reason']}* ({it['created_at'][:10]})" for it in items[:20]]
        embed = discord.Embed(
            title="🚫 DM Blacklisted Users",
            description="\n".join(lines),
            color=0xE74C3C
        )
        embed.set_footer(text=f"Total blacklisted: {len(items)}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ============================================================
    # Group 3: /template (Reusable Message Templates CRUD)
    # ============================================================
    template_group = app_commands.Group(
        name="template",
        description="Manage reusable DM templates (Founder & Admin Only)",
        default_permissions=discord.Permissions(administrator=True)
    )

    @template_group.command(name="create", description="Save a reusable template")
    @app_commands.describe(name="Template name (e.g. webinar, giveaway)", content="The message body")
    @founder_or_admin_only()
    async def template_create(self, interaction: discord.Interaction, name: str, content: str):
        await interaction.response.defer(ephemeral=True)
        success = await db.create_template(interaction.guild_id, name.lower().strip(), content, interaction.user.id)
        if success:
            await interaction.followup.send(f"✅ Template **'{name}'** saved successfully!", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Failed to save template. A template with the name **'{name}'** might already exist.", ephemeral=True)

    @template_group.command(name="get", description="Read an existing template")
    @app_commands.describe(name="The name of the template")
    @founder_or_admin_only()
    async def template_get(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        tmpl = await db.get_template(interaction.guild_id, name.lower().strip())
        if not tmpl:
            await interaction.followup.send(f"❌ Template **'{name}'** not found.", ephemeral=True)
            return

        embed = discord.Embed(title=f"📝 Template: {tmpl['name']}", description=tmpl['content'], color=0x9B59B6)
        embed.set_footer(text=f"Updated: {tmpl['updated_at'][:16]}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @template_group.command(name="list", description="List all saved templates")
    @founder_or_admin_only()
    async def template_list(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        templates = await db.list_templates(interaction.guild_id)
        if not templates:
            await interaction.followup.send("ℹ️ No custom templates saved yet. Create one with `/template create`.", ephemeral=True)
            return

        embed = discord.Embed(title="📚 Saved Message Templates", color=0x9B59B6)
        for t in templates:
            preview = t['content'][:100] + "..." if len(t['content']) > 100 else t['content']
            embed.add_field(name=f"🔖 {t['name']}", value=f"```{preview}```", inline=False)

        await interaction.followup.send(embed=embed, ephemeral=True)

    @template_group.command(name="delete", description="Delete a saved template")
    @app_commands.describe(name="Template name to delete")
    @founder_or_admin_only()
    async def template_delete(self, interaction: discord.Interaction, name: str):
        await interaction.response.defer(ephemeral=True)
        deleted = await db.delete_template(interaction.guild_id, name.lower().strip())
        if deleted:
            await interaction.followup.send(f"🗑️ Template **'{name}'** was deleted.", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Template **'{name}'** not found.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))

