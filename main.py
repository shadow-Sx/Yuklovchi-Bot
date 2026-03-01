import telebot
import json
import os
import random
import string
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
ADMIN_ID = 7797502113
DB_FILE = "db.json"

bot = telebot.TeleBot(TOKEN)

# --- JSON baza ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {"contents": []}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

db = load_db()

# --- Random kod generator ---
def generate_code(length=12):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

# --- Admin holati ---
admin_state = {}

# --- Admin panel ---
def admin_panel():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("Cantent Qo'shish"),
        KeyboardButton("Majburi Obuna")
    )
    markup.row(KeyboardButton("Habar Yuborish"))
    return markup

# --- /start ---
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    args = message.text.split()

    # start parametri bo'lsa → kontentni yuboramiz
    if len(args) > 1:
        code = args[1].replace(f"@{BOT_USERNAME}", "")

        for item in db["contents"]:
            if item.get("code") == code:

                if item["type"] == "text":
                    bot.send_message(uid, item["text"])

                elif item["type"] == "photo":
                    bot.send_photo(uid, item["file_id"], caption=item.get("caption"))

                elif item["type"] == "video":
                    bot.send_video(uid, item["file_id"], caption=item.get("caption"))

                elif item["type"] == "document":
                    bot.send_document(uid, item["file_id"], caption=item.get("caption"))

                return

        bot.send_message(uid, "❗ Kontent topilmadi.")
        return

    # Oddiy start
    if uid == ADMIN_ID:
        bot.send_message(uid, "⚙️ Admin panelga xush kelibsiz!", reply_markup=admin_panel())
    else:
        bot.send_message(uid, "Salom! Botdan foydalanishingiz mumkin 😊")

# --- Admin tugmalari ---
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text in [
    "Cantent Qo'shish", "Majburi Obuna", "Habar Yuborish"
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

# --- Cantentni qabul qilish ---
@bot.message_handler(content_types=['text', 'photo', 'video', 'document'])
def save_content(message):
    uid = message.from_user.id

    # faqat admin va faqat add_content holatida saqlansin
    if uid != ADMIN_ID or admin_state.get(uid) != "add_content":
        return

    # tugma matnlarini saqlamaslik
    if message.text in ["Cantent Qo'shish", "Majburi Obuna", "Habar Yuborish"]:
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

    # faqat havola reply sifatida
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.reply_to(message, link, reply_markup=admin_panel())

    admin_state[uid] = None

bot.infinity_polling()
