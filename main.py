ADMIN_ID = 7797502113  # allaqachon bor bo‘lsa, qayta yozish shart emas
admin_state = {}       # allaqachon bor bo‘lsa, qayta yozish shart emas

from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# ==========================
#   ADMIN PANEL KLAVIATURA
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

# ==========================
#   /admin KOMANDASI
# ==========================
@bot.message_handler(commands=['admin'])
def admin_start(message):
    uid = message.from_user.id

    if uid != ADMIN_ID:
        bot.reply_to(message, "❌ Siz admin emassiz!")
        return

    bot.reply_to(
        message,
        "⚙️ Admin panelga xush kelibsiz!",
        reply_markup=admin_panel()
    )

# ==========================
#   ADMIN TUGMALARI
# ==========================
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text in [
    "Cantent Qo'shish", "Majburi Obuna", "Habar Yuborish", "🔙 Chiqish"
])
def admin_buttons(message):
    text = message.text
    uid = message.from_user.id

    if text == "Cantent Qo'shish":
        admin_state[uid] = "add_content"
        bot.reply_to(message, "📥 Cantent yuboring:")

    elif text == "Majburi Obuna":
        bot.reply_to(message, "📌 Bu bo‘lim keyin qo‘shiladi.")

    elif text == "Habar Yuborish":
        bot.reply_to(message, "📨 Bu bo‘lim keyin qo‘shiladi.")

    elif text == "🔙 Chiqish":
        admin_state[uid] = None
        bot.send_message(
            uid,
            "Admin paneldan chiqdingiz.",
            reply_markup=telebot.types.ReplyKeyboardRemove()
        )

# ==========================
#   CANTENT SAQLASH QISMI
# ==========================
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def save_content(message):
    uid = message.from_user.id

    # faqat admin va faqat add_content holatida
    if uid != ADMIN_ID or admin_state.get(uid) != "add_content":
        return

    if message.text in ["Cantent Qo'shish", "Majburi Obuna", "Habar Yuborish", "🔙 Chiqish"]:
        return

    content = {}
    code = generate_code()

    if message.content_type == "text":
        content = {"type": "text", "text": message.text, "code": code}

    elif message.content_type == "photo":
        content = {
            "type": "photo",
            "file_id": message.photo[-1].file_id,
            "caption": message.caption,
            "code": code
        }

    elif message.content_type == "video":
        content = {
            "type": "video",
            "file_id": message.video.file_id,
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

    db["contents"].append(content)
    save_db(db)

    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.reply_to(message, link, reply_markup=admin_panel())

    admin_state[uid] = None
