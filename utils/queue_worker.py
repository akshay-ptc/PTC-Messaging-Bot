import asyncio
import random
import logging
import json
import os
from typing import Optional, List
import discord
from discord.ext import tasks
from database.db import db
import config

logger = logging.getLogger("ptc_bot.queue_worker")

class SafeDMQueueWorker:
    """
    Robust, rate-limit protected background queue worker for Discord DMs.
    Ensures the bot stays under Discord's anti-spam thresholds, handles HTTP 429 backoff,
    gracefully catches 50007 (Closed DMs), and implements cool-off pauses.
    """
    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.is_running = False
        self.consecutive_errors = 0
        self.processed_in_current_batch = 0

    def start(self):
        if not self.worker_loop.is_running():
            self.worker_loop.start()
            logger.info("Safe DM Queue Worker started.")

    def stop(self):
        if self.worker_loop.is_running():
            self.worker_loop.stop()
            logger.info("Safe DM Queue Worker stopped.")

    @tasks.loop(seconds=1.0)
    async def worker_loop(self):
        # Wait until bot is fully ready
        if not self.bot.is_ready():
            return

        try:
            item = await db.get_next_queue_item()
            if not item:
                # No pending items in queue
                await asyncio.sleep(2.0)
                return

            await self._process_queue_item(item)

        except Exception as e:
            logger.error(f"Unexpected error in DM queue worker loop: {e}", exc_info=True)
            await asyncio.sleep(5.0)

    async def _process_queue_item(self, item: dict):
        queue_id = item["id"]
        campaign_id = item["campaign_id"]
        user_id = item["user_id"]
        guild_id = item["guild_id"]
        content = item.get("content", "")
        title = item.get("title", "PTC Notice")
        attachments_json = item.get("attachments_json", "[]")

        try:
            attachments_list: List[str] = json.loads(attachments_json) if attachments_json else []
        except Exception:
            attachments_list = []

        # 1. Check if user is blacklisted / opted out
        if await db.is_blacklisted(user_id, guild_id):
            logger.info(f"Skipping user {user_id} - blacklisted/opted-out.")
            await db.mark_queue_item_result(queue_id, campaign_id, "failed", "User is on DM Blacklist / Opt-Out")
            return

        # 2. Batch cool-down mechanism to avoid spam detection
        self.processed_in_current_batch += 1
        if self.processed_in_current_batch >= config.DM_BATCH_SIZE:
            logger.info(f"Processed {config.DM_BATCH_SIZE} DMs in batch. Taking a cool-down pause of {config.DM_BATCH_PAUSE_SECONDS}s to keep Discord trust rating high...")
            await asyncio.sleep(config.DM_BATCH_PAUSE_SECONDS)
            self.processed_in_current_batch = 0

        # 3. Fetch user safely
        user = self.bot.get_user(user_id)
        if not user:
            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                logger.warning(f"User {user_id} not found on Discord.")
                await db.mark_queue_item_result(queue_id, campaign_id, "failed", "Discord user not found")
                return
            except discord.HTTPException as e:
                logger.error(f"HTTP error fetching user {user_id}: {e}")
                await db.mark_queue_item_result(queue_id, campaign_id, "failed", f"Fetch user error: {e}")
                return

        # 4. Prepare files/attachments
        discord_files = []
        try:
            for path in attachments_list:
                if os.path.exists(path):
                    discord_files.append(discord.File(path, filename=os.path.basename(path)))
        except Exception as e:
            logger.warning(f"Error loading attachment for campaign {campaign_id}: {e}")

        # 5. Attempt DM delivery with error handling & anti-spam rate limiting
        try:
            # Deliver DM
            await user.send(content=content if content else None, files=discord_files if discord_files else None)
            
            # Success! Reset consecutive errors
            self.consecutive_errors = 0
            await db.mark_queue_item_result(queue_id, campaign_id, "sent")
            logger.info(f"[SUCCESS] Sent DM to user {user} ({user_id}) for campaign #{campaign_id}")

        except discord.Forbidden:
            # Discord Error 50007: Cannot send messages to this user (DMs disabled / bot blocked)
            logger.warning(f"[DM BLOCKED] User {user_id} has closed DMs or blocked the bot.")
            await db.mark_queue_item_result(queue_id, campaign_id, "blocked_dms", "Direct messages closed or bot blocked by user")

        except discord.RateLimited as rl:
            # Discord HTTP 429
            retry_after = getattr(rl, "retry_after", 10.0)
            logger.warning(f"[RATE LIMITED] Discord 429 detected! Backing off for {retry_after + 2.0} seconds.")
            await asyncio.sleep(retry_after + 2.0)
            # Do NOT mark as failed, leave it pending so it retries safely next loop
            return

        except discord.HTTPException as he:
            self.consecutive_errors += 1
            logger.error(f"[HTTP ERROR] Code {he.code} when sending DM to {user_id}: {he.text}")
            await db.mark_queue_item_result(queue_id, campaign_id, "failed", f"HTTP {he.code}: {he.text}")

            # Check consecutive error breaker
            if self.consecutive_errors >= config.MAX_CONSECUTIVE_ERRORS:
                logger.critical(f"Circuit breaker tripped: {self.consecutive_errors} consecutive errors! Pausing campaign #{campaign_id}")
                await db.update_campaign_status(campaign_id, "paused")
                self.consecutive_errors = 0

        except Exception as ex:
            self.consecutive_errors += 1
            logger.error(f"[ERROR] Failed to send DM to {user_id}: {ex}")
            await db.mark_queue_item_result(queue_id, campaign_id, "failed", str(ex))

        # 6. Apply humanized jitter delay between messages
        # Random sleep between DM_MIN_DELAY_SECONDS and DM_MAX_DELAY_SECONDS (e.g. 3.0 to 6.0s)
        jitter = random.uniform(config.DM_MIN_DELAY_SECONDS, config.DM_MAX_DELAY_SECONDS)
        await asyncio.sleep(jitter)

