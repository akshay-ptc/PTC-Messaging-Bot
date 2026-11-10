import re
import os
import shutil
import aiohttp
import logging
from typing import Optional, List
import discord
from discord import app_commands
from discord.ext import commands

import config
from database.db import db
from utils.permissions import founder_or_admin_only

logger = logging.getLogger("ptc_bot.broadcast")

DISCORD_MSG_LINK_REGEX = re.compile(
    r"https?://(?:canary\.|ptb\.)?discord(?:app)?\.com/channels/(?P<guild_id>\d+)/(?P<channel_id>\d+)/(?P<message_id>\d+)"
)


class BroadcastConfirmView(discord.ui.View):
    """
    Interactive confirmation View requiring the admin/founder to explicitly
    click 'Confirm & Send' (Yes) or 'Cancel Broadcast' (No) after reviewing
    the preview of the DM and its attachments.
    """
    def __init__(
        self,
        author_id: int,
        guild_id: int,
        title: str,
        target_type: str,
        target_id: Optional[int],
        content: str,
        attachments: List[str],
        recipient_ids: List[int],
        target_label: str,
        temp_dir: Optional[str] = None,
        timeout: float = 120.0
    ):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.guild_id = guild_id
        self.title = title
        self.target_type = target_type
        self.target_id = target_id
        self.content = content
        self.attachments = attachments
        self.recipient_ids = recipient_ids
        self.target_label = target_label
        self.temp_dir = temp_dir
        self.message: Optional[discord.WebhookMessage] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "⛔ Only the administrator who initiated this broadcast can confirm or cancel it.",
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Confirm & Send DMs", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True

        # Enqueue campaign into SQLite database
        campaign_id = await db.create_campaign(
            guild_id=self.guild_id,
            title=self.title,
            target_type=self.target_type,
            target_id=self.target_id,
            content=self.content,
            attachments=self.attachments,
            recipient_ids=self.recipient_ids,
            created_by=self.author_id
        )

        est_seconds = len(self.recipient_ids) * 4.5
        est_minutes = round(est_seconds / 60, 1)

        embed = discord.Embed(
            title="🚀 Broadcast Confirmed & Enqueued!",
            color=0x00FF88,
            description="Your message has been scheduled and is now being dispatched safely through the anti-spam rate limiter."
        )
        embed.add_field(name="Campaign ID", value=f"`#{campaign_id}`", inline=True)
        embed.add_field(name="Target Audience", value=self.target_label, inline=True)
        embed.add_field(name="Total Recipients", value=f"**{len(self.recipient_ids)}** members", inline=True)
        embed.add_field(name="Attachments", value=f"{len(self.attachments)} file(s)", inline=True)
        embed.add_field(name="Est. Completion Time", value=f"~{est_minutes} min (Safe Mode)", inline=True)
        embed.add_field(name="Anti-Spam Safety", value="🛡️ Jitter delay (3-6s) + 429 auto-backoff active", inline=False)
        embed.set_footer(text=f"Use /campaign status {campaign_id} to monitor progress in real-time.")

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Cancel Broadcast", style=discord.ButtonStyle.danger, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True

        # Clean up temporary uploaded/downloaded files
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception as e:
                logger.warning(f"Error removing temp_dir {self.temp_dir}: {e}")

        embed = discord.Embed(
            title="🛑 Broadcast Cancelled",
            description="You cancelled this broadcast. **No direct messages were sent**, and temporary files have been deleted.",
            color=0xE74C3C
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

        if self.message:
            try:
                timeout_embed = discord.Embed(
                    title="⏳ Confirmation Timed Out",
                    description="Confirmation took longer than 2 minutes. The broadcast was **automatically cancelled** and no DMs were sent.",
                    color=0x95A5A6
                )
                await self.message.edit(embed=timeout_embed, view=self)
            except Exception:
                pass


class BroadcastCog(commands.Cog, name="Broadcast"):
    """Handles mass DM broadcasts and cloning messages from server links into user DMs with confirmation preview."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    dm_group = app_commands.Group(
        name="dm",
        description="DM broadcast tools (Founder & Admin Only)",
        default_permissions=discord.Permissions(administrator=True)
    )

    # ============================================================
    # Command 1: /dm send (Custom text & up to 3 attachments)
    # ============================================================
    @dm_group.command(name="send", description="Send a custom DM with optional attachments to all, role, or user")
    @app_commands.describe(
        target_type="Send to: All Server Members, Specific Role, or Specific User",
        message="The message content to deliver",
        role="The target role (if target_type is Role)",
        user="The target user (if target_type is User)",
        image_1="Optional first image/file attachment",
        image_2="Optional second image/file attachment",
        image_3="Optional third image/file attachment"
    )
    @app_commands.choices(target_type=[
        app_commands.Choice(name="Every Member (@everyone)", value="all"),
        app_commands.Choice(name="Specific Role", value="role"),
        app_commands.Choice(name="Specific User", value="user"),
    ])
    @founder_or_admin_only()
    async def dm_send(
        self,
        interaction: discord.Interaction,
        target_type: app_commands.Choice[str],
        message: str,
        role: Optional[discord.Role] = None,
        user: Optional[discord.Member] = None,
        image_1: Optional[discord.Attachment] = None,
        image_2: Optional[discord.Attachment] = None,
        image_3: Optional[discord.Attachment] = None,
    ):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # 1. Resolve recipients
        recipients = await self._resolve_recipients(guild, target_type.value, role, user)
        if not recipients:
            await interaction.followup.send("❌ No valid members found for the selected target.", ephemeral=True)
            return

        # 2. Save attachments locally so admin can preview and worker can deliver
        saved_files = []
        campaign_temp_dir = config.BASE_DIR / "temp_attachments" / f"upload_{interaction.id}"
        os.makedirs(campaign_temp_dir, exist_ok=True)

        for i, att in enumerate([image_1, image_2, image_3], start=1):
            if att:
                file_dest = campaign_temp_dir / f"att_{i}_{att.filename}"
                await att.save(str(file_dest))
                saved_files.append(str(file_dest))

        target_label = "All Server Members (@everyone)" if target_type.value == "all" else (role.name if role else str(user))
        est_seconds = len(recipients) * 4.5
        est_minutes = round(est_seconds / 60, 1)

        # 3. Build Preview Embed
        preview_embed = discord.Embed(
            title="🔍 Broadcast Confirmation & Message Preview",
            description="Please review the message details below before confirming dispatch.\n**No DMs will be sent until you click 'Confirm & Send DMs'.**",
            color=0xF39C12
        )
        preview_embed.add_field(name="🎯 Target Audience", value=target_label, inline=True)
        preview_embed.add_field(name="👥 Total Recipients", value=f"**{len(recipients)}** members", inline=True)
        preview_embed.add_field(name="⏱️ Est. Delivery Time", value=f"~{est_minutes} min (Anti-Spam Mode)", inline=True)

        att_summary = ", ".join(os.path.basename(p) for p in saved_files) if saved_files else "*None*"
        preview_embed.add_field(name="📎 Attached Files", value=att_summary, inline=False)

        preview_text = message[:900] + ("..." if len(message) > 900 else "")
        preview_embed.add_field(
            name="📝 Message Content Preview",
            value=f">>> {preview_text}",
            inline=False
        )
        preview_embed.set_footer(text="Anti-Spam Shield Ready • Confirmation auto-expires in 2 minutes")

        # 4. Attach files so admin can inspect preview in Discord
        preview_files = [discord.File(p, filename=os.path.basename(p)) for p in saved_files]

        # 5. Create Interactive View
        view = BroadcastConfirmView(
            author_id=interaction.user.id,
            guild_id=guild.id,
            title=f"DM Broadcast to {target_label}",
            target_type=target_type.value,
            target_id=role.id if role else (user.id if user else None),
            content=message,
            attachments=saved_files,
            recipient_ids=[m.id for m in recipients],
            target_label=target_label,
            temp_dir=str(campaign_temp_dir)
        )

        sent_msg = await interaction.followup.send(
            embed=preview_embed,
            files=preview_files if preview_files else None,
            view=view,
            ephemeral=True
        )
        view.message = sent_msg

    # ============================================================
    # Command 2: /dm from_link (Fetch message from link & mirror to DMs)
    # ============================================================
    @dm_group.command(name="from_link", description="Clone and send an existing Discord message with attachments to DMs")
    @app_commands.describe(
        message_link="The link to the Discord message (Copy Message Link)",
        target_type="Send to: All Server Members, Specific Role, or Specific User",
        role="The target role (if target_type is Role)",
        user="The target user (if target_type is User)"
    )
    @app_commands.choices(target_type=[
        app_commands.Choice(name="Every Member (@everyone)", value="all"),
        app_commands.Choice(name="Specific Role", value="role"),
        app_commands.Choice(name="Specific User", value="user"),
    ])
    @founder_or_admin_only()
    async def dm_from_link(
        self,
        interaction: discord.Interaction,
        message_link: str,
        target_type: app_commands.Choice[str],
        role: Optional[discord.Role] = None,
        user: Optional[discord.Member] = None,
    ):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # 1. Parse message link
        match = DISCORD_MSG_LINK_REGEX.match(message_link.strip())
        if not match:
            await interaction.followup.send(
                "❌ **Invalid Message Link format!**\nPlease right-click the message in Discord and click **'Copy Message Link'**.\n"
                "Example: `https://discord.com/channels/12345/67890/98765`",
                ephemeral=True
            )
            return

        source_guild_id = int(match.group("guild_id"))
        source_channel_id = int(match.group("channel_id"))
        source_message_id = int(match.group("message_id"))

        if source_guild_id != guild.id:
            await interaction.followup.send("⚠️ The linked message must be from this Discord server.", ephemeral=True)
            return

        # 2. Fetch the target message
        channel = guild.get_channel(source_channel_id)
        if not channel:
            try:
                channel = await guild.fetch_channel(source_channel_id)
            except Exception:
                await interaction.followup.send("❌ Could not access the channel where the message is located.", ephemeral=True)
                return

        try:
            fetched_msg = await channel.fetch_message(source_message_id)
        except discord.NotFound:
            await interaction.followup.send("❌ Message not found. It may have been deleted.", ephemeral=True)
            return
        except discord.Forbidden:
            await interaction.followup.send("❌ Bot lacks permission to read that channel.", ephemeral=True)
            return

        # 3. Download attachments from the source message
        saved_files = []
        temp_dir = config.BASE_DIR / "temp_attachments" / f"msg_{source_message_id}"
        if fetched_msg.attachments:
            os.makedirs(temp_dir, exist_ok=True)
            async with aiohttp.ClientSession() as session:
                for i, att in enumerate(fetched_msg.attachments, start=1):
                    file_path = temp_dir / f"cloned_{i}_{att.filename}"
                    async with session.get(att.url) as resp:
                        if resp.status == 200:
                            with open(file_path, "wb") as f:
                                f.write(await resp.read())
                            saved_files.append(str(file_path))

        msg_content = fetched_msg.content or ""
        if not msg_content and not saved_files and fetched_msg.embeds:
            emb = fetched_msg.embeds[0]
            msg_content = f"**{emb.title or 'PTC Announcement'}**\n\n{emb.description or ''}"

        # 4. Resolve target members
        recipients = await self._resolve_recipients(guild, target_type.value, role, user)
        if not recipients:
            await interaction.followup.send("❌ No valid members found for the selected target.", ephemeral=True)
            return

        target_label = "All Server Members (@everyone)" if target_type.value == "all" else (role.name if role else str(user))
        est_seconds = len(recipients) * 4.5
        est_minutes = round(est_seconds / 60, 1)

        # 5. Build Preview Embed
        preview_embed = discord.Embed(
            title="🔍 Cloned Message Confirmation & Preview",
            description=f"Extracted message from {channel.mention}.\n**Review below and click 'Confirm & Send DMs' to start dispatching.**",
            color=0xF39C12
        )
        preview_embed.add_field(name="🎯 Target Audience", value=target_label, inline=True)
        preview_embed.add_field(name="👥 Total Recipients", value=f"**{len(recipients)}** members", inline=True)
        preview_embed.add_field(name="⏱️ Est. Delivery Time", value=f"~{est_minutes} min (Anti-Spam Mode)", inline=True)

        att_summary = ", ".join(os.path.basename(p) for p in saved_files) if saved_files else "*None*"
        preview_embed.add_field(name="📎 Cloned Attachments", value=f"{len(saved_files)} file(s) ({att_summary})", inline=False)

        preview_text = msg_content[:900] + ("..." if len(msg_content) > 900 else "") if msg_content else "*(Attachments only)*"
        preview_embed.add_field(
            name="📝 Message Content Preview",
            value=f">>> {preview_text}",
            inline=False
        )
        preview_embed.set_footer(text="Anti-Spam Shield Ready • Confirmation auto-expires in 2 minutes")

        preview_files = [discord.File(p, filename=os.path.basename(p)) for p in saved_files]

        # 6. Create Interactive View
        view = BroadcastConfirmView(
            author_id=interaction.user.id,
            guild_id=guild.id,
            title=f"Cloned Message Broadcast from #{channel.name}",
            target_type=target_type.value,
            target_id=role.id if role else (user.id if user else None),
            content=msg_content,
            attachments=saved_files,
            recipient_ids=[m.id for m in recipients],
            target_label=target_label,
            temp_dir=str(temp_dir) if saved_files else None
        )

        sent_msg = await interaction.followup.send(
            embed=preview_embed,
            files=preview_files if preview_files else None,
            view=view,
            ephemeral=True
        )
        view.message = sent_msg

    # ============================================================
    # Helper to resolve recipients
    # ============================================================
    async def _resolve_recipients(
        self,
        guild: discord.Guild,
        target_type: str,
        role: Optional[discord.Role],
        user: Optional[discord.Member]
    ) -> List[discord.Member]:
        if target_type == "user":
            return [user] if user and not user.bot else []

        if target_type == "role":
            if not role:
                return []
            return [m for m in role.members if not m.bot]

        # Target: All members
        if not guild.chunked:
            try:
                await guild.chunk()
            except Exception:
                pass
        return [m for m in guild.members if not m.bot]


async def setup(bot: commands.Bot):
    await bot.add_cog(BroadcastCog(bot))
