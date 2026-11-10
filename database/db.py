import aiosqlite
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import config

logger = logging.getLogger("ptc_bot.db")

class Database:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path

    async def init(self):
        """Initialize tables and create indexes."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS guild_settings (
                    guild_id INTEGER PRIMARY KEY,
                    verification_channel_id INTEGER DEFAULT NULL,
                    unverified_role_id INTEGER DEFAULT NULL,
                    verified_role_id INTEGER DEFAULT NULL,
                    reminder_enabled INTEGER DEFAULT 1,
                    initial_delay_hours REAL DEFAULT 24.0,
                    repeat_interval_hours REAL DEFAULT 24.0,
                    verify_message_template TEXT DEFAULT NULL,
                    verify_image_path TEXT DEFAULT NULL,
                    admin_log_channel_id INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS unverified_reminders (
                    user_id INTEGER,
                    guild_id INTEGER,
                    joined_at TIMESTAMP,
                    first_reminder_sent INTEGER DEFAULT 0,
                    last_reminded_at TIMESTAMP DEFAULT NULL,
                    reminder_count INTEGER DEFAULT 0,
                    is_verified INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id)
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS dm_campaigns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    title TEXT,
                    target_type TEXT, -- 'everyone', 'role', 'user'
                    target_id INTEGER DEFAULT NULL,
                    content TEXT,
                    attachments_json TEXT DEFAULT '[]',
                    status TEXT DEFAULT 'pending', -- 'pending', 'running', 'paused', 'completed', 'cancelled'
                    total_targets INTEGER DEFAULT 0,
                    sent_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    blocked_count INTEGER DEFAULT 0,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS campaign_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_id INTEGER,
                    user_id INTEGER,
                    status TEXT DEFAULT 'pending', -- 'pending', 'sent', 'failed', 'blocked_dms'
                    error_message TEXT DEFAULT NULL,
                    processed_at TIMESTAMP DEFAULT NULL,
                    FOREIGN KEY(campaign_id) REFERENCES dm_campaigns(id) ON DELETE CASCADE
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS dm_blacklist (
                    user_id INTEGER,
                    guild_id INTEGER,
                    reason TEXT DEFAULT 'User requested opt-out or admin blacklisted',
                    added_by INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, guild_id)
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS custom_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER,
                    name TEXT,
                    content TEXT,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, name)
                );
            """)

            await db.commit()
            logger.info("Database initialized successfully.")

    # ============================================================
    # Guild Settings CRUD
    # ============================================================

    async def get_settings(self, guild_id: int) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            row = None
            async with db.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
                fetched = await cursor.fetchone()
                if fetched:
                    row = dict(fetched)

            if row:
                return row

            # Insert defaults if not exists (outside cursor context)
            now = datetime.now(timezone.utc).isoformat()
            await db.execute("""
                INSERT INTO guild_settings (guild_id, verify_message_template, verify_image_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (guild_id, config.DEFAULT_VERIFY_TEXT, config.DEFAULT_VERIFY_BANNER, now, now))
            await db.commit()

            async with db.execute("SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)) as cursor:
                fresh = await cursor.fetchone()
                return dict(fresh) if fresh else {}

    async def update_settings(self, guild_id: int, **kwargs) -> Dict[str, Any]:
        valid_fields = [
            "verification_channel_id", "unverified_role_id", "verified_role_id",
            "reminder_enabled", "initial_delay_hours", "repeat_interval_hours",
            "verify_message_template", "verify_image_path", "admin_log_channel_id"
        ]
        updates = []
        values = []
        for key, val in kwargs.items():
            if key in valid_fields:
                updates.append(f"{key} = ?")
                values.append(val)

        if not updates:
            return await self.get_settings(guild_id)

        updates.append("updated_at = ?")
        values.append(datetime.now(timezone.utc).isoformat())
        values.append(guild_id)

        # Ensure record exists first
        await self.get_settings(guild_id)

        async with aiosqlite.connect(self.db_path) as db:
            query = f"UPDATE guild_settings SET {', '.join(updates)} WHERE guild_id = ?"
            await db.execute(query, tuple(values))
            await db.commit()

        return await self.get_settings(guild_id)

    # ============================================================
    # Unverified Reminders CRUD
    # ============================================================

    async def register_member_join(self, user_id: int, guild_id: int, joined_at: datetime):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO unverified_reminders (user_id, guild_id, joined_at, first_reminder_sent)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    joined_at = excluded.joined_at,
                    first_reminder_sent = 1,
                    is_verified = 0
            """, (user_id, guild_id, joined_at.isoformat()))
            await db.commit()

    async def mark_member_verified(self, user_id: int, guild_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE unverified_reminders
                SET is_verified = 1
                WHERE user_id = ? AND guild_id = ?
            """, (user_id, guild_id))
            await db.commit()

    async def record_reminder_sent(self, user_id: int, guild_id: int):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO unverified_reminders (user_id, guild_id, joined_at, first_reminder_sent, last_reminded_at, reminder_count)
                VALUES (?, ?, ?, 1, ?, 1)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    last_reminded_at = excluded.last_reminded_at,
                    reminder_count = reminder_count + 1
            """, (user_id, guild_id, now, now))
            await db.commit()

    async def get_member_reminder_record(self, user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM unverified_reminders WHERE user_id = ? AND guild_id = ?
            """, (user_id, guild_id)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    # ============================================================
    # DM Campaigns CRUD & Queue Management
    # ============================================================

    async def create_campaign(
        self,
        guild_id: int,
        title: str,
        target_type: str,
        target_id: Optional[int],
        content: str,
        attachments: List[str],
        recipient_ids: List[int],
        created_by: int
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO dm_campaigns 
                (guild_id, title, target_type, target_id, content, attachments_json, status, total_targets, created_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
            """, (
                guild_id, title, target_type, target_id, content,
                json.dumps(attachments), len(recipient_ids), created_by, now, now
            ))
            campaign_id = cursor.lastrowid

            # Filter out blacklisted members
            placeholders = ",".join("?" for _ in recipient_ids) if recipient_ids else ""
            blacklisted = set()
            if placeholders:
                async with db.execute(f"SELECT user_id FROM dm_blacklist WHERE guild_id = ? AND user_id IN ({placeholders})", [guild_id] + recipient_ids) as b_cur:
                    rows = await b_cur.fetchall()
                    blacklisted = {r[0] for r in rows}

            queue_items = [
                (campaign_id, uid, 'pending')
                for uid in recipient_ids if uid not in blacklisted
            ]

            if queue_items:
                await db.executemany("""
                    INSERT INTO campaign_queue (campaign_id, user_id, status)
                    VALUES (?, ?, ?)
                """, queue_items)

            # Update count if some were skipped due to blacklist
            await db.execute("UPDATE dm_campaigns SET total_targets = ? WHERE id = ?", (len(queue_items), campaign_id))
            await db.commit()
            return campaign_id

    async def get_campaign(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM dm_campaigns WHERE id = ?", (campaign_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def list_campaigns(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM dm_campaigns 
                WHERE guild_id = ? 
                ORDER BY id DESC LIMIT ?
            """, (guild_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def update_campaign_status(self, campaign_id: int, status: str):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE dm_campaigns SET status = ?, updated_at = ? WHERE id = ?
            """, (status, now, campaign_id))
            await db.commit()

    async def delete_campaign(self, campaign_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM campaign_queue WHERE campaign_id = ?", (campaign_id,))
            cursor = await db.execute("DELETE FROM dm_campaigns WHERE id = ?", (campaign_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def get_next_queue_item(self) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            # Pick next pending item from any running or pending campaign
            async with db.execute("""
                SELECT q.*, c.guild_id, c.content, c.attachments_json, c.title
                FROM campaign_queue q
                JOIN dm_campaigns c ON q.campaign_id = c.id
                WHERE q.status = 'pending' AND c.status IN ('pending', 'running')
                ORDER BY q.id ASC
                LIMIT 1
            """) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def mark_queue_item_result(self, queue_id: int, campaign_id: int, status: str, error_msg: Optional[str] = None):
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE campaign_queue
                SET status = ?, error_message = ?, processed_at = ?
                WHERE id = ?
            """, (status, error_msg, now, queue_id))

            # Update campaign counters
            if status == 'sent':
                await db.execute("UPDATE dm_campaigns SET sent_count = sent_count + 1 WHERE id = ?", (campaign_id,))
            elif status == 'blocked_dms':
                await db.execute("UPDATE dm_campaigns SET blocked_count = blocked_count + 1 WHERE id = ?", (campaign_id,))
            else:
                await db.execute("UPDATE dm_campaigns SET failed_count = failed_count + 1 WHERE id = ?", (campaign_id,))

            # Check if all items in this campaign are finished
            async with db.execute("SELECT COUNT(*) FROM campaign_queue WHERE campaign_id = ? AND status = 'pending'", (campaign_id,)) as c:
                pending_left = (await c.fetchone())[0]

            if pending_left == 0:
                await db.execute("UPDATE dm_campaigns SET status = 'completed', updated_at = ? WHERE id = ?", (now, campaign_id))

            await db.commit()

    # ============================================================
    # Blacklist CRUD (Opt-Out Management)
    # ============================================================

    async def add_to_blacklist(self, user_id: int, guild_id: int, reason: str, added_by: Optional[int]) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO dm_blacklist (user_id, guild_id, reason, added_by)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET
                    reason = excluded.reason,
                    added_by = excluded.added_by
            """, (user_id, guild_id, reason, added_by))
            await db.commit()
            return True

    async def remove_from_blacklist(self, user_id: int, guild_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM dm_blacklist WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
            await db.commit()
            return cursor.rowcount > 0

    async def is_blacklisted(self, user_id: int, guild_id: int) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT 1 FROM dm_blacklist WHERE user_id = ? AND guild_id = ?", (user_id, guild_id)) as cur:
                return (await cur.fetchone()) is not None

    async def list_blacklist(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM dm_blacklist WHERE guild_id = ? ORDER BY created_at DESC LIMIT ?", (guild_id, limit)) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    # ============================================================
    # Custom Templates CRUD
    # ============================================================

    async def create_template(self, guild_id: int, name: str, content: str, created_by: int) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT INTO custom_templates (guild_id, name, content, created_by, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (guild_id, name, content, created_by, now, now))
                await db.commit()
                return True
            except Exception as e:
                logger.error(f"Error creating template: {e}")
                return False

    async def get_template(self, guild_id: int, name: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM custom_templates WHERE guild_id = ? AND name = ?", (guild_id, name)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else None

    async def list_templates(self, guild_id: int) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM custom_templates WHERE guild_id = ? ORDER BY name ASC", (guild_id,)) as cur:
                rows = await cur.fetchall()
                return [dict(r) for r in rows]

    async def update_template(self, guild_id: int, name: str, new_content: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE custom_templates SET content = ?, updated_at = ? WHERE guild_id = ? AND name = ?
            """, (new_content, now, guild_id, name))
            await db.commit()
            return cursor.rowcount > 0

    async def delete_template(self, guild_id: int, name: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM custom_templates WHERE guild_id = ? AND name = ?", (guild_id, name))
            await db.commit()
            return cursor.rowcount > 0


# Global database instance
db = Database()
