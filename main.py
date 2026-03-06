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
from pymongo import MongoClient, ReturnDocument
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
required_channels_collection = db["required_channels"]
optional_channels_collection = db["optional_channels"]
required_stats = db["required_stats"]

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
#   SELF-PING (Render Free)
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
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("Cantent Qo'shish"),
        KeyboardButton("Majburi Obuna")
    )
    markup.row(
        KeyboardButton("Habar Yuborish"),
        KeyboardButton("🔙 Chiqish")
    )
    return markup

def required_menu():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Majburi qo‘shish", callback_data="req_add"),
        InlineKeyboardButton("➕ Ixtiyoriy qo‘shish", callback_data="opt_add")
    )
    kb.add(
        InlineKeyboardButton("✏️ Tahrirlash", callback_data="req_edit"),
        InlineKeyboardButton("🗑 O‘chirish", callback_data="req_delete")
    )
    kb.add(
        InlineKeyboardButton("🔙 Orqaga", callback_data="req_back")
    )
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
    text = message.text

    if text == "Cantent Qo'shish":
        admin_state[uid] = "multi_add"
        bot.reply_to(message, "📥 Hamma videolarni tashlang.\n\nTugagach /stop deb yozing.")

    elif text == "Majburi Obuna":
        bot.send_message(
            message.chat.id,
            "📌 Majburiy obuna bo‘limi:",
            reply_markup=required_menu()
        )

    elif text == "Habar Yuborish":
        bot.reply_to(message, "📨 Bu bo‘lim keyin qo‘shiladi.")

    elif text == "🔙 Chiqish":
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
#   KANAL POST HAVOLASI PARSER (STANDART FORMAT)
# ==========================
def extract_channel_id_from_post(url: str):
    """
    Faqat standart format:
    https://t.me/MyChannel/123
    https://t.me/c/123456789/55
    """
    url = url.replace("https://", "").replace("http://", "")
    parts = url.split("/")

    # private: t.me/c/123456789/55
    if parts[1] == "c":
        return int("-100" + parts[2])

    # public: t.me/MyChannel/123
    username = parts[1]
    chat = bot.get_chat(username)
    return chat.id

# ==========================
#   MAJBURIY OBUNA ADMIN CALLBACK
# ==========================
@bot.callback_query_handler(func=lambda c: c.data in [
    "req_add", "opt_add", "req_edit", "req_delete", "req_back",
    "del_req_list", "del_opt_list",
    "req_add_public", "req_add_private"
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
            "➕ Majburiy kanal qo‘shish turini tanlang:",
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

    if data == "del_req_list":
        delete_required_list(call)
        return

    if data == "del_opt_list":
        delete_optional_list(call)
        return

# ==========================
#   OMMAVIY KANAL QO‘SHISH
# ==========================
def start_required_add_public(call):
    uid = call.from_user.id
    admin_state[uid] = "req_add_public_link"
    admin_data[uid] = {}
    bot.edit_message_text(
        "📢 Ommaviy kanal qo‘shish boshlandi.\n\n"
        "Iltimos kanal POST havolasini yuboring:\n"
        "Masalan: https://t.me/MyChannel/123",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_public_link")
def req_add_public_link_handler(message):
    uid = message.from_user.id
    url = message.text.strip()

    try:
        channel_id = extract_channel_id_from_post(url)
    except:
        bot.reply_to(message, "❌ Havola noto‘g‘ri. Faqat POST havolasi yuboring.")
        return

    try:
        member = bot.get_chat_member(channel_id, bot.get_me().id)
        if member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "❌ Bot kanalda admin emas. Avval botni kanalga admin qiling.")
            return
    except:
        bot.reply_to(message, "❌ Kanalga ulanib bo‘lmadi.")
        return

    admin_data[uid]["channel_id"] = channel_id
    admin_state[uid] = "req_add_invite_url"
    bot.reply_to(
        message,
        "🔗 Endi foydalanuvchilar kanalga qo‘shiladigan asosiy havolani yuboring."
    )

# ==========================
#   SHAXSIY KANAL QO‘SHISH
# ==========================
def start_required_add_private(call):
    uid = call.from_user.id
    admin_state[uid] = "req_add_private_link"
    admin_data[uid] = {}
    bot.edit_message_text(
        "🔒 Shaxsiy kanal qo‘shish boshlandi.\n\n"
        "Iltimos kanal POST havolasini yuboring:\n"
        "Masalan: https://t.me/c/123456789/55",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_private_link")
def req_add_private_link_handler(message):
    uid = message.from_user.id
    url = message.text.strip()

    try:
        channel_id = extract_channel_id_from_post(url)
    except:
        bot.reply_to(message, "❌ Havola noto‘g‘ri. Faqat POST havolasi yuboring.")
        return

    try:
        member = bot.get_chat_member(channel_id, bot.get_me().id)
        if member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "❌ Bot kanalda admin emas.")
            return
    except:
        bot.reply_to(message, "❌ Kanalga ulanib bo‘lmadi.")
        return

    admin_data[uid]["channel_id"] = channel_id
    admin_state[uid] = "req_add_invite_url"
    bot.reply_to(
        message,
        "🔗 Endi foydalanuvchilar kanalga qo‘shiladigan asosiy havolani yuboring."
    )
    
# ==========================
#   IXT.IYORIY KANAL QO‘SHISH (SODDA)
# ==========================
def start_optional_add(call):
    uid = call.from_user.id
    admin_state[uid] = "opt_add_url"
    admin_data[uid] = {}
    bot.edit_message_text(
        "➕ Ixtiyoriy kanal qo‘shish boshlandi.\n\n"
        "Iltimos kanal havolasini yuboring:",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_add_url")
def opt_get_url(message):
    uid = message.from_user.id
    url = message.text.strip()

    admin_data[uid]["url"] = url
    admin_state[uid] = "opt_add_name"
    bot.reply_to(message, "📛 Ixtiyoriy kanal uchun nom kiriting:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_add_name")
def opt_get_name(message):
    uid = message.from_user.id
    name = message.text.strip()

    new_channel = {
        "type": "optional",
        "name": name,
        "url": admin_data[uid]["url"]
    }

    optional_channels_collection.insert_one(new_channel)

    bot.reply_to(message, f"✅ Ixtiyoriy kanal <b>{name}</b> qo‘shildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   MAJBURIY KANALLARNI TAHRIRLASH (STATISTIKA BILAN)
# ==========================
def start_required_edit(call):
    channels = list(required_channels_collection.find({}))

    if not channels:
        bot.edit_message_text(
            "❌ Majburiy kanallar yo‘q.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    kb = InlineKeyboardMarkup()

    for ch in channels:
        kb.add(
            InlineKeyboardButton(
                f"{ch['name']} (ID: {ch['channel_id']})",
                callback_data=f"edit_req:{ch['_id']}"
            )
        )

    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_back"))

    bot.edit_message_text(
        "✏️ Tahrirlash uchun kanalni tanlang:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_req:"))
def edit_required_menu(call):
    ch_id = call.data.split(":")[1]
    ch = required_channels_collection.find_one({"_id": ObjectId(ch_id)})

    if not ch:
        bot.answer_callback_query(call.id, "❌ Kanal topilmadi.")
        return

    qolgan = ch["count"] - ch["joined_count"]

    text = (
        f"📊 <b>{ch['name']}</b> kanal holati:\n\n"
        f"🆔 ID: <code>{ch['channel_id']}</code>\n"
        f"🔗 Havola: {ch['url']}\n\n"
        f"👥 Kerak: <b>{ch['count']}</b> ta\n"
        f"➕ Qo‘shilgan: <b>{ch['joined_count']}</b> ta\n"
        f"⏳ Qolgan: <b>{qolgan}</b> ta\n"
    )

    kb = InlineKeyboardMarkup()

    if ch.get("auto"):
        kb.add(InlineKeyboardButton("📛 Nom (o‘zgartirib bo‘lmaydi)", callback_data="none"))
    else:
        kb.add(InlineKeyboardButton("📛 Nomni o‘zgartirish", callback_data=f"edit_name:{ch_id}"))

    kb.add(
        InlineKeyboardButton("🔗 Havolani o‘zgartirish", callback_data=f"edit_url:{ch_id}"),
        InlineKeyboardButton("👥 Miqdorni o‘zgartirish", callback_data=f"edit_count:{ch_id}")
    )

    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_edit"))

    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

# ==========================
#   NOMNI O‘ZGARTIRISH
# ==========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_name:"))
def edit_name_start(call):
    uid = call.from_user.id
    ch_id = call.data.split(":")[1]
    admin_state[uid] = "edit_name_state"
    admin_data[uid] = {"ch_id": ch_id}

    bot.edit_message_text(
        "📛 Yangi nomni kiriting:",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "edit_name_state")
def edit_name_save(message):
    uid = message.from_user.id
    new_name = message.text.strip()
    ch_id = admin_data[uid]["ch_id"]

    required_channels_collection.update_one(
        {"_id": ObjectId(ch_id)},
        {"$set": {"name": new_name}}
    )

    bot.reply_to(message, f"✅ Nom <b>{new_name}</b> ga o‘zgartirildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   HAVOLANI O‘ZGARTIRISH
# ==========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_url:"))
def edit_url_start(call):
    uid = call.from_user.id
    ch_id = call.data.split(":")[1]
    admin_state[uid] = "edit_url_state"
    admin_data[uid] = {"ch_id": ch_id}

    bot.edit_message_text(
        "🔗 Yangi havolani yuboring:",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "edit_url_state")
def edit_url_save(message):
    uid = message.from_user.id
    new_url = message.text.strip()
    ch_id = admin_data[uid]["ch_id"]

    required_channels_collection.update_one(
        {"_id": ObjectId(ch_id)},
        {"$set": {"url": new_url}}
    )

    bot.reply_to(message, "✅ Havola yangilandi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   MIQDORNI O‘ZGARTIRISH
# ==========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_count:"))
def edit_count_start(call):
    uid = call.from_user.id
    ch_id = call.data.split(":")[1]
    admin_state[uid] = "edit_count_state"
    admin_data[uid] = {"ch_id": ch_id}

    bot.edit_message_text(
        "👥 Yangi miqdorni kiriting:",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "edit_count_state")
def edit_count_save(message):
    uid = message.from_user.id
    try:
        new_count = int(message.text)
        if new_count <= 0:
            raise ValueError
    except:
        bot.reply_to(message, "❌ Miqdor faqat musbat raqam bo‘lishi kerak.")
        return

    ch_id = admin_data[uid]["ch_id"]

    required_channels_collection.update_one(
        {"_id": ObjectId(ch_id)},
        {"$set": {"count": new_count}}
    )

    bot.reply_to(message, f"✅ Miqdor {new_count} ga o‘zgartirildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   MAJBURIY / IXT.IYORIY O‘CHIRISH
# ==========================
def start_required_delete(call):
    req = list(required_channels_collection.find({}))
    opt = list(optional_channels_collection.find({}))

    kb = InlineKeyboardMarkup()

    if req:
        kb.add(InlineKeyboardButton("📛 Majburiy kanallar", callback_data="del_req_list"))
    if opt:
        kb.add(InlineKeyboardButton("📛 Ixtiyoriy kanallar", callback_data="del_opt_list"))

    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_back"))

    bot.edit_message_text(
        "🗑 O‘chirish bo‘limi:\nQaysi turdagi kanallarni o‘chirmoqchisiz?",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

def delete_required_list(call):
    channels = list(required_channels_collection.find({}))

    kb = InlineKeyboardMarkup()

    for ch in channels:
        kb.add(
            InlineKeyboardButton(
                f"{ch['name']} (ID: {ch['channel_id']})",
                callback_data=f"del_req:{ch['_id']}"
            )
        )

    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_delete"))

    bot.edit_message_text(
        "🗑 O‘chirish uchun majburiy kanalni tanlang:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

def delete_optional_list(call):
    channels = list(optional_channels_collection.find({}))

    kb = InlineKeyboardMarkup()

    for ch in channels:
        kb.add(
            InlineKeyboardButton(
                f"{ch['name']}",
                callback_data=f"del_opt:{ch['_id']}"
            )
        )

    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_delete"))

    bot.edit_message_text(
        "🗑 O‘chirish uchun ixtiyoriy kanalni tanlang:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_req:"))
def delete_required_confirm(call):
    ch_id = call.data.split(":")[1]
    ch = required_channels_collection.find_one({"_id": ObjectId(ch_id)})

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("❌ Ha, o‘chirish", callback_data=f"del_req_yes:{ch_id}"),
        InlineKeyboardButton("🔙 Bekor qilish", callback_data="del_req_list")
    )

    bot.edit_message_text(
        f"⚠️ <b>{ch['name']}</b> kanalini o‘chirmoqchimisiz?",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_opt:"))
def delete_optional_confirm(call):
    ch_id = call.data.split(":")[1]
    ch = optional_channels_collection.find_one({"_id": ObjectId(ch_id)})

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("❌ Ha, o‘chirish", callback_data=f"del_opt_yes:{ch_id}"),
        InlineKeyboardButton("🔙 Bekor qilish", callback_data="del_opt_list")
    )

    bot.edit_message_text(
        f"⚠️ <b>{ch['name']}</b> kanalini o‘chirmoqchimisiz?",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_req_yes:"))
def delete_required_yes(call):
    ch_id = call.data.split(":")[1]

    required_channels_collection.delete_one({"_id": ObjectId(ch_id)})

    auto_channels = list(required_channels_collection.find({"auto": True}))
    auto_channels.sort(key=lambda x: x["name"])

    for i, ch in enumerate(auto_channels):
        new_name = f"{i+1}-Kanal"
        required_channels_collection.update_one(
            {"_id": ch["_id"]},
            {"$set": {"name": new_name}}
        )

    bot.edit_message_text(
        "✅ Kanal o‘chirildi!",
        call.message.chat.id,
        call.message.message_id
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_opt_yes:"))
def delete_optional_yes(call):
    ch_id = call.data.split(":")[1]

    optional_channels_collection.delete_one({"_id": ObjectId(ch_id)})

    bot.edit_message_text(
        "✅ Ixtiyoriy kanal o‘chirildi!",
        call.message.chat.id,
        call.message.message_id
    )

# ==========================
#   REQUEST-TO-JOIN STATUSLARINI HAM OBUNA DEB HISOBLASH
# ==========================
def is_subscribed(member):
    if member.status in ["member", "administrator", "creator"]:
        return True

    if member.status == "restricted":
        return True

    if member.status == "left" and getattr(member, "until_date", 0) != 0:
        return True

    return False

# ==========================
#   MAJBURIY OBUNA TEKSHIRISH
# ==========================
def check_required_subs(user_id):
    required = list(required_channels_collection.find({}))

    for ch in required:
        try:
            member = bot.get_chat_member(ch["channel_id"], user_id)
            if not is_subscribed(member):
                return False
        except:
            return False

    return True

# ==========================
#   OBUNACHI SANASH (joined_count)
# ==========================
def handle_join_counts(user_id):
    channels = list(required_channels_collection.find({}))

    for ch in channels:
        ch_id = ch["_id"]
        channel_id = ch["channel_id"]

        try:
            member = bot.get_chat_member(channel_id, user_id)
            if is_subscribed(member):

                exists = required_stats.find_one({
                    "channel_id": channel_id,
                    "user_id": user_id
                })
                if exists:
                    continue

                required_stats.insert_one({
                    "channel_id": channel_id,
                    "user_id": user_id
                })

                updated = required_channels_collection.find_one_and_update(
                    {"_id": ch_id},
                    {"$inc": {"joined_count": 1}},
                    return_document=ReturnDocument.AFTER
                )

                if updated and not updated.get("completed") and updated["joined_count"] >= updated["count"]:
                    required_channels_collection.update_one(
                        {"_id": ch_id},
                        {"$set": {"completed": True}}
                    )
                    bot.send_message(
                        ADMIN_ID,
                        f"🎉 <b>{updated['name']}</b> kanaliga barcha {updated['count']} ta obunachi qo‘shib berildi!"
                    )

        except Exception as e:
            print("handle_join_counts error:", e)

# ==========================
#   MAJBURIY OBUNA OYNASI (URL TEKSHIRISH TUGMASI BILAN)
# ==========================
def get_required_keyboard(user_id, code):
    required = list(required_channels_collection.find({}))
    optional = list(optional_channels_collection.find({}))

    kb = InlineKeyboardMarkup(row_width=1)

    for ch in required:
        kb.add(InlineKeyboardButton(ch["name"], url=ch["url"]))

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
#   /start (ODDIY)
# ==========================
@bot.message_handler(commands=['start'])
def start_handler(message):
    args = message.text.split()

    # /start
    if len(args) == 1:
        return show_main_menu(message)

    # /start check_CODE
    if args[1].startswith("check_"):
        return check_start(message)

    # /start CODE
    return start_with_code(message)


def show_main_menu(message):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📝 Bot Haqida", callback_data="about"),
        InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{message.message_id}")
    )

    bot.reply_to(
        message,
        "<b>Bu bot orqali kanaldagi animelarni yuklab olishingiz mumkin.\n\n"
        "❗️Botga habar yozmang❗️</b>",
        reply_markup=markup
    )


# ==========================
#   /start CODE (MAJBURIY OBUNA BILAN)
# ==========================
def start_with_code(message):
    code = message.text.split()[1]

    item = contents.find_one({"code": code})
    if not item:
        bot.send_message(message.chat.id, "❌ Kontent topilmadi yoki o‘chirilgan.")
        return

    if not check_required_subs(message.from_user.id):
        kb = get_required_keyboard(message.from_user.id, code)
        bot.send_message(
            message.chat.id,
            "📌 Iltimos quyidagi kanallarga obuna bo‘ling:",
            reply_markup=kb
        )
        return

    handle_join_counts(message.from_user.id)
    send_content(message.chat.id, item)


# ==========================
#   /start check_CODE — URL TEKSHIRISH
# ==========================
def check_start(message):
    code = message.text.replace("/start check_", "")

    if check_required_subs(message.from_user.id):
        handle_join_counts(message.from_user.id)

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
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("👨‍💻 Yaratuvchi", callback_data="creator"),
            InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{call.message.message_id}")
        )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=(
                "<b>"
                "Botni ishlatishni bilmaganlar uchun!\n\n"
                "❏ Botni ishlatish qo'llanmasi:\n"
                "1. Kanallarga obuna bo'ling!\n"
                "2. Tekshirish tugmasini bosing ✅\n"
                "3. Kanaldagi anime post past qismidagi yuklab olish tugmasini bosing\n\n"
                "📢 Kanal: <i>@AniGonUz</i>"
                "</b>"
            ),
            reply_markup=markup
        )

    if data == "creator":
        markup = InlineKeyboardMarkup()
        markup.add(
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
                "• Reklama: <i>@AniReklamaUz</i>\n\n"
                "👨‍💻 Savollar Boʻlsa: <i>@AniManxwaBot</i>"
                "</b>"
            ),
            reply_markup=markup
        )


# ==========================
#   MULTI-UPLOAD CONTENT SAVING
# ==========================
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def save_multi(message):
    uid = message.from_user.id

    if admin_state.get(uid) != "multi_add":
        return

    time.sleep(0.7)

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
#   XAVFSIZLIK: BOT ADMIN EMAS BO‘LSA KANALNI O‘CHIRISH
# ==========================
def security_check():
    while True:
        try:
            channels = list(required_channels_collection.find({}))

            for ch in channels:
                channel_id = ch["channel_id"]

                try:
                    member = bot.get_chat_member(channel_id, bot.get_me().id)

                    if member.status in ["administrator", "creator"]:
                        continue

                    required_channels_collection.delete_one({"_id": ch["_id"]})

                    bot.send_message(
                        ADMIN_ID,
                        f"⚠️ <b>{ch['name']}</b> kanalidan chiqarildim.\n"
                        f"Iltimos meni yana admin qiling.\n\n"
                        f"Kanal vaqtincha majburiy ro‘yxatdan o‘chirildi."
                    )

                except:
                    required_channels_collection.delete_one({"_id": ch["_id"]})

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
