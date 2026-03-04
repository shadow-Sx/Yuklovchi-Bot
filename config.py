import os

# ==========================
#   BOT SETTINGS
# ==========================

# Telegram bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Bot username (masalan: AniGonBot)
BOT_USERNAME = os.getenv("BOT_USERNAME")

# Admin ID (raqam ko‘rinishida)
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# ==========================
#   DATABASE SETTINGS
# ==========================

# MongoDB Atlas ulanish manzili
MONGO_URI = os.getenv("MONGO_URI")

# ==========================
#   OTHER SETTINGS
# ==========================

# Render Free rejimida botni uyg‘otib turish uchun URL
KEEP_ALIVE_URL = os.getenv("KEEP_ALIVE_URL", "")
