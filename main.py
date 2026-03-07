import os
import time
import threading
from typing import Optional

import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from flask import Flask, request
from pymongo import MongoClient
from bson.objectid import ObjectId

# ==========================
#   CONFIG
# ==========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7797502113"))
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

client = MongoClient(MONGO_URI)
db = client["mandatory_sub_bot"]
channels_col = db["channels"]  # majburiy kanallar

# ==========================
#   FLASK (WEBHOOK UCHUN)
# ==========================
app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "Mandatory Sub Bot is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    json_data = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "OK", 200

# ==========================
#   ADMIN STATE
# ==========================
admin_state = {}
admin_data = {}

# ==========================
#   ADMIN PANEL
# ==========================
def admin_main_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(
        KeyboardButton("➕ Kanal qo‘shish"),
        KeyboardButton("📋 Kanallar ro‘yxati")
    )
    kb.row(
        KeyboardButton("🔙 Chiqish")
    )
    return kb

def channel_type_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📢 Public", callback_data="add_public"),
        InlineKeyboardButton("🔒 Private", callback_data="add_private")
    )
    kb.add(
        InlineKeyboardButton("📝 Request-to-Join", callback_data="add_request")
    )
    kb.add(
        InlineKeyboardButton("🔙 Orqaga", callback_data="admin_back")
    )
    return kb

def channel_manage_keyboard(ch_id: str):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📛 Nomni o‘zgartirish", callback_data=f"edit_name:{ch_id}")
    )
    kb.add(
        InlineKeyboardButton("🔗 Havolani o‘zgartirish", callback_data=f"edit_link:{ch_id}")
    )
    kb.add(
        InlineKeyboardButton("🗑 O‘chirish", callback_data=f"del_channel:{ch_id}")
    )
    kb.add(
        InlineKeyboardButton("🔙 Orqaga", callback_data="list_channels")
    )
    return kb

# ==========================
#   /admin
# ==========================
@bot.message_handler(commands=["admin"])
def admin_cmd(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Siz admin emassiz.")
        return

    admin_state[ADMIN_ID] = None
    admin_data[ADMIN_ID] = {}
    bot.reply_to(
        message,
        "⚙️ Admin panelga xush kelibsiz.",
        reply_markup=admin_main_keyboard()
    )

# ==========================
#   ADMIN TEXT HANDLER
# ==========================
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
def admin_text_handler(message):
    uid = message.from_user.id
    text = message.text

    # Global admin commands
    if text == "➕ Kanal qo‘shish":
        admin_state[uid] = None
        admin_data[uid] = {}
        bot.send_message(
            uid,
            "Qaysi turdagi kanal qo‘shamiz?",
            reply_markup=channel_type_keyboard()
        )
        return

    if text == "📋 Kanallar ro‘yxati":
        send_channels_list(uid)
        return

    if text == "🔙 Chiqish":
        admin_state[uid] = None
        admin_data[uid] = {}
        bot.send_message(uid, "Admin paneldan chiqdingiz.", reply_markup=telebot.types.ReplyKeyboardRemove())
        return

    # State-based inputs
    state = admin_state.get(uid)

    if state == "await_public_username":
        handle_public_username(message)
    elif state == "await_private_invite":
        handle_private_invite(message)
    elif state == "await_request_invite":
        handle_request_invite(message)
    elif state == "edit_name":
        handle_edit_name(message)
    elif state == "edit_link":
        handle_edit_link(message)
    else:
        # ignore other texts
        pass

# ==========================
#   ADMIN CALLBACKS
# ==========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("add_") or
                                         c.data in ["admin_back", "list_channels"] or
                                         c.data.startswith("manage:") or
                                         c.data.startswith("edit_name:") or
                                         c.data.startswith("edit_link:") or
                                         c.data.startswith("del_channel:"))
def admin_callback(call):
    uid = call.from_user.id
    data = call.data

    if uid != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Siz admin emassiz.")
        return

    if data == "admin_back":
        bot.edit_message_text(
            "Admin panel:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=channel_type_keyboard()
        )
        return

    if data == "add_public":
        admin_state[uid] = "await_public_username"
        admin_data[uid] = {"type": "public"}
        bot.edit_message_text(
            "📢 Public kanal qo‘shish.\n\n"
            "Kanal username yoki havolasini yuboring:\n"
            "Masalan: @MyChannel yoki https://t.me/MyChannel",
            call.message.chat.id,
            call.message.message_id
        )
        return

    if data == "add_private":
        admin_state[uid] = "await_private_invite"
        admin_data[uid] = {"type": "private"}
        bot.edit_message_text(
            "🔒 Private kanal qo‘shish.\n\n"
            "Kanal invite havolasini yuboring (t.me/+...):",
            call.message.chat.id,
            call.message.message_id
        )
        return

    if data == "add_request":
        admin_state[uid] = "await_request_invite"
        admin_data[uid] = {"type": "request"}
        bot.edit_message_text(
            "📝 Request-to-Join kanal qo‘shish.\n\n"
            "Kanal invite havolasini yuboring (t.me/+...):",
            call.message.chat.id,
            call.message.message_id
        )
        return

    if data == "list_channels":
        send_channels_list(uid, edit_message=(call.message.chat.id, call.message.message_id))
        return

    if data.startswith("manage:"):
        ch_id = data.split(":", 1)[1]
        show_channel_manage(call, ch_id)
        return

    if data.startswith("edit_name:"):
        ch_id = data.split(":", 1)[1]
        admin_state[uid] = "edit_name"
        admin_data[uid] = {"ch_id": ch_id}
        bot.edit_message_text(
            "📛 Yangi nomni kiriting:",
            call.message.chat.id,
            call.message.message_id
        )
        return

    if data.startswith("edit_link:"):
        ch_id = data.split(":", 1)[1]
        admin_state[uid] = "edit_link"
        admin_data[uid] = {"ch_id": ch_id}
        bot.edit_message_text(
            "🔗 Yangi invite havolasini yuboring:",
            call.message.chat.id,
            call.message.message_id
        )
        return

    if data.startswith("del_channel:"):
        ch_id = data.split(":", 1)[1]
        channels_col.delete_one({"_id": ObjectId(ch_id)})
        bot.edit_message_text(
            "✅ Kanal o‘chirildi.",
            call.message.chat.id,
            call.message.message_id
        )
        return

# ==========================
#   ADMIN HELPERS
# ==========================
def normalize_username_or_link(text: str) -> str:
    text = text.strip()
    if text.startswith("@"):
        return text[1:]
    if text.startswith("https://t.me/") or text.startswith("http://t.me/"):
        return text.split("/")[-1]
    return text

def handle_public_username(message):
    uid = message.from_user.id
    username = normalize_username_or_link(message.text)

    try:
        chat = bot.get_chat(username)
    except Exception as e:
        bot.reply_to(message, f"❌ Kanal topilmadi yoki ulanishda xato.\n{e}")
        return

    if not chat.username:
        bot.reply_to(message, "❌ Bu kanal public emas (username yo‘q).")
        return

    doc = {
        "chat_id": chat.id,
        "type": "public",
        "title": chat.title or chat.username,
        "invite_link": f"https://t.me/{chat.username}",
        "username": chat.username
    }
    channels_col.insert_one(doc)

    bot.reply_to(
        message,
        f"✅ Public kanal qo‘shildi:\n\n"
        f"📛 <b>{doc['title']}</b>\n"
        f"🆔 <code>{doc['chat_id']}</code>\n"
        f"🔗 {doc['invite_link']}"
    )
    admin_state[uid] = None
    admin_data[uid] = {}

def handle_private_invite(message):
    uid = message.from_user.id
    invite = message.text.strip()

    try:
        chat = bot.get_chat(invite)
    except Exception as e:
        bot.reply_to(message, f"❌ Kanalga ulanib bo‘lmadi.\n{e}")
        return

    if chat.type != "channel":
        bot.reply_to(message, "❌ Bu kanal emas.")
        return

    doc = {
        "chat_id": chat.id,
        "type": "private",
        "title": chat.title or "Private Channel",
        "invite_link": invite,
        "username": chat.username  # bo‘lmasligi mumkin
    }
    channels_col.insert_one(doc)

    bot.reply_to(
        message,
        f"✅ Private kanal qo‘shildi:\n\n"
        f"📛 <b>{doc['title']}</b>\n"
        f"🆔 <code>{doc['chat_id']}</code>\n"
        f"🔗 {doc['invite_link']}"
    )
    admin_state[uid] = None
    admin_data[uid] = {}

def handle_request_invite(message):
    uid = message.from_user.id
    invite = message.text.strip()

    try:
        chat = bot.get_chat(invite)
    except Exception as e:
        bot.reply_to(message, f"❌ Kanalga ulanib bo‘lmadi.\n{e}")
        return

    if chat.type != "channel":
        bot.reply_to(message, "❌ Bu kanal emas.")
        return

    doc = {
        "chat_id": chat.id,
        "type": "request",
        "title": chat.title or "Request Channel",
        "invite_link": invite,
        "username": chat.username
    }
    channels_col.insert_one(doc)

    bot.reply_to(
        message,
        f"✅ Request-to-Join kanal qo‘shildi:\n\n"
        f"📛 <b>{doc['title']}</b>\n"
        f"🆔 <code>{doc['chat_id']}</code>\n"
        f"🔗 {doc['invite_link']}"
    )
    admin_state[uid] = None
    admin_data[uid] = {}

def send_channels_list(chat_id: int, edit_message: Optional[tuple] = None):
    channels = list(channels_col.find({}))
    if not channels:
        text = "📋 Hozircha majburiy kanallar yo‘q."
        if edit_message:
            bot.edit_message_text(text, edit_message[0], edit_message[1])
        else:
            bot.send_message(chat_id, text)
        return

    kb = InlineKeyboardMarkup()
    for ch in channels:
        icon = "📢" if ch["type"] == "public" else ("🔒" if ch["type"] == "private" else "📝")
        kb.add(
            InlineKeyboardButton(
                f"{icon} {ch['title']}",
                callback_data=f"manage:{ch['_id']}"
            )
        )

    if edit_message:
        bot.edit_message_text(
            "📋 Majburiy kanallar ro‘yxati:",
            edit_message[0],
            edit_message[1],
            reply_markup=kb
        )
    else:
        bot.send_message(
            chat_id,
            "📋 Majburiy kanallar ro‘yxati:",
            reply_markup=kb
        )

def show_channel_manage(call, ch_id: str):
    ch = channels_col.find_one({"_id": ObjectId(ch_id)})
    if not ch:
        bot.answer_callback_query(call.id, "❌ Kanal topilmadi.")
        return

    icon = "📢" if ch["type"] == "public" else ("🔒" if ch["type"] == "private" else "📝")
    text = (
        f"{icon} <b>{ch['title']}</b>\n\n"
        f"🆔 <code>{ch['chat_id']}</code>\n"
        f"🔗 {ch['invite_link']}\n"
        f"🔠 Tur: <code>{ch['type']}</code>\n"
        f"👤 Username: <code>{ch.get('username') or '-'}</code>"
    )

    kb = channel_manage_keyboard(str(ch["_id"]))
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

def handle_edit_name(message):
    uid = message.from_user.id
    new_name = message.text.strip()
    ch_id = admin_data[uid]["ch_id"]

    channels_col.update_one(
        {"_id": ObjectId(ch_id)},
        {"$set": {"title": new_name}}
    )

    bot.reply_to(message, f"✅ Nom <b>{new_name}</b> ga o‘zgartirildi.")
    admin_state[uid] = None
    admin_data[uid] = {}

def handle_edit_link(message):
    uid = message.from_user.id
    new_link = message.text.strip()
    ch_id = admin_data[uid]["ch_id"]

    channels_col.update_one(
        {"_id": ObjectId(ch_id)},
        {"$set": {"invite_link": new_link}}
    )

    bot.reply_to(message, "✅ Invite havola yangilandi.")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   OBUNA TEKSHIRISH
# ==========================
def is_request_like(member) -> bool:
    # Request-to-join kanal uchun "join request"ni aniqlashga yaqin taxmin
    if member.status in ["member", "administrator", "creator"]:
        return True
    if member.status == "restricted":
        return True
    if member.status == "left" and getattr(member, "until_date", 0) != 0:
        return True
    return False

def check_user_in_channel(user_id: int, ch: dict) -> bool:
    try:
        member = bot.get_chat_member(ch["chat_id"], user_id)
    except Exception:
        return False

    if ch["type"] in ["public", "private"]:
        return member.status in ["member", "administrator", "creator", "restricted"]

    if ch["type"] == "request":
        return is_request_like(member)

    return False

def check_all_required(user_id: int) -> bool:
    channels = list(channels_col.find({}))
    if not channels:
        return True  # majburiy kanal yo‘q bo‘lsa, o‘tkazib yuboramiz

    for ch in channels:
        if not check_user_in_channel(user_id, ch):
            return False
    return True

def required_keyboard(user_id: int):
    channels = list(channels_col.find({}))
    kb = InlineKeyboardMarkup(row_width=1)

    for ch in channels:
        kb.add(
            InlineKeyboardButton(
                ch["title"],
                url=ch["invite_link"]
            )
        )

    kb.add(
        InlineKeyboardButton(
            "✔️ Tekshirish",
            callback_data="check_subs"
        )
    )
    return kb

# ==========================
#   /start
# ==========================
@bot.message_handler(commands=["start"])
def start_cmd(message):
    user_id = message.from_user.id

    if not check_all_required(user_id):
        kb = required_keyboard(user_id)
        bot.send_message(
            message.chat.id,
            "📌 Iltimos quyidagi kanallarga obuna bo‘ling:",
            reply_markup=kb
        )
        return

    show_main_menu(message.chat.id)

def show_main_menu(chat_id: int):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📝 Bot haqida", callback_data="about"),
        InlineKeyboardButton("🔒 Yopish", callback_data="close")
    )
    bot.send_message(
        chat_id,
        "<b>Asosiy menyu.</b>\n\n"
        "Siz barcha majburiy kanallarga obuna bo‘lgansiz.",
        reply_markup=kb
    )

# ==========================
#   USER CALLBACKS
# ==========================
@bot.callback_query_handler(func=lambda c: c.data in ["check_subs", "about", "close"])
def user_callback(call):
    data = call.data
    user_id = call.from_user.id

    if data == "check_subs":
        if check_all_required(user_id):
            bot.answer_callback_query(call.id, "✅ Hammasiga obuna bo‘lgansiz.")
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            show_main_menu(call.message.chat.id)
        else:
            bot.answer_callback_query(call.id, "❌ Hali hammasiga obuna bo‘lmadingiz.")
        return

    if data == "about":
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            "<b>Bot haqida:</b>\n\n"
            "Bu bot majburiy obuna tizimi bilan ishlaydi.\n"
            "Barcha ko‘rsatilgan kanallarga obuna bo‘lgach, asosiy funksiyalar ochiladi.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    if data == "close":
        bot.answer_callback_query(call.id)
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        return

# ==========================
#   SECURITY CHECK (KANALDAN CHIQARILGAN BOT)
# ==========================
def security_loop():
    while True:
        try:
            channels = list(channels_col.find({}))
            for ch in channels:
                try:
                    member = bot.get_chat_member(ch["chat_id"], bot.get_me().id)
                    if member.status not in ["administrator", "creator"]:
                        channels_col.delete_one({"_id": ch["_id"]})
                        bot.send_message(
                            ADMIN_ID,
                            f"⚠️ Bot <b>{ch['title']}</b> kanalidan chiqarilgan yoki admin emas.\n"
                            f"Kanal majburiy ro‘yxatdan o‘chirildi."
                        )
                except Exception:
                    channels_col.delete_one({"_id": ch["_id"]})
                    bot.send_message(
                        ADMIN_ID,
                        f"⚠️ <b>{ch['title']}</b> kanaliga ulanib bo‘lmadi.\n"
                        f"Kanal majburiy ro‘yxatdan o‘chirildi."
                    )
        except Exception as e:
            print("Security error:", e)

        time.sleep(30)

threading.Thread(target=security_loop, daemon=True).start()

# ==========================
#   RUN
# ==========================
if __name__ == "__main__":
    # Agar webhook ishlatayotgan bo‘lsang, shu yerda set_webhook qilasan.
    # Hozircha polling uchun:
    bot.infinity_polling()
