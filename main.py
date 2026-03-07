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
required_channels = db["required_channels"]   # public + private
optional_channels = db["optional_channels"]

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
#   KEEP ALIVE (RENDER)
# ==========================
def keep_alive():
    while True:
        try:
            requests.get("https://yuklovchi-bot-80ui.onrender.com")
        except:
            pass
        time.sleep(600)

threading.Thread(target=keep_alive).start()

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
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(
        KeyboardButton("Cantent Qo'shish"),
        KeyboardButton("Majburi Obuna")
    )
    kb.row(
        KeyboardButton("Habar Yuborish"),
        KeyboardButton("🔙 Chiqish")
    )
    return kb

def required_menu():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Majburiy qo‘shish", callback_data="req_add"),
        InlineKeyboardButton("➕ Ixtiyoriy qo‘shish", callback_data="opt_add")
    )
    kb.add(
        InlineKeyboardButton("✏️ Tahrirlash", callback_data="req_edit"),
        InlineKeyboardButton("🗑 O‘chirish", callback_data="req_delete")
    )
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_back"))
    return kb

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
    "Cantent Qo'shish", "Majburi Obuna", "Habar Yuborish", "🔙 Chiqish"
])
def admin_buttons(message):
    uid = message.from_user.id
    txt = message.text

    if txt == "Cantent Qo'shish":
        admin_state[uid] = "multi_add"
        bot.reply_to(message, "📥 Videolarni tashlang.\nTugagach /stop deb yozing.")

    elif txt == "Majburi Obuna":
        bot.send_message(
            message.chat.id,
            "📌 Majburiy obuna bo‘limi:",
            reply_markup=required_menu()
        )

    elif txt == "Habar Yuborish":
        bot.reply_to(message, "📨 Bu bo‘lim keyin qo‘shiladi.")

    elif txt == "🔙 Chiqish":
        admin_state[uid] = None
        bot.send_message(uid, "Admin paneldan chiqdingiz.", reply_markup=telebot.types.ReplyKeyboardRemove())

# ==========================
#   /stop — multi upload tugatish
# ==========================
@bot.message_handler(commands=['stop'])
def stop(message):
    uid = message.from_user.id
    if admin_state.get(uid) == "multi_add":
        admin_state[uid] = None
        bot.reply_to(message, "✅ Barcha kontentlar qabul qilindi.", reply_markup=admin_panel())

# ==========================
#   PRIVATE POST HAVOLADAN ID OLISH
# ==========================
def extract_private_id(url: str):
    # https://t.me/c/123456789/55
    url = url.replace("https://", "").replace("http://", "")
    parts = url.split("/")
    # ['t.me', 'c', '123456789', '55']
    if len(parts) >= 3 and parts[0] == "t.me" and parts[1] == "c":
        return int("-100" + parts[2])
    return None

# ==========================
#   MAJBURIY OBUNA ADMIN CALLBACK
# ==========================
@bot.callback_query_handler(func=lambda c: c.data in [
    "req_add", "opt_add", "req_edit", "req_delete", "req_back",
    "req_add_public", "req_add_private",
    "edit_req_list", "edit_opt_list"
])
def req_menu_handler(call):
    data = call.data

    if data == "req_back":
        bot.edit_message_text(
            "⚙️ Admin panelga qaytdingiz.",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=required_menu()
        )
        return

    if data == "req_add":
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("📢 Ommaviy kanal", callback_data="req_add_public"),
            InlineKeyboardButton("🔒 Shaxsiy kanal", callback_data="req_add_private")
        )
        kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_back"))
        bot.edit_message_text(
            "➕ Majburiy kanal turini tanlang:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )
        return

    if data == "req_add_public":
        start_required_add_public(call)
        return

    if data == "req_add_private":
        start_required_add_private(call)
        return

    if data == "opt_add":
        start_optional_add(call)
        return

    if data == "req_edit":
        start_required_edit(call)
        return

    if data == "req_delete":
        start_required_delete(call)
        return

# ==========================
#   OMMAVIY KANAL QO‘SHISH (PUBLIC)
# ==========================
def start_required_add_public(call):
    uid = call.from_user.id
    admin_state[uid] = "req_public_link"
    admin_data[uid] = {}
    bot.edit_message_text(
        "📢 Ommaviy kanal qo‘shish.\n\n"
        "Kanal ulanish havolasini yuboring:\n"
        "• https://t.me/+Qe4Z9nlabmxlMWQy\n"
        "yoki\n"
        "• https://t.me/MyChannel",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_public_link")
def req_public_link_handler(message):
    uid = message.from_user.id
    url = message.text.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        bot.reply_to(message, "❌ Havola noto‘g‘ri. http:// yoki https:// bilan boshlansin.")
        return

    admin_data[uid]["url"] = url
    admin_state[uid] = "req_public_name"
    bot.reply_to(message, "📛 Tugma uchun nom kiriting:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_public_name")
def req_public_name_handler(message):
    uid = message.from_user.id
    name = message.text.strip()

    required_channels.insert_one({
        "type": "public",
        "name": name,
        "url": admin_data[uid]["url"],
        "channel_id": None
    })

    bot.reply_to(message, f"✅ Ommaviy kanal <b>{name}</b> majburiy ro‘yxatga qo‘shildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   SHAXSIY KANAL QO‘SHISH (PRIVATE)
# ==========================
def start_required_add_private(call):
    uid = call.from_user.id
    admin_state[uid] = "req_private_post"
    admin_data[uid] = {}
    bot.edit_message_text(
        "🔒 Shaxsiy kanal qo‘shish.\n\n"
        "POST havolasini yuboring:\n"
        "Masalan: https://t.me/c/123456789/55",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_private_post")
def req_private_post_handler(message):
    uid = message.from_user.id
    url = message.text.strip()

    channel_id = extract_private_id(url)
    if not channel_id:
        bot.reply_to(message, "❌ POST havola noto‘g‘ri.")
        return

    try:
        member = bot.get_chat_member(channel_id, bot.get_me().id)
        if member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "❌ Bot kanalga admin emas.")
            return
    except:
        bot.reply_to(message, "❌ Kanalga ulanib bo‘lmadi.")
        return

    admin_data[uid]["channel_id"] = channel_id
    admin_state[uid] = "req_private_invite"
    bot.reply_to(message, "🔗 Kanalga ulanish havolasini yuboring (faqat t.me/+...):")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_private_invite")
def req_private_invite_handler(message):
    uid = message.from_user.id
    url = message.text.strip()

    if not url.startswith("https://t.me/+") and not url.startswith("http://t.me/+"):
        bot.reply_to(message, "❌ Faqat t.me/+ formatidagi havola yuboring.")
        return

    admin_data[uid]["url"] = url
    admin_state[uid] = "req_private_name"
    bot.reply_to(message, "📛 Tugma uchun nom kiriting:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_private_name")
def req_private_name_handler(message):
    uid = message.from_user.id
    name = message.text.strip()

    required_channels.insert_one({
        "type": "private",
        "name": name,
        "url": admin_data[uid]["url"],
        "channel_id": admin_data[uid]["channel_id"]
    })

    bot.reply_to(message, f"✅ Shaxsiy kanal <b>{name}</b> majburiy ro‘yxatga qo‘shildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   IXT.IYORIY KANAL QO‘SHISH
# ==========================
def start_optional_add(call):
    uid = call.from_user.id
    admin_state[uid] = "opt_url"
    admin_data[uid] = {}
    bot.edit_message_text(
        "➕ Ixtiyoriy kanal qo‘shish.\n\n"
        "Kanal havolasini yuboring (http:// yoki https:// bilan):",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_url")
def opt_url_handler(message):
    uid = message.from_user.id
    url = message.text.strip()

    if not (url.startswith("http://") or url.startswith("https://")):
        bot.reply_to(message, "❌ Havola noto‘g‘ri.")
        return

    admin_data[uid]["url"] = url
    admin_state[uid] = "opt_name"
    bot.reply_to(message, "📛 Tugma uchun nom kiriting:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_name")
def opt_name_handler(message):
    uid = message.from_user.id
    name = message.text.strip()

    optional_channels.insert_one({
        "name": name,
        "url": admin_data[uid]["url"]
    })

    bot.reply_to(message, f"✅ Ixtiyoriy kanal <b>{name}</b> qo‘shildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   TAHRIRLASH MENYUSI
# ==========================
def start_required_edit(call):
    req = list(required_channels.find({}))
    opt = list(optional_channels.find({}))

    kb = InlineKeyboardMarkup()
    if req:
        kb.add(InlineKeyboardButton("📛 Majburiy kanallar", callback_data="edit_req_list"))
    if opt:
        kb.add(InlineKeyboardButton("📛 Ixtiyoriy kanallar", callback_data="edit_opt_list"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_back"))

    bot.edit_message_text(
        "✏️ Tahrirlash bo‘limi:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

# ==========================
#   MAJBURIY KANALLARNI TAHRIRLASH RO‘YXATI
# ==========================
@bot.callback_query_handler(func=lambda c: c.data == "edit_req_list")
def edit_req_list(call):
    channels = list(required_channels.find({}))
    kb = InlineKeyboardMarkup()

    for ch in channels:
        kb.add(
            InlineKeyboardButton(
                f"{'🔒' if ch['type']=='private' else '📢'} {ch['name']}",
                callback_data=f"edit_req:{ch['_id']}"
            )
        )

    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_edit"))

    bot.edit_message_text(
        "✏️ Tahrirlash uchun majburiy kanalni tanlang:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_req:"))
def edit_req_menu(call):
    ch_id = call.data.split(":")[1]
    ch = required_channels.find_one({"_id": ObjectId(ch_id)})

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📛 Nomni o‘zgartirish", callback_data=f"req_edit_name:{ch_id}"))
    kb.add(InlineKeyboardButton("🔗 Havolani o‘zgartirish", callback_data=f"req_edit_url:{ch_id}"))
    kb.add(InlineKeyboardButton("🗑 O‘chirish", callback_data=f"req_delete_one:{ch_id}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="edit_req_list"))

    bot.edit_message_text(
        f"✏️ <b>{ch['name']}</b> kanalini tahrirlash:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

# ==========================
#   MAJBURIY KANAL NOMINI O‘ZGARTIRISH
# ==========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("req_edit_name:"))
def req_edit_name_start(call):
    uid = call.from_user.id
    ch_id = call.data.split(":")[1]

    admin_state[uid] = "req_edit_name"
    admin_data[uid] = {"ch_id": ch_id}

    bot.edit_message_text("📛 Yangi nomni kiriting:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_edit_name")
def req_edit_name_save(message):
    uid = message.from_user.id
    new_name = message.text.strip()
    ch_id = admin_data[uid]["ch_id"]

    required_channels.update_one(
        {"_id": ObjectId(ch_id)},
        {"$set": {"name": new_name}}
    )

    bot.reply_to(message, f"✅ Nom <b>{new_name}</b> ga o‘zgartirildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   MAJBURIY KANAL HAVOLASINI O‘ZGARTIRISH
# ==========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("req_edit_url:"))
def req_edit_url_start(call):
    uid = call.from_user.id
    ch_id = call.data.split(":")[1]

    admin_state[uid] = "req_edit_url"
    admin_data[uid] = {"ch_id": ch_id}

    bot.edit_message_text("🔗 Yangi havolani yuboring:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_edit_url")
def req_edit_url_save(message):
    uid = message.from_user.id
    new_url = message.text.strip()

    if not (new_url.startswith("http://") or new_url.startswith("https://")):
        bot.reply_to(message, "❌ Havola noto‘g‘ri.")
        return

    ch_id = admin_data[uid]["ch_id"]

    required_channels.update_one(
        {"_id": ObjectId(ch_id)},
        {"$set": {"url": new_url}}
    )

    bot.reply_to(message, "✅ Havola yangilandi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   MAJBURIY KANALNI O‘CHIRISH
# ==========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("req_delete_one:"))
def req_delete_one(call):
    ch_id = call.data.split(":")[1]
    required_channels.delete_one({"_id": ObjectId(ch_id)})

    bot.edit_message_text(
        "✅ Majburiy kanal o‘chirildi!",
        call.message.chat.id,
        call.message.message_id
    )

# ==========================
#   IXT.IYORIY KANALLARNI O‘CHIRISH MENYUSI
# ==========================
def start_required_delete(call):
    req = list(required_channels.find({}))
    opt = list(optional_channels.find({}))

    kb = InlineKeyboardMarkup()
    if req:
        kb.add(InlineKeyboardButton("📛 Majburiy kanallar", callback_data="edit_req_list"))
    if opt:
        kb.add(InlineKeyboardButton("📛 Ixtiyoriy kanallar", callback_data="edit_opt_list"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_back"))

    bot.edit_message_text(
        "🗑 O‘chirish bo‘limi:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )
# ==========================
#   OBUNA TEKSHIRISH (FAQAT PRIVATE KANALLAR)
# ==========================
def check_required_subs(user_id):
    required = list(required_channels.find({}))

    for ch in required:
        if ch["type"] == "public":
            continue  # public kanal tekshirilmaydi

        channel_id = ch.get("channel_id")
        if not channel_id:
            continue

        try:
            member = bot.get_chat_member(channel_id, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False

    return True

# ==========================
#   KONTENT YUBORISH
# ==========================
def send_content(chat_id, item):
    if item["type"] == "text":
        bot.send_message(chat_id, item["text"])
    elif item["type"] == "photo":
        bot.send_photo(chat_id, item["file_id"], caption=item.get("caption"))
    elif item["type"] == "video":
        bot.send_video(chat_id, item["file_id"], caption=item.get("caption"))
    elif item["type"] == "document":
        bot.send_document(chat_id, item["file_id"], caption=item.get("caption"))

# ==========================
#   OBUNA OYNASI (PUBLIC + PRIVATE)
# ==========================
def get_required_keyboard(user_id, code):
    required = list(required_channels.find({}))
    optional = list(optional_channels.find({}))

    kb = InlineKeyboardMarkup(row_width=1)

    # Majburiy kanallar tugmalari
    for ch in required:
        kb.add(InlineKeyboardButton(ch["name"], url=ch["url"]))

    # Ixtiyoriy kanallar faqat obuna bo‘lmaganda chiqadi
    if not check_required_subs(user_id):
        for ch in optional:
            kb.add(InlineKeyboardButton(ch["name"], url=ch["url"]))

    kb.add(
        InlineKeyboardButton(
            "✔️ Tekshirish",
            url=f"https://t.me/{BOT_USERNAME}?start=check_{code}"
        )
    )

    return kb

# ==========================
#   /start HANDLER
# ==========================
@bot.message_handler(commands=['start'])
def start_handler(message):
    args = message.text.split()

    if len(args) == 1:
        return show_main_menu(message)

    if args[1].startswith("check_"):
        return check_start(message)

    return start_with_code(message)

# ==========================
#   ASOSIY MENYU
# ==========================
def show_main_menu(message):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📝 Bot Haqida", callback_data="about"),
        InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{message.message_id}")
    )

    bot.reply_to(
        message,
        "<b>Bu bot orqali kanaldagi animelarni yuklab olishingiz mumkin.\n\n"
        "❗️Botga habar yozmang❗️</b>",
        reply_markup=kb
    )

# ==========================
#   /start CODE (KONTENT)
# ==========================
def start_with_code(message):
    code = message.text.split()[1]

    item = contents.find_one({"code": code})
    if not item:
        bot.send_message(message.chat.id, "❌ Kontent topilmadi yoki o‘chirilgan.")
        return

    # Private kanallar bo‘yicha obuna tekshirish
    if not check_required_subs(message.from_user.id):
        kb = get_required_keyboard(message.from_user.id, code)
        bot.send_message(
            message.chat.id,
            "📌 Iltimos quyidagi kanallarga obuna bo‘ling:",
            reply_markup=kb
        )
        return

    # Obuna bo‘lgan → kontent yuboriladi
    send_content(message.chat.id, item)

# ==========================
#   /start check_CODE — TEKSHIRISH
# ==========================
def check_start(message):
    code = message.text.replace("/start check_", "")

    if check_required_subs(message.from_user.id):
        item = contents.find_one({"code": code})
        if item:
            send_content(message.chat.id, item)
    else:
        kb = get_required_keyboard(message.from_user.id, code)
        bot.send_message(
            message.chat.id,
            "❌ Hali hammasiga obuna bo‘lmadingiz!",
            reply_markup=kb
        )

# ==========================
#   CALLBACK HANDLER (ABOUT / CREATOR / CLOSE)
# ==========================
@bot.callback_query_handler(func=lambda call: call.data in ["about", "creator"] or call.data.startswith("close:"))
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
            "<b>"
            "Botni ishlatish qo‘llanmasi:\n"
            "1. Kanallarga obuna bo‘ling\n"
            "2. Tekshirish tugmasini bosing\n"
            "3. Anime yuklab olish tugmasini bosing\n\n"
            "📢 Kanal: <i>@AniGonUz</i>"
            "</b>",
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
            "<b>"
            "• Admin: <i>@Shadow_Sxi</i>\n"
            "• Asosiy Kanal: <i>@AniGonUz</i>\n"
            "• Reklama: <i>@AniReklamaUz</i>\n\n"
            "👨‍💻 Savollar: <i>@AniManxwaBot</i>"
            "</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )

# ==========================
#   MULTI-UPLOAD CONTENT SAQLASH
# ==========================
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def save_multi(message):
    uid = message.from_user.id

    if admin_state.get(uid) != "multi_add":
        return

    time.sleep(0.5)
    code = generate_code()

    if message.content_type == "video":
        content = {"type": "video", "file_id": message.video.file_id, "caption": message.caption, "code": code}
    elif message.content_type == "photo":
        content = {"type": "photo", "file_id": message.photo[-1].file_id, "caption": message.caption, "code": code}
    elif message.content_type == "document":
        content = {"type": "document", "file_id": message.document.file_id, "caption": message.caption, "code": code}
    else:
        content = {"type": "text", "text": message.text, "code": code}

    contents.insert_one(content)
    bot.reply_to(message, f"https://t.me/{BOT_USERNAME}?start={code}")

# ==========================
#   SECURITY CHECK (PRIVATE KANALLAR)
# ==========================
def security_check():
    while True:
        try:
            channels = list(required_channels.find({"type": "private"}))

            for ch in channels:
                channel_id = ch["channel_id"]

                try:
                    member = bot.get_chat_member(channel_id, bot.get_me().id)
                    if member.status in ["administrator", "creator"]:
                        continue

                    required_channels.delete_one({"_id": ch["_id"]})
                    bot.send_message(
                        ADMIN_ID,
                        f"⚠️ Bot <b>{ch['name']}</b> kanalidan chiqarildi.\n"
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

        time.sleep(20)

threading.Thread(target=security_check).start()

# ==========================
#   RUN SERVER
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
