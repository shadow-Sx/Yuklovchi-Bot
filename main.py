import os
import time
import random
import string
import threading
import requests
import telebot
from flask import Flask, request
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from pymongo import MongoClient
from bson.objectid import ObjectId

# ==========================
#   TOKEN & SETTINGS
# ==========================
TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
ADMIN_ID = 7797502113

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ==========================
#   MONGO DB CONNECTION
# ==========================
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

db = client["xanimelar_bot"]

contents = db["contents"]
required_channels = db["required_channels"]
optional_channels = db["optional_channels"]
referrals = db["referrals"]
settings = db["settings"]
users = db["users"]

# ==========================
#   FLASK SERVER
# ==========================
app = Flask(__name__)

@app.route('/')
def home():
    return "XAnimelarBot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    json_data = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "OK", 200

# ==========================
#   KEEP ALIVE (Render Free)
# ==========================
def keep_alive():
    while True:
        try:
            requests.get("https://yuklovchi-bot-80ui.onrender.com")
        except:
            pass
        time.sleep(600)

threading.Thread(target=keep_alive, daemon=True).start()

# ==========================
#   RANDOM CODE GENERATOR
# ==========================
def generate_code(length=12):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

admin_state = {}
admin_data = {}

# ==========================
#   ADMIN PANEL
# ==========================
def admin_panel():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("Kontent Qo‘shish"),
        KeyboardButton("Majburiy Obuna")
    )
    markup.row(
        KeyboardButton("Broadcast"),
        KeyboardButton("🔙 Chiqish")
    )
    return markup

# ==========================
#   /admin
# ==========================
@bot.message_handler(commands=['admin'])
def admin_start(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Siz admin emassiz!")
        return

    bot.reply_to(
        message,
        "⚙️ Admin panelga xush kelibsiz!",
        reply_markup=admin_panel()
    )

# ==========================
#   ADMIN BUTTONS
# ==========================
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text in [
    "Kontent Qo‘shish", "Majburiy Obuna", "Broadcast", "🔙 Chiqish"
])
def admin_buttons(message):
    uid = message.from_user.id
    text = message.text

    if text == "Kontent Qo‘shish":
        admin_state[uid] = "multi_add"
        bot.reply_to(message, "📥 Videolarni tashlang.\nTugagach /stop deb yozing.")

    elif text == "Majburiy Obuna":
        show_required_menu(message.chat.id)

    elif text == "Broadcast":
        admin_state[uid] = "wait_broadcast"
        bot.reply_to(message, "📨 Broadcast uchun xabar yuboring.")

    elif text == "🔙 Chiqish":
        admin_state[uid] = None
        bot.send_message(uid, "Admin paneldan chiqdingiz.", reply_markup=telebot.types.ReplyKeyboardRemove())

# ==========================
#   REQUIRED MENU
# ==========================
def show_required_menu(chat_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Qo‘shish", callback_data="req_add"),
        InlineKeyboardButton("🗑 O‘chirish", callback_data="req_delete")
    )
    kb.add(InlineKeyboardButton("📋 Ro‘yxat", callback_data="req_list"))
    bot.send_message(chat_id, "📌 Majburiy obuna:", reply_markup=kb)

# ==========================
#   REQUIRED ADD
# ==========================
@bot.callback_query_handler(func=lambda c: c.data == "req_add")
def req_add_start(call):
    uid = call.from_user.id
    admin_state[uid] = "req_add_id"
    admin_data[uid] = {}
    bot.edit_message_text("➕ Kanal ID yuboring:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_id")
def req_add_id(message):
    uid = message.from_user.id
    try:
        admin_data[uid]["channel_id"] = int(message.text)
    except:
        bot.reply_to(message, "❌ ID faqat raqam.")
        return
    admin_state[uid] = "req_add_url"
    bot.reply_to(message, "🔗 Kanal havolasini yuboring:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_url")
def req_add_url(message):
    uid = message.from_user.id
    url = message.text.strip()
    cid = admin_data[uid]["channel_id"]

    try:
        bot.get_chat_member(cid, bot.get_me().id)
    except:
        bot.reply_to(message, "❌ Kanalga ulanib bo‘lmadi.")
        return

    admin_data[uid]["url"] = url
    admin_state[uid] = "req_add_name"
    bot.reply_to(message, "📛 Kanal nomini kiriting:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_name")
def req_add_name(message):
    uid = message.from_user.id
    name = message.text.strip()
    data = admin_data[uid]

    required_channels.insert_one({
        "name": name,
        "channel_id": data["channel_id"],
        "url": data["url"]
    })

    bot.reply_to(message, f"✅ Qo‘shildi:\n<b>{name}</b>")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   MULTI-UPLOAD /stop
# ==========================
@bot.message_handler(commands=['stop'])
def stop_multi(message):
    uid = message.from_user.id
    if admin_state.get(uid) == "multi_add":
        admin_state[uid] = None
        bot.reply_to(message, "✅ Kontent qabul qilindi.", reply_markup=admin_panel())

# ==========================
#   MULTI-UPLOAD SAQLASH
# ==========================
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def save_multi(message):
    uid = message.from_user.id

    if admin_state.get(uid) != "multi_add":
        return

    code = generate_code()

    if message.content_type == "video":
        content = {
            "type": "video",
            "file_id": message.video.file_id,
            "caption": message.caption,
            "code": code
        }

    elif message.content_type == "photo":
        content = {
            "type": "photo",
            "file_id": message.photo[-1].file_id,
            "caption": message.caption,
            "code": code
        }

    elif message.content_type == "document":
        content = {
            "type": "document",
            "file_id": message.document.file_id,
            "caption": message.caption,
            "code": code
        }

    else:
        content = {"type": "text", "text": message.text, "code": code}

    contents.insert_one(content)

    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.reply_to(message, link)

# ==========================
#   START-LINK HANDLER
# ==========================
@bot.message_handler(func=lambda m: m.text.startswith("/start ") and len(m.text.split()) == 2)
def start_with_code_handler(message):
    start_with_code(message)

# ==========================
#   /start
# ==========================
@bot.message_handler(commands=['start'])
def start(message):
    users.update_one({"user_id": message.from_user.id}, {"$set": {"user_id": message.from_user.id}}, upsert=True)

    if len(message.text.split()) == 2:
        return start_with_code(message)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📝 Bot Haqida", callback_data="about"),
        InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{message.message_id}")
    )

    bot.reply_to(
        message,
        "<b>Botga xush kelibsiz!\nStart-linklardan foydalaning.</b>",
        reply_markup=kb
    )

# ==========================
#   START-LINK
# ==========================
def start_with_code(message):
    code = message.text.split()[1]
    item = contents.find_one({"code": code})

    if not item:
        bot.send_message(message.chat.id, "❌ Kontent topilmadi.")
        return

    send_content(message.chat.id, item)

def send_content(chat_id, item):
    t = item["type"]

    if t == "text":
        bot.send_message(chat_id, item["text"])
    elif t == "photo":
        bot.send_photo(chat_id, item["file_id"], caption=item.get("caption"))
    elif t == "video":
        bot.send_video(chat_id, item["file_id"], caption=item.get("caption"))
    elif t == "document":
        bot.send_document(chat_id, item["file_id"], caption=item.get("caption"))

# ==========================
#   CALLBACK HANDLER
# ==========================
@bot.callback_query_handler(func=lambda call: call.data in ["about", "creator"] or call.data.startswith("close"))
def callback(call):
    data = call.data

    if data.startswith("close"):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        return

    if data == "about":
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("👨‍💻 Yaratuvchi", callback_data="creator"),
            InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{call.message.message_id}")
        )
        bot.edit_message_text(
            "<b>Botdan foydalanish qo‘llanmasi:\n1. Obuna bo‘ling\n2. Tekshiring\n3. Yuklab oling</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )

    if data == "creator":
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("📝 Bot Haqida", callback_data="about"),
            InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{call.message.message_id}")
        )
        bot.edit_message_text(
            "<b>• Admin: @Shadow_Sxi\n• Kanal: @AniGonUz</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )

# ==========================
#   SECURITY CHECK
# ==========================
def security_check():
    while True:
        try:
            chans = list(required_channels.find({}))
            for ch in chans:
                cid = ch["channel_id"]
                try:
                    member = bot.get_chat_member(cid, bot.get_me().id)
                    if member.status in ["administrator", "creator"]:
                        continue

                    required_channels.delete_one({"_id": ch["_id"]})
                    bot.send_message(ADMIN_ID, f"⚠️ {ch['name']} kanalidan chiqarildim.")
                except:
                    required_channels.delete_one({"_id": ch["_id"]})
                    bot.send_message(ADMIN_ID, f"⚠️ {ch['name']} kanaliga ulanib bo‘lmadi.")
        except:
            pass

        time.sleep(30)

threading.Thread(target=security_check, daemon=True).start()

# ==========================
#   RUN SERVER
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
