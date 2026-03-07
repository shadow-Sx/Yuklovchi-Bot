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
joined_users = db["joined_users"]

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
#   KEEP ALIVE
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
#   RANDOM CODE
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
        InlineKeyboardButton("➕ Majburi qo‘shish", callback_data="req_add"),
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
#   /stop
# ==========================
@bot.message_handler(commands=['stop'])
def stop(message):
    uid = message.from_user.id
    if admin_state.get(uid) == "multi_add":
        admin_state[uid] = None
        bot.reply_to(message, "✅ Barcha kontentlar qabul qilindi.", reply_markup=admin_panel())

# ==========================
#   CALLBACK HANDLER
# ==========================
@bot.callback_query_handler(func=lambda c: c.data in [
    "req_add", "opt_add", "req_edit", "req_delete", "req_back",
    "del_req_list", "del_opt_list"
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
        start_required_add(call)
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
#   MAJBURIY KANAL QO‘SHISH (PUBLIC ONLY)
# ==========================
def start_required_add(call):
    uid = call.from_user.id
    admin_state[uid] = "req_add_id"
    admin_data[uid] = {}
    bot.edit_message_text(
        "➕ Majburiy kanal qo‘shish boshlandi.\n\n"
        "Iltimos kanal ID raqamini yuboring:",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_id")
def req_add_id(message):
    uid = message.from_user.id

    try:
        channel_id = int(message.text)
    except:
        bot.reply_to(message, "❌ ID faqat raqam bo‘lishi kerak.")
        return

    try:
        chat = bot.get_chat(channel_id)
        if not chat.username:
            bot.reply_to(message, "❌ Bu public kanal emas. Username bo‘lishi shart.")
            return
    except:
        bot.reply_to(message, "❌ Kanalga ulanib bo‘lmadi. ID xato.")
        return

    admin_data[uid]["channel_id"] = channel_id
    admin_data[uid]["username"] = chat.username

    admin_state[uid] = "req_add_count"
    bot.reply_to(message, "👥 Iltimos kanalga qo‘shilishi kerak bo‘lgan miqdorni kiriting:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_count")
def req_add_count(message):
    uid = message.from_user.id

    try:
        count = int(message.text)
        if count <= 0:
            raise ValueError
    except:
        bot.reply_to(message, "❌ Miqdor faqat musbat raqam bo‘lishi kerak.")
        return

    admin_data[uid]["count"] = count

    total = required_channels.count_documents({})
    auto_name = f"{total + 1}-Kanal"

    channel_id = admin_data[uid]["channel_id"]
    username = admin_data[uid]["username"]

    invite_link = f"https://t.me/{username}"

    required_channels.insert_one({
        "name": auto_name,
        "channel_id": channel_id,
        "url": invite_link,
        "count": count,
        "joined": 0,
        "auto": True,
        "completed": False
    })

    bot.reply_to(
        message,
        f"✅ Majburiy kanal qo‘shildi!\n\n"
        f"📛 Nomi: <b>{auto_name}</b>\n"
        f"🆔 ID: <code>{channel_id}</code>\n"
        f"🔗 Havola: {invite_link}\n"
        f"👥 Miqdor: {count}"
    )

    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   IXT.IYORIY KANAL QO‘SHISH (O‘ZGARMAGAN)
# ==========================
def start_optional_add(call):
    uid = call.from_user.id
    admin_state[uid] = "opt_add_id"
    admin_data[uid] = {}
    bot.edit_message_text(
        "➕ Ixtiyoriy kanal qo‘shish boshlandi.\n\nIltimos kanal ID raqamini yuboring:",
        call.message.chat.id,
        call.message.message_id
    )

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_add_id")
def opt_get_id(message):
    uid = message.from_user.id
    try:
        channel_id = int(message.text)
    except:
        bot.reply_to(message, "❌ ID faqat raqam bo‘lishi kerak.")
        return

    admin_data[uid]["channel_id"] = channel_id
    admin_state[uid] = "opt_add_url"
    bot.reply_to(message, "🔗 Endi kanal havolasini yuboring:")

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
    data = admin_data.get(uid, {})

    optional_channels.insert_one({
        "name": name,
        "channel_id": data["channel_id"],
        "url": data["url"]
    })

    bot.reply_to(message, f"✅ Ixtiyoriy kanal <b>{name}</b> qo‘shildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   MAJBURIY KANALLARNI TAHRIRLASH
# ==========================
def start_required_edit(call):
    channels = list(required_channels.find({}))

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
    ch = required_channels.find_one({"_id": ObjectId(ch_id)})

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("👥 Miqdorni o‘zgartirish", callback_data=f"edit_count:{ch_id}"))
    kb.add(InlineKeyboardButton("🗑 O‘chirish", callback_data=f"del_req:{ch_id}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_edit"))

    bot.edit_message_text(
        f"✏️ <b>{ch['name']}</b> kanalini tahrirlash:\n\n"
        f"🆔 ID: <code>{ch['channel_id']}</code>\n"
        f"🔗 Havola: {ch['url']}\n"
        f"👥 Kerak: {ch['count']}\n"
        f"➕ Qo‘shilgan: {ch.get('joined', 0)}",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

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
    except:
        bot.reply_to(message, "❌ Miqdor faqat raqam bo‘lishi kerak.")
        return

    ch_id = admin_data[uid]["ch_id"]

    required_channels.update_one(
        {"_id": ObjectId(ch_id)},
        {"$set": {"count": new_count}}
    )

    bot.reply_to(message, f"✅ Miqdor {new_count} ga o‘zgartirildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   O‘CHIRISH
# ==========================
def start_required_delete(call):
    channels = list(required_channels.find({}))

    kb = InlineKeyboardMarkup()

    for ch in channels:
        kb.add(
            InlineKeyboardButton(
                f"{ch['name']} (ID: {ch['channel_id']})",
                callback_data=f"del_req:{ch['_id']}"
            )
        )

    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_back"))

    bot.edit_message_text(
        "🗑 O‘chirish uchun kanalni tanlang:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_req:"))
def delete_required(call):
    ch_id = call.data.split(":")[1]
    required_channels.delete_one({"_id": ObjectId(ch_id)})

    bot.edit_message_text(
        "🗑 Kanal o‘chirildi!",
        call.message.chat.id,
        call.message.message_id
    )

# ==========================
#   OBUNA TEKSHIRISH
# ==========================
def check_required_subs(user_id):
    channels = list(required_channels.find({}))

    for ch in channels:
        try:
            member = bot.get_chat_member(ch["channel_id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False

    return True

# ==========================
#   /start
# ==========================
@bot.message_handler(func=lambda m: m.text == "/start")
def start(message):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📝 Bot Haqida", callback_data="about"),
        InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{message.message_id}")
    )

    bot.reply_to(
        message,
        "<b>Bu bot orqali kanaldagi animelarni yuklab olishingiz mumkin.</b>",
        reply_markup=kb
    )

# ==========================
#   START-LINK CONTENT
# ==========================
@bot.message_handler(func=lambda m: m.text.startswith("/start ") and len(m.text.split()) == 2)
def start_with_code(message):
    code = message.text.split()[1]

    # Agar bu check bo‘lsa → tekshirishga yuboramiz
    if code.startswith("check_"):
        real_code = code.replace("check_", "")
        return check_start(message, real_code)

    item = contents.find_one({"code": code})
    if not item:
        bot.send_message(message.chat.id, "❌ Kontent topilmadi.")
        return

    if not check_required_subs(message.from_user.id):
        kb = InlineKeyboardMarkup()

        for ch in required_channels.find({}):
            kb.add(InlineKeyboardButton(ch["name"], url=ch["url"]))

        # URL tugma — callback emas!
        kb.add(
            InlineKeyboardButton(
                "✔️ Tekshirish",
                url=f"https://t.me/{BOT_USERNAME}?start=check_{code}"
            )
        )

        bot.send_message(
            message.chat.id,
            "📌 Iltimos quyidagi kanallarga obuna bo‘ling:",
            reply_markup=kb
        )
        return

    send_content(message.chat.id, item)

# ==========================
#   CHECK START HANDLER
# ==========================
def check_start(message, code):
    if check_required_subs(message.from_user.id):
        item = contents.find_one({"code": code})
        if item:
            send_content(message.chat.id, item)
    else:
        kb = InlineKeyboardMarkup()

        for ch in required_channels.find({}):
            kb.add(InlineKeyboardButton(ch["name"], url=ch["url"]))

        kb.add(
            InlineKeyboardButton(
                "✔️ Tekshirish",
                url=f"https://t.me/{BOT_USERNAME}?start=check_{code}"
            )
        )

        bot.send_message(
            message.chat.id,
            "❌ Hali hammasiga obuna bo‘lmadingiz!",
            reply_markup=kb
        )


# ==========================
#   CALLBACK HANDLER (ABOUT / CREATOR / CLOSE)
# ==========================
@bot.callback_query_handler(func=lambda call: True)
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
            "Botni ishlatishni bilmaganlar uchun!\n\n"
            "❏ Botni ishlatish qo'llanmasi:\n"
            "1. Kanallarga obuna bo'ling!\n"
            "2. Tekshirish tugmasini bosing\n"
            "3. Anime yuklab olish tugmasini bosing\n\n"
            "📢 Kanal: <i>@AniGonUz</i>"
            "</b>",
            call.message.chat.id,
            call.message.message_id,
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
        return


# ==========================
#   MULTI-UPLOAD CONTENT SAVING
# ==========================
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def save_multi(message):
    uid = message.from_user.id

    if admin_state.get(uid) != "multi_add":
        return

    time.sleep(0.5)
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

    bot.reply_to(message, f"https://t.me/{BOT_USERNAME}?start={code}")


# ==========================
#   SECURITY CHECK (BOT ADMIN EMAS BO‘LSA)
# ==========================
def security_check():
    while True:
        try:
            channels = list(required_channels.find({}))

            for ch in channels:
                channel_id = ch["channel_id"]

                try:
                    member = bot.get_chat_member(channel_id, bot.get_me().id)

                    if member.status in ["administrator", "creator"]:
                        continue

                    required_channels.delete_one({"_id": ch["_id"]})

                    bot.send_message(
                        ADMIN_ID,
                        f"⚠️ <b>{ch['name']}</b> kanalidan chiqarildim.\n"
                        f"Iltimos meni yana admin qiling.\n\n"
                        f"Kanal vaqtincha majburiy ro‘yxatdan o‘chirildi."
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
