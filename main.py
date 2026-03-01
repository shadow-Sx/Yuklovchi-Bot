import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import threading
import requests
import re

TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

app = Flask(__name__)

# ==========================
#   STATE MANAGEMENT
# ==========================
user_state = {}
media_buffer = {}

# ==========================
#   FLASK WEBHOOK
# ==========================
@app.route('/webhook', methods=['POST'])
def webhook():
    json_data = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return "OK", 200

@app.route('/')
def home():
    return "Video Combo Bot is running!"

# ==========================
#   KEEP ALIVE (Render Free)
# ==========================
def keep_alive():
    while True:
        try:
            requests.get("https://your-render-url.onrender.com")
        except:
            pass
        time.sleep(600)

threading.Thread(target=keep_alive).start()

# ==========================
#   FORMAT ENGINE
# ==========================
def generate_caption(template, number):
    """Matndagi {qism - X} va {noqism - X} ni almashtiradi."""

    # {qism - X} → <i>N-qism</i>
    qism_pattern = r"\{qism\s*-\s*(\d+)\}"
    match = re.search(qism_pattern, template)

    if match:
        template = re.sub(qism_pattern, f"<i>{number}-qism</i>", template)

    # {noqism - X} → N
    noqism_pattern = r"\{noqism\s*-\s*(\d+)\}"
    match2 = re.search(noqism_pattern, template)

    if match2:
        template = re.sub(noqism_pattern, f"{number}", template)

    return template

# ==========================
#   /copy — MATN KO‘PAYTIRISH
# ==========================
@bot.message_handler(commands=['copy'])
def copy_start(message):
    user_state[message.chat.id] = {"mode": "copy_wait_text"}
    bot.reply_to(message, "Nusxa olish uchun matnni yuboring.")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id, {}).get("mode") == "copy_wait_text")
def copy_process(message):
    template = message.text
    user_state[message.chat.id] = None

    # {qism - X} yoki {noqism - X} dan X ni topamiz
    match = re.search(r"\{(?:qism|noqism)\s*-\s*(\d+)\}", template)
    if not match:
        bot.reply_to(message, "❌ Matnda {qism - X} yoki {noqism - X} topilmadi.")
        return

    limit = int(match.group(1))

    for i in range(1, limit + 1):
        caption = generate_caption(template, i)
        bot.send_message(message.chat.id, caption)

# ==========================
#   /elementbilan — 1 MEDIA + MATN
# ==========================
@bot.message_handler(commands=['elementbilan'])
def element_start(message):
    user_state[message.chat.id] = {"mode": "element_wait_text"}
    bot.reply_to(message, "Matnni yuboring.")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id, {}).get("mode") == "element_wait_text")
def element_got_text(message):
    user_state[message.chat.id] = {
        "mode": "element_wait_media",
        "template": message.text
    }
    bot.reply_to(message, "Endi videoni/rasmni/faylni yuboring.")

@bot.message_handler(content_types=['video', 'photo', 'document'], func=lambda m: user_state.get(m.chat.id, {}).get("mode") == "element_wait_media")
def element_process(message):
    state = user_state[message.chat.id]
    template = state["template"]

    caption = generate_caption(template, 1)

    if message.content_type == "video":
        bot.send_video(message.chat.id, message.video.file_id, caption=caption)

    elif message.content_type == "photo":
        bot.send_photo(message.chat.id, message.photo[-1].file_id, caption=caption)

    elif message.content_type == "document":
        bot.send_document(message.chat.id, message.document.file_id, caption=caption)

    user_state[message.chat.id] = None

# ==========================
#   /vidocombo — KO‘P MEDIA + MATN
# ==========================
@bot.message_handler(commands=['vidocombo'])
def combo_start(message):
    user_state[message.chat.id] = {"mode": "combo_wait_text"}
    bot.reply_to(message, "Matnni yuboring.")

@bot.message_handler(func=lambda m: user_state.get(m.chat.id, {}).get("mode") == "combo_wait_text")
def combo_got_text(message):
    user_state[message.chat.id] = {
        "mode": "combo_collect_media",
        "template": message.text,
        "counter": 1
    }
    media_buffer[message.chat.id] = []
    bot.reply_to(message, "Barcha videolar/rasmlar/fayllarni tashlang.\nTugagach /stop deb yozing.")

@bot.message_handler(commands=['stop'])
def combo_finish(message):
    chat_id = message.chat.id

    if user_state.get(chat_id, {}).get("mode") != "combo_collect_media":
        bot.reply_to(message, "❌ Hozir combo rejimida emassiz.")
        return

    template = user_state[chat_id]["template"]
    counter = 1

    for media in media_buffer.get(chat_id, []):
        caption = generate_caption(template, counter)

        if media["type"] == "video":
            bot.send_video(chat_id, media["file_id"], caption=caption)

        elif media["type"] == "photo":
            bot.send_photo(chat_id, media["file_id"], caption=caption)

        elif media["type"] == "document":
            bot.send_document(chat_id, media["file_id"], caption=caption)

        counter += 1

    bot.send_message(chat_id, "Tugallandi! 🎉")
    user_state[chat_id] = None
    media_buffer[chat_id] = []

@bot.message_handler(content_types=['video', 'photo', 'document'], func=lambda m: user_state.get(m.chat.id, {}).get("mode") == "combo_collect_media")
def combo_collect(message):
    chat_id = message.chat.id

    if message.content_type == "video":
        media_buffer[chat_id].append({"type": "video", "file_id": message.video.file_id})

    elif message.content_type == "photo":
        media_buffer[chat_id].append({"type": "photo", "file_id": message.photo[-1].file_id})

    elif message.content_type == "document":
        media_buffer[chat_id].append({"type": "document", "file_id": message.document.file_id})

    bot.reply_to(message, "Qo‘shildi ✔")

# ==========================
#   RUN SERVER
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
