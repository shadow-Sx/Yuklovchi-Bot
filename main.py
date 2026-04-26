import os, time, random, string, threading, requests, telebot
from flask import Flask, request
from telebot.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from pymongo import MongoClient
from bson.objectid import ObjectId
import functions
from functions import add_premium_reaction, set_bot_username

# =================== TOKEN & SETTINGS ===================
TOKEN = os.getenv("BOT_TOKEN")
BOT_USERNAME = os.getenv("BOT_USERNAME")
ADMIN_ID = 7797502113

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
set_bot_username(BOT_USERNAME)

# =================== MONGO DB ===================
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
join_requests_collection = db["join_requests"]
ads_collection = db["ads"]

# =================== FLASK ===================
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

def keep_alive():
    while True:
        try:
            requests.get("https://yuklovchi-bot-5kne.onrender.com")
        except:
            pass
        time.sleep(60)

threading.Thread(target=keep_alive).start()

def generate_code(length=12):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

admin_state = {}
admin_data = {}
add_button_state = {}
broadcast_state = {}
ad_state = {}
custom_code_state = {}
edit_channel_state = {}

# =================== ADMIN PANEL ===================
def admin_panel():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("Cantent Qo'shish"), KeyboardButton("Majburi Obuna"))
    markup.row(KeyboardButton("Habar Yuborish"), KeyboardButton("Rasm Sozlash"))
    markup.row(KeyboardButton("2-Bo'lim"), KeyboardButton("🔙 Chiqish"))
    return markup

def second_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("Referal"), KeyboardButton("Zayavka sozlamari"))
    markup.row(KeyboardButton("Cantnetga tugma qoshish"), KeyboardButton("Reklama"))
    markup.row(KeyboardButton("1-Bo'lim"))
    return markup

def required_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("➕ Majburiy kanal", callback_data="req_add"),
           InlineKeyboardButton("➕ Ixtiyoriy kanal", callback_data="opt_add"))
    kb.add(InlineKeyboardButton("🤖 Majburiy bot", callback_data="bot_add_menu"),
           InlineKeyboardButton("✏️ Tahrirlash", callback_data="req_edit"))
    kb.add(InlineKeyboardButton("🗑 O'chirish", callback_data="req_delete"),
           InlineKeyboardButton("🔙 Orqaga", callback_data="req_back"))
    return kb

def required_bots_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("➕ Bot qo'shish", callback_data="bot_add"),
           InlineKeyboardButton("✏️ Tahrirlash", callback_data="bot_edit"))
    kb.add(InlineKeyboardButton("🗑 O'chirish", callback_data="bot_delete"),
           InlineKeyboardButton("🔙 Orqaga", callback_data="bot_back"))
    return kb

def ad_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("Habar miqdori"), KeyboardButton("Reklama joylash"))
    markup.row(KeyboardButton("Statistika"), KeyboardButton("O'chirish"))
    markup.row(KeyboardButton("🔙 Orqaga"))
    return markup

# =================== /admin ===================
@bot.message_handler(commands=['admin'])
def admin_start(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Siz admin emassiz!")
        return
    users_collection.update_one({"user_id": message.from_user.id},
                                {"$set": {"user_id": message.from_user.id}}, upsert=True)
    sent = bot.reply_to(message, "⚙️ Admin panelga xush kelibsiz!", reply_markup=admin_panel())
    add_premium_reaction(bot, sent.chat.id, sent.message_id, "👑")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text in [
    "Cantent Qo'shish", "Majburi Obuna", "Habar Yuborish", "Referal",
    "Rasm Sozlash", "🔙 Chiqish", "2-Bo'lim", "1-Bo'lim",
    "Cantnetga tugma qoshish", "Zayavka sozlamari", "Reklama",
    "Habar miqdori", "Reklama joylash", "Statistika", "O'chirish"
])
def admin_buttons(message):
    uid = message.from_user.id
    text = message.text

    if text == "Cantent Qo'shish":
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("1 - 1", callback_data="multi_mode_single"),
               InlineKeyboardButton("♾️ - 1", callback_data="multi_mode_batch"))
        admin_state[uid] = None
        bot.reply_to(message, "Qaysi tarzda kontent qo'shmoqchisiz?", reply_markup=kb)

    elif text == "Habar Yuborish":
        broadcast_state[uid] = {"step": "choose_mode"}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Forward", callback_data="broadcast_forward"),
               InlineKeyboardButton("Oddiy", callback_data="broadcast_normal"))
        bot.reply_to(message, "Qaysi tarzda foydalanuvchilarga habar yubormoqchisiz?", reply_markup=kb)

    elif text == "Majburi Obuna":
        bot.send_message(uid, "📌 Majburiy obuna bo'limi:", reply_markup=required_menu())

    elif text == "Referal":
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("➕ Yangi qo'shish", callback_data="referral_add"),
               InlineKeyboardButton("📊 Statistika", callback_data="referral_stats"))
        bot.send_message(uid, "Salom Admin bugun nima qilamiz?", reply_markup=kb)

    elif text == "Rasm Sozlash":
        admin_state[uid] = "set_main_image"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🗑 Rasmni o'chirish", callback_data="delete_main_image"))
        bot.reply_to(message, "🖼 Majburiy obuna xabari uchun rasm yuboring:", reply_markup=kb)

    elif text == "2-Bo'lim":
        bot.send_message(uid, "🔽 2-Bo'lim menyusi:", reply_markup=second_menu())

    elif text == "1-Bo'lim":
        bot.send_message(uid, "🔽 Asosiy menyu:", reply_markup=admin_panel())

    elif text == "Cantnetga tugma qoshish":
        add_button_state[uid] = {"step": "waiting_code"}
        bot.reply_to(message, "📎 Iltimos, kontent havolasini yoki start kodini yuboring:\n\n"
                     f"Masalan: <code>https://t.me/{BOT_USERNAME}?start=abc123</code>\nyoki <code>abc123</code>")

    elif text == "Zayavka sozlamari":
        bot.reply_to(message, "⚙️ Zayavka sozlamari hozircha mavjud emas. Bot avtomatik ravishda barcha zayavkalarni qabul qiladi.")

    elif text == "Reklama":
        bot.send_message(uid, "📢 Reklama bo'limi:", reply_markup=ad_menu())

    elif text == "Habar miqdori":
        ad_state[uid] = {"step": "waiting_threshold"}
        bot.reply_to(message, "🔢 Nechta kontentdan keyin reklama chiqsin? (raqam kiriting):")

    elif text == "Reklama joylash":
        ad_state[uid] = {"step": "choose_mode"}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Forward", callback_data="ad_forward"),
               InlineKeyboardButton("Oddiy", callback_data="ad_normal"))
        bot.reply_to(message, "Qaysi tarzda reklama joylamoqchisiz?", reply_markup=kb)

    elif text == "Statistika":
        ads = list(ads_collection.find({}))
        if not ads:
            bot.reply_to(message, "📊 Hozircha hech qanday reklama mavjud emas.")
            return
        text = "📊 <b>Reklamalar statistikasi</b>\n\n"
        for ad in ads:
            text += f"• ID: {ad['_id']} | Ko'rilgan: {ad.get('impressions', 0)}\n"
        bot.reply_to(message, text)

    elif text == "O'chirish":
        show_ads_for_delete(uid, message.chat.id)

    elif text == "🔙 Chiqish" or text == "🔙 Orqaga":
        admin_state.pop(uid, None)
        admin_data.pop(uid, None)
        add_button_state.pop(uid, None)
        broadcast_state.pop(uid, None)
        ad_state.pop(uid, None)
        custom_code_state.pop(uid, None)
        bot.send_message(uid, "<b>Admin paneldan chiqdingiz.</b>",
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        if text == "🔙 Orqaga":
            bot.send_message(uid, "Asosiy menyu:", reply_markup=second_menu())

# ---------- Reklama o'chirish ----------
def show_ads_for_delete(uid, chat_id):
    ads = list(ads_collection.find({}))
    if not ads:
        bot.send_message(chat_id, "❌ Hech qanday reklama mavjud emas.")
        return
    kb = InlineKeyboardMarkup()
    for ad in ads:
        kb.add(InlineKeyboardButton(f"🗑 Reklama {ad['_id']}", callback_data=f"del_ad:{ad['_id']}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="ad_back"))
    bot.send_message(chat_id, "O'chirish uchun reklamani tanlang:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_ad:"))
def confirm_delete_ad(call):
    ad_id = call.data.split(":")[1]
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Tasdiqlash", callback_data=f"confirm_del_ad:{ad_id}"),
           InlineKeyboardButton("❌ Bekor qilish", callback_data="ad_back"))
    bot.edit_message_text("⚠️ Haqiqatdan ham bu reklamani o'chirmoqchimisiz?",
                          call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_del_ad:"))
def delete_ad(call):
    ad_id = call.data.split(":")[1]
    ads_collection.delete_one({"_id": ObjectId(ad_id)})
    bot.answer_callback_query(call.id, "✅ Reklama o'chirildi!")
    show_ads_for_delete(call.from_user.id, call.message.chat.id)

@bot.callback_query_handler(func=lambda c: c.data == "ad_back")
def ad_back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.send_message(call.from_user.id, "📢 Reklama bo'limi:", reply_markup=ad_menu())

# ---------- Reklama joylash handlerlari ----------
@bot.callback_query_handler(func=lambda c: c.data in ["ad_forward", "ad_normal"])
def ad_mode_selected(call):
    uid = call.from_user.id
    mode = "forward" if call.data == "ad_forward" else "normal"
    ad_state[uid] = {"step": "waiting_ad_message", "mode": mode}
    bot.edit_message_text("📨 Reklama xabarini yuboring:", call.message.chat.id, call.message.message_id)

@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'sticker', 'audio', 'voice', 'video_note'],
                    func=lambda m: ad_state.get(m.from_user.id, {}).get("step") == "waiting_ad_message")
def ad_receive_message(message):
    uid = message.from_user.id
    ad_state[uid]["message"] = message
    ad_state[uid]["step"] = "ask_buttons"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("➕ Tugma qo'shish", callback_data="ad_add_btn"),
           InlineKeyboardButton("⏭ O'tkazib yuborish", callback_data="ad_skip_btn"))
    bot.reply_to(message, "Tugma qo'shishni xohlaysizmi?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "ad_add_btn")
def ad_add_buttons_start(call):
    uid = call.from_user.id
    ad_state[uid]["step"] = "waiting_buttons"
    bot.edit_message_text("🔘 Tugmalarni quyidagi formatda yuboring:\n\n"
                          "<code>Tugma nomi - URL</code>",
                          call.message.chat.id, call.message.message_id, parse_mode="HTML")

@bot.message_handler(func=lambda m: ad_state.get(m.from_user.id, {}).get("step") == "waiting_buttons")
def ad_save_buttons(message):
    uid = message.from_user.id
    text = message.text.strip()
    buttons = []
    for line in text.split("\n"):
        line = line.strip()
        if not line: continue
        if " - " in line:
            name, url = line.split(" - ", 1)
            buttons.append({"text": name.strip(), "url": url.strip()})
    ad_state[uid]["buttons"] = buttons
    ad_state[uid]["step"] = "confirm"
    show_ad_confirm(message.chat.id, uid, message)

@bot.callback_query_handler(func=lambda c: c.data == "ad_skip_btn")
def ad_skip_buttons(call):
    uid = call.from_user.id
    ad_state[uid]["step"] = "confirm"
    show_ad_confirm(call.message.chat.id, uid)

def show_ad_confirm(chat_id, uid, reply_to=None):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Tasdiqlash", callback_data="ad_final_confirm"),
           InlineKeyboardButton("❌ Bekor qilish", callback_data="ad_cancel"))
    if reply_to:
        bot.reply_to(reply_to, "⚠️ Reklamani saqlashni tasdiqlaysizmi?", reply_markup=kb)
    else:
        bot.send_message(chat_id, "⚠️ Reklamani saqlashni tasdiqlaysizmi?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "ad_final_confirm")
def ad_final_confirm(call):
    uid = call.from_user.id
    data = ad_state[uid]
    msg = data["message"]
    buttons = data.get("buttons", [])
    ad_doc = {
        "mode": data["mode"],
        "chat_id": msg.chat.id,
        "message_id": msg.message_id,
        "content_type": msg.content_type,
        "buttons": buttons,
        "impressions": 0,
        "created_at": time.time()
    }
    ads_collection.insert_one(ad_doc)
    bot.edit_message_text("✅ Reklama muvaffaqiyatli saqlandi!",
                          call.message.chat.id, call.message.message_id)
    ad_state.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data == "ad_cancel")
def ad_cancel(call):
    uid = call.from_user.id
    bot.edit_message_text("❌ Bekor qilindi.", call.message.chat.id, call.message.message_id)
    ad_state.pop(uid, None)

# ---------- Habar miqdori ----------
@bot.message_handler(func=lambda m: ad_state.get(m.from_user.id, {}).get("step") == "waiting_threshold")
def set_ad_threshold(message):
    uid = message.from_user.id
    try:
        threshold = int(message.text)
        bot_settings_collection.update_one({"setting": "ad_threshold"},
                                          {"$set": {"value": threshold}}, upsert=True)
        bot.reply_to(message, f"✅ Reklama har {threshold} kontentdan keyin chiqadigan bo'ldi.")
        ad_state.pop(uid, None)
    except:
        bot.reply_to(message, "❌ Iltimos, faqat raqam kiriting!")

# =================== MAJBURIY KANAL QO'SHISH ===================
@bot.callback_query_handler(func=lambda c: c.data == "req_add")
def start_required_add(call):
    uid = call.from_user.id
    admin_state[uid] = "req_add_id"
    admin_data[uid] = {}
    bot.edit_message_text("➕ Majburiy kanal qo'shish boshlandi.\n\nIltimos kanal ID raqamini yuboring:",
                          call.message.chat.id, call.message.message_id)

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
    bot.reply_to(message, "📛 Kanal uchun nom kiriting yoki pastdagi tugmani bosing:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "req_auto_name")
def req_auto_name(call):
    uid = call.from_user.id
    if admin_state.get(uid) != "req_add_name":
        return
    auto_channels = list(required_channels_collection.find({"auto": True}))
    auto_channels.sort(key=lambda x: x.get("name", ""))
    auto_name = f"{len(auto_channels) + 1}-Kanal"
    data = admin_data[uid]
    order = required_channels_collection.count_documents({}) + 1
    new_channel = {
        "name": auto_name,
        "channel_id": data["channel_id"],
        "url": data["url"],
        "count": data["count"],
        "auto": True,
        "order": order
    }
    required_channels_collection.insert_one(new_channel)
    bot.edit_message_text(f"✅ <b>{auto_name}</b> muvaffaqiyatli qo'shildi!",
                          call.message.chat.id, call.message.message_id, parse_mode="HTML")
    admin_state[uid] = None
    admin_data[uid] = {}

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_name")
def req_custom_name(message):
    uid = message.from_user.id
    name = message.text.strip()
    data = admin_data[uid]
    order = required_channels_collection.count_documents({}) + 1
    new_channel = {
        "name": name,
        "channel_id": data["channel_id"],
        "url": data["url"],
        "count": data["count"],
        "auto": False,
        "order": order
    }
    required_channels_collection.insert_one(new_channel)
    sent = bot.reply_to(message, f"✅ <b>{name}</b> muvaffaqiyatli qo'shildi!", parse_mode="HTML")
    add_premium_reaction(bot, sent.chat.id, sent.message_id, "➕")
    admin_state[uid] = None
    admin_data[uid] = {}

# =================== IXTIYORIY KANAL ===================
@bot.callback_query_handler(func=lambda c: c.data == "opt_add")
def start_optional_add(call):
    uid = call.from_user.id
    admin_state[uid] = "opt_add_name"
    admin_data[uid] = {}
    bot.edit_message_text("➕ Ixtiyoriy kanal qo'shish boshlandi.\n\nIltimos tugma uchun nom kiriting:",
                          call.message.chat.id, call.message.message_id)

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
    optional_channels_collection.insert_one({"name": name, "url": url})
    sent = bot.reply_to(message, f"✅ Ixtiyoriy kanal <b>{name}</b> qo'shildi!", parse_mode="HTML")
    add_premium_reaction(bot, sent.chat.id, sent.message_id, "➕")
    admin_state[uid] = None
    admin_data[uid] = {}

# =================== MAJBURIY BOT ===================
@bot.callback_query_handler(func=lambda c: c.data == "bot_add_menu")
def bot_add_menu(call):
    bot.edit_message_text("🤖 Majburiy botlar bo'limi:", call.message.chat.id, call.message.message_id,
                          reply_markup=required_bots_menu())

@bot.callback_query_handler(func=lambda c: c.data == "bot_add")
def start_bot_add(call):
    uid = call.from_user.id
    admin_state[uid] = "bot_add_username"
    admin_data[uid] = {}
    bot.edit_message_text("➕ Majburiy bot qo'shish boshlandi.\n\nIltimos bot username ni yuboring (masalan: @example_bot):",
                          call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "bot_add_username")
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
    admin_state[uid] = "bot_add_name_final"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🤖 Avto nomlash", callback_data="bot_auto_name"))
    bot.reply_to(message, "📛 Bot uchun nom kiriting yoki pastdagi tugmani bosing:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "bot_auto_name")
def bot_auto_name(call):
    uid = call.from_user.id
    if admin_state.get(uid) != "bot_add_name_final":
        return
    auto_bots = list(required_bots_collection.find({}))
    auto_name = f"{len(auto_bots) + 1}-Bot"
    data = admin_data[uid]
    new_bot = {"name": auto_name, "bot_username": data["bot_username"], "count": data["count"], "auto": True}
    required_bots_collection.insert_one(new_bot)
    bot.edit_message_text(f"✅ <b>{auto_name}</b> muvaffaqiyatli qo'shildi!",
                          call.message.chat.id, call.message.message_id, parse_mode="HTML")
    admin_state[uid] = None
    admin_data[uid] = {}

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "bot_add_name_final")
def bot_custom_name(message):
    uid = message.from_user.id
    name = message.text.strip()
    data = admin_data[uid]
    new_bot = {"name": name, "bot_username": data["bot_username"], "count": data["count"], "auto": False}
    required_bots_collection.insert_one(new_bot)
    sent = bot.reply_to(message, f"✅ <b>{name}</b> muvaffaqiyatli qo'shildi!", parse_mode="HTML")
    add_premium_reaction(bot, sent.chat.id, sent.message_id, "🤖")
    admin_state[uid] = None
    admin_data[uid] = {}

# =================== O'CHIRISH VA TAHRIRLASH ===================
@bot.callback_query_handler(func=lambda c: c.data == "req_edit")
def start_required_edit(call):
    channels = list(required_channels_collection.find({}).sort("order", 1))
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
    kb.add(InlineKeyboardButton("📛 Nomni o'zgartirish", callback_data=f"edit_name:{ch_id}"),
           InlineKeyboardButton("🔗 Havolani o'zgartirish", callback_data=f"edit_url:{ch_id}"),
           InlineKeyboardButton("👥 Miqdorni o'zgartirish", callback_data=f"edit_count:{ch_id}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_edit"))
    bot.edit_message_text(f"✏️ <b>{channel['name']}</b> kanalini tahrirlash:",
                          call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_name:"))
def edit_channel_name_start(call):
    uid = call.from_user.id
    ch_id = call.data.split(":")[1]
    edit_channel_state[uid] = {"id": ch_id, "field": "name"}
    bot.edit_message_text("📛 Yangi nomni yuboring:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: edit_channel_state.get(m.from_user.id, {}).get("field") == "name")
def edit_channel_name_save(message):
    uid = message.from_user.id
    data = edit_channel_state[uid]
    required_channels_collection.update_one({"_id": ObjectId(data["id"])}, {"$set": {"name": message.text.strip()}})
    bot.reply_to(message, "✅ Nom o'zgartirildi!")
    edit_channel_state.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_url:"))
def edit_channel_url_start(call):
    uid = call.from_user.id
    ch_id = call.data.split(":")[1]
    edit_channel_state[uid] = {"id": ch_id, "field": "url"}
    bot.edit_message_text("🔗 Yangi havolani yuboring:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: edit_channel_state.get(m.from_user.id, {}).get("field") == "url")
def edit_channel_url_save(message):
    uid = message.from_user.id
    data = edit_channel_state[uid]
    required_channels_collection.update_one({"_id": ObjectId(data["id"])}, {"$set": {"url": message.text.strip()}})
    bot.reply_to(message, "✅ Havola o'zgartirildi!")
    edit_channel_state.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_count:"))
def edit_channel_count_start(call):
    uid = call.from_user.id
    ch_id = call.data.split(":")[1]
    edit_channel_state[uid] = {"id": ch_id, "field": "count"}
    bot.edit_message_text("👥 Yangi miqdorni yuboring:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: edit_channel_state.get(m.from_user.id, {}).get("field") == "count")
def edit_channel_count_save(message):
    uid = message.from_user.id
    try:
        count = int(message.text.strip())
        data = edit_channel_state[uid]
        required_channels_collection.update_one({"_id": ObjectId(data["id"])}, {"$set": {"count": count}})
        bot.reply_to(message, "✅ Miqdor o'zgartirildi!")
    except:
        bot.reply_to(message, "❌ Raqam kiriting!")
    edit_channel_state.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data == "req_delete")
def start_required_delete(call):
    req = list(required_channels_collection.find({}))
    opt = list(optional_channels_collection.find({}))
    kb = InlineKeyboardMarkup()
    if req: kb.add(InlineKeyboardButton("📛 Majburiy kanallar", callback_data="del_req_list"))
    if opt: kb.add(InlineKeyboardButton("📛 Ixtiyoriy kanallar", callback_data="del_opt_list"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_back"))
    bot.edit_message_text("🗑 O'chirish bo'limi:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "del_req_list")
def delete_required_list(call):
    channels = list(required_channels_collection.find({}).sort("order", 1))
    if not channels:
        bot.edit_message_text("❌ Majburiy kanallar yo'q.", call.message.chat.id, call.message.message_id)
        return
    kb = InlineKeyboardMarkup()
    for ch in channels:
        kb.add(InlineKeyboardButton(f"🗑 {ch['name']}", callback_data=f"del_req_confirm:{ch['_id']}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_delete"))
    bot.edit_message_text("🗑 O'chirish uchun kanalni tanlang:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_req_confirm:"))
def delete_required_confirm(call):
    ch_id = call.data.split(":")[1]
    ch = required_channels_collection.find_one({"_id": ObjectId(ch_id)})
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"del_req_yes:{ch_id}"),
           InlineKeyboardButton("❌ Yo'q", callback_data="del_req_list"))
    bot.edit_message_text(f"⚠️ <b>{ch['name']}</b> kanalini o'chirmoqchimisiz?",
                          call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_req_yes:"))
def delete_required_yes(call):
    ch_id = call.data.split(":")[1]
    required_channels_collection.delete_one({"_id": ObjectId(ch_id)})
    for i, ch in enumerate(required_channels_collection.find().sort("order", 1)):
        required_channels_collection.update_one({"_id": ch["_id"]}, {"$set": {"order": i+1}})
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
        kb.add(InlineKeyboardButton(f"🗑 {ch['name']}", callback_data=f"del_opt_confirm:{ch['_id']}"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="req_delete"))
    bot.edit_message_text("🗑 O'chirish uchun kanalni tanlang:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_opt_confirm:"))
def delete_optional_confirm(call):
    ch_id = call.data.split(":")[1]
    ch = optional_channels_collection.find_one({"_id": ObjectId(ch_id)})
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"del_opt_yes:{ch_id}"),
           InlineKeyboardButton("❌ Yo'q", callback_data="del_opt_list"))
    bot.edit_message_text(f"⚠️ <b>{ch['name']}</b> kanalini o'chirmoqchimisiz?",
                          call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_opt_yes:"))
def delete_optional_yes(call):
    ch_id = call.data.split(":")[1]
    optional_channels_collection.delete_one({"_id": ObjectId(ch_id)})
    bot.edit_message_text("✅ Kanal o'chirildi!", call.message.chat.id, call.message.message_id)
    delete_optional_list(call)

@bot.callback_query_handler(func=lambda c: c.data == "req_back")
def back_to_required_menu(call):
    bot.edit_message_text("📌 Majburiy obuna bo'limi:", call.message.chat.id, call.message.message_id,
                          reply_markup=required_menu())

# Bot tahrirlash va o'chirish
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
    bot.answer_callback_query(call.id, "Hozircha qo'llab-quvvatlanmaydi.")

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
    kb.add(InlineKeyboardButton("✅ Ha", callback_data=f"del_bot_yes:{bot_id}"),
           InlineKeyboardButton("❌ Yo'q", callback_data="bot_delete"))
    bot.edit_message_text(f"⚠️ <b>{bot_info['name']}</b> botini o'chirmoqchimisiz?",
                          call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="HTML")

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_bot_yes:"))
def delete_bot_yes(call):
    bot_id = call.data.split(":")[1]
    required_bots_collection.delete_one({"_id": ObjectId(bot_id)})
    bot.edit_message_text("✅ Bot o'chirildi!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "bot_back")
def bot_back(call):
    bot.edit_message_text("📌 Majburiy obuna bo'limi:", call.message.chat.id, call.message.message_id,
                          reply_markup=required_menu())

# =================== MULTI MODE ===================
@bot.callback_query_handler(func=lambda c: c.data in ["multi_mode_single", "multi_mode_batch"])
def multi_mode_select(call):
    uid = call.from_user.id
    if uid != ADMIN_ID: return
    if call.data == "multi_mode_single":
        admin_state[uid] = "multi_add_single"
        bot.edit_message_text("📥 Kontentlarni tashlang.\n\nHar bir kontent uchun alohida havola beriladi.\nTugagach /stop deb yozing.",
                              call.message.chat.id, call.message.message_id)
    else:
        admin_state[uid] = "multi_add_batch"
        admin_data[uid] = {"batch": []}
        bot.edit_message_text("📥 Barcha kontentlarni yuboring va oxirida /stop bosing.\n\nBarchasi uchun bitta havola beriladi.",
                              call.message.chat.id, call.message.message_id)

@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'sticker', 'audio', 'voice', 'video_note'],
                    func=lambda m: admin_state.get(m.from_user.id) in ["multi_add_single", "multi_add_batch"]
                    and not (hasattr(m, 'text') and m.text == "/stop"))
def save_multi(message):
    uid = message.from_user.id
    state = admin_state.get(uid)
    if state == "multi_add_single": time.sleep(0.1)
    elif state == "multi_add_batch": time.sleep(0.7)
    content_type = message.content_type
    item = {"type": content_type, "order": 1}
    if content_type == "video":
        item["file_id"] = message.video.file_id
        item["caption"] = message.caption
    elif content_type == "photo":
        item["file_id"] = message.photo[-1].file_id
        item["caption"] = message.caption
    elif content_type == "document":
        item["file_id"] = message.document.file_id
        item["caption"] = message.caption
    elif content_type == "sticker": item["file_id"] = message.sticker.file_id
    elif content_type == "audio":
        item["file_id"] = message.audio.file_id
        item["caption"] = message.caption
    elif content_type == "voice": item["file_id"] = message.voice.file_id
    elif content_type == "video_note": item["file_id"] = message.video_note.file_id
    else: item["text"] = message.text

    if state == "multi_add_single":
        code = generate_code()
        item["code"] = code
        contents.insert_one(item)
        link = f"https://t.me/{BOT_USERNAME}?start={code}"
        sent = bot.reply_to(message, link)
        add_premium_reaction(bot, sent.chat.id, sent.message_id, "✅")
    else:
        batch = admin_data[uid]["batch"]
        item["order"] = len(batch) + 1
        batch.append(item)
        admin_data[uid]["batch"] = batch
        sent = bot.reply_to(message, f"✅ {len(batch)}-kontent qabul qilindi.")
        add_premium_reaction(bot, sent.chat.id, sent.message_id, "✅")

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
        custom_code_state[uid] = {"batch": batch}
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("Random", callback_data="code_random"),
               InlineKeyboardButton("Qo'lda yozish", callback_data="code_custom"))
        bot.reply_to(message, "Iltimos havola turini tanlang", reply_markup=kb)
        return
    if state == "multi_add_single":
        admin_state[uid] = None
        sent = bot.reply_to(message, "<b>✅ Barcha kontentlar qabul qilindi.</b>", reply_markup=admin_panel())
        add_premium_reaction(bot, sent.chat.id, sent.message_id, "✅")
        return
    bot.reply_to(message, "❌ Hech qanday faol jarayon yo'q.")

@bot.callback_query_handler(func=lambda c: c.data in ["code_random", "code_custom"])
def handle_code_choice(call):
    uid = call.from_user.id
    if uid not in custom_code_state:
        bot.answer_callback_query(call.id, "Jarayon topilmadi!")
        return
    if call.data == "code_random":
        batch = custom_code_state[uid]["batch"]
        code = generate_code()
        save_batch_with_code(uid, code, batch)
        link = f"https://t.me/{BOT_USERNAME}?start={code}"
        bot.send_message(call.message.chat.id, link)
        bot.edit_message_text("✅ Havola yaratildi!", call.message.chat.id, call.message.message_id)
        custom_code_state.pop(uid, None)
        admin_state[uid] = None
        admin_data[uid] = {}
    else:
        custom_code_state[uid]["step"] = "enter_code"
        bot.edit_message_text("✏️ Havola uchun matn kiriting (bo'sh joylar '_' bilan almashtiriladi):",
                              call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: custom_code_state.get(m.from_user.id, {}).get("step") == "enter_code")
def custom_code_entered(message):
    uid = message.from_user.id
    raw = message.text.strip()
    code = raw.replace(" ", "_")
    if contents.count_documents({"code": code}) > 0:
        bot.reply_to(message, "❌ Bu kod allaqachon band! Boshqa nom kiriting.")
        return
    batch = custom_code_state[uid]["batch"]
    save_batch_with_code(uid, code, batch)
    link = f"https://t.me/{BOT_USERNAME}?start={code}"
    bot.reply_to(message, link)
    custom_code_state.pop(uid, None)
    admin_state[uid] = None
    admin_data[uid] = {}

def save_batch_with_code(uid, code, batch):
    docs = []
    for item in batch:
        doc = {"type": item["type"], "code": code, "order": item["order"]}
        if item["type"] in ["video", "photo", "document", "sticker", "audio", "voice", "video_note"]:
            doc["file_id"] = item.get("file_id")
            if "caption" in item: doc["caption"] = item["caption"]
        else:
            doc["text"] = item.get("text")
        docs.append(doc)
    contents.insert_many(docs)

# =================== CONTENTGA TUGMA QO'SHISH ===================
@bot.message_handler(func=lambda m: add_button_state.get(m.from_user.id, {}).get("step") == "waiting_code")
def button_add_code(message):
    uid = message.from_user.id
    text = message.text.strip()
    if "?start=" in text:
        code = text.split("?start=")[-1].split()[0].split("&")[0]
    else:
        code = text
    items = list(contents.find({"code": code}))
    if not items:
        bot.reply_to(message, "❌ Bunday kodli kontent topilmadi!")
        add_button_state.pop(uid, None)
        return
    add_button_state[uid] = {"step": "waiting_buttons", "code": code}
    bot.reply_to(message,
        "✅ Kod qabul qilindi!\n\nEndi tugmalarni quyidagi formatda yuboring:\n\n"
        "<b>Oddiy tugma:</b>\n<code>Kanal - https://t.me/kanal</code>\n\n"
        "<b>Bir qatorda bir nechta:</b>\n<code>Tugma1 - url1 | Tugma2 - url2</code>\n\n"
        "Har bir qator yangi qatordan boshlansin.", parse_mode="HTML")

@bot.message_handler(func=lambda m: add_button_state.get(m.from_user.id, {}).get("step") == "waiting_buttons")
def button_add_buttons(message):
    uid = message.from_user.id
    code = add_button_state[uid]["code"]
    text = message.text.strip()
    buttons = []
    for line in text.split("\n"):
        line = line.strip()
        if not line: continue
        row_buttons = []
        for part in line.split("|"):
            part = part.strip()
            if " - " in part:
                name, url = part.split(" - ", 1)
                row_buttons.append({"text": name.strip(), "url": url.strip()})
        if row_buttons:
            buttons.append(row_buttons)
    if not buttons:
        bot.reply_to(message, "❌ Hech qanday tugma topilmadi!")
        return
    contents.update_many({"code": code}, {"$set": {"buttons": buttons}})
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(b["text"], url=b["url"]) for b in row] for row in buttons])
    sent = bot.reply_to(message, f"✅ Tugmalar qo'shildi! Kod: <code>{code}</code>", reply_markup=kb)
    add_premium_reaction(bot, sent.chat.id, sent.message_id, "✅")
    add_button_state.pop(uid, None)

# =================== BROADCAST ===================
@bot.callback_query_handler(func=lambda c: c.data in ["broadcast_forward", "broadcast_normal"])
def broadcast_mode_selected(call):
    uid = call.from_user.id
    if uid != ADMIN_ID: return
    mode = "forward" if call.data == "broadcast_forward" else "normal"
    broadcast_state[uid] = {"step": "waiting_message", "mode": mode}
    bot.edit_message_text("📨 Xabaringizni yuboring.", call.message.chat.id, call.message.message_id)

@bot.message_handler(content_types=['text', 'photo', 'video', 'document', 'sticker', 'audio', 'voice', 'video_note'],
                    func=lambda m: broadcast_state.get(m.from_user.id, {}).get("step") == "waiting_message")
def broadcast_receive_message(message):
    uid = message.from_user.id
    broadcast_state[uid]["message"] = message
    broadcast_state[uid]["step"] = "confirm"
    show_broadcast_confirm(message.chat.id, uid, message)

def show_broadcast_confirm(chat_id, uid, reply_to=None):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ Tasdiqlash", callback_data="broadcast_final_confirm"),
           InlineKeyboardButton("❌ Bekor qilish", callback_data="broadcast_cancel"))
    text = "⚠️ Haqiqatdan ham shu xabarni barchaga yubormoqchimisiz?"
    if reply_to: bot.reply_to(reply_to, text, reply_markup=kb)
    else: bot.send_message(chat_id, text, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "broadcast_final_confirm")
def broadcast_final_confirm(call):
    uid = call.from_user.id
    data = broadcast_state[uid]
    msg = data["message"]
    users = users_collection.find({})
    success = fail = 0
    status_msg = bot.edit_message_text("⏳ Yuborilmoqda...", call.message.chat.id, call.message.message_id)
    for u in users:
        try:
            if data["mode"] == "forward":
                bot.copy_message(u["user_id"], msg.chat.id, msg.message_id)
            else:
                bot.copy_message(u["user_id"], msg.chat.id, msg.message_id)
            success += 1
            time.sleep(0.05)
        except: fail += 1
    bot.edit_message_text(f"✅ Yuborildi! Muvaffaqiyatli: {success}, Xatolik: {fail}",
                          call.message.chat.id, call.message.message_id)
    broadcast_state.pop(uid, None)

@bot.callback_query_handler(func=lambda c: c.data == "broadcast_cancel")
def broadcast_cancel(call):
    uid = call.from_user.id
    bot.edit_message_text("❌ Bekor qilindi.", call.message.chat.id, call.message.message_id)
    broadcast_state.pop(uid, None)

# =================== ZAYAVKA ===================
@bot.chat_join_request_handler()
def handle_join_request(update: telebot.types.ChatJoinRequest):
    try:
        chat_id = update.chat.id
        user_id = update.from_user.id
        channel = required_channels_collection.find_one({"channel_id": chat_id})
        if channel:
            join_requests_collection.update_one(
                {"user_id": user_id, "channel_id": chat_id},
                {"$set": {"timestamp": time.time()}}, upsert=True)
            users_collection.update_one({"user_id": user_id}, {"$set": {"user_id": user_id}}, upsert=True)
    except Exception as e:
        print(f"Zayavka xatolik: {e}")

# =================== MAJBURIY OBUNA ===================
def check_required_subs(user_id):
    required = list(required_channels_collection.find({}))
    for ch in required:
        channel_id = ch["channel_id"]
        try:
            member = bot.get_chat_member(channel_id, user_id)
            if member.status in ["member", "administrator", "creator", "restricted"]: continue
        except: pass
        if join_requests_collection.find_one({"user_id": user_id, "channel_id": channel_id}): continue
        return False
    return True

def get_required_keyboard(user_id, code):
    required = list(required_channels_collection.find({}).sort("order", 1))
    buttons = []
    for ch in required:
        channel_id = ch["channel_id"]
        is_member = False
        try:
            member = bot.get_chat_member(channel_id, user_id)
            if member.status in ["member", "administrator", "creator", "restricted"]: is_member = True
        except: pass
        if not is_member and join_requests_collection.find_one({"user_id": user_id, "channel_id": channel_id}):
            is_member = True
        if not is_member:
            buttons.append(InlineKeyboardButton(ch["name"], url=ch["url"]))
    if not check_required_subs(user_id):
        for ch in optional_channels_collection.find({}):
            buttons.append(InlineKeyboardButton(ch["name"], url=ch["url"]))
    random.shuffle(buttons)
    kb = InlineKeyboardMarkup(row_width=1)
    for btn in buttons: kb.add(btn)
    kb.add(InlineKeyboardButton("Tekshirish ♻️", url=f"https://t.me/{BOT_USERNAME}?start={code}"))
    return kb

# =================== KONTENTNI YUBORISH ===================
def schedule_delete(chat_id, message_id, delay=300):
    def _delete():
        try: bot.delete_message(chat_id, message_id)
        except: pass
    threading.Timer(delay, _delete).start()

def send_ad(chat_id):
    ads = list(ads_collection.find({}))
    if not ads: return
    ad = random.choice(ads)
    ads_collection.update_one({"_id": ad["_id"]}, {"$inc": {"impressions": 1}})
    markup = None
    if ad.get("buttons"):
        markup = InlineKeyboardMarkup([[InlineKeyboardButton(b["text"], url=b["url"]) for b in ad["buttons"]]])
    try:
        bot.copy_message(chat_id, ad["chat_id"], ad["message_id"], reply_markup=markup, protect_content=True)
    except: pass

def send_content(chat_id, items, is_batch=False):
    markup = None
    if items and "buttons" in items[0]:
        rows = [[InlineKeyboardButton(b["text"], url=b["url"]) for b in row] for row in items[0]["buttons"]]
        markup = InlineKeyboardMarkup(rows)

    for item in items:
        try:
            if item["type"] == "text": msg = bot.send_message(chat_id, item["text"], reply_markup=markup)
            elif item["type"] == "photo": msg = bot.send_photo(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=markup)
            elif item["type"] == "video": msg = bot.send_video(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=markup)
            elif item["type"] == "document": msg = bot.send_document(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=markup)
            elif item["type"] == "sticker": msg = bot.send_sticker(chat_id, item["file_id"], reply_markup=markup)
            elif item["type"] == "audio": msg = bot.send_audio(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=markup)
            elif item["type"] == "voice": msg = bot.send_voice(chat_id, item["file_id"], reply_markup=markup)
            elif item["type"] == "video_note": msg = bot.send_video_note(chat_id, item["file_id"], reply_markup=markup)
            if msg: schedule_delete(chat_id, msg.message_id, 300)
        except: pass
    warn = bot.send_message(chat_id, "<b>⚠️ ESLATMA ⚠️\n<blockquote>❗ Ushbu habarlar Ba'zi sabablarga kora 5 daqiqadan so'ng o'chiriladi.</blockquote></b>")
    schedule_delete(chat_id, warn.message_id, 300)

    # Har bir foydalanuvchi uchun alohida reklama hisoblagichi
    user = users_collection.find_one({"user_id": chat_id})
    count = user.get("content_count", 0) + (len(items) if is_batch else 1)
    users_collection.update_one({"user_id": chat_id}, {"$set": {"content_count": count}})

    threshold_doc = bot_settings_collection.find_one({"setting": "ad_threshold"})
    threshold = threshold_doc["value"] if threshold_doc else 10

    if count >= threshold:
        send_ad(chat_id)
        users_collection.update_one({"user_id": chat_id}, {"$set": {"content_count": 0}})

# =================== /start ===================
@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    users_collection.update_one({"user_id": uid}, {"$set": {"user_id": uid}}, upsert=True)
    args = message.text.split()
    
    if len(args) == 1:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📝 Bot Haqida", callback_data="about"),
                   InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{message.message_id}"))
        sent = bot.reply_to(message, "<i><blockquote>Bu bot orqali kanaldagi animelarni yuklab olishingiz mumkin.</blockquote></i>\n<b>❗️Botga habar yozmang❗️</b>", reply_markup=markup)
        add_premium_reaction(bot, sent.chat.id, sent.message_id, "🎉")
        return

    code = args[1]
    if code.startswith("ref_"):
        ref_name = code[4:]
        if referrals_collection.find_one({"name": ref_name}):
            user_referrals_collection.update_one({"user_id": uid}, {"$set": {"referral_name": ref_name}}, upsert=True)
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📝 Bot Haqida", callback_data="about"),
                   InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{message.message_id}"))
        sent = bot.reply_to(message, "<b>Bu bot orqali kanaldagi animelarni yuklab olishingiz mumkin.</b>", reply_markup=markup)
        add_premium_reaction(bot, sent.chat.id, sent.message_id, "🎉")
        return

    items = list(contents.find({"code": code}).sort("order", 1))
    if not items:
        sent = bot.send_message(message.chat.id, "")
        add_premium_reaction(bot, sent.chat.id, sent.message_id, "❌")
        return

    # Majburiy obuna tekshiruvi
    if not check_required_subs(uid):
        settings = bot_settings_collection.find_one({"setting": "main_image"})
        kb = get_required_keyboard(uid, code)
        
        # Eski xabarni o'chirish
        user = users_collection.find_one({"user_id": uid})
        if user and user.get("last_required_msg_id"):
            try:
                bot.delete_message(message.chat.id, user["last_required_msg_id"])
            except: pass
        
        sent = None
        if settings and settings.get("image_id"):
            sent = bot.send_photo(message.chat.id, settings["image_id"],
                                  caption="📢 <b>Animeni yuklab olish uchun quyidagi kanallarga obuna bo'lishingiz kerak:</b>",
                                  reply_markup=kb)
        else:
            sent = bot.send_message(message.chat.id,
                                    "📢 <b>Animeni yuklab olish uchun quyidagi kanallarga obuna bo'lishingiz kerak:</b>",
                                    reply_markup=kb)
        users_collection.update_one({"user_id": uid}, {"$set": {"last_required_msg_id": sent.message_id}})
        add_premium_reaction(bot, sent.chat.id, sent.message_id, "🔔")
        return

    # Obuna bo'lgan bo'lsa, eski xabarni o'chirish
    user = users_collection.find_one({"user_id": uid})
    if user and user.get("last_required_msg_id"):
        try:
            bot.delete_message(message.chat.id, user["last_required_msg_id"])
        except: pass
        users_collection.update_one({"user_id": uid}, {"$unset": {"last_required_msg_id": ""}})

    is_batch = len(items) > 1
    send_content(message.chat.id, items, is_batch)

# =================== CALLBACK ===================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    data = call.data
    if data.startswith("close"):
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        return
    if data == "about":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("👨‍💻 Yaratuvchi", callback_data="creator"),
                   InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{call.message.message_id}"))
        bot.edit_message_text("<b>Botni ishlatishni bilmaganlar uchun!\n\n❏ Botni ishlatish qo'llanmasi:</b>\n<b>1. Kanallarga obuna boling!</b>\n<b>2. Tekshirish Tugmasini bosing ✅</b>\n<b>3. Kanaldagi anime post past qismidagi yuklab olish tugmasini bosing</b>\n\n<b>👨‍💻 Yaratuvchi @ShadowUzDev</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)
    if data == "creator":
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📝 Bot Haqida", callback_data="about"),
                   InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{call.message.message_id}"))
        bot.edit_message_text("<b>• Admin: @Shadow_Sxi\n• Asosiy Kanal: @AniGonUz\n• Reklama: @AniReklamaUz\n\n👨‍💻 Savollar Boʻlsa: @AniUzbChat</b>", call.message.chat.id, call.message.message_id, reply_markup=markup)

# =================== RUN ===================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
