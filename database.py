from pymongo import MongoClient
from config import MONGO_URI

# ==========================
#   MONGO DB CONNECTION
# ==========================

client = MongoClient(MONGO_URI)

# Asosiy database
db = client["xanimelar_bot"]

# ==========================
#   COLLECTIONS
# ==========================

# Kontentlar (video, photo, document, text)
contents = db["contents"]

# Majburiy obuna kanallari
required_channels = db["required_channels"]

# Ixtiyoriy obuna kanallari
optional_channels = db["optional_channels"]

# Adminlar (hozircha ishlatilmaydi, lekin kelajakda kerak bo‘ladi)
admins = db["admins"]
