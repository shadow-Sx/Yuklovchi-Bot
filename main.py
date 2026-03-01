import telebot
import json
import os
import random
import string
from flask import Flask, request
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
ADMIN_ID = 7797502113
DB_FILE = "db.json"

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ==========================
#   FLASK SERVER
# ==========================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running"

@app.route('/webhook', methods=['POST'])
def webhook():
    json_data = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "OK", 200

# ==========================
#   JSON DATABASE
# ==========================
def load_db():
    if not os.path.exists(DB_FILE):
        return {"contents": []}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_db()

# ==========================
#   RANDOM CODE GENERATOR
# ==========================
def generate_code(length=12):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

admin_state = {}

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

# ==========================
#   /admin COMMAND
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
        admin_state[uid] = "add_content"
        bot.reply_to(message, "📥 Cantent yuboring:")

    elif text == "Majburi Obuna":
        bot.reply_to(message, "📌 Bu bo‘lim keyin qo‘shiladi.")

    elif text == "Habar Yuborish":
        bot.reply_to(message, "📨 Bu bo‘lim keyin qo‘shiladi.")

    elif text == "🔙 Chiqish":
        admin_state[uid] = None
        bot.send_message(uid, "Admin paneldan chiqdingiz.", reply_markup=telebot.types.ReplyKeyboardRemove())

# ==========================
#   /start (ODDIY)
# ==========================
@bot.message_handler(func=lambda m: m.text == "/start")
def start(message):
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
#   START-LINK CONTENT VIEW
# ==========================
@bot.message_handler(func=lambda m: m.text.startswith("/start ") and len(m.text.split()) == 2)
def start_with_code(message):
    code = message.text.split()[1]

    for item in db["contents"]:
        if item["code"] == code:

            if item["type"] == "text":
                bot.send_message(message.chat.id, item["text"])
                return

            if item["type"] == "photo":
                bot.send_photo(message.chat.chat.id, item["file_id"], caption=item.get("caption"))
                return

            if item["type"] == "video":
                bot.send_video(message.chat.id, item["file_id"], caption=item.get("caption"))
                return

            if item["type"] == "document":
                bot.send_document(message.chat.id, item["file_id"], caption=item.get("caption"))
                return

    bot.send_message(message.chat.id, "❌ Kontent topilmadi yoki o‘chirilgan.")

# ==========================
#   CALLBACK HANDLER
# ==========================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    data = call.data

    if data.startswith("close"):
        start_msg_id = int(data.split(":")[1])
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.delete_message(call.message.chat.id, start_msg_id)
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
#   CONTENT SAVING
# ==========================
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def save_content(message):
    uid = message.from_user.id

    if uid != ADMIN_ID or admin_state.get(uid) != "add_content":
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

# ==========================
#   RUN FLASK SERVER
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
