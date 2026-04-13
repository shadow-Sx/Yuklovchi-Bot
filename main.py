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
required_channels_collection = db["required_channels"]
optional_channels_collection = db["optional_channels"]
users_collection = db["users"]
referrals_collection = db["referrals"]
user_referrals_collection = db["user_referrals"]
bot_settings_collection = db["bot_settings"]
required_bots_collection = db["required_bots"]
content_buttons_collection = db["content_buttons"]

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

# ==========================
#   PREMIUM REAKSIYA
# ==========================
def add_premium_reaction(chat_id, message_id, emoji="🎉"):
    try:
        time.sleep(0.3)
        bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=[{"type": "emoji", "emoji": emoji}],
            is_big=True
        )
        return True
    except:
        return False

# ==========================
#   ADMIN PANEL
# ==========================
def admin_panel():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("Cantent qo'shish ➕"),
        KeyboardButton("Majburi obuna 🧷")
    )
    markup.row(
        KeyboardButton("Habar yuborish 🕧"),
        KeyboardButton("Rasm so'zlash 🎑")
    )
    markup.row(
        KeyboardButton("2-Bo'lim ⛩️"),
        KeyboardButton("🔙 Chiqish")
    )
    return markup

def second_section_panel():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(
        KeyboardButton("Referal 🖇"),
        KeyboardButton("Text Copy 🗂")
    )
    markup.row(
        KeyboardButton("Post tayyorlash 📢"),
        KeyboardButton("Video Edit 🎛")
    )
    markup.row(
        KeyboardButton("Cantnetga tugma qoshish ➕"),
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
    add_premium_reaction(sent.chat.id, sent.message_id, "👑")

# ==========================
#   ADMIN BUTTONS
# ==========================
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID)
def admin_buttons(message):
    uid = message.from_user.id
    text = message.text

    if text == "Cantent qo'shish ➕":
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("1 - 1", callback_data="multi_mode_single"),
            InlineKeyboardButton("♾️ - 1", callback_data="multi_mode_batch")
        )
        admin_state[uid] = None
        bot.reply_to(message, "Qaysi tarzda kontent qo'shmoqchisiz?", reply_markup=kb)

    elif text == "Majburi obuna 🧷":
        bot.send_message(message.chat.id, "📌 Majburiy obuna bo'limi:", reply_markup=required_menu())

    elif text == "Habar yuborish 🕧":
        admin_state[uid] = "send_broadcast"
        bot.reply_to(message, "📨 Xabar yuboring:")

    elif text == "Rasm so'zlash 🎑":
        admin_state[uid] = "set_main_image"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🗑 Rasmni o'chirish", callback_data="delete_main_image"))
        bot.reply_to(message, "🖼 Majburiy obuna xabari uchun rasm yuboring:", reply_markup=kb)

    elif text == "2-Bo'lim ⛩️":
        bot.send_message(message.chat.id, "⛩️ 2-Bo'lim:", reply_markup=second_section_panel())

    elif text == "Referal 🖇":
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("➕ Yangi qo'shish", callback_data="referral_add"),
            InlineKeyboardButton("📊 Statistika", callback_data="referral_stats")
        )
        bot.send_message(uid, "Salom Admin bugun nima qilamiz?", reply_markup=kb)

    elif text == "Text Copy 🗂":
        admin_state[uid] = "text_copy_waiting"
        bot.reply_to(message, "📝 Nusxalanadigan matnni yuboring:")

    elif text == "Post tayyorlash 📢":
        admin_state[uid] = "post_editor_waiting_link"
        bot.reply_to(message, "📢 Post havolasini yuboring:")

    elif text == "Video Edit 🎛":
        start_video_edit(message)

    elif text == "Cantnetga tugma qoshish ➕":
        admin_state[uid] = "content_button_waiting_code"
        bot.reply_to(message, "➕ Tugma qo'shiladigan kontent havolasini yoki kodini yuboring:")

    elif text == "1-Bo'lim":
        bot.send_message(message.chat.id, "⚙️ Asosiy panel:", reply_markup=admin_panel())

    elif text == "🔙 Chiqish":
        admin_state[uid] = None
        admin_data[uid] = {}
        bot.send_message(uid, "<b>Admin paneldan chiqdingiz.</b>", reply_markup=telebot.types.ReplyKeyboardRemove())

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
            "📥 1-1 rejimi: Kontentlarni tashlang.\nTugagach /stop yozing.",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        admin_state[uid] = "multi_add_batch"
        admin_data[uid] = {"batch": []}
        bot.edit_message_text(
            "📥 ♾️-1 rejimi: Barcha kontentlarni yuboring.\nTugagach /stop bosing.",
            call.message.chat.id,
            call.message.message_id
        )

# ==========================
#   /stop (BIRINCHI HANDLER - MUHIM!)
# ==========================
@bot.message_handler(commands=['stop'])
def stop_command(message):
    uid = message.from_user.id
    state = admin_state.get(uid)
    
    print(f"STOP komandasi: uid={uid}, state={state}")

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
            docs.append({
                "type": item["type"],
                "file_id": item.get("file_id"),
                "caption": item.get("caption"),
                "text": item.get("text"),
                "code": code,
                "order": item["order"]
            })

        contents.insert_many(docs)
        link = f"https://t.me/{BOT_USERNAME}?start={code}"
        bot.reply_to(message, link)
        admin_state[uid] = None
        admin_data[uid] = {}
        return

    if state == "multi_add_single":
        admin_state[uid] = None
        bot.reply_to(message, "✅ Barcha kontentlar qabul qilindi.", reply_markup=admin_panel())
        return
    
    bot.reply_to(message, "❌ Hech qanday faol jarayon yo'q. /admin -> Cantent qo'shish ➕")

# ==========================
#   MULTI-UPLOAD CONTENT SAVING
# ==========================
@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'sticker', 'audio', 'voice', 'animation'])
def save_multi(message):
    uid = message.from_user.id
    
    # MUHIM: /stop ni tekshirish va o'tkazib yuborish
    if message.text and message.text.strip() == "/stop":
        print(f"save_multi: /stop ni o'tkazib yuborish")
        return
    
    state = admin_state.get(uid)
    
    if state not in ["multi_add_single", "multi_add_batch"]:
        return

    if state == "multi_add_single":
        # 1-1 rejimi: tez yuklash
        code = generate_code()

        if message.content_type == "video":
            content = {"type": "video", "file_id": message.video.file_id, "caption": message.caption, "code": code, "order": 1}
        elif message.content_type == "photo":
            content = {"type": "photo", "file_id": message.photo[-1].file_id, "caption": message.caption, "code": code, "order": 1}
        elif message.content_type == "document":
            content = {"type": "document", "file_id": message.document.file_id, "caption": message.caption, "code": code, "order": 1}
        elif message.content_type == "sticker":
            content = {"type": "sticker", "file_id": message.sticker.file_id, "code": code, "order": 1}
        elif message.content_type == "audio":
            content = {"type": "audio", "file_id": message.audio.file_id, "caption": message.caption, "code": code, "order": 1}
        elif message.content_type == "voice":
            content = {"type": "voice", "file_id": message.voice.file_id, "code": code, "order": 1}
        elif message.content_type == "animation":
            content = {"type": "animation", "file_id": message.animation.file_id, "caption": message.caption, "code": code, "order": 1}
        else:
            content = {"type": "text", "text": message.text, "code": code, "order": 1}

        contents.insert_one(content)
        link = f"https://t.me/{BOT_USERNAME}?start={code}"
        bot.reply_to(message, link)
        print(f"1-1 rejimi: kontent saqlandi, code={code}")

    elif state == "multi_add_batch":
        # ♾️-1 rejimi: sekin yuklash (0.7 sekund)
        time.sleep(0.7)
        
        batch = admin_data.get(uid, {}).get("batch", [])
        order = len(batch) + 1

        if message.content_type == "video":
            item = {"type": "video", "file_id": message.video.file_id, "caption": message.caption, "order": order}
        elif message.content_type == "photo":
            item = {"type": "photo", "file_id": message.photo[-1].file_id, "caption": message.caption, "order": order}
        elif message.content_type == "document":
            item = {"type": "document", "file_id": message.document.file_id, "caption": message.caption, "order": order}
        elif message.content_type == "sticker":
            item = {"type": "sticker", "file_id": message.sticker.file_id, "order": order}
        elif message.content_type == "audio":
            item = {"type": "audio", "file_id": message.audio.file_id, "caption": message.caption, "order": order}
        elif message.content_type == "voice":
            item = {"type": "voice", "file_id": message.voice.file_id, "order": order}
        elif message.content_type == "animation":
            item = {"type": "animation", "file_id": message.animation.file_id, "caption": message.caption, "order": order}
        else:
            item = {"type": "text", "text": message.text, "order": order}

        batch.append(item)
        admin_data[uid]["batch"] = batch
        bot.reply_to(message, f"✅ {order}-kontent qabul qilindi. /stop bilan tugating.")
        print(f"♾️-1 rejimi: {order}-kontent qabul qilindi")

# ==========================
#   DELETE MAIN IMAGE
# ==========================
@bot.callback_query_handler(func=lambda c: c.data == "delete_main_image")
def delete_main_image(call):
    bot_settings_collection.delete_one({"setting": "main_image"})
    bot.edit_message_text("✅ Rasm o'chirildi!", call.message.chat.id, call.message.message_id)

# ==========================
#   MAIN IMAGE SETUP
# ==========================
@bot.message_handler(content_types=['photo'])
def save_main_image(message):
    uid = message.from_user.id
    if admin_state.get(uid) == "set_main_image":
        file_id = message.photo[-1].file_id
        bot_settings_collection.update_one({"setting": "main_image"}, {"$set": {"image_id": file_id}}, upsert=True)
        bot.reply_to(message, "✅ Rasm saqlandi!")
        admin_state[uid] = None

# ==========================
#   REFERRAL SYSTEM (SODDA)
# ==========================
@bot.callback_query_handler(func=lambda c: c.data == "referral_add")
def referral_add(call):
    uid = call.from_user.id
    admin_state[uid] = "referral_add_name"
    bot.edit_message_text("📛 Yangi referal uchun nom kiriting:", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "referral_stats")
def referral_stats(call):
    referrals = list(referrals_collection.find({}))
    if not referrals:
        bot.edit_message_text("📊 Referallar mavjud emas.", call.message.chat.id, call.message.message_id)
        return
    text = "📊 Referallar statistikasi\n\n"
    kb = InlineKeyboardMarkup()
    for ref in referrals:
        count = user_referrals_collection.count_documents({"referral_name": ref["name"]})
        text += f"• {ref['name']}: {count} ta foydalanuvchi\n"
        kb.add(InlineKeyboardButton(f"🗑 {ref['name']}", callback_data=f"del_ref:{ref['name']}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="referral_back"))
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "referral_add_name")
def referral_save_name(message):
    uid = message.from_user.id
    name = message.text.strip()
    if not all(c.isalnum() or c == '_' for c in name):
        bot.reply_to(message, "❌ Nom faqat lotin harflari, raqamlar va pastki chiziq (_) dan iborat bo'lishi kerak!")
        return
    if len(name) < 3 or len(name) > 20:
        bot.reply_to(message, "❌ Nom 3-20 belgi orasida bo'lishi kerak!")
        return
    if referrals_collection.find_one({"name": name}):
        bot.reply_to(message, "❌ Bunday nomli referal allaqachon mavjud!")
        return
    referrals_collection.insert_one({"name": name, "created_at": time.time()})
    bot.reply_to(message, f"✅ {name} referali yaratildi!\n\nHavola: https://t.me/{BOT_USERNAME}?start=ref_{name}")
    admin_state[uid] = None

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_ref:"))
def delete_referral_confirm(call):
    ref_name = call.data.split(":")[1]
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Ha", callback_data=f"del_ref_yes:{ref_name}"), InlineKeyboardButton("❌ Yo'q", callback_data="referral_stats"))
    bot.edit_message_text(f"⚠️ {ref_name} havolasini o'chirmoqchimisiz?", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_ref_yes:"))
def delete_referral_yes(call):
    ref_name = call.data.split(":")[1]
    referrals_collection.delete_one({"name": ref_name})
    user_referrals_collection.delete_many({"referral_name": ref_name})
    bot.edit_message_text(f"✅ {ref_name} referali o'chirildi!", call.message.chat.id, call.message.message_id)
    referral_stats(call)

@bot.callback_query_handler(func=lambda c: c.data == "referral_back")
def referral_back(call):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Yangi qo'shish", callback_data="referral_add"), InlineKeyboardButton("📊 Statistika", callback_data="referral_stats"))
    bot.edit_message_text("Salom Admin bugun nima qilamiz?", call.message.chat.id, call.message.message_id, reply_markup=kb)

# ==========================
#   BROADCAST
# ==========================
@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "send_broadcast")
def send_broadcast_handler(message):
    uid = message.from_user.id
    admin_data[uid] = {"broadcast_message": message}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Tasdiqlash", callback_data="broadcast_confirm"), InlineKeyboardButton("❌ Bekor qilish", callback_data="broadcast_cancel"))
    bot.reply_to(message, "⚠️ Haqiqatdan ham shu xabarni barchaga yubormaymi?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "broadcast_confirm")
def broadcast_confirm(call):
    uid = call.from_user.id
    msg = admin_data.get(uid, {}).get("broadcast_message")
    if not msg:
        bot.answer_callback_query(call.id, "❌ Xato yuz berdi!")
        return
    users = users_collection.find({})
    success = 0
    fail = 0
    bot.edit_message_text("⏳ Xabar yuborilmoqda...", call.message.chat.id, call.message.message_id)
    for u in users:
        try:
            if msg.forward_from or msg.forward_from_chat or msg.forward_date:
                bot.copy_message(u["user_id"], msg.chat.id, msg.message_id)
            elif msg.content_type == "text":
                bot.send_message(u["user_id"], msg.text, parse_mode="HTML")
            elif msg.content_type == "photo":
                bot.send_photo(u["user_id"], msg.photo[-1].file_id, caption=msg.caption)
            elif msg.content_type == "video":
                bot.send_video(u["user_id"], msg.video.file_id, caption=msg.caption)
            elif msg.content_type == "document":
                bot.send_document(u["user_id"], msg.document.file_id, caption=msg.caption)
            elif msg.content_type == "sticker":
                bot.send_sticker(u["user_id"], msg.sticker.file_id)
            else:
                bot.copy_message(u["user_id"], msg.chat.id, msg.message_id)
            success += 1
            time.sleep(0.05)
        except:
            fail += 1
    bot.edit_message_text(f"✅ Xabar yuborildi!\n✅ Muvaffaqiyatli: {success}\n❌ Xatolik: {fail}", call.message.chat.id, call.message.message_id)
    admin_state[uid] = None
    admin_data[uid] = {}

@bot.callback_query_handler(func=lambda c: c.data == "broadcast_cancel")
def broadcast_cancel(call):
    uid = call.from_user.id
    bot.edit_message_text("❌ Xabar yuborish bekor qilindi.", call.message.chat.id, call.message.message_id)
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   MAJBURIY KANAL QO'SHISH
# ==========================
@bot.callback_query_handler(func=lambda c: c.data == "req_add")
def start_required_add(call):
    uid = call.from_user.id
    admin_state[uid] = "req_add_id"
    admin_data[uid] = {}
    bot.edit_message_text("➕ Majburiy kanal qo'shish. Kanal ID raqamini yuboring:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_id")
def req_get_id(message):
    uid = message.from_user.id
    try:
        channel_id = int(message.text)
    except:
        bot.reply_to(message, "❌ ID faqat raqam bo'lishi kerak.")
        return
    admin_data[uid]["channel_id"] = channel_id
    admin_state[uid] = "req_add_url"
    bot.reply_to(message, "🔗 Endi kanal havolasini yuboring:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_url")
def req_get_url(message):
    uid = message.from_user.id
    url = message.text.strip()
    channel_id = admin_data[uid]["channel_id"]
    try:
        member = bot.get_chat_member(channel_id, bot.get_me().id)
        if member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "❌ Bot kanalda admin emas.")
            return
    except:
        bot.reply_to(message, "❌ Kanalga ulanib bo'lmadi.")
        return
    admin_data[uid]["url"] = url
    admin_state[uid] = "req_add_count"
    bot.reply_to(message, "👥 Ushbu kanalga qancha obunachi qo'shmoqchisiz?")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_count")
def req_get_count(message):
    uid = message.from_user.id
    try:
        count = int(message.text)
    except:
        bot.reply_to(message, "❌ Miqdor faqat raqam bo'lishi kerak.")
        return
    admin_data[uid]["count"] = count
    admin_state[uid] = "req_add_name"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🤖 Avto nomlash", callback_data="req_auto_name"))
    bot.reply_to(message, "📛 Kanal uchun nom kiriting:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "req_auto_name")
def req_auto_name(call):
    uid = call.from_user.id
    if admin_state.get(uid) != "req_add_name":
        return
    auto_channels = list(required_channels_collection.find({"auto": True}))
    auto_name = f"{len(auto_channels) + 1}-Kanal"
    data = admin_data.get(uid, {})
    new_channel = {"name": auto_name, "channel_id": data["channel_id"], "url": data["url"], "count": data["count"], "auto": True}
    required_channels_collection.insert_one(new_channel)
    bot.edit_message_text(f"✅ {auto_name} qo'shildi!", call.message.chat.id, call.message.message_id)
    admin_state[uid] = None
    admin_data[uid] = {}

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_name")
def req_custom_name(message):
    uid = message.from_user.id
    name = message.text.strip()
    data = admin_data.get(uid, {})
    new_channel = {"name": name, "channel_id": data["channel_id"], "url": data["url"], "count": data["count"], "auto": False}
    required_channels_collection.insert_one(new_channel)
    bot.reply_to(message, f"✅ {name} qo'shildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   IXTIYORIY KANAL QO'SHISH
# ==========================
@bot.callback_query_handler(func=lambda c: c.data == "opt_add")
def start_optional_add(call):
    uid = call.from_user.id
    admin_state[uid] = "opt_add_name"
    admin_data[uid] = {}
    bot.edit_message_text("➕ Ixtiyoriy kanal qo'shish. Tugma uchun nom kiriting:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_add_name")
def opt_get_name(message):
    uid = message.from_user.id
    admin_data[uid]["name"] = message.text.strip()
    admin_state[uid] = "opt_add_url"
    bot.reply_to(message, "🔗 Endi kanal havolasini yuboring:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_add_url")
def opt_get_url(message):
    uid = message.from_user.id
    name = admin_data[uid]["name"]
    url = message.text.strip()
    new_channel = {"name": name, "url": url}
    optional_channels_collection.insert_one(new_channel)
    bot.reply_to(message, f"✅ Ixtiyoriy kanal {name} qo'shildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   MAJBURIY BOT QO'SHISH
# ==========================
@bot.callback_query_handler(func=lambda c: c.data == "bot_add_menu")
def bot_add_menu(call):
    bot.edit_message_text("🤖 Majburiy botlar bo'limi:", call.message.chat.id, call.message.message_id, reply_markup=required_bots_menu())

@bot.callback_query_handler(func=lambda c: c.data == "bot_add")
def start_bot_add(call):
    uid = call.from_user.id
    admin_state[uid] = "bot_add_name"
    admin_data[uid] = {}
    bot.edit_message_text("➕ Majburiy bot qo'shish. Bot username ni yuboring:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "bot_add_name")
def bot_add_username(message):
    uid = message.from_user.id
    username = message.text.strip().replace("@", "")
    if not username:
        bot.reply_to(message, "❌ Noto'g'ri username formati!")
        return
    admin_data[uid]["bot_username"] = username
    admin_state[uid] = "bot_add_count"
    bot.reply_to(message, "👥 Ushbu botga qancha foydalanuvchi start bosgan?")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "bot_add_count")
def bot_add_count(message):
    uid = message.from_user.id
    try:
        count = int(message.text)
    except:
        bot.reply_to(message, "❌ Miqdor faqat raqam bo'lishi kerak.")
        return
    admin_data[uid]["count"] = count
    admin_state[uid] = "bot_add_name"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🤖 Avto nomlash", callback_data="bot_auto_name"))
    bot.reply_to(message, "📛 Bot uchun nom kiriting:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "bot_auto_name")
def bot_auto_name(call):
    uid = call.from_user.id
    if admin_state.get(uid) != "bot_add_name":
        return
    auto_bots = list(required_bots_collection.find({}))
    auto_name = f"{len(auto_bots) + 1}-Bot"
    data = admin_data.get(uid, {})
    new_bot = {"name": auto_name, "bot_username": data["bot_username"], "count": data["count"], "auto": True}
    required_bots_collection.insert_one(new_bot)
    bot.edit_message_text(f"✅ {auto_name} qo'shildi!", call.message.chat.id, call.message.message_id)
    admin_state[uid] = None
    admin_data[uid] = {}

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "bot_add_name")
def bot_custom_name(message):
    uid = message.from_user.id
    name = message.text.strip()
    data = admin_data.get(uid, {})
    new_bot = {"name": name, "bot_username": data["bot_username"], "count": data["count"], "auto": False}
    required_bots_collection.insert_one(new_bot)
    bot.reply_to(message, f"✅ {name} qo'shildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   BOT TAHRIRLASH VA O'CHIRISH
# ==========================
@bot.callback_query_handler(func=lambda c: c.data == "bot_edit")
def bot_edit_list(call):
    bots = list(required_bots_collection.find({}))
    if not bots:
        bot.edit_message_text("❌ Majburiy botlar yo'q.", call.message.chat.id, call.message.message_id)
        return
    kb = InlineKeyboardMarkup()
    for b in bots:
        kb.add(InlineKeyboardButton(b["name"], callback_data=f"edit_bot:{b['_id']}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="bot_back"))
    bot.edit_message_text("✏️ Tahrirlash uchun botni tanlang:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_bot:"))
def edit_bot_menu(call):
    bot_id = call.data.split(":")[1]
    bot_info = required_bots_collection.find_one({"_id": ObjectId(bot_id)})
    if not bot_info:
        bot.answer_callback_query(call.id, "❌ Bot topilmadi.")
        return
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📛 Nomni o'zgartirish", callback_data=f"edit_bot_name:{bot_id}"))
    kb.add(InlineKeyboardButton("👥 Miqdorni o'zgartirish", callback_data=f"edit_bot_count:{bot_id}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="bot_edit"))
    bot.edit_message_text(f"✏️ {bot_info['name']} botini tahrirlash:\n🤖 Username: @{bot_info['bot_username']}\n👥 Obunachilar: {bot_info['count']}", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "bot_delete")
def bot_delete_list(call):
    bots = list(required_bots_collection.find({}))
    if not bots:
        bot.edit_message_text("❌ Majburiy botlar yo'q.", call.message.chat.id, call.message.message_id)
        return
    kb = InlineKeyboardMarkup()
    for b in bots:
        kb.add(InlineKeyboardButton(b["name"], callback_data=f"del_bot:{b['_id']}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="bot_back"))
    bot.edit_message_text("🗑 O'chirish uchun botni tanlang:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_bot:"))
def delete_bot_confirm(call):
    bot_id = call.data.split(":")[1]
    bot_info = required_bots_collection.find_one({"_id": ObjectId(bot_id)})
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Ha", callback_data=f"del_bot_yes:{bot_id}"), InlineKeyboardButton("❌ Yo'q", callback_data="bot_delete"))
    bot.edit_message_text(f"⚠️ {bot_info['name']} botini o'chirmoqchimisiz?", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_bot_yes:"))
def delete_bot_yes(call):
    bot_id = call.data.split(":")[1]
    required_bots_collection.delete_one({"_id": ObjectId(bot_id)})
    bot.edit_message_text("✅ Bot o'chirildi!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "bot_back")
def bot_back(call):
    bot.edit_message_text("📌 Majburiy obuna bo'limi:", call.message.chat.id, call.message.message_id, reply_markup=required_menu())

# ==========================
#   TAHRIRLASH (KANAL UCHUN)
# ==========================
@bot.callback_query_handler(func=lambda c: c.data == "req_edit")
def start_required_edit(call):
    channels = list(required_channels_collection.find({}))
    if not channels:
        bot.edit_message_text("❌ Majburiy kanallar yo'q.", call.message.chat.id, call.message.message_id)
        return
    kb = InlineKeyboardMarkup()
    for ch in channels:
        kb.add(InlineKeyboardButton(ch["name"], callback_data=f"edit_req:{ch['_id']}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_back"))
    bot.edit_message_text("✏️ Tahrirlash uchun kanalni tanlang:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_req:"))
def edit_required_menu(call):
    ch_id = call.data.split(":")[1]
    channel = required_channels_collection.find_one({"_id": ObjectId(ch_id)})
    if not channel:
        bot.answer_callback_query(call.id, "❌ Kanal topilmadi.")
        return
    kb = InlineKeyboardMarkup()
    if not channel.get("auto"):
        kb.add(InlineKeyboardButton("📛 Nomni o'zgartirish", callback_data=f"edit_name:{ch_id}"))
    kb.add(InlineKeyboardButton("🔗 Havolani o'zgartirish", callback_data=f"edit_url:{ch_id}"))
    kb.add(InlineKeyboardButton("👥 Miqdorni o'zgartirish", callback_data=f"edit_count:{ch_id}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_edit"))
    bot.edit_message_text(f"✏️ {channel['name']} kanalini tahrirlash:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_name:"))
def edit_name_start(call):
    uid = call.from_user.id
    ch_id = call.data.split(":")[1]
    admin_state[uid] = f"edit_name_{ch_id}"
    admin_data[uid] = {"ch_id": ch_id}
    bot.edit_message_text("📛 Yangi nomni kiriting:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) and admin_state.get(m.from_user.id).startswith("edit_name_"))
def edit_name_save(message):
    uid = message.from_user.id
    name = message.text.strip()
    ch_id = admin_data[uid]["ch_id"]
    required_channels_collection.update_one({"_id": ObjectId(ch_id)}, {"$set": {"name": name}})
    bot.reply_to(message, f"✅ Nom {name} ga o'zgartirildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_url:"))
def edit_url_start(call):
    uid = call.from_user.id
    ch_id = call.data.split(":")[1]
    admin_state[uid] = f"edit_url_{ch_id}"
    admin_data[uid] = {"ch_id": ch_id}
    bot.edit_message_text("🔗 Yangi havolani kiriting:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) and admin_state.get(m.from_user.id).startswith("edit_url_"))
def edit_url_save(message):
    uid = message.from_user.id
    url = message.text.strip()
    ch_id = admin_data[uid]["ch_id"]
    required_channels_collection.update_one({"_id": ObjectId(ch_id)}, {"$set": {"url": url}})
    bot.reply_to(message, "✅ Havola o'zgartirildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_count:"))
def edit_count_start(call):
    uid = call.from_user.id
    ch_id = call.data.split(":")[1]
    admin_state[uid] = f"edit_count_{ch_id}"
    admin_data[uid] = {"ch_id": ch_id}
    bot.edit_message_text("👥 Yangi miqdorni kiriting:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) and admin_state.get(m.from_user.id).startswith("edit_count_"))
def edit_count_save(message):
    uid = message.from_user.id
    try:
        new_count = int(message.text)
    except:
        bot.reply_to(message, "❌ Miqdor faqat raqam bo'lishi kerak.")
        return
    ch_id = admin_data[uid]["ch_id"]
    required_channels_collection.update_one({"_id": ObjectId(ch_id)}, {"$set": {"count": new_count}})
    bot.reply_to(message, f"✅ Miqdor {new_count} ga o'zgartirildi!")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   O'CHIRISH (KANAL UCHUN)
# ==========================
@bot.callback_query_handler(func=lambda c: c.data == "req_delete")
def start_required_delete(call):
    req = list(required_channels_collection.find({}))
    opt = list(optional_channels_collection.find({}))
    kb = InlineKeyboardMarkup()
    if req:
        kb.add(InlineKeyboardButton("📛 Majburiy kanallar", callback_data="del_req_list"))
    if opt:
        kb.add(InlineKeyboardButton("📛 Ixtiyoriy kanallar", callback_data="del_opt_list"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_back"))
    bot.edit_message_text("🗑 O'chirish bo'limi:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "del_req_list")
def delete_required_list(call):
    channels = list(required_channels_collection.find({}))
    if not channels:
        bot.edit_message_text("❌ Majburiy kanallar yo'q.", call.message.chat.id, call.message.message_id)
        return
    kb = InlineKeyboardMarkup()
    for ch in channels:
        kb.add(InlineKeyboardButton(ch["name"], callback_data=f"del_req_confirm:{ch['_id']}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_delete"))
    bot.edit_message_text("🗑 O'chirish uchun kanalni tanlang:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_req_confirm:"))
def delete_required_confirm(call):
    ch_id = call.data.split(":")[1]
    ch = required_channels_collection.find_one({"_id": ObjectId(ch_id)})
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Ha", callback_data=f"del_req_yes:{ch_id}"), InlineKeyboardButton("❌ Yo'q", callback_data="del_req_list"))
    bot.edit_message_text(f"⚠️ {ch['name']} kanalini o'chirmoqchimisiz?", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_req_yes:"))
def delete_required_yes(call):
    ch_id = call.data.split(":")[1]
    required_channels_collection.delete_one({"_id": ObjectId(ch_id)})
    auto_channels = list(required_channels_collection.find({"auto": True}))
    auto_channels.sort(key=lambda x: x.get("name", ""))
    for i, ch in enumerate(auto_channels):
        new_name = f"{i+1}-Kanal"
        required_channels_collection.update_one({"_id": ch["_id"]}, {"$set": {"name": new_name}})
    bot.edit_message_text("✅ Kanal o'chirildi!", call.message.chat.id, call.message.message_id)
    delete_required_list(call)

@bot.callback_query_handler(func=lambda c: c.data == "del_opt_list")
def delete_optional_list(call):
    channels = list(optional_channels_collection.find({}))
    if not channels:
        bot.edit_message_text("❌ Ixtiyoriy kanallar yo'q.", call.message.chat.id, call.message.message_id)
        return
    kb = InlineKeyboardMarkup()
    for ch in channels:
        kb.add(InlineKeyboardButton(ch["name"], callback_data=f"del_opt_confirm:{ch['_id']}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_delete"))
    bot.edit_message_text("🗑 O'chirish uchun kanalni tanlang:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_opt_confirm:"))
def delete_optional_confirm(call):
    ch_id = call.data.split(":")[1]
    ch = optional_channels_collection.find_one({"_id": ObjectId(ch_id)})
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Ha", callback_data=f"del_opt_yes:{ch_id}"), InlineKeyboardButton("❌ Yo'q", callback_data="del_opt_list"))
    bot.edit_message_text(f"⚠️ {ch['name']} kanalini o'chirmoqchimisiz?", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_opt_yes:"))
def delete_optional_yes(call):
    ch_id = call.data.split(":")[1]
    optional_channels_collection.delete_one({"_id": ObjectId(ch_id)})
    bot.edit_message_text("✅ Kanal o'chirildi!", call.message.chat.id, call.message.message_id)
    delete_optional_list(call)

@bot.callback_query_handler(func=lambda c: c.data == "req_back")
def back_to_required_menu(call):
    bot.edit_message_text("📌 Majburiy obuna bo'limi:", call.message.chat.id, call.message.message_id, reply_markup=required_menu())

# ==========================
#   TEXT COPY (SODDA)
# ==========================
@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "text_copy_waiting")
def text_copy_get_text(message):
    uid = message.from_user.id
    admin_data[uid] = {
        "text_template": message.text if message.text else message.caption,
        "content_type": message.content_type,
        "file_id": None
    }
    if message.content_type == "photo":
        admin_data[uid]["file_id"] = message.photo[-1].file_id
    elif message.content_type == "video":
        admin_data[uid]["file_id"] = message.video.file_id
    elif message.content_type == "document":
        admin_data[uid]["file_id"] = message.document.file_id
    admin_state[uid] = "text_copy_waiting_count"
    bot.reply_to(message, "🔢 Nechta nusxa kerak? (raqam kiriting):")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "text_copy_waiting_count")
def text_copy_get_count(message):
    uid = message.from_user.id
    try:
        count = int(message.text.strip())
        if count < 1 or count > 10000:
            bot.reply_to(message, "❌ 1 dan 10000 gacha son kiriting!")
            return
    except:
        bot.reply_to(message, "❌ Iltimos, faqat son kiriting!")
        return
    admin_data[uid]["count"] = count
    admin_state[uid] = "text_copy_waiting_channel"
    bot.reply_to(message, "📢 Kanal ID raqamini kiriting (masalan: -1001234567890):")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "text_copy_waiting_channel")
def text_copy_get_channel(message):
    uid = message.from_user.id
    try:
        channel_id = int(message.text.strip())
    except:
        bot.reply_to(message, "❌ Noto'g'ri kanal ID formati!")
        return
    data = admin_data[uid]
    text_template = data["text_template"]
    count = data["count"]
    content_type = data["content_type"]
    file_id = data.get("file_id")
    try:
        bot.get_chat(channel_id)
    except:
        bot.reply_to(message, "❌ Bot kanalda admin emas yoki kanal topilmadi!")
        return
    status_msg = bot.reply_to(message, f"📤 Xabarlar yuborilmoqda...\n📝 Jami: {count} ta")
    success = 0
    fail = 0
    for i in range(1, count + 1):
        try:
            formatted_text = text_template.replace("{raqam}", str(i))
            if content_type == "text":
                bot.send_message(channel_id, formatted_text, parse_mode="HTML")
            elif content_type == "photo":
                bot.send_photo(channel_id, file_id, caption=formatted_text, parse_mode="HTML")
            elif content_type == "video":
                bot.send_video(channel_id, file_id, caption=formatted_text, parse_mode="HTML")
            elif content_type == "document":
                bot.send_document(channel_id, file_id, caption=formatted_text, parse_mode="HTML")
            else:
                bot.send_message(channel_id, formatted_text, parse_mode="HTML")
            success += 1
            if i % 10 == 0 or i == count:
                try:
                    bot.edit_message_text(f"📤 Xabarlar yuborilmoqda...\n✅ {success}/{count} muvaffaqiyatli\n❌ {fail} xatolik", status_msg.chat.id, status_msg.message_id)
                except:
                    pass
            time.sleep(0.7)
        except:
            fail += 1
    bot.edit_message_text(f"✅ Xabarlar yuborish tugallandi!\n\n✅ Muvaffaqiyatli: {success}\n❌ Xatolik: {fail}", status_msg.chat.id, status_msg.message_id)
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   POST EDITOR (SODDA)
# ==========================
@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "post_editor_waiting_link")
def post_editor_get_link(message):
    uid = message.from_user.id
    post_url = message.text.strip()
    try:
        if "t.me/" in post_url:
            parts = post_url.split("/")
            username = parts[-2]
            msg_id = int(parts[-1])
            chat = bot.get_chat(f"@{username}")
            chat_id = chat.id
            post = bot.forward_message(chat_id, chat_id, msg_id)
            admin_data[uid] = {
                "chat_id": chat_id,
                "message_id": msg_id,
                "content": {
                    "text": post.text if post.text else "",
                    "caption": post.caption if post.caption else "",
                    "photo": post.photo[-1].file_id if post.photo else None,
                    "video": post.video.file_id if post.video else None,
                },
                "buttons": []
            }
            admin_state[uid] = "post_editor_waiting_buttons"
            bot.reply_to(message, "✅ Post topildi!\n\nEndi tugmalarni yuboring:\n<code>Tugma nomi - https://t.me/kanal</code>\n\nTugatish uchun /done yuboring.", parse_mode="HTML")
    except Exception as e:
        bot.reply_to(message, f"❌ Xatolik: {str(e)}")
        admin_state[uid] = None

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "post_editor_waiting_buttons" and not m.text.startswith("/"))
def post_editor_add_button(message):
    uid = message.from_user.id
    text = message.text.strip()
    if "|" in text:
        # Bir qatordagi bir nechta tugmalar
        sub_buttons = text.split(" | ")
        for sub in sub_buttons:
            if " - " in sub:
                name, link = sub.split(" - ", 1)
                admin_data[uid]["buttons"].append({"name": name.strip(), "url": link.strip()})
    elif " - " in text:
        name, link = text.split(" - ", 1)
        admin_data[uid]["buttons"].append({"name": name.strip(), "url": link.strip()})
    else:
        bot.reply_to(message, "❌ Noto'g'ri format! Tugma nomi va havolani ' - ' bilan ajrating.")
        return
    current = "\n".join([f"• {b['name']} -> {b['url']}" for b in admin_data[uid]["buttons"]])
    bot.reply_to(message, f"✅ Tugma qo'shildi!\n\n📋 Joriy tugmalar:\n{current}\n\nYana tugma qo'shishingiz mumkin yoki /done bilan tugating.")

@bot.message_handler(commands=['done'])
def done_handler(message):
    uid = message.from_user.id
    state = admin_state.get(uid)
    
    if state == "post_editor_waiting_buttons":
        data = admin_data.get(uid, {})
        if not data.get("buttons"):
            bot.reply_to(message, "❌ Hech qanday tugma qo'shilmagan!")
            admin_state[uid] = None
            admin_data[uid] = {}
            return
        kb = InlineKeyboardMarkup(row_width=1)
        for btn in data["buttons"]:
            kb.add(InlineKeyboardButton(btn["name"], url=btn["url"]))
        try:
            bot.delete_message(data["chat_id"], data["message_id"])
            content = data["content"]
            if content["photo"]:
                bot.send_photo(data["chat_id"], content["photo"], caption=content["caption"] or content["text"], reply_markup=kb)
            elif content["video"]:
                bot.send_video(data["chat_id"], content["video"], caption=content["caption"] or content["text"], reply_markup=kb)
            else:
                bot.send_message(data["chat_id"], content["text"] or content["caption"], reply_markup=kb)
            bot.reply_to(message, "✅ Post yangilandi va tugmalar qo'shildi!")
        except Exception as e:
            bot.reply_to(message, f"❌ Xatolik: {str(e)}")
        admin_state[uid] = None
        admin_data[uid] = {}
        return
    
    elif state == "content_button_waiting_buttons":
        if not admin_data.get(uid, {}).get("buttons"):
            bot.reply_to(message, "❌ Hech qanday tugma qo'shilmagan!")
            admin_state[uid] = None
            admin_data[uid] = {}
            return
        content_code = admin_data[uid]["content_code"]
        buttons = admin_data[uid]["buttons"]
        content_buttons_collection.update_one(
            {"code": content_code},
            {"$set": {"buttons": buttons, "updated_at": time.time()}},
            upsert=True
        )
        bot.reply_to(message, f"✅ {len(buttons)} ta tugma kontentga qo'shildi!")
        admin_state[uid] = None
        admin_data[uid] = {}
        return
    
    elif state == "text_copy_waiting_count":
        admin_state[uid] = None
        admin_data[uid] = {}
        bot.reply_to(message, "❌ Text copy bekor qilindi.")
        return

# ==========================
#   CANTENTGA TUGMA QOSHISH
# ==========================
@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "content_button_waiting_code")
def content_button_get_code(message):
    uid = message.from_user.id
    code_or_link = message.text.strip()
    code = code_or_link
    if "start=" in code_or_link:
        code = code_or_link.split("start=")[-1]
    content = contents.find_one({"code": code})
    if not content:
        bot.reply_to(message, "❌ Kontent topilmadi! To'g'ri kod yoki havola yuboring.")
        return
    admin_data[uid] = {"content_code": code, "buttons": []}
    admin_state[uid] = "content_button_waiting_buttons"
    bot.reply_to(message, "✅ Kontent topildi!\n\nEndi tugmalarni yuboring.\n\n<b>Format:</b>\n<code>Tugma nomi - https://t.me/kanal</code>\n\n<b>Bir qatorga bir nechta tugma:</b>\n<code>Tugma 1 - link1 | Tugma 2 - link2</code>\n\nTugatish uchun /done yuboring.", parse_mode="HTML")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "content_button_waiting_buttons" and not m.text.startswith("/"))
def content_button_add_buttons(message):
    uid = message.from_user.id
    text = message.text.strip()
    if "|" in text:
        sub_buttons = text.split(" | ")
        for sub in sub_buttons:
            if " - " in sub:
                name, link = sub.split(" - ", 1)
                admin_data[uid]["buttons"].append({"name": name.strip(), "url": link.strip(), "style": {}})
    elif " - " in text:
        name, link = text.split(" - ", 1)
        admin_data[uid]["buttons"].append({"name": name.strip(), "url": link.strip(), "style": {}})
    else:
        bot.reply_to(message, "❌ Noto'g'ri format! Tugma nomi va havolani ' - ' bilan ajrating.")
        return
    current = "\n".join([f"• {b['name']} -> {b['url']}" for b in admin_data[uid]["buttons"]])
    bot.reply_to(message, f"✅ Tugma qo'shildi!\n\n📋 Joriy tugmalar:\n{current}\n\nYana tugma qo'shishingiz mumkin yoki /done bilan tugating.")

# ==========================
#   VIDEO EDIT (SODDA)
# ==========================
video_edit_state = {}

def start_video_edit(message):
    uid = message.from_user.id
    video_edit_state[uid] = {"step": "menu", "image_id": None}
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🖼 Rasm", callback_data="ve_image"), InlineKeyboardButton("🎬 Video", callback_data="ve_video"))
    kb.add(InlineKeyboardButton("🔙 Chiqish", callback_data="ve_exit"))
    bot.send_message(message.chat.id, "🎬 Video ustiga rasm qo'yish\n1. Avval rasm tanlang\n2. So'ng video yuboring", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ve_"))
def ve_callback(call):
    uid = call.from_user.id
    if call.data == "ve_image":
        video_edit_state[uid]["step"] = "waiting_image"
        bot.edit_message_text("🖼 Rasm yuboring:", call.message.chat.id, call.message.message_id)
    elif call.data == "ve_video":
        if not video_edit_state.get(uid, {}).get("image_id"):
            bot.answer_callback_query(call.id, "❌ Avval rasm tanlang!", show_alert=True)
            return
        video_edit_state[uid]["step"] = "waiting_video"
        bot.edit_message_text("🎬 Video yuboring:", call.message.chat.id, call.message.message_id)
    elif call.data == "ve_exit":
        if uid in video_edit_state:
            del video_edit_state[uid]
        bot.delete_message(call.message.chat.id, call.message.message_id)

@bot.message_handler(content_types=['photo'])
def ve_handle_photo(message):
    uid = message.from_user.id
    if video_edit_state.get(uid, {}).get("step") == "waiting_image":
        file_id = message.photo[-1].file_id
        video_edit_state[uid]["image_id"] = file_id
        video_edit_state[uid]["step"] = "menu"
        bot.reply_to(message, "✅ Rasm saqlandi! Endi '🎬 Video' tugmasini bosing.")

@bot.message_handler(content_types=['video'])
def ve_handle_video(message):
    uid = message.from_user.id
    if video_edit_state.get(uid, {}).get("step") != "waiting_video":
        return
    image_id = video_edit_state[uid].get("image_id")
    if not image_id:
        bot.reply_to(message, "❌ Rasm topilmadi!")
        return
    status_msg = bot.reply_to(message, "⏳ Video ishlanmoqda...")
    try:
        import io
        file_info = bot.get_file(message.video.file_id)
        downloaded = bot.download_file(file_info.file_path)
        img_info = bot.get_file(image_id)
        img_data = bot.download_file(img_info.file_path)
        video_io = io.BytesIO(downloaded)
        video_io.name = f"video_{int(time.time())}.mp4"
        thumb_io = io.BytesIO(img_data)
        thumb_io.name = "thumb.jpg"
        sent = bot.send_video(message.chat.id, video_io, caption=message.caption, thumbnail=thumb_io, supports_streaming=True)
        bot.edit_message_text("✅ Video tayyor!", status_msg.chat.id, status_msg.message_id)
        bot.delete_message(status_msg.chat.id, status_msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Xatolik: {str(e)}", status_msg.chat.id, status_msg.message_id)

# ==========================
#   MAJBURIY OBUNA TEKSHIRISH
# ==========================
def check_required_subs(user_id):
    required = list(required_channels_collection.find({}))
    for ch in required:
        try:
            member = bot.get_chat_member(ch["channel_id"], user_id)
            if member.status not in ["member", "administrator", "creator", "restricted"]:
                return False
        except:
            return False
    return True

def check_required_bots(user_id):
    required = list(required_bots_collection.find({}))
    for bot_info in required:
        try:
            member = bot.get_chat_member(f"@{bot_info['bot_username']}", user_id)
            if member.status != "member":
                return False
        except:
            return False
    return True

def get_required_keyboard(user_id, code):
    required = list(required_channels_collection.find({}))
    optional = list(optional_channels_collection.find({}))
    buttons = []
    for ch in required:
        try:
            member = bot.get_chat_member(ch["channel_id"], user_id)
            if member.status in ["member", "administrator", "creator", "restricted"]:
                continue
        except:
            pass
        buttons.append(InlineKeyboardButton(ch["name"], url=ch["url"]))
    if not check_required_subs(user_id):
        for ch in optional:
            buttons.append(InlineKeyboardButton(ch["name"], url=ch["url"]))
    random.shuffle(buttons)
    kb = InlineKeyboardMarkup(row_width=1)
    for btn in buttons:
        kb.add(btn)
    kb.add(InlineKeyboardButton("✔️ Tekshirish", url=f"https://t.me/{BOT_USERNAME}?start={code}"))
    return kb

def get_required_bots_keyboard(user_id, code):
    required = list(required_bots_collection.find({}))
    buttons = []
    for bot_info in required:
        try:
            member = bot.get_chat_member(f"@{bot_info['bot_username']}", user_id)
            if member.status == "member":
                continue
        except:
            pass
        buttons.append(InlineKeyboardButton(bot_info["name"], url=f"https://t.me/{bot_info['bot_username']}?start=from_{BOT_USERNAME}"))
    random.shuffle(buttons)
    kb = InlineKeyboardMarkup(row_width=1)
    for btn in buttons:
        kb.add(btn)
    kb.add(InlineKeyboardButton("✔️ Tekshirish", url=f"https://t.me/{BOT_USERNAME}?start={code}"))
    return kb

def schedule_delete(chat_id, message_id, delay=300):
    def _delete():
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
    threading.Timer(delay, _delete).start()

def send_content(chat_id, items, is_batch=False):
    # Tugmalarni tekshirish
    if items and len(items) > 0:
        first_item = items[0]
        content_code = first_item.get("code")
        if content_code:
            button_data = content_buttons_collection.find_one({"code": content_code})
            if button_data and button_data.get("buttons"):
                kb = InlineKeyboardMarkup(row_width=1)
                for btn in button_data["buttons"]:
                    kb.add(InlineKeyboardButton(btn["name"], url=btn["url"]))
                first = items[0]
                if first["type"] == "text":
                    bot.send_message(chat_id, first["text"], reply_markup=kb)
                elif first["type"] == "photo":
                    bot.send_photo(chat_id, first["file_id"], caption=first.get("caption"), reply_markup=kb)
                elif first["type"] == "video":
                    bot.send_video(chat_id, first["file_id"], caption=first.get("caption"), reply_markup=kb)
                elif first["type"] == "document":
                    bot.send_document(chat_id, first["file_id"], caption=first.get("caption"), reply_markup=kb)
                for item in items[1:]:
                    if item["type"] == "text":
                        bot.send_message(chat_id, item["text"])
                    elif item["type"] == "photo":
                        bot.send_photo(chat_id, item["file_id"], caption=item.get("caption"))
                    elif item["type"] == "video":
                        bot.send_video(chat_id, item["file_id"], caption=item.get("caption"))
                    elif item["type"] == "document":
                        bot.send_document(chat_id, item["file_id"], caption=item.get("caption"))
                warn = bot.send_message(chat_id, "⚠️ ESLATMA\n❗ Ushbu habarlar 5 daqiqadan so'ng o'chiriladi!")
                schedule_delete(chat_id, warn.message_id, 300)
                return
    for item in items:
        if item["type"] == "text":
            msg = bot.send_message(chat_id, item["text"])
        elif item["type"] == "photo":
            msg = bot.send_photo(chat_id, item["file_id"], caption=item.get("caption"))
        elif item["type"] == "video":
            msg = bot.send_video(chat_id, item["file_id"], caption=item.get("caption"))
        elif item["type"] == "document":
            msg = bot.send_document(chat_id, item["file_id"], caption=item.get("caption"))
        elif item["type"] == "sticker":
            msg = bot.send_sticker(chat_id, item["file_id"])
        elif item["type"] == "audio":
            msg = bot.send_audio(chat_id, item["file_id"], caption=item.get("caption"))
        elif item["type"] == "voice":
            msg = bot.send_voice(chat_id, item["file_id"])
        elif item["type"] == "animation":
            msg = bot.send_animation(chat_id, item["file_id"], caption=item.get("caption"))
        else:
            continue
        if msg:
            schedule_delete(chat_id, msg.message_id, 300)
    warn = bot.send_message(chat_id, "⚠️ ESLATMA\n❗ Ushbu habarlar 5 daqiqadan so'ng o'chiriladi!")
    schedule_delete(chat_id, warn.message_id, 300)

# ==========================
#   /start
# ==========================
@bot.message_handler(commands=['start'])
def start(message):
    print(f"START komandasi: {message.text}")
    
    if len(message.text.split()) == 1:
        users_collection.update_one({"user_id": message.from_user.id}, {"$set": {"user_id": message.from_user.id}}, upsert=True)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📝 Bot Haqida", callback_data="about"), InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{message.message_id}"))
        bot.reply_to(message, "Bu bot orqali kanaldagi animelarni yuklab olishingiz mumkin.\n\n❗️Botga habar yozmang❗️", reply_markup=markup)
        return
    
    code = message.text.split()[1]
    print(f"START code: {code}")
    
    if code.startswith("ref_"):
        ref_name = code.replace("ref_", "")
        referral = referrals_collection.find_one({"name": ref_name})
        if referral:
            user = users_collection.find_one({"user_id": message.from_user.id})
            if not user:
                user_referrals_collection.update_one({"user_id": message.from_user.id}, {"$set": {"referral_name": ref_name}}, upsert=True)
        users_collection.update_one({"user_id": message.from_user.id}, {"$set": {"user_id": message.from_user.id}}, upsert=True)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📝 Bot Haqida", callback_data="about"), InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{message.message_id}"))
        bot.reply_to(message, "Bu bot orqali kanaldagi animelarni yuklab olishingiz mumkin.\n\n❗️Botga habar yozmang❗️", reply_markup=markup)
        return
    
    items = list(contents.find({"code": code}).sort("order", 1))
    print(f"Kontentlar soni: {len(items)}")
    
    if not items:
        bot.send_message(message.chat.id, "❌ Kontent topilmadi.")
        return
    
    if not check_required_subs(message.from_user.id):
        settings = bot_settings_collection.find_one({"setting": "main_image"})
        if settings and settings.get("image_id"):
            bot.send_photo(message.chat.id, settings["image_id"], caption="📢 Animeni yuklab olish uchun quyidagi kanallarga obuna bo'ling:", reply_markup=get_required_keyboard(message.from_user.id, code))
        else:
            bot.send_message(message.chat.id, "📢 Animeni yuklab olish uchun quyidagi kanallarga obuna bo'ling:", reply_markup=get_required_keyboard(message.from_user.id, code))
        return
    
    if not check_required_bots(message.from_user.id):
        settings = bot_settings_collection.find_one({"setting": "main_image"})
        if settings and settings.get("image_id"):
            bot.send_photo(message.chat.id, settings["image_id"], caption="📢 Kontentni ko'rish uchun quyidagi botlarga start bosing:", reply_markup=get_required_bots_keyboard(message.from_user.id, code))
        else:
            bot.send_message(message.chat.id, "📢 Kontentni ko'rish uchun quyidagi botlarga start bosing:", reply_markup=get_required_bots_keyboard(message.from_user.id, code))
        return
    
    is_batch = contents.count_documents({"code": code}) > 1
    send_content(message.chat.id, items, is_batch)

# ==========================
#   CALLBACK HANDLER
# ==========================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    data = call.data
    print(f"CALLBACK: {data}")

    if data.startswith("close"):
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        return

    if data == "about":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("👨‍💻 Yaratuvchi", callback_data="creator"), InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{call.message.message_id}"))
        bot.edit_message_text("Botni ishlatish qo'llanmasi:\n1. Kanallarga obuna bo'ling!\n2. Botlarga start bosing!\n3. Tekshirish tugmasini bosing\n4. Yuklab oling", call.message.chat.id, call.message.message_id, reply_markup=markup)

    if data == "creator":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📝 Bot Haqida", callback_data="about"), InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{call.message.message_id}"))
        bot.edit_message_text("Admin: @Shadow_Sxi\nKanal: @AniGonUz", call.message.chat.id, call.message.message_id, reply_markup=markup)

# ==========================
#   RUN SERVER
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
