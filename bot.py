import telebot
import json
import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 7797502113  # Sizning ID'ingiz

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

DATA_FILE = "data/messages.json"

# JSON mavjud bo'lmasa yaratamiz
if not os.path.exists("data"):
    os.mkdir("data")

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump([], f)


def load_messages():
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_messages(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ---------------------- START ----------------------

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Bot ishlamoqda.")


# ---------------------- ADMIN PANEL ----------------------

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📥 Habar Qo'shish", "📤 Habar Yuborish")
    markup.add("📌 Majburi Obuna")

    bot.send_message(message.chat.id, "Admin panel:", reply_markup=markup)


# ---------------------- HABAR QO‘SHISH ----------------------

@bot.message_handler(func=lambda m: m.text == "📥 Habar Qo'shish")
def add_message_start(message):
    if message.from_user.id != ADMIN_ID:
        return

    bot.send_message(message.chat.id, "Istalgan faylni yuboring (rasm, video, mp3, pdf, zip va boshqalar).")


@bot.message_handler(content_types=[
    'photo', 'video', 'document', 'audio', 'voice', 'animation'
])
def save_any_file(message):
    if message.from_user.id != ADMIN_ID:
        return

    data = load_messages()

    # Fayl turini aniqlaymiz
    if message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"

    elif message.video:
        file_id = message.video.file_id
        file_type = "video"

    elif message.document:
        file_id = message.document.file_id
        file_type = f"document ({message.document.mime_type})"

    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"

    elif message.voice:
        file_id = message.voice.file_id
        file_type = "voice"

    elif message.animation:
