import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import config

logger = logging.getLogger("ptc_bot.db")


class JSONDatabase:
    """
    Robust, thread-safe asynchronous JSON database.
    Provides complete CRUD capabilities, atomic disk persistence, and instant backup/restore.
    """
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        self._lock = asyncio.Lock()
        self.data: Dict[str, Any] = {
            "version": "2.0.0",
            "_meta": {
                "next_campaign_id": 1,
                "next_queue_id": 1,
                "next_template_id": 1
            },
            "guild_settings": {},
            "unverified_reminders": {},
            "dm_campaigns": {},
            "campaign_queue": [],
            "dm_blacklist": {},
            "custom_templates": {}
        }

    async def init(self):
        """Load database from JSON file or create initial database file if it does not exist."""
        async with self._lock:
            if os.path.exists(self.db_path):
                try:
                    with open(self.db_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        self.data.update(loaded)
                    logger.info(f"Loaded JSON database from {self.db_path}")
                except Exception as e:
                    logger.error(f"Error loading JSON database: {e}. Reinitializing with defaults.", exc_info=True)
                    self._save_to_disk()
            else:
                os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
                self._save_to_disk()
                logger.info(f"Created new JSON database file at {self.db_path}")

    def _save_to_disk(self):
        """Atomic write to disk to ensure zero file corruption."""
        temp_path = f"{self.db_path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.db_path)
        except Exception as e:
            logger.error(f"Failed to atomically write JSON database: {e}", exc_info=True)
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

    # ============================================================
    # Guild Settings CRUD
    # ============================================================

    async def get_settings(self, guild_id: int) -> Dict[str, Any]:
        async with self._lock:
            g_key = str(guild_id)
            if g_key in self.data["guild_settings"]:
                return dict(self.data["guild_settings"][g_key])

            # Insert default settings
            now = datetime.now(timezone.utc).isoformat()
            default_settings = {
                "guild_id": guild_id,
                "verification_channel_id": None,
                "unverified_role_id": None,
                "verified_role_id": None,
                "reminder_enabled": 1,
                "initial_delay_hours": 24.0,
                "repeat_interval_hours": 24.0,
                "verify_message_template": config.DEFAULT_VERIFY_TEXT,
                "verify_image_path": config.DEFAULT_VERIFY_BANNER,
                "admin_log_channel_id": None,
                "created_at": now,
                "updated_at": now
            }
            self.data["guild_settings"][g_key] = default_settings
            self._save_to_disk()
            return dict(default_settings)

    async def update_settings(self, guild_id: int, **kwargs) -> Dict[str, Any]:
        async with self._lock:
            g_key = str(guild_id)
            if g_key not in self.data["guild_settings"]:
                now = datetime.now(timezone.utc).isoformat()
                self.data["guild_settings"][g_key] = {
                    "guild_id": guild_id,
                    "verification_channel_id": None,
                    "unverified_role_id": None,
                    "verified_role_id": None,
                    "reminder_enabled": 1,
                    "initial_delay_hours": 24.0,
                    "repeat_interval_hours": 24.0,
                    "verify_message_template": config.DEFAULT_VERIFY_TEXT,
                    "verify_image_path": config.DEFAULT_VERIFY_BANNER,
                    "admin_log_channel_id": None,
                    "created_at": now,
                    "updated_at": now
                }

            valid_fields = [
                "verification_channel_id", "unverified_role_id", "verified_role_id",
                "reminder_enabled", "initial_delay_hours", "repeat_interval_hours",
                "verify_message_template", "verify_image_path", "admin_log_channel_id"
            ]
            changed = False
            for key, val in kwargs.items():
                if key in valid_fields:
                    self.data["guild_settings"][g_key][key] = val
                    changed = True

            if changed:
                self.data["guild_settings"][g_key]["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_to_disk()

            return dict(self.data["guild_settings"][g_key])

    # ============================================================
    # Unverified Reminders CRUD
    # ============================================================

    async def register_member_join(self, user_id: int, guild_id: int, joined_at: datetime):
        async with self._lock:
            key = f"{guild_id}_{user_id}"
            now_iso = joined_at.isoformat() if hasattr(joined_at, "isoformat") else str(joined_at)
            if key in self.data["unverified_reminders"]:
                self.data["unverified_reminders"][key]["joined_at"] = now_iso
                self.data["unverified_reminders"][key]["first_reminder_sent"] = 1
                self.data["unverified_reminders"][key]["is_verified"] = 0
            else:
                self.data["unverified_reminders"][key] = {
                    "user_id": user_id,
                    "guild_id": guild_id,
                    "joined_at": now_iso,
                    "first_reminder_sent": 1,
                    "last_reminded_at": None,
                    "reminder_count": 0,
                    "is_verified": 0
                }
            self._save_to_disk()

    async def mark_member_verified(self, user_id: int, guild_id: int):
        async with self._lock:
            key = f"{guild_id}_{user_id}"
            if key in self.data["unverified_reminders"]:
                self.data["unverified_reminders"][key]["is_verified"] = 1
                self._save_to_disk()

    async def record_reminder_sent(self, user_id: int, guild_id: int):
        async with self._lock:
            key = f"{guild_id}_{user_id}"
            now = datetime.now(timezone.utc).isoformat()
            if key in self.data["unverified_reminders"]:
                self.data["unverified_reminders"][key]["last_reminded_at"] = now
                self.data["unverified_reminders"][key]["reminder_count"] += 1
            else:
                self.data["unverified_reminders"][key] = {
                    "user_id": user_id,
                    "guild_id": guild_id,
                    "joined_at": now,
                    "first_reminder_sent": 1,
                    "last_reminded_at": now,
                    "reminder_count": 1,
                    "is_verified": 0
                }
            self._save_to_disk()

    async def get_member_reminder_record(self, user_id: int, guild_id: int) -> Optional[Dict[str, Any]]:
        async with self._lock:
            key = f"{guild_id}_{user_id}"
            rec = self.data["unverified_reminders"].get(key)
            return dict(rec) if rec else None

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
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            campaign_id = self.data["_meta"]["next_campaign_id"]
            self.data["_meta"]["next_campaign_id"] += 1

            filtered_recipients = [
                uid for uid in recipient_ids
                if f"{guild_id}_{uid}" not in self.data["dm_blacklist"]
            ]

            campaign_record = {
                "id": campaign_id,
                "guild_id": guild_id,
                "title": title,
                "target_type": target_type,
                "target_id": target_id,
                "content": content,
                "attachments_json": json.dumps(attachments),
                "status": "pending",
                "total_targets": len(filtered_recipients),
                "sent_count": 0,
                "failed_count": 0,
                "blocked_count": 0,
                "created_by": created_by,
                "created_at": now,
                "updated_at": now
            }
            self.data["dm_campaigns"][str(campaign_id)] = campaign_record

            for uid in filtered_recipients:
                q_id = self.data["_meta"]["next_queue_id"]
                self.data["_meta"]["next_queue_id"] += 1
                self.data["campaign_queue"].append({
                    "id": q_id,
                    "campaign_id": campaign_id,
                    "user_id": uid,
                    "status": "pending",
                    "error_message": None,
                    "processed_at": None
                })

            self._save_to_disk()
            return campaign_id

    async def get_campaign(self, campaign_id: int) -> Optional[Dict[str, Any]]:
        async with self._lock:
            camp = self.data["dm_campaigns"].get(str(campaign_id))
            return dict(camp) if camp else None

    async def list_campaigns(self, guild_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        async with self._lock:
            matching = [
                dict(c) for c in self.data["dm_campaigns"].values()
                if c.get("guild_id") == guild_id
            ]
            matching.sort(key=lambda x: x["id"], reverse=True)
            return matching[:limit]

    async def update_campaign_status(self, campaign_id: int, status: str):
        async with self._lock:
            c_key = str(campaign_id)
            if c_key in self.data["dm_campaigns"]:
                self.data["dm_campaigns"][c_key]["status"] = status
                self.data["dm_campaigns"][c_key]["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_to_disk()

    async def delete_campaign(self, campaign_id: int) -> bool:
        async with self._lock:
            c_key = str(campaign_id)
            if c_key in self.data["dm_campaigns"]:
                del self.data["dm_campaigns"][c_key]
                self.data["campaign_queue"] = [
                    q for q in self.data["campaign_queue"]
                    if q["campaign_id"] != campaign_id
                ]
                self._save_to_disk()
                return True
            return False

    async def get_next_queue_item(self) -> Optional[Dict[str, Any]]:
        async with self._lock:
            for item in self.data["campaign_queue"]:
                if item["status"] == "pending":
                    campaign_id = item["campaign_id"]
                    camp = self.data["dm_campaigns"].get(str(campaign_id))
                    if camp and camp["status"] in ("pending", "running"):
                        return {
                            **item,
                            "guild_id": camp["guild_id"],
                            "content": camp["content"],
                            "attachments_json": camp["attachments_json"],
                            "title": camp["title"]
                        }
            return None

    async def mark_queue_item_result(self, queue_id: int, campaign_id: int, status: str, error_msg: Optional[str] = None):
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            for item in self.data["campaign_queue"]:
                if item["id"] == queue_id:
                    item["status"] = status
                    item["error_message"] = error_msg
                    item["processed_at"] = now
                    break

            c_key = str(campaign_id)
            if c_key in self.data["dm_campaigns"]:
                camp = self.data["dm_campaigns"][c_key]
                if status == "sent":
                    camp["sent_count"] += 1
                elif status == "blocked_dms":
                    camp["blocked_count"] += 1
                else:
                    camp["failed_count"] += 1

                has_pending = any(
                    q["campaign_id"] == campaign_id and q["status"] == "pending"
                    for q in self.data["campaign_queue"]
                )
                if not has_pending:
                    camp["status"] = "completed"
                    camp["updated_at"] = now

            self._save_to_disk()

    # ============================================================
    # Blacklist CRUD (Opt-Out Management)
    # ============================================================

    async def add_to_blacklist(self, user_id: int, guild_id: int, reason: str, added_by: Optional[int]) -> bool:
        async with self._lock:
            key = f"{guild_id}_{user_id}"
            now = datetime.now(timezone.utc).isoformat()
            self.data["dm_blacklist"][key] = {
                "user_id": user_id,
                "guild_id": guild_id,
                "reason": reason,
                "added_by": added_by,
                "created_at": now
            }
            self._save_to_disk()
            return True

    async def remove_from_blacklist(self, user_id: int, guild_id: int) -> bool:
        async with self._lock:
            key = f"{guild_id}_{user_id}"
            if key in self.data["dm_blacklist"]:
                del self.data["dm_blacklist"][key]
                self._save_to_disk()
                return True
            return False

    async def is_blacklisted(self, user_id: int, guild_id: int) -> bool:
        async with self._lock:
            key = f"{guild_id}_{user_id}"
            return key in self.data["dm_blacklist"]

    async def list_blacklist(self, guild_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        async with self._lock:
            matching = [
                dict(v) for v in self.data["dm_blacklist"].values()
                if v.get("guild_id") == guild_id
            ]
            matching.sort(key=lambda x: x["created_at"], reverse=True)
            return matching[:limit]

    # ============================================================
    # Custom Templates CRUD
    # ============================================================

    async def create_template(self, guild_id: int, name: str, content: str, created_by: int) -> bool:
        async with self._lock:
            key = f"{guild_id}_{name.lower().strip()}"
            if key in self.data["custom_templates"]:
                return False

            now = datetime.now(timezone.utc).isoformat()
            t_id = self.data["_meta"]["next_template_id"]
            self.data["_meta"]["next_template_id"] += 1

            self.data["custom_templates"][key] = {
                "id": t_id,
                "guild_id": guild_id,
                "name": name.lower().strip(),
                "content": content,
                "created_by": created_by,
                "created_at": now,
                "updated_at": now
            }
            self._save_to_disk()
            return True

    async def get_template(self, guild_id: int, name: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            key = f"{guild_id}_{name.lower().strip()}"
            tmpl = self.data["custom_templates"].get(key)
            return dict(tmpl) if tmpl else None

    async def list_templates(self, guild_id: int) -> List[Dict[str, Any]]:
        async with self._lock:
            matching = [
                dict(v) for v in self.data["custom_templates"].values()
                if v.get("guild_id") == guild_id
            ]
            matching.sort(key=lambda x: x["name"])
            return matching

    async def update_template(self, guild_id: int, name: str, new_content: str) -> bool:
        async with self._lock:
            key = f"{guild_id}_{name.lower().strip()}"
            if key in self.data["custom_templates"]:
                self.data["custom_templates"][key]["content"] = new_content
                self.data["custom_templates"][key]["updated_at"] = datetime.now(timezone.utc).isoformat()
                self._save_to_disk()
                return True
            return False

    async def delete_template(self, guild_id: int, name: str) -> bool:
        async with self._lock:
            key = f"{guild_id}_{name.lower().strip()}"
            if key in self.data["custom_templates"]:
                del self.data["custom_templates"][key]
                self._save_to_disk()
                return True
            return False

    # ============================================================
    # Backup & Restore Methods
    # ============================================================

    async def create_backup_file(self, backup_dir: Optional[str] = None) -> str:
        """Create a standalone JSON backup file and return its path."""
        async with self._lock:
            target_dir = backup_dir or os.path.join(os.path.dirname(os.path.abspath(self.db_path)), "backups")
            os.makedirs(target_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(target_dir, f"PTC_Bot_Backup_{timestamp}.json")

            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)

            logger.info(f"Database backup created: {backup_path}")
            return backup_path

    async def restore_from_json(self, json_data_or_path) -> bool:
        """Restore entire database from a JSON dict or JSON file path."""
        async with self._lock:
            try:
                if isinstance(json_data_or_path, str):
                    if os.path.exists(json_data_or_path):
                        with open(json_data_or_path, "r", encoding="utf-8") as f:
                            imported = json.load(f)
                    else:
                        imported = json.loads(json_data_or_path)
                elif isinstance(json_data_or_path, dict):
                    imported = json_data_or_path
                else:
                    return False

                required_keys = ["guild_settings", "unverified_reminders", "dm_campaigns", "dm_blacklist", "custom_templates"]
                for k in required_keys:
                    if k not in imported:
                        imported[k] = {}

                if "_meta" not in imported:
                    imported["_meta"] = {"next_campaign_id": 1, "next_queue_id": 1, "next_template_id": 1}

                if "campaign_queue" not in imported:
                    imported["campaign_queue"] = []

                self.data = imported
                self._save_to_disk()
                logger.info("Database successfully restored from JSON backup!")
                return True
            except Exception as e:
                logger.error(f"Failed to restore database from JSON: {e}", exc_info=True)
                return False


# Global database instance
db = JSONDatabase()
