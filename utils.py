import os
import time
import random
import string
import threading
import requests
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

client = MongoClient(MONGO_URI)
db = client["super_bot"]

contents = db["contents"]
required_channels = db["required_channels"]
optional_channels = db["optional_channels"]
referrals = db["referrals"]
settings = db["settings"]
users = db["users"]

admin_state = {}
admin_data = {}

def generate_code(length=12):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def save_user(user_id):
    users.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)

def get_auto_delete_seconds():
    doc = settings.find_one({"key": "auto_delete"})
    if not doc:
        return None
    return int(doc.get("seconds", 0)) or None

def schedule_delete(bot, chat_id, msg, code=None):
    seconds = get_auto_delete_seconds()
    if not seconds:
        return

    note = bot.send_message(chat_id, f"⚠️ Kontent {seconds} soniyada o‘chiriladi.")
    note_id = note.message_id

    def worker():
        time.sleep(seconds)
        try:
            bot.delete_message(chat_id, msg.message_id)
        except:
            pass

        markup = None
        if code:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("♻️ Qayta tiklash", url=f"https://t.me/{BOT_USERNAME}?start={code}"))

        try:
            bot.edit_message_text(
                "⏳ Kontent o‘chirildi.",
                chat_id,
                note_id,
                reply_markup=markup
            )
        except:
            pass

    threading.Thread(target=worker, daemon=True).start()
