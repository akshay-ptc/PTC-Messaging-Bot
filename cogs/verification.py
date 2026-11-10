import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
from database.db import db
from utils.permissions import founder_or_admin_only

logger = logging.getLogger("ptc_bot.verification")

class VerificationCog(commands.Cog, name="Verification"):
    """Handles automated welcome verification DMs and scheduled reminders for unverified members."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.reminder_task.start()

    def cog_unload(self):
        self.reminder_task.cancel()

    # ============================================================
    # Event: on_member_join -> Immediate Welcome DM
    # ============================================================
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if member.bot:
            return

        guild = member.guild
        settings = await db.get_settings(guild.id)
        if not settings.get("reminder_enabled", 1):
            return

        # Anti-spam delay: wait 5 seconds before DMing so Discord doesn't flag automated burst
        await asyncio.sleep(5)

        # Record member join in database
        joined_at = member.joined_at or datetime.now(timezone.utc)
        await db.register_member_join(member.id, guild.id, joined_at)

        # Prepare verification message
        channel_id = settings.get("verification_channel_id") or "verification"
        channel_mention = f"<#{channel_id}>" if isinstance(channel_id, int) or str(channel_id).isdigit() else f"#{channel_id}"
        
        template = settings.get("verify_message_template") or config.DEFAULT_VERIFY_TEXT
        content = template.replace("{channel_id}", str(channel_id)).replace("<#{channel_id}>", channel_mention)

        image_path = settings.get("verify_image_path") or config.DEFAULT_VERIFY_BANNER

        file_attachment = None
        if os.path.exists(image_path):
            file_attachment = discord.File(image_path, filename="verify_instruction.jpg")

        try:
            await member.send(content=content, file=file_attachment)
            logger.info(f"Sent welcome verification DM to new member {member} ({member.id})")
        except discord.Forbidden:
            logger.warning(f"Could not send welcome DM to {member} ({member.id}) - DMs are closed.")
        except Exception as e:
            logger.error(f"Error sending welcome DM to {member}: {e}")

    # ============================================================
    # Event: on_member_update -> Auto Mark Verified
    # ============================================================
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        settings = await db.get_settings(after.guild.id)
        verified_role_id = settings.get("verified_role_id")
        unverified_role_id = settings.get("unverified_role_id")

        # If member gained verified role or lost unverified role
        if verified_role_id:
            had_verified = any(r.id == verified_role_id for r in before.roles)
            has_verified = any(r.id == verified_role_id for r in after.roles)
            if not had_verified and has_verified:
                await db.mark_member_verified(after.id, after.guild.id)
                logger.info(f"Member {after} verified! Stopped unverified reminders.")

        if unverified_role_id:
            had_unverified = any(r.id == unverified_role_id for r in before.roles)
            has_unverified = any(r.id == unverified_role_id for r in after.roles)
            if had_unverified and not has_unverified:
                await db.mark_member_verified(after.id, after.guild.id)
                logger.info(f"Member {after} unverified role removed! Marked verified.")

    # ============================================================
    # Background Scheduled Task: Remind Unverified Members
    # ============================================================
    @tasks.loop(minutes=20.0)
    async def reminder_task(self):
        """Checks for unverified members who need a reminder after initial delay & every interval."""
        if not self.bot.is_ready():
            return

        for guild in self.bot.guilds:
            try:
                settings = await db.get_settings(guild.id)
                if not settings.get("reminder_enabled", 1):
                    continue

                unverified_role_id = settings.get("unverified_role_id")
                initial_delay_hours = float(settings.get("initial_delay_hours", 24.0))
                repeat_interval_hours = float(settings.get("repeat_interval_hours", 24.0))
                channel_id = settings.get("verification_channel_id") or "verification"
                channel_mention = f"<#{channel_id}>" if isinstance(channel_id, int) or str(channel_id).isdigit() else f"#{channel_id}"

                template = settings.get("verify_message_template") or config.DEFAULT_VERIFY_TEXT
                content = template.replace("{channel_id}", str(channel_id)).replace("<#{channel_id}>", channel_mention)
                image_path = settings.get("verify_image_path") or config.DEFAULT_VERIFY_BANNER

                now = datetime.now(timezone.utc)

                # Find unverified target members
                target_members = []
                if unverified_role_id:
                    role = guild.get_role(unverified_role_id)
                    if role:
                        target_members = [m for m in role.members if not m.bot]
                else:
                    # If unverified role is not configured, check members without verified role if configured
                    verified_role_id = settings.get("verified_role_id")
                    if verified_role_id:
                        target_members = [m for m in guild.members if not m.bot and not any(r.id == verified_role_id for r in m.roles)]

                for member in target_members:
                    # Check database record
                    rec = await db.get_member_reminder_record(member.id, guild.id)
                    if rec and rec.get("is_verified"):
                        continue

                    # Determine joined time
                    joined_time = member.joined_at or now
                    time_in_server = now - joined_time

                    # Has the initial delay passed? (e.g. 24 hours / 1 day)
                    if time_in_server < timedelta(hours=initial_delay_hours):
                        continue

                    # Check when last reminded
                    last_reminded_str = rec.get("last_reminded_at") if rec else None
                    if last_reminded_str:
                        last_reminded = datetime.fromisoformat(last_reminded_str)
                        if last_reminded.tzinfo is None:
                            last_reminded = last_reminded.replace(tzinfo=timezone.utc)
                        time_since_last_remind = now - last_reminded
                        # Check if repeat interval has passed (e.g. 24 hours)
                        if time_since_last_remind < timedelta(hours=repeat_interval_hours):
                            continue

                    # Member qualifies for reminder!
                    # Check blacklist / opt-out
                    if await db.is_blacklisted(member.id, guild.id):
                        continue

                    # Send with rate limit protection
                    file_att = None
                    if os.path.exists(image_path):
                        file_att = discord.File(image_path, filename="verify_instruction.jpg")

                    try:
                        await member.send(content=content, file=file_att)
                        await db.record_reminder_sent(member.id, guild.id)
                        logger.info(f"Dispatched scheduled unverified reminder to {member} ({member.id})")
                        # Anti-spam delay between individual reminder DMs
                        await asyncio.sleep(4.0)
                    except discord.Forbidden:
                        logger.warning(f"Could not send reminder DM to {member} (DMs closed).")
                        await db.record_reminder_sent(member.id, guild.id)
                        await asyncio.sleep(2.0)
                    except discord.RateLimited as rl:
                        wait_sec = getattr(rl, "retry_after", 10.0)
                        logger.warning(f"Rate limited during reminder task. Sleeping {wait_sec + 2}s")
                        await asyncio.sleep(wait_sec + 2.0)
                        break
                    except Exception as e:
                        logger.error(f"Error dispatching reminder DM to {member}: {e}")
                        await asyncio.sleep(3.0)

            except Exception as e:
                logger.error(f"Error running verification reminder task for guild {guild.id}: {e}", exc_info=True)

    @reminder_task.before_loop
    async def before_reminder_task(self):
        await self.bot.wait_until_ready()

    # ============================================================
    # Slash Commands for Founder / Admins
    # ============================================================
    verify_group = app_commands.Group(
        name="verify",
        description="Verification DM and reminder controls (Admins & Founder only)",
        default_permissions=discord.Permissions(administrator=True)
    )

    @verify_group.command(name="preview", description="Send a preview of the verification DM to yourself")
    @founder_or_admin_only()
    async def verify_preview(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        settings = await db.get_settings(interaction.guild_id)

        channel_id = settings.get("verification_channel_id") or "verification"
        channel_mention = f"<#{channel_id}>" if isinstance(channel_id, int) or str(channel_id).isdigit() else f"#{channel_id}"
        
        template = settings.get("verify_message_template") or config.DEFAULT_VERIFY_TEXT
        content = template.replace("{channel_id}", str(channel_id)).replace("<#{channel_id}>", channel_mention)
        image_path = settings.get("verify_image_path") or config.DEFAULT_VERIFY_BANNER

        file_attachment = None
        if os.path.exists(image_path):
            file_attachment = discord.File(image_path, filename="verify_instruction.jpg")

        try:
            await interaction.user.send(content=content, file=file_attachment)
            await interaction.followup.send("✅ Preview verification message has been sent to your DMs!", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("❌ Could not send preview DM. Please enable direct messages from server members in your Privacy & Safety settings.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to send preview: {e}", ephemeral=True)

    @verify_group.command(name="status", description="View current verification setup and unverified member count")
    @founder_or_admin_only()
    async def verify_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        settings = await db.get_settings(interaction.guild_id)

        v_channel = f"<#{settings.get('verification_channel_id')}>" if settings.get('verification_channel_id') else "Not Configured"
        unverified_role = interaction.guild.get_role(settings.get("unverified_role_id")) if settings.get("unverified_role_id") else None
        verified_role = interaction.guild.get_role(settings.get("verified_role_id")) if settings.get("verified_role_id") else None

        unverified_count = len(unverified_role.members) if unverified_role else "Role not set"

        embed = discord.Embed(
            title="🛡️ PTC Verification & Reminder Status",
            color=0x00A8FF,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Auto-Reminder Status", value="🟢 **Enabled**" if settings.get("reminder_enabled") else "🔴 **Disabled**", inline=True)
        embed.add_field(name="Verification Channel", value=v_channel, inline=True)
        embed.add_field(name="Unverified Role", value=unverified_role.mention if unverified_role else "None", inline=True)
        embed.add_field(name="Verified Role", value=verified_role.mention if verified_role else "None", inline=True)
        embed.add_field(name="Currently Unverified", value=f"**{unverified_count}** members", inline=True)
        embed.add_field(name="Schedule Timing", value=f"Initial Delay: **{settings.get('initial_delay_hours')}h** (1 day)\nRepeat Every: **{settings.get('repeat_interval_hours')}h**", inline=False)
        embed.set_footer(text="PTC Security Bot • Prop Traders Community")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @verify_group.command(name="trigger_reminders", description="Immediately trigger a reminder cycle for all unverified members")
    @founder_or_admin_only()
    async def trigger_reminders(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # Run reminder pass in background
        asyncio.create_task(self.reminder_task())
        await interaction.followup.send("🚀 **Reminder cycle dispatched in background!** Unverified members will be reminded safely under anti-spam rate limits.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(VerificationCog(bot))

