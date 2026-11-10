import discord
from discord import app_commands
import config
import logging

logger = logging.getLogger("ptc_bot.permissions")

def is_guild_founder_or_admin(interaction: discord.Interaction) -> bool:
    """Check if the user invoking the interaction is Founder/Owner or Administrator."""
    if not interaction.guild:
        return False

    # Check 1: Guild Owner
    if interaction.user.id == interaction.guild.owner_id:
        return True

    # Check 2: Configured Founder ID from environment
    if config.FOUNDER_ID and interaction.user.id == config.FOUNDER_ID:
        return True

    # Check 3: Discord Administrator Permission
    if isinstance(interaction.user, discord.Member):
        if interaction.user.guild_permissions.administrator:
            return True

        # Check 4: Configured Admin Role
        if config.ADMIN_ROLE_ID:
            if any(role.id == config.ADMIN_ROLE_ID for role in interaction.user.roles):
                return True

    return False

def founder_or_admin_only():
    """Slash command check decorator to restrict command execution."""
    async def predicate(interaction: discord.Interaction) -> bool:
        allowed = is_guild_founder_or_admin(interaction)
        if not allowed:
            logger.warning(f"Unauthorized command attempt by {interaction.user} (ID: {interaction.user.id}) in guild {interaction.guild_id}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "⛔ **Access Denied**: This command is restricted to the **Server Founder** and **Administrators** only.",
                    ephemeral=True
                )
            return False
        return True
    return app_commands.check(predicate)

