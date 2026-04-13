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

# Import functions
import functions
from functions import video_edit_state, text_copy_state, post_edit_state

# ==========================
#   TOKEN & SETTINGS
# ==========================
TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
ADMIN_ID = 7797502113

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# functions.py ga username ni set qilish
functions.set_bot_username(BOT_USERNAME)

# ==========================
#   MONGO DB CONNECTION
# ==========================
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)

db = client["xanimelar_bot"]
contents = db["contents"]
required_channels_collection = db["required_channels"]
optional_channels_collection = db["optional_channels"]
users_collection = db["users"]
referrals_collection = db["referrals"]
user_referrals_collection = db["user_referrals"]
bot_settings_collection = db["bot_settings"]
required_bots_collection = db["required_bots"]

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
#   SELF-PING
# ==========================
def keep_alive():
    while True:
        try:
            requests.get("https://yuklovchi-bot-80ui.onrender.com")
        except:
            pass
        time.sleep(60)

threading.Thread(target=keep_alive).start()

# ==========================
#   RANDOM CODE GENERATOR
# ==========================
def generate_code(length=12):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

admin_state = {}
admin_data = {}
add_button_state = {}  # Yangi: tugma qo'shish holati uchun

# ==========================
#   ADMIN PANEL (ASOSIY)
# ==========================
def admin_panel():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("Cantent Qo'shish"),
        KeyboardButton("Majburi Obuna")
    )
    markup.row(
        KeyboardButton("Habar Yuborish"),
        KeyboardButton("Rasm Sozlash")
    )
    markup.row(
        KeyboardButton("2-Bo'lim"),
        KeyboardButton("🔙 Chiqish")
    )
    return markup

def second_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("Referal"),
        KeyboardButton("Text Copy")
    )
    markup.row(
        KeyboardButton("Post Tayyorla"),
        KeyboardButton("Video Edit")
    )
    markup.row(
        KeyboardButton("Cantnetga tugma qoshish"),
        KeyboardButton("1-Bo'lim")
    )
    return markup

def required_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ Majburiy kanal", callback_data="req_add"),
        InlineKeyboardButton("➕ Ixtiyoriy kanal", callback_data="opt_add")
    )
    kb.add(
        InlineKeyboardButton("🤖 Majburiy bot", callback_data="bot_add_menu"),
        InlineKeyboardButton("✏️ Tahrirlash", callback_data="req_edit")
    )
    kb.add(
        InlineKeyboardButton("🗑 O'chirish", callback_data="req_delete"),
        InlineKeyboardButton("🔙 Orqaga", callback_data="req_back")
    )
    return kb

def required_bots_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ Bot qo'shish", callback_data="bot_add"),
        InlineKeyboardButton("✏️ Tahrirlash", callback_data="bot_edit")
    )
    kb.add(
        InlineKeyboardButton("🗑 O'chirish", callback_data="bot_delete"),
        InlineKeyboardButton("🔙 Orqaga", callback_data="bot_back")
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

    users_collection.update_one(
        {"user_id": message.from_user.id},
        {"$set": {"user_id": message.from_user.id}},
        upsert=True
    )

    sent = bot.reply_to(message, "⚙️ Admin panelga xush kelibsiz!", reply_markup=admin_panel())
    functions.add_premium_reaction(bot, sent.chat.id, sent.message_id, "👑")

# ==========================
#   ADMIN BUTTONS
# ==========================
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text in [
    "Cantent Qo'shish", "Majburi Obuna", "Habar Yuborish", "Referal", 
    "Rasm Sozlash", "Video Edit", "Text Copy", "Post Tayyorla", "🔙 Chiqish",
    "2-Bo'lim", "1-Bo'lim", "Cantnetga tugma qoshish"
])
def admin_buttons(message):
    uid = message.from_user.id
    text = message.text

    if text == "Cantent Qo'shish":
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("1 - 1", callback_data="multi_mode_single"),
            InlineKeyboardButton("♾️ - 1", callback_data="multi_mode_batch")
        )
        admin_state[uid] = None
        bot.reply_to(message, "Qaysi tarzda kontent qo'shmoqchisiz?", reply_markup=kb)

    elif text == "Habar Yuborish":
        admin_state[uid] = "send_broadcast"
        bot.reply_to(message, "📨 Xabar yuboring (forward qilingan xabar ham bo'lishi mumkin):")

    elif text == "Majburi Obuna":
        bot.send_message(message.chat.id, "📌 Majburiy obuna bo'limi:", reply_markup=required_menu())

    elif text == "Referal":
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("➕ Yangi qo'shish", callback_data="referral_add"),
            InlineKeyboardButton("📊 Statistika", callback_data="referral_stats")
        )
        bot.send_message(uid, "Salom Admin bugun nima qilamiz?", reply_markup=kb)

    elif text == "Rasm Sozlash":
        admin_state[uid] = "set_main_image"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🗑 Rasmni o'chirish", callback_data="delete_main_image"))
        bot.reply_to(message, "🖼 Majburiy obuna xabari uchun rasm yuboring:", reply_markup=kb)

    elif text == "Video Edit":
        functions.start_video_edit(bot, message)

    elif text == "Text Copy":
        functions.start_text_copy(bot, uid)

    elif text == "Post Tayyorla":
        functions.start_post_editor(bot, message)

    elif text == "2-Bo'lim":
        bot.send_message(uid, "🔽 2-Bo'lim menyusi:", reply_markup=second_menu())

    elif text == "1-Bo'lim":
        bot.send_message(uid, "🔽 Asosiy menyu:", reply_markup=admin_panel())

    elif text == "Cantnetga tugma qoshish":
        add_button_state[uid] = {"step": "waiting_code"}
        bot.reply_to(message, "📎 Iltimos, kontent havolasini yoki start kodini yuboring:\n\n"
                     "Masalan:\n"
                     f"<code>https://t.me/{BOT_USERNAME}?start=abc123</code>\n"
                     "yoki\n<code>abc123</code>")

    elif text == "🔙 Chiqish":
        admin_state[uid] = None
        admin_data[uid] = {}
        add_button_state.pop(uid, None)
        bot.send_message(uid, "<b>Admin paneldan chiqdingiz.</b>", reply_markup=telebot.types.ReplyKeyboardRemove())

# ==========================
#   DELETE MAIN IMAGE
# ==========================
@bot.callback_query_handler(func=lambda c: c.data == "delete_main_image")
def delete_main_image(call):
    bot_settings_collection.delete_one({"setting": "main_image"})
    bot.edit_message_text(
        "✅ Rasm o'chirildi! Endi majburiy obuna xabari rasm bilan chiqmaydi.",
        call.message.chat.id,
        call.message.message_id
    )

# ==========================
#   MAIN IMAGE SETUP
# ==========================
@bot.message_handler(content_types=['photo'])
def save_main_image(message):
    uid = message.from_user.id
    if admin_state.get(uid) == "set_main_image":
        file_id = message.photo[-1].file_id
        bot_settings_collection.update_one(
            {"setting": "main_image"},
            {"$set": {"image_id": file_id}},
            upsert=True
        )
        sent = bot.reply_to(message, "✅ Rasm saqlandi! Endi majburiy obuna xabari rasm bilan chiqadi.")
        functions.add_premium_reaction(bot, sent.chat.id, sent.message_id, "✅")
        admin_state[uid] = None

# ==========================
#   REFERRAL SYSTEM (o'zgarishsiz)
# ==========================
# ... (oldingi kod o'zgarishsiz qoldiriladi) ...
# Bu qismni qisqartirish uchun joy tashladim, lekin asl kod to'liq saqlanadi.

# ==========================
#   BROADCAST (o'zgarishsiz)
# ==========================
# ... (oldingi kod o'zgarishsiz qoldiriladi) ...

# ==========================
#   CONTENTGA TUGMA QO'SHISH
# ==========================
@bot.message_handler(func=lambda m: add_button_state.get(m.from_user.id, {}).get("step") == "waiting_code")
def button_add_code(message):
    uid = message.from_user.id
    text = message.text.strip()
    
    # Havoladan kodni ajratish
    if "?start=" in text:
        code = text.split("?start=")[-1].split()[0].split("&")[0]
    else:
        code = text
    
    # Kod mavjudligini tekshirish
    items = list(contents.find({"code": code}))
    if not items:
        bot.reply_to(message, "❌ Bunday kodli kontent topilmadi!")
        add_button_state.pop(uid, None)
        return
    
    add_button_state[uid] = {
        "step": "waiting_buttons",
        "code": code
    }
    
    bot.reply_to(
        message,
        "✅ Kod qabul qilindi!\n\n"
        "Endi tugmalarni quyidagi formatda yuboring:\n\n"
        "<b>Oddiy tugma:</b>\n"
        "<code>Kanal - https://t.me/kanal</code>\n\n"
        "<b>Bir qatorda bir nechta:</b>\n"
        "<code>Tugma1 - url1 | Tugma2 - url2</code>\n\n"
        "<b>Rangli qilish (ixtiyoriy):</b>\n"
        "<code>Tugma - url - rang:yashil</code>\n"
        "(Ranglar: yashil, kok, qizil – Telegramda ishlamaydi, lekin format saqlanadi)\n\n"
        "Har bir qator yangi qatordan boshlansin.",
        parse_mode="HTML"
    )

@bot.message_handler(func=lambda m: add_button_state.get(m.from_user.id, {}).get("step") == "waiting_buttons")
def button_add_buttons(message):
    uid = message.from_user.id
    code = add_button_state[uid]["code"]
    text = message.text.strip()
    
    buttons = []
    lines = text.split("\n")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Qatordagi tugmalarni | bo'yicha ajratish
        row_buttons = []
        parts = line.split("|")
        for part in parts:
            part = part.strip()
            if " - " not in part:
                continue
            # Rangni olib tashlash (agar mavjud bo'lsa)
            if " - rang:" in part:
                main_part = part.split(" - rang:")[0].strip()
            else:
                main_part = part.strip()
            
            if " - " in main_part:
                name, url = main_part.split(" - ", 1)
                name = name.strip()
                url = url.strip()
                if url and name:
                    row_buttons.append(InlineKeyboardButton(name, url=url))
        
        if row_buttons:
            buttons.append(row_buttons)
    
    if not buttons:
        bot.reply_to(message, "❌ Hech qanday to'g'ri formatdagi tugma topilmadi!")
        return
    
    # Tugmalarni saqlash
    kb = InlineKeyboardMarkup(buttons)
    
    # Barcha shu kodli kontentlarga bir xil tugmalarni biriktirish
    contents.update_many(
        {"code": code},
        {"$set": {"buttons": buttons}}
    )
    
    # Tasdiqlash
    sent = bot.reply_to(
        message,
        f"✅ Tugmalar muvaffaqiyatli qo'shildi!\n\n"
        f"Kod: <code>{code}</code>\n"
        f"Jami kontentlar soni: {contents.count_documents({'code': code})}",
        reply_markup=kb
    )
    functions.add_premium_reaction(bot, sent.chat.id, sent.message_id, "✅")
    add_button_state.pop(uid, None)

# ==========================
#   MULTI MODE TANLASH
# ==========================
@bot.callback_query_handler(func=lambda c: c.data in ["multi_mode_single", "multi_mode_batch"])
def multi_mode_select(call):
    uid = call.from_user.id
    if uid != ADMIN_ID:
        return

    if call.data == "multi_mode_single":
        admin_state[uid] = "multi_add_single"
        bot.edit_message_text(
            "📥 Kontentlarni tashlang.\n\nHar bir kontent uchun alohida havola beriladi.\n"
            "Tugagach /stop deb yozing.",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        admin_state[uid] = "multi_add_batch"
        admin_data[uid] = {"batch": []}
        bot.edit_message_text(
            "📥 Barcha kontentlarni yuboring va oxirida /stop bosing.\n\n"
            "Barchasi uchun bitta havola beriladi.",
            call.message.chat.id,
            call.message.message_id
        )

# ==========================
#   MULTI-UPLOAD CONTENT SAVING
# ==========================
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'sticker', 'audio', 'voice', 'video_note'],
                    func=lambda m: admin_state.get(m.from_user.id) in ["multi_add_single", "multi_add_batch"] 
                    and not (hasattr(m, 'text') and m.text == "/stop"))
def save_multi(message):
    uid = message.from_user.id
    state = admin_state.get(uid)

    # Delay qo'shish (so'rovga ko'ra)
    if state == "multi_add_single":
        time.sleep(0.1)   # 1-1 rejim: tezkor
    elif state == "multi_add_batch":
        time.sleep(0.7)   # batch rejim: sekinroq (Telegram cheklovi uchun)

    # Kontent ma'lumotlarini tayyorlash
    content_type = message.content_type
    item = {
        "type": content_type,
        "order": 1  # default
    }

    if content_type == "video":
        item["file_id"] = message.video.file_id
        item["caption"] = message.caption
    elif content_type == "photo":
        item["file_id"] = message.photo[-1].file_id
        item["caption"] = message.caption
    elif content_type == "document":
        item["file_id"] = message.document.file_id
        item["caption"] = message.caption
    elif content_type == "sticker":
        item["file_id"] = message.sticker.file_id
        # sticker da caption bo'lmaydi
    elif content_type == "audio":
        item["file_id"] = message.audio.file_id
        item["caption"] = message.caption
    elif content_type == "voice":
        item["file_id"] = message.voice.file_id
    elif content_type == "video_note":
        item["file_id"] = message.video_note.file_id
    else:  # text
        item["text"] = message.text

    if state == "multi_add_single":
        code = generate_code()
        item["code"] = code

        contents.insert_one(item)
        link = f"https://t.me/{BOT_USERNAME}?start={code}"
        sent = bot.reply_to(message, link)
        functions.add_premium_reaction(bot, sent.chat.id, sent.message_id, "✅")

    elif state == "multi_add_batch":
        batch = admin_data.get(uid, {}).get("batch", [])
        item["order"] = len(batch) + 1
        batch.append(item)
        admin_data[uid]["batch"] = batch
        sent = bot.reply_to(message, f"✅ {len(batch)}-kontent qabul qilindi.")
        functions.add_premium_reaction(bot, sent.chat.id, sent.message_id, "✅")

# ==========================
#   /stop
# ==========================
@bot.message_handler(commands=['stop'])
def stop(message):
    uid = message.from_user.id
    state = admin_state.get(uid)

    if state == "multi_add_batch":
        batch = admin_data.get(uid, {}).get("batch", [])
        if not batch:
            bot.reply_to(message, "❌ Hech qanday kontent yuborilmadi.")
            admin_state[uid] = None
            admin_data[uid] = {}
            return

        code = generate_code()
        docs = []
        for item in batch:
            doc = {
                "type": item["type"],
                "code": code,
                "order": item["order"]
            }
            if item["type"] in ["video", "photo", "document", "sticker", "audio", "voice", "video_note"]:
                doc["file_id"] = item.get("file_id")
                if "caption" in item:
                    doc["caption"] = item["caption"]
            else:
                doc["text"] = item.get("text")
            docs.append(doc)

        contents.insert_many(docs)

        link = f"https://t.me/{BOT_USERNAME}?start={code}"
        sent = bot.reply_to(message, link)
        functions.add_premium_reaction(bot, sent.chat.id, sent.message_id, "✅")

        admin_state[uid] = None
        admin_data[uid] = {}
        return

    if state == "multi_add_single":
        admin_state[uid] = None
        sent = bot.reply_to(message, "<b>✅ Barcha kontentlar qabul qilindi.</b>", reply_markup=admin_panel())
        functions.add_premium_reaction(bot, sent.chat.id, sent.message_id, "✅")
        return
    
    bot.reply_to(message, "❌ Hech qanday faol jarayon yo'q.")

# ==========================
#   MAJBURIY KANAL QO'SHISH (o'zgarishsiz)
# ==========================
# ... (oldingi kod o'zgarishsiz qoldiriladi) ...

# ==========================
#   IXTIYORIY KANAL QO'SHISH (o'zgarishsiz)
# ==========================
# ...

# ==========================
#   MAJBURIY BOT QO'SHISH (o'zgarishsiz)
# ==========================
# ...

# ==========================
#   TAHRIRLASH VA O'CHIRISH (o'zgarishsiz)
# ==========================
# ...

# ==========================
#   MAJBURIY OBUNA TEKSHIRISH (o'zgarishsiz)
# ==========================
# ...

def send_content(chat_id, items, is_batch=False):
    """Kontentni yuborish (tugmalar bilan birga)"""
    # Tugmalarni olish (barcha itemlar uchun bir xil bo'ladi, chunki bir xil kod)
    buttons = None
    if items:
        first_item = items[0]
        if "buttons" in first_item:
            buttons = InlineKeyboardMarkup(first_item["buttons"])
    
    if is_batch:
        for item in items:
            msg = None
            if item["type"] == "text":
                msg = bot.send_message(chat_id, item["text"], reply_markup=buttons)
            elif item["type"] == "photo":
                msg = bot.send_photo(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=buttons)
            elif item["type"] == "video":
                msg = bot.send_video(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=buttons)
            elif item["type"] == "document":
                msg = bot.send_document(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=buttons)
            elif item["type"] == "sticker":
                msg = bot.send_sticker(chat_id, item["file_id"], reply_markup=buttons)
            elif item["type"] == "audio":
                msg = bot.send_audio(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=buttons)
            elif item["type"] == "voice":
                msg = bot.send_voice(chat_id, item["file_id"], reply_markup=buttons)
            elif item["type"] == "video_note":
                msg = bot.send_video_note(chat_id, item["file_id"], reply_markup=buttons)
            
            if msg:
                schedule_delete(chat_id, msg.message_id, 300)
        
        warn = bot.send_message(
            chat_id,
            "<b>⚠️ ESLATMA ⚠️\n\n❗ Ushbu habarlar 5 daqiqadan so'ng o'chiriladi. Tezda saqlash joyingizga saqlab oling!</b>",
            reply_markup=buttons
        )
        schedule_delete(chat_id, warn.message_id, 300)
        functions.add_premium_reaction(bot, warn.chat.id, warn.message_id, "⚠️")
    
    else:
        for item in items:
            msg = None
            if item["type"] == "text":
                msg = bot.send_message(chat_id, item["text"], reply_markup=buttons)
            elif item["type"] == "photo":
                msg = bot.send_photo(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=buttons)
            elif item["type"] == "video":
                msg = bot.send_video(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=buttons)
            elif item["type"] == "document":
                msg = bot.send_document(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=buttons)
            elif item["type"] == "sticker":
                msg = bot.send_sticker(chat_id, item["file_id"], reply_markup=buttons)
            elif item["type"] == "audio":
                msg = bot.send_audio(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=buttons)
            elif item["type"] == "voice":
                msg = bot.send_voice(chat_id, item["file_id"], reply_markup=buttons)
            elif item["type"] == "video_note":
                msg = bot.send_video_note(chat_id, item["file_id"], reply_markup=buttons)
            
            if msg:
                schedule_delete(chat_id, msg.message_id, 300)
                warn = bot.send_message(
                    chat_id,
                    "<b>⚠️ ESLATMA ⚠️\n\n❗ Ushbu habar 5 daqiqadan so'ng o'chiriladi. Tezda saqlash joyingizga saqlab oling!</b>"
                )
                schedule_delete(chat_id, warn.message_id, 300)
                functions.add_premium_reaction(bot, warn.chat.id, warn.message_id, "⚠️")

# ==========================
#   /start (tugmalar bilan)
# ==========================
@bot.message_handler(commands=['start'])
def start(message):
    def add_start_reaction(msg):
        time.sleep(0.3)
        try:
            bot.set_message_reaction(
                chat_id=msg.chat.id,
                message_id=msg.message_id,
                reaction=[{"type": "emoji", "emoji": "🎉"}],
                is_big=True
            )
        except:
            pass

    if len(message.text.split()) == 1:
        users_collection.update_one(
            {"user_id": message.from_user.id},
            {"$set": {"user_id": message.from_user.id}},
            upsert=True
        )

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("📝 Bot Haqida", callback_data="about"),
            InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{message.message_id}")
        )

        sent = bot.reply_to(
            message,
            "<b>Bu bot orqali kanaldagi animelarni yuklab olishingiz mumkin.\n\n"
            "❗️Botga habar yozmang❗️</b>",
            reply_markup=markup
        )
        threading.Thread(target=add_start_reaction, args=(sent,)).start()
        
    else:
        code = message.text.split()[1]
        
        # Referal kodni tekshirish
        if code.startswith("ref_"):
            # ... (oldingi referal kodi saqlanadi)
            # Referal qismi o'zgarishsiz
            pass

        items = list(contents.find({"code": code}).sort("order", 1))
        if not items:
            sent = bot.send_message(message.chat.id, "❌ Kontent topilmadi.")
            functions.add_premium_reaction(bot, sent.chat.id, sent.message_id, "❌")
            return

        # Majburiy obuna tekshirish (kanal va bot)
        if not check_required_subs(message.from_user.id):
            settings = bot_settings_collection.find_one({"setting": "main_image"})
            if settings and settings.get("image_id"):
                sent = bot.send_photo(
                    message.chat.id,
                    settings["image_id"],
                    caption="📢 <b>Animeni yuklab olish uchun quyidagi kanallarga obuna bo'ling:</b>",
                    reply_markup=get_required_keyboard(message.from_user.id, code)
                )
            else:
                sent = bot.send_message(
                    message.chat.id,
                    "📢 <b>Animeni yuklab olish uchun quyidagi kanallarga obuna bo'ling:</b>",
                    reply_markup=get_required_keyboard(message.from_user.id, code)
                )
            functions.add_premium_reaction(bot, sent.chat.id, sent.message_id, "🔔")
            return

        if not check_required_bots(message.from_user.id):
            settings = bot_settings_collection.find_one({"setting": "main_image"})
            if settings and settings.get("image_id"):
                sent = bot.send_photo(
                    message.chat.id,
                    settings["image_id"],
                    caption="📢 <b>Kontentni ko'rish uchun quyidagi botlarga start bosing:</b>",
                    reply_markup=get_required_bots_keyboard(message.from_user.id, code)
                )
            else:
                sent = bot.send_message(
                    message.chat.id,
                    "📢 <b>Kontentni ko'rish uchun quyidagi botlarga start bosing:</b>",
                    reply_markup=get_required_bots_keyboard(message.from_user.id, code)
                )
            functions.add_premium_reaction(bot, sent.chat.id, sent.message_id, "🤖")
            return

        is_batch = contents.count_documents({"code": code}) > 1
        send_content(message.chat.id, items, is_batch)

# ==========================
#   CALLBACK HANDLER (o'zgarishsiz)
# ==========================
# ...

# ==========================
#   VIDEO EDIT MESSAGE HANDLERS (o'zgarishsiz)
# ==========================
# ...

# ==========================
#   TEXT COPY MESSAGE HANDLERS (o'zgarishsiz)
# ==========================
# ...

# ==========================
#   POST EDITOR MESSAGE HANDLERS (o'zgarishsiz)
# ==========================
# ...

# ==========================
#   RUN SERVER
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
