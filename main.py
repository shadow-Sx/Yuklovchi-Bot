import os
import time
import random
import string
import threading
import requests
from flask import Flask, request
import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from pymongo import MongoClient
from bson.objectid import ObjectId

# ==========================
#   ENV VARIABLES
# ==========================
TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ==========================
#   FLASK SERVER (WEBHOOK)
# ==========================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    json_data = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "OK", 200

# ==========================
#   KEEP ALIVE (RENDER)
# ==========================
def keep_alive():
    while True:
        try:
            requests.get(os.getenv("KEEP_ALIVE_URL", "https://example.com"))
        except:
            pass
        time.sleep(600)

threading.Thread(target=keep_alive, daemon=True).start()

# ==========================
#   MONGO DB
# ==========================
client = MongoClient(MONGO_URI)
db = client["super_bot"]

contents = db["contents"]
required_channels = db["required_channels"]
optional_channels = db["optional_channels"]
referrals = db["referrals"]
settings = db["settings"]
users = db["users"]

# ==========================
#   GLOBAL STATES
# ==========================
admin_state = {}
admin_data = {}

# ==========================
#   HELPERS
# ==========================
def generate_code(length=12):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

def save_user(user_id):
    users.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)

def get_auto_delete_seconds():
    doc = settings.find_one({"key": "auto_delete"})
    if not doc:
        return None
    return int(doc.get("seconds", 0)) or None

def schedule_delete(chat_id, msg, code=None):
    seconds = get_auto_delete_seconds()
    if not seconds:
        return

    note = bot.send_message(
        chat_id,
        f"⚠️ Eslatma: Ushbu kontent {seconds} soniyadan so‘ng o‘chiriladi."
    )
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
            markup.add(
                InlineKeyboardButton(
                    "♻️ Qayta tiklash",
                    url=f"https://t.me/{BOT_USERNAME}?start={code}"
                )
            )

        try:
            bot.edit_message_text(
                "⏳ Kontent o‘chirildi.\nQuyidagi tugma orqali qayta tiklashingiz mumkin.",
                chat_id,
                note_id,
                reply_markup=markup
            )
        except:
            pass

    threading.Thread(target=worker, daemon=True).start()

# ==========================
#   ADMIN PANEL MARKUP
# ==========================
def admin_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(
        KeyboardButton("📥 Kontent Qo‘shish"),
        KeyboardButton("📢 Broadcast")
    )
    kb.row(
        KeyboardButton("📌 Majburiy Obuna"),
        KeyboardButton("📌 Ixtiyoriy Obuna")
    )
    kb.row(
        KeyboardButton("🔗 Referal"),
        KeyboardButton("⏱ Avto-o‘chirish")
    )
    kb.row(
        KeyboardButton("📊 Statistika"),
        KeyboardButton("❌ Chiqish")
    )
    return kb

# ==========================
#   MULTI-UPLOAD MODE SELECT
# ==========================
def multi_upload_menu():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🔹 Alohida kodlar bilan", callback_data="multi_single"),
        InlineKeyboardButton("🔸 Bitta kod bilan (playlist)", callback_data="multi_group")
    )
    kb.add(InlineKeyboardButton("🔙 Bekor qilish", callback_data="multi_cancel"))
    return kb
# ==========================
#   ADMIN /admin
# ==========================
@bot.message_handler(commands=["admin"])
def admin_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    admin_state[message.from_user.id] = None
    admin_data[message.from_user.id] = {}
    bot.reply_to(
        message,
        "⚙️ Admin panelga xush kelibsiz!",
        reply_markup=admin_main_menu()
    )

# ==========================
#   ADMIN TEXT BUTTONS
# ==========================
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text in [
    "📥 Kontent Qo‘shish",
    "📢 Broadcast",
    "📌 Majburiy Obuna",
    "📌 Ixtiyoriy Obuna",
    "🔗 Referal",
    "⏱ Avto-o‘chirish",
    "📊 Statistika",
    "❌ Chiqish"
])
def admin_buttons(message):
    uid = message.from_user.id
    text = message.text

    if text == "📥 Kontent Qo‘shish":
        admin_state[uid] = "choose_multi_mode"
        bot.send_message(
            uid,
            "Kontent qo‘shish rejimini tanlang:",
            reply_markup=multi_upload_menu()
        )

    elif text == "📢 Broadcast":
        admin_state[uid] = "wait_broadcast_content"
        admin_data[uid] = {}
        bot.send_message(
            uid,
            "Broadcast uchun xabar yuboring.\n"
            "Matn, foto, video, fayl va hokazo bo‘lishi mumkin."
        )

    elif text == "📌 Majburiy Obuna":
        show_required_menu(message.chat.id)

    elif text == "📌 Ixtiyoriy Obuna":
        show_optional_menu(message.chat.id)

    elif text == "🔗 Referal":
        show_referral_menu(message.chat.id)

    elif text == "⏱ Avto-o‘chirish":
        admin_state[uid] = "wait_auto_delete"
        bot.send_message(
            uid,
            "Avto-o‘chirish vaqtini kiriting (mm:ss)\nMasalan: 1:30"
        )

    elif text == "📊 Statistika":
        total_users = users.count_documents({})
        bot.send_message(
            uid,
            f"📊 Foydalanuvchilar soni: <b>{total_users}</b>"
        )

    elif text == "❌ Chiqish":
        admin_state[uid] = None
        admin_data[uid] = {}
        bot.send_message(
            uid,
            "Admin paneldan chiqdingiz.",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )

# ==========================
#   REQUIRED / OPTIONAL MENUS
# ==========================
def show_required_menu(chat_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Majburiy qo‘shish", callback_data="req_add"),
        InlineKeyboardButton("✏️ Tahrirlash", callback_data="req_edit")
    )
    kb.add(
        InlineKeyboardButton("🗑 O‘chirish", callback_data="req_delete"),
        InlineKeyboardButton("📋 Ro‘yxat", callback_data="req_list")
    )
    bot.send_message(chat_id, "📌 Majburiy obuna bo‘limi:", reply_markup=kb)

def show_optional_menu(chat_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Ixtiyoriy qo‘shish", callback_data="opt_add"),
        InlineKeyboardButton("🗑 O‘chirish", callback_data="opt_delete")
    )
    kb.add(InlineKeyboardButton("📋 Ro‘yxat", callback_data="opt_list"))
    bot.send_message(chat_id, "📌 Ixtiyoriy obuna bo‘limi:", reply_markup=kb)

def show_referral_menu(chat_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Yaratish", callback_data="ref_create"),
        InlineKeyboardButton("📊 Ko‘rish", callback_data="ref_view")
    )
    bot.send_message(chat_id, "🔗 Referal bo‘limi:", reply_markup=kb)

# ==========================
#   CALLBACKLAR (ADMIN)
# ==========================
@bot.callback_query_handler(func=lambda c: c.from_user.id == ADMIN_ID and c.data in [
    "multi_single", "multi_group", "multi_cancel",
    "req_add", "req_edit", "req_delete", "req_list",
    "opt_add", "opt_delete", "opt_list",
    "ref_create", "ref_view"
])
def admin_callback_router(call):
    uid = call.from_user.id
    data = call.data

    # MULTI UPLOAD MODE
    if data == "multi_single":
        admin_state[uid] = "multi_single"
        admin_data[uid] = {"group_mode": False}
        bot.edit_message_text(
            "🔹 Alohida kodlar rejimi.\n"
            "Endi kontent yuboring.\n"
            "Tugagach /stop deb yozing.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    if data == "multi_group":
        admin_state[uid] = "multi_group"
        admin_data[uid] = {"group_mode": True, "items": []}
        bot.edit_message_text(
            "🔸 Bitta kod (playlist) rejimi.\n"
            "Bir nechta kontent yuboring.\n"
            "Tugagach /stop deb yozing.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    if data == "multi_cancel":
        admin_state[uid] = None
        admin_data[uid] = {}
        bot.edit_message_text(
            "❌ Kontent qo‘shish bekor qilindi.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    # REQUIRED / OPTIONAL / REFERRAL
    if data == "req_add":
        start_required_add(call)
    elif data == "req_edit":
        start_required_edit(call)
    elif data == "req_delete":
        start_required_delete(call)
    elif data == "req_list":
        list_required_channels(call)
    elif data == "opt_add":
        start_optional_add(call)
    elif data == "opt_delete":
        start_optional_delete(call)
    elif data == "opt_list":
        list_optional_channels(call)
    elif data == "ref_create":
        start_ref_create(call)
    elif data == "ref_view":
        view_referrals(call)

# ==========================
#   REQUIRED CHANNEL ADD
# ==========================
def start_required_add(call):
    uid = call.from_user.id
    admin_state[uid] = "req_add_id"
    admin_data[uid] = {}
    bot.edit_message_text(
        "➕ Majburiy kanal qo‘shish.\nKanal ID raqamini yuboring:",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_id")
def req_add_id(message):
    uid = message.from_user.id
    try:
        channel_id = int(message.text.strip())
    except:
        bot.reply_to(message, "❌ ID faqat raqam bo‘lishi kerak.")
        return

    admin_data[uid]["channel_id"] = channel_id
    admin_state[uid] = "req_add_url"
    bot.reply_to(message, "🔗 Endi kanal havolasini yuboring:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_url")
def req_add_url(message):
    uid = message.from_user.id
    url = message.text.strip()
    channel_id = admin_data[uid]["channel_id"]

    try:
        member = bot.get_chat_member(channel_id, bot.get_me().id)
        if member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "❌ Bot kanalda admin emas. Avval admin qiling.")
            return
    except:
        bot.reply_to(message, "❌ Kanalga ulanib bo‘lmadi. ID yoki havola xato.")
        return

    admin_data[uid]["url"] = url
    admin_state[uid] = "req_add_name_count"

    bot.reply_to(
        message,
        "📛 Kanal nomini kiriting (masalan: 1-Kanal)\n"
        "Yoki shunchaki raqam bilan nomlasangiz ham bo‘ladi."
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_name_count")
def req_add_name_count(message):
    uid = message.from_user.id
    name = message.text.strip()
    data = admin_data[uid]

    new_channel = {
        "name": name,
        "channel_id": data["channel_id"],
        "url": data["url"],
        "type": "required"
    }
    required_channels.insert_one(new_channel)

    bot.reply_to(
        message,
        f"✅ Majburiy kanal qo‘shildi:\n<b>{name}</b>\n{data['url']}"
    )
    admin_state[uid] = None
    admin_data[uid] = {}

def list_required_channels(call):
    chans = list(required_channels.find({}))
    if not chans:
        bot.edit_message_text(
            "❌ Majburiy kanallar yo‘q.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    text = "📋 Majburiy kanallar:\n\n"
    for ch in chans:
        text += f"• <b>{ch['name']}</b> — {ch['url']}\n"

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )

def start_required_edit(call):
    chans = list(required_channels.find({}))
    if not chans:
        bot.edit_message_text(
            "❌ Majburiy kanallar yo‘q.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    kb = InlineKeyboardMarkup()
    for ch in chans:
        kb.add(
            InlineKeyboardButton(
                f"{ch['name']} (ID: {ch['channel_id']})",
                callback_data=f"edit_req:{ch['_id']}"
            )
        )
    bot.edit_message_text(
        "✏️ Tahrirlash uchun kanalni tanlang:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

def start_required_delete(call):
    chans = list(required_channels.find({}))
    if not chans:
        bot.edit_message_text(
            "❌ Majburiy kanallar yo‘q.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    kb = InlineKeyboardMarkup()
    for ch in chans:
        kb.add(
            InlineKeyboardButton(
                f"{ch['name']} (ID: {ch['channel_id']})",
                callback_data=f"del_req:{ch['_id']}"
            )
        )
    bot.edit_message_text(
        "🗑 O‘chirish uchun kanalni tanlang:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

# ==========================
#   OPTIONAL CHANNELS
# ==========================
def start_optional_add(call):
    uid = call.from_user.id
    admin_state[uid] = "opt_add_id"
    admin_data[uid] = {}
    bot.edit_message_text(
        "➕ Ixtiyoriy kanal qo‘shish.\nKanal ID raqamini yuboring:",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_add_id")
def opt_add_id(message):
    uid = message.from_user.id
    try:
        channel_id = int(message.text.strip())
    except:
        bot.reply_to(message, "❌ ID faqat raqam bo‘lishi kerak.")
        return

    admin_data[uid]["channel_id"] = channel_id
    admin_state[uid] = "opt_add_url"
    bot.reply_to(message, "🔗 Endi kanal havolasini yuboring:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_add_url")
def opt_add_url(message):
    uid = message.from_user.id
    url = message.text.strip()
    channel_id = admin_data[uid]["channel_id"]

    try:
        bot.get_chat_member(channel_id, bot.get_me().id)
    except:
        bot.reply_to(message, "❌ Kanalga ulanib bo‘lmadi. ID yoki havola xato.")
        return

    admin_data[uid]["url"] = url
    admin_state[uid] = "opt_add_name"
    bot.reply_to(message, "📛 Ixtiyoriy kanal nomini kiriting:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_add_name")
def opt_add_name(message):
    uid = message.from_user.id
    name = message.text.strip()
    data = admin_data[uid]

    new_channel = {
        "name": name,
        "channel_id": data["channel_id"],
        "url": data["url"],
        "type": "optional"
    }
    optional_channels.insert_one(new_channel)

    bot.reply_to(
        message,
        f"✅ Ixtiyoriy kanal qo‘shildi:\n<b>{name}</b>\n{data['url']}"
    )
    admin_state[uid] = None
    admin_data[uid] = {}

def list_optional_channels(call):
    chans = list(optional_channels.find({}))
    if not chans:
        bot.edit_message_text(
            "❌ Ixtiyoriy kanallar yo‘q.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    text = "📋 Ixtiyoriy kanallar:\n\n"
    for ch in chans:
        text += f"• <b>{ch['name']}</b> — {ch['url']}\n"

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id
    )

def start_optional_delete(call):
    chans = list(optional_channels.find({}))
    if not chans:
        bot.edit_message_text(
            "❌ Ixtiyoriy kanallar yo‘q.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    kb = InlineKeyboardMarkup()
    for ch in chans:
        kb.add(
            InlineKeyboardButton(
                f"{ch['name']} (ID: {ch['channel_id']})",
                callback_data=f"del_opt:{ch['_id']}"
            )
        )
    bot.edit_message_text(
        "🗑 O‘chirish uchun ixtiyoriy kanalni tanlang:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

# ==========================
#   DELETE REQUIRED/OPTIONAL CALLBACKS
# ==========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("del_req:") or c.data.startswith("del_opt:"))
def delete_channel_callback(call):
    data = call.data
    if data.startswith("del_req:"):
        ch_id = data.split(":")[1]
        required_channels.delete_one({"_id": ObjectId(ch_id)})
        bot.edit_message_text(
            "✅ Majburiy kanal o‘chirildi.",
            call.message.chat.id,
            call.message.message_id
        )
    elif data.startswith("del_opt:"):
        ch_id = data.split(":")[1]
        optional_channels.delete_one({"_id": ObjectId(ch_id)})
        bot.edit_message_text(
            "✅ Ixtiyoriy kanal o‘chirildi.",
            call.message.chat.id,
            call.message.message_id
        )

# ==========================
#   REFERAL
# ==========================
def start_ref_create(call):
    uid = call.from_user.id
    admin_state[uid] = "ref_create_key"
    bot.send_message(uid, "Referal kalit so‘zini kiriting (masalan: Reklama1):")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "ref_create_key")
def ref_create_key(message):
    uid = message.from_user.id
    key = message.text.strip()

    referrals.update_one(
        {"key": key},
        {"$set": {"key": key}},
        upsert=True
    )

    link = f"https://t.me/{BOT_USERNAME}?start={key}"
    bot.reply_to(
        message,
        "✅ Referal yaratildi:\n"
        f"<code>{link}</code>"
    )
    admin_state[uid] = None

def view_referrals(call):
    items = list(referrals.find({}))
    if not items:
        bot.send_message(call.message.chat.id, "Hali referallar yo‘q.")
        return

    text = "📊 Referallar:\n\n"
    for r in items:
        text += f"• <b>{r['key']}</b> — {r.get('count', 0)} ta start\n"
    bot.send_message(call.message.chat.id, text)

# ==========================
#   AVTO-O‘CHIRISH
# ==========================
@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "wait_auto_delete")
def set_auto_delete(message):
    uid = message.from_user.id
    text = message.text.strip()

    if ":" not in text:
        bot.reply_to(message, "❌ Format xato. Masalan: 1:30")
        return

    m, s = text.split(":")
    if not (m.isdigit() and s.isdigit()):
        bot.reply_to(message, "❌ Faqat raqam kiriting. Masalan: 2:00")
        return

    total = int(m) * 60 + int(s)
    settings.update_one(
        {"key": "auto_delete"},
        {"$set": {"seconds": total}},
        upsert=True
    )

    bot.reply_to(
        message,
        f"✅ Avto-o‘chirish yoqildi: {text}"
    )
    admin_state[uid] = None

# ==========================
#   MULTI-UPLOAD /stop
# ==========================
@bot.message_handler(commands=["stop"])
def stop_multi(message):
    uid = message.from_user.id
    state = admin_state.get(uid)

    if state not in
# ==========================
#   OBUNA TEKSHIRISH
# ==========================
def check_required_subs(user_id):
    chans = list(required_channels.find({}))
    if not chans:
        return True

    for ch in chans:
        try:
            member = bot.get_chat_member(ch["channel_id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def get_subscribe_keyboard(user_id, code):
    req = list(required_channels.find({}))
    opt = list(optional_channels.find({}))

    buttons = []

    for ch in req:
        buttons.append(InlineKeyboardButton(ch["name"], url=ch["url"]))

    if not check_required_subs(user_id):
        for ch in opt:
            buttons.append(InlineKeyboardButton(ch["name"], url=ch["url"]))

    random.shuffle(buttons)

    kb = InlineKeyboardMarkup(row_width=1)
    for b in buttons:
        kb.add(b)

    kb.add(InlineKeyboardButton("✔️ Tekshirish", callback_data=f"check:{code}"))
    return kb

# ==========================
#   KONTENT YUBORISH
# ==========================
def send_content(chat_id, item, code=None):
    t = item["type"]

    msg = None

    if t == "group":
        for sub in item["items"]:
            send_content(chat_id, sub, code=None)
        return

    if t == "text":
        msg = bot.send_message(chat_id, item["text"])
    elif t == "photo":
        msg = bot.send_photo(chat_id, item["file_id"], caption=item.get("caption"))
    elif t == "video":
        msg = bot.send_video(chat_id, item["file_id"], caption=item.get("caption"))
    elif t == "document":
        msg = bot.send_document(chat_id, item["file_id"], caption=item.get("caption"))
    elif t == "audio":
        msg = bot.send_audio(chat_id, item["file_id"], caption=item.get("caption"))
    elif t == "voice":
        msg = bot.send_voice(chat_id, item["file_id"], caption=item.get("caption"))
    elif t == "animation":
        msg = bot.send_animation(chat_id, item["file_id"], caption=item.get("caption"))

    if msg and code:
        schedule_delete(chat_id, msg, code=code)

# ==========================
#   OBUNA TEKSHIRISH CALLBACK
# ==========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("check:"))
def check_subs_callback(call):
    code = call.data.split(":")[1]
    user_id = call.from_user.id

    if not check_required_subs(user_id):
        bot.answer_callback_query(call.id, "❌ Hali hammasiga obuna bo‘lmadingiz!", show_alert=True)
        return

    item = contents.find_one({"code": code})
    if not item:
        bot.answer_callback_query(call.id, "❌ Kontent topilmadi.", show_alert=True)
        return

    send_content(call.message.chat.id, item, code=code)

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

# ==========================
#   /START (ODDIY)
# ==========================
@bot.message_handler(func=lambda m: m.text == "/start")
def start(message):
    save_user(message.from_user.id)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📝 Bot Haqida", callback_data="about"),
        InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{message.message_id}")
    )

    bot.reply_to(
        message,
        "<b>Bu bot orqali kanaldagi kontentlarni yuklab olishingiz mumkin.\n\n"
        "❗️Botga oddiy habar yozmang, faqat tugmalar orqali ishlating.</b>",
        reply_markup=kb
    )

# ==========================
#   /START CODE
# ==========================
@bot.message_handler(func=lambda m: m.text.startswith("/start ") and len(m.text.split()) == 2)
def start_with_code(message):
    save_user(message.from_user.id)

    code = message.text.split()[1]

    item = contents.find_one({"code": code})
    if item:
        if not check_required_subs(message.from_user.id):
            kb = get_subscribe_keyboard(message.from_user.id, code)
            bot.send_message(
                message.chat.id,
                "📌 Iltimos quyidagi kanallarga obuna bo‘ling:",
                reply_markup=kb
            )
            return

        send_content(message.chat.id, item, code=code)
        return

    referrals.update_one(
        {"key": code},
        {"$inc": {"count": 1}},
        upsert=True
    )

    bot.send_message(
        message.chat.id,
        "✅ Referal orqali keldingiz.\nBotdan foydalanishni davom ettirishingiz mumkin."
    )

# ==========================
#   CALLBACKLAR (ABOUT / CREATOR / CLOSE)
# ==========================
@bot.callback_query_handler(func=lambda call: True)
def generic_callback(call):
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
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                "<b>"
                "Botni ishlatish qo‘llanmasi:\n\n"
                "1. Kanallarga obuna bo‘ling.\n"
                "2. Tekshirish tugmasini bosing.\n"
                "3. Kanaldagi post pastidagi yuklab olish tugmasini bosing.\n"
                "</b>"
            ),
            reply_markup=kb
        )
        return

    if data == "creator":
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("📝 Bot Haqida", callback_data="about"),
            InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{call.message.message_id}")
        )
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                "<b>"
                "• Admin: <i>@Shadow_Sxi</i>\n"
                "• Asosiy Kanal: <i>@AniGonUz</i>\n"
                "• Reklama: <i>@AniReklamaUz</i>\n"
                "</b>"
            ),
            reply_markup=kb
        )
        return

# ==========================
#   XAVFSIZLIK: KANALDAN CHIQARILSA
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
                    bot.send_message(
                        ADMIN_ID,
                        f"⚠️ <b>{ch['name']}</b> kanalidan chiqarildim.\n"
                        f"Kanal majburiy ro‘yxatdan o‘chirildi."
                    )
                except:
                    required_channels.delete_one({"_id": ch["_id"]})
                    bot.send_message(
                        ADMIN_ID,
                        f"⚠️ <b>{ch['name']}</b> kanaliga ulanib bo‘lmadi.\n"
                        f"Kanal majburiy ro‘yxatdan o‘chirildi."
                    )
        except Exception as e:
            print("Security error:", e)

        time.sleep(30)

threading.Thread(target=security_check, daemon=True).start()

# ==========================
#   RUN SERVER
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
