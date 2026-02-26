import telebot
import json
import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 123456789  # O'zingizning Telegram ID'ingizni yozing

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


# ---------------------- ADMIN PANEL ----------------------

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Bot ishlamoqda.")


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

    bot.send_message(message.chat.id, "Istalgan faylni yuboring (rasm, video, mp3, pdf va boshqalar).")


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
        file_id = message.animation.file_id
        file_type = "gif"

    else:
        bot.reply_to(message, "Bu fayl turi qo‘llab-quvvatlanmaydi.")
        return

    entry = {
        "id": len(data) + 1,
        "file_id": file_id,
        "type": file_type
    }

    data.append(entry)
    save_messages(data)

    bot.reply_to(
        message,
        f"Fayl saqlandi!\n"
        f"ID: <code>{entry['id']}</code>\n"
        f"Fayl turi: <b>{file_type}</b>\n"
        f"Havola: <code>{file_id}</code>"
    )


# ---------------------- HABAR YUBORISH ----------------------

@bot.message_handler(func=lambda m: m.text == "📤 Habar Yuborish")
def send_message_start(message):
    if message.from_user.id != ADMIN_ID:
        return

    bot.send_message(message.chat.id, "Qaysi ID dagi faylni yuboramiz?\nID kiriting.")


@bot.message_handler(func=lambda m: m.text.isdigit())
def send_saved_media(message):
    if message.from_user.id != ADMIN_ID:
        return

    msg_id = int(message.text)
    data = load_messages()

    item = next((x for x in data if x["id"] == msg_id), None)

    if not item:
        bot.send_message(message.chat.id, "Bunday ID topilmadi.")
        return

    t = item["type"]
    f = item["file_id"]

    if "photo" in t:
        bot.send_photo(message.chat.id, f)
    elif "video" in t:
        bot.send_video(message.chat.id, f)
    elif "audio" in t:
        bot.send_audio(message.chat.id, f)
    elif "voice" in t:
        bot.send_voice(message.chat.id, f)
    elif "gif" in t:
        bot.send_animation(message.chat.id, f)
    else:
        bot.send_document(message.chat.id, f)

    bot.send_message(message.chat.id, "Yuborildi!")


# ---------------------- MAJBURI OBUNA ----------------------

@bot.message_handler(func=lambda m: m.text == "📌 Majburi Obuna")
def sub_settings(message):
    if message.from_user.id != ADMIN_ID:
        return

    bot.send_message(message.chat.id, "Majburi obuna funksiyasi hali qo‘shilmagan.")


# ---------------------- RUN ----------------------

bot.infinity_polling()
