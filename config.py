import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Discord Bot Token
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

# Server / Guild ID (Optional for global or guild-specific sync)
GUILD_ID = os.getenv("GUILD_ID", "")
try:
    GUILD_ID = int(GUILD_ID) if GUILD_ID.strip() else None
except (ValueError, TypeError):
    GUILD_ID = None

# Admin Configuration
FOUNDER_ID = os.getenv("FOUNDER_ID", "")
try:
    FOUNDER_ID = int(FOUNDER_ID) if FOUNDER_ID.strip() else None
except (ValueError, TypeError):
    FOUNDER_ID = None

ADMIN_ROLE_ID = os.getenv("ADMIN_ROLE_ID", "")
try:
    ADMIN_ROLE_ID = int(ADMIN_ROLE_ID) if ADMIN_ROLE_ID.strip() else None
except (ValueError, TypeError):
    ADMIN_ROLE_ID = None

# Web Server Settings (for Render / UptimeRobot 24/7 keep-alive)
PORT = int(os.getenv("PORT", "8080"))

# Database Path
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR / "bot_database.sqlite"))

# Assets Path
ASSETS_DIR = BASE_DIR / "assets"
DEFAULT_VERIFY_BANNER = str(ASSETS_DIR / "verify_banner.jpg")

# Anti-Spam Safety Settings
# Base delay between each DM in seconds (humanized rate limiting)
DM_MIN_DELAY_SECONDS = float(os.getenv("DM_MIN_DELAY_SECONDS", "3.0"))
DM_MAX_DELAY_SECONDS = float(os.getenv("DM_MAX_DELAY_SECONDS", "6.0"))

# Batch size before taking a cool-off breather pause
DM_BATCH_SIZE = int(os.getenv("DM_BATCH_SIZE", "20"))
DM_BATCH_PAUSE_SECONDS = float(os.getenv("DM_BATCH_PAUSE_SECONDS", "25.0"))

# Consecutive error circuit breaker threshold
MAX_CONSECUTIVE_ERRORS = int(os.getenv("MAX_CONSECUTIVE_ERRORS", "5"))

# Default Verification Message Template
DEFAULT_VERIFY_TEXT = """## 🚀 VERIFY NOW & UNLOCK FULL SERVER ACCESS!

Head over to <#{channel_id}> and click the Verify button as shown in the image above.

🔓 Unlock chats, events, giveaways, exclusive channels & much more!

**Don't miss out — verify now and become part of the Prop Traders Community(PTC)!**"""

