import telebot
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from utils import (
    TOKEN, BOT_USERNAME, ADMIN_ID,
    contents, required_channels, optional_channels,
    referrals, settings, users,
    admin_state, admin_data,
    generate_code, save_user, schedule_delete
)
from bson.objectid import ObjectId
import threading
import time
import random

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ==========================
#   ADMIN PANEL MARKUP
# ==========================
def admin_main_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("📥 Kontent Qo‘shish"), KeyboardButton("📢 Broadcast"))
    kb.row(KeyboardButton("📌 Majburiy Obuna"), KeyboardButton("📌 Ixtiyoriy Obuna"))
    kb.row(KeyboardButton("🔗 Referal"), KeyboardButton("⏱ Avto-o‘chirish"))
    kb.row(KeyboardButton("📊 Statistika"), KeyboardButton("❌ Chiqish"))
    return kb

def multi_upload_menu():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🔹 Alohida kodlar bilan", callback_data="multi_single"),
        InlineKeyboardButton("🔸 Bitta kod bilan (playlist)", callback_data="multi_group")
    )
    kb.add(InlineKeyboardButton("🔙 Bekor qilish", callback_data="multi_cancel"))
    return kb

# ==========================
#   ADMIN /admin
# ==========================
@bot.message_handler(commands=["admin"])
def admin_start(message):
    if message.from_user.id != ADMIN_ID:
        return
    admin_state[message.from_user.id] = None
    admin_data[message.from_user.id] = {}
    bot.reply_to(message, "⚙️ Admin panelga xush kelibsiz!", reply_markup=admin_main_menu())

# ==========================
#   ADMIN TEXT BUTTONS
# ==========================
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and m.text in [
    "📥 Kontent Qo‘shish", "📢 Broadcast",
    "📌 Majburiy Obuna", "📌 Ixtiyoriy Obuna",
    "🔗 Referal", "⏱ Avto-o‘chirish",
    "📊 Statistika", "❌ Chiqish"
])
def admin_buttons(message):
    uid = message.from_user.id
    text = message.text

    if text == "📥 Kontent Qo‘shish":
        admin_state[uid] = "choose_multi_mode"
        bot.send_message(uid, "Kontent qo‘shish rejimini tanlang:", reply_markup=multi_upload_menu())

    elif text == "📢 Broadcast":
        admin_state[uid] = "wait_broadcast_content"
        admin_data[uid] = {}
        bot.send_message(uid, "Broadcast uchun xabar yuboring.")

    elif text == "📌 Majburiy Obuna":
        show_required_menu(message.chat.id)

    elif text == "📌 Ixtiyoriy Obuna":
        show_optional_menu(message.chat.id)

    elif text == "🔗 Referal":
        show_referral_menu(message.chat.id)

    elif text == "⏱ Avto-o‘chirish":
        admin_state[uid] = "wait_auto_delete"
        bot.send_message(uid, "Avto-o‘chirish vaqtini kiriting (mm:ss)")

    elif text == "📊 Statistika":
        total = users.count_documents({})
        bot.send_message(uid, f"📊 Foydalanuvchilar: <b>{total}</b>")

    elif text == "❌ Chiqish":
        admin_state[uid] = None
        admin_data[uid] = {}
        bot.send_message(uid, "Admin paneldan chiqdingiz.", reply_markup=telebot.types.ReplyKeyboardRemove())

# ==========================
#   REQUIRED / OPTIONAL MENUS
# ==========================
def show_required_menu(chat_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Qo‘shish", callback_data="req_add"),
        InlineKeyboardButton("✏️ Tahrirlash", callback_data="req_edit")
    )
    kb.add(
        InlineKeyboardButton("🗑 O‘chirish", callback_data="req_delete"),
        InlineKeyboardButton("📋 Ro‘yxat", callback_data="req_list")
    )
    bot.send_message(chat_id, "📌 Majburiy obuna:", reply_markup=kb)

def show_optional_menu(chat_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Qo‘shish", callback_data="opt_add"),
        InlineKeyboardButton("🗑 O‘chirish", callback_data="opt_delete")
    )
    kb.add(InlineKeyboardButton("📋 Ro‘yxat", callback_data="opt_list"))
    bot.send_message(chat_id, "📌 Ixtiyoriy obuna:", reply_markup=kb)

def show_referral_menu(chat_id):
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("➕ Yaratish", callback_data="ref_create"),
        InlineKeyboardButton("📊 Ko‘rish", callback_data="ref_view")
    )
    bot.send_message(chat_id, "🔗 Referal bo‘limi:", reply_markup=kb)

# ==========================
#   CALLBACK ROUTER
# ==========================
@bot.callback_query_handler(func=lambda c: c.from_user.id == ADMIN_ID)
def admin_callback(call):
    data = call.data
    uid = call.from_user.id

    if data == "multi_single":
        admin_state[uid] = "multi_single"
        admin_data[uid] = {"group_mode": False}
        bot.edit_message_text("🔹 Alohida kodlar rejimi.\nKontent yuboring.\n/stop bilan tugating.", call.message.chat.id, call.message.message_id)
        return

    if data == "multi_group":
        admin_state[uid] = "multi_group"
        admin_data[uid] = {"group_mode": True, "items": []}
        bot.edit_message_text("🔸 Playlist rejimi.\nBir nechta kontent yuboring.\n/stop bilan tugating.", call.message.chat.id, call.message.message_id)
        return

    if data == "multi_cancel":
        admin_state[uid] = None
        admin_data[uid] = {}
        bot.edit_message_text("❌ Bekor qilindi.", call.message.chat.id, call.message.message_id)
        return

    if data == "req_add": start_required_add(call)
    elif data == "req_edit": start_required_edit(call)
    elif data == "req_delete": start_required_delete(call)
    elif data == "req_list": list_required_channels(call)
    elif data == "opt_add": start_optional_add(call)
    elif data == "opt_delete": start_optional_delete(call)
    elif data == "opt_list": list_optional_channels(call)
    elif data == "ref_create": start_ref_create(call)
    elif data == "ref_view": view_referrals(call)

# ==========================
#   REQUIRED CHANNEL ADD
# ==========================
def start_required_add(call):
    uid = call.from_user.id
    admin_state[uid] = "req_add_id"
    admin_data[uid] = {}
    bot.edit_message_text("➕ Kanal ID yuboring:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_id")
def req_add_id(message):
    uid = message.from_user.id
    try:
        admin_data[uid]["channel_id"] = int(message.text)
    except:
        bot.reply_to(message, "❌ ID faqat raqam.")
        return
    admin_state[uid] = "req_add_url"
    bot.reply_to(message, "🔗 Kanal havolasini yuboring:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_url")
def req_add_url(message):
    uid = message.from_user.id
    url = message.text.strip()
    cid = admin_data[uid]["channel_id"]

    try:
        member = bot.get_chat_member(cid, bot.get_me().id)
        if member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "❌ Bot kanalda admin emas.")
            return
    except:
        bot.reply_to(message, "❌ Kanalga ulanib bo‘lmadi.")
        return

    admin_data[uid]["url"] = url
    admin_state[uid] = "req_add_name"
    bot.reply_to(message, "📛 Kanal nomini kiriting:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_name")
def req_add_name(message):
    uid = message.from_user.id
    name = message.text.strip()
    data = admin_data[uid]

    required_channels.insert_one({
        "name": name,
        "channel_id": data["channel_id"],
        "url": data["url"],
        "type": "required"
    })

    bot.reply_to(message, f"✅ Qo‘shildi:\n<b>{name}</b>\n{data['url']}")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   OPTIONAL CHANNELS
# ==========================
def start_optional_add(call):
    uid = call.from_user.id
    admin_state[uid] = "opt_add_id"
    admin_data[uid] = {}
    bot.edit_message_text("➕ Ixtiyoriy kanal ID yuboring:", call.message.chat.id, call.message.message_id)

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_add_id")
def opt_add_id(message):
    uid = message.from_user.id
    try:
        admin_data[uid]["channel_id"] = int(message.text)
    except:
        bot.reply_to(message, "❌ ID faqat raqam.")
        return
    admin_state[uid] = "opt_add_url"
    bot.reply_to(message, "🔗 Kanal havolasini yuboring:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_add_url")
def opt_add_url(message):
    uid = message.from_user.id
    url = message.text.strip()
    cid = admin_data[uid]["channel_id"]

    try:
        bot.get_chat_member(cid, bot.get_me().id)
    except:
        bot.reply_to(message, "❌ Kanalga ulanib bo‘lmadi.")
        return

    admin_data[uid]["url"] = url
    admin_state[uid] = "opt_add_name"
    bot.reply_to(message, "📛 Kanal nomini kiriting:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_add_name")
def opt_add_name(message):
    uid = message.from_user.id
    name = message.text.strip()
    data = admin_data[uid]

    optional_channels.insert_one({
        "name": name,
        "channel_id": data["channel_id"],
        "url": data["url"],
        "type": "optional"
    })

    bot.reply_to(message, f"✅ Qo‘shildi:\n<b>{name}</b>\n{data['url']}")
    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   LIST REQUIRED / OPTIONAL
# ==========================
def list_required_channels(call):
    chans = list(required_channels.find({}))
    if not chans:
        bot.edit_message_text("❌ Majburiy kanallar yo‘q.", call.message.chat.id, call.message.message_id)
        return

    text = "📋 Majburiy kanallar:\n\n"
    for ch in chans:
        text += f"• <b>{ch['name']}</b> — {ch['url']}\n"

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

def list_optional_channels(call):
    chans = list(optional_channels.find({}))
    if not chans:
        bot.edit_message_text("❌ Ixtiyoriy kanallar yo‘q.", call.message.chat.id, call.message.message_id)
        return

    text = "📋 Ixtiyoriy kanallar:\n\n"
    for ch in chans:
        text += f"• <b>{ch['name']}</b> — {ch['url']}\n"

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

# ==========================
#   DELETE REQUIRED/OPTIONAL
# ==========================
def start_required_delete(call):
    chans = list(required_channels.find({}))
    if not chans:
        bot.edit_message_text("❌ Majburiy kanallar yo‘q.", call.message.chat.id, call.message.message_id)
        return

    kb = InlineKeyboardMarkup()
    for ch in chans:
        kb.add(InlineKeyboardButton(f"{ch['name']} (ID: {ch['channel_id']})", callback_data=f"del_req:{ch['_id']}"))

    bot.edit_message_text("🗑 O‘chirish uchun tanlang:", call.message.chat.id, call.message.message_id, reply_markup=kb)

def start_optional_delete(call):
    chans = list(optional_channels.find({}))
    if not chans:
        bot.edit_message_text("❌ Ixtiyoriy kanallar yo‘q.", call.message.chat.id, call.message.message_id)
        return

    kb = InlineKeyboardMarkup()
    for ch in chans:
        kb.add(InlineKeyboardButton(f"{ch['name']} (ID: {ch['channel_id']})", callback_data=f"del_opt:{ch['_id']}"))

    bot.edit_message_text("🗑 O‘chirish uchun tanlang:", call.message.chat.id, call.message.message_id, reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("del_req:") or c.data.startswith("del_opt:"))
def delete_channel_callback(call):
    data = call.data
    if data.startswith("del_req:"):
        required_channels.delete_one({"_id": ObjectId(data.split(":")[1])})
        bot.edit_message_text("✅ Majburiy kanal o‘chirildi.", call.message.chat.id, call.message.message_id)
    else:
        optional_channels.delete_one({"_id": ObjectId(data.split(":")[1])})
        bot.edit_message_text("✅ Ixtiyoriy kanal o‘chirildi.", call.message.chat.id, call.message.message_id)

# ==========================
#   REFERAL
# ==========================
def start_ref_create(call):
    uid = call.from_user.id
    admin_state[uid] = "ref_create_key"
    bot.send_message(uid, "Referal kalit so‘zini kiriting:")

@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "ref_create_key")
def ref_create_key(message):
    uid = message.from_user.id
    key = message.text.strip()

    referrals.update_one({"key": key}, {"$set": {"key": key}}, upsert=True)

    link = f"https://t.me/{BOT_USERNAME}?start={key}"
    bot.reply_to(message, f"✅ Referal yaratildi:\n<code>{link}</code>")

    admin_state[uid] = None

def view_referrals(call):
    items = list(referrals.find({}))
    if not items:
        bot.send_message(call.message.chat.id, "Hali referallar yo‘q.")
        return

    text = "📊 Referallar:\n\n"
    for r in items:
        text += f"• <b>{r['key']}</b> — {r.get('count', 0)} ta start\n"

    bot.send_message(call.message.chat.id, text)

# ==========================
#   AVTO-O‘CHIRISH
# ==========================
@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "wait_auto_delete")
def set_auto_delete(message):
    uid = message.from_user.id
    text = message.text.strip()

    if ":" not in text:
        bot.reply_to(message, "❌ Format xato. Masalan: 1:30")
        return

    m, s = text.split(":")
    if not (m.isdigit() and s.isdigit()):
        bot.reply_to(message, "❌ Faqat raqam kiriting.")
        return

    total = int(m) * 60 + int(s)
    settings.update_one({"key": "auto_delete"}, {"$set": {"seconds": total}}, upsert=True)

    bot.reply_to(message, f"✅ Avto-o‘chirish yoqildi: {text}")
    admin_state[uid] = None

# ==========================
#   MULTI-UPLOAD /stop
# ==========================
@bot.message_handler(commands=["stop"])
def stop_multi(message):
    uid = message.from_user.id
    state = admin_state.get(uid)

    if state not in ["multi_single", "multi_group"]:
        return

    if state == "multi_group":
        items = admin_data.get(uid, {}).get("items", [])
        if not items:
            bot.reply_to(message, "❌ Hech qanday kontent yuborilmadi.")
            admin_state[uid] = None
            admin_data[uid] = {}
            return

        code = generate_code()
        contents.insert_one({"type": "group", "items": items, "code": code})

        link = f"https://t.me/{BOT_USERNAME}?start={code}"
        bot.reply_to(message, f"✅ Playlist saqlandi.\n<code>{link}</code>", reply_markup=admin_main_menu())

    else:
        bot.reply_to(message, "✅ Kontent qo‘shish yakunlandi.", reply_markup=admin_main_menu())

    admin_state[uid] = None
    admin_data[uid] = {}

# ==========================
#   MULTI-UPLOAD SAQLASH
# ==========================
@bot.message_handler(content_types=["text", "photo", "video", "document", "audio", "voice", "animation"])
def save_content(message):
    uid = message.from_user.id
    state = admin_state.get(uid)

    # ADMIN MULTI-UPLOAD
    if uid == ADMIN_ID and state in ["multi_single", "multi_group"]:
        group_mode = (state == "multi_group")

        if message.content_type == "video":
            item = {"type": "video", "file_id": message.video.file_id, "caption": message.caption}
        elif message.content_type == "photo":
            item = {"type": "photo", "file_id": message.photo[-1].file_id, "caption": message.caption}
        elif message.content_type == "document":
            item = {"type": "document", "file_id": message.document.file_id, "caption": message.caption}
        elif message.content_type == "audio":
            item = {"type": "audio", "file_id": message.audio.file_id, "caption": message.caption}
        elif message.content_type == "voice":
            item = {"type": "voice", "file_id": message.voice.file_id, "caption": message.caption}
        elif message.content_type == "animation":
            item = {"type": "animation", "file_id": message.animation.file_id, "caption": message.caption}
        else:
            item = {"type": "text", "text": message.text}

        if group_mode:
            admin_data.setdefault(uid, {}).setdefault("items", []).append(item)
            bot.reply_to(message, "✅ Playlistga qo‘shildi.")
        else:
            code = generate_code()
            item["code"] = code
            contents.insert_one(item)
            link = f"https://t.me/{BOT_USERNAME}?start={code}"
            bot.reply_to(message, f"✅ Saqlandi:\n<code>{link}</code>")

        return

    # ADMIN BROADCAST
    if uid == ADMIN_ID and state == "wait_broadcast_content":
        doc = {}

        if message.content_type == "video":
            doc = {"type": "video", "file_id": message.video.file_id, "caption": message.caption}
        elif message.content_type == "photo":
            doc = {"type": "photo", "file_id": message.photo[-1].file_id, "caption": message.caption}
        elif message.content_type == "document":
            doc = {"type": "document", "file_id": message.document.file_id, "caption": message.caption}
        elif message.content_type == "audio":
            doc = {"type": "audio", "file_id": message.audio.file_id, "caption": message.caption}
        elif message.content_type == "voice":
            doc = {"type": "voice", "file_id": message.voice.file_id, "caption": message.caption}
        elif message.content_type == "animation":
            doc = {"type": "animation", "file_id": message.animation.file_id, "caption": message.caption}
        else:
            doc = {"type": "text", "text": message.text}

        admin_data[uid] = {"broadcast": doc, "buttons": []}
        admin_state[uid] = "broadcast_menu"

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("➕ Tugma qo‘shish", callback_data="bc_add_btn"))
        kb.add(
            InlineKeyboardButton("👁 Ko‘rish", callback_data="bc_preview"),
            InlineKeyboardButton("📨 Yuborish", callback_data="bc_send")
        )
        kb.add(InlineKeyboardButton("❌ Bekor qilish", callback_data="bc_cancel"))

        bot.reply_to(message, "✅ Broadcast xabari saqlandi.\nEndi tugmalarni qo‘shishingiz mumkin.", reply_markup=kb)
        return

# ==========================
#   BROADCAST TUGMA NOMI / URL
# ==========================
@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and admin_state.get(m.from_user.id) == "bc_wait_btn_name")
def bc_btn_name(message):
    uid = message.from_user.id
    admin_data[uid]["tmp_btn_name"] = message.text.strip()
    admin_state[uid] = "bc_wait_btn_url"
    bot.reply_to(message, "Endi tugma uchun URL yuboring:")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and admin_state.get(m.from_user.id) == "bc_wait_btn_url")
def bc_btn_url(message):
    uid = message.from_user.id
    url = message.text.strip()

    admin_data[uid].setdefault("buttons", []).append({
        "name": admin_data[uid]["tmp_btn_name"],
        "url": url
    })

    admin_state[uid] = "broadcast_menu"
    bot.reply_to(message, "✅ Tugma qo‘shildi.")

# ==========================
#   OBUNA TEKSHIRISH
# ==========================
def check_required_subs(user_id):
    chans = list(required_channels.find({}))
    if not chans:
        return True

    for ch in chans:
        try:
            member = bot.get_chat_member(ch["channel_id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False

    return True

def get_subscribe_keyboard(user_id, code):
    req = list(required_channels.find({}))
    opt = list(optional_channels.find({}))

    buttons = []

    for ch in req:
        buttons.append(InlineKeyboardButton(ch["name"], url=ch["url"]))

    for ch in opt:
        buttons.append(InlineKeyboardButton(ch["name"], url=ch["url"]))

    random.shuffle(buttons)

    kb = InlineKeyboardMarkup(row_width=1)
    for b in buttons:
        kb.add(b)

    kb.add(InlineKeyboardButton("✔️ Tekshirish", callback_data=f"check:{code}"))
    return kb

# ==========================
#   KONTENT YUBORISH
# ==========================
def send_content(chat_id, item, code=None):
    t = item["type"]

    msg = None

    if t == "group":
        for sub in item["items"]:
            send_content(chat_id, sub, code=None)
        return

    if t == "text":
        msg = bot.send_message(chat_id, item["text"])
    elif t == "photo":
        msg = bot.send_photo(chat_id, item["file_id"], caption=item.get("caption"))
    elif t == "video":
        msg = bot.send_video(chat_id, item["file_id"], caption=item.get("caption"))
    elif t == "document":
        msg = bot.send_document(chat_id, item["file_id"], caption=item.get("caption"))
    elif t == "audio":
        msg = bot.send_audio(chat_id, item["file_id"], caption=item.get("caption"))
    elif t == "voice":
        msg = bot.send_voice(chat_id, item["file_id"], caption=item.get("caption"))
    elif t == "animation":
        msg = bot.send_animation(chat_id, item["file_id"], caption=item.get("caption"))

    if msg and code:
        schedule_delete(bot, chat_id, msg, code=code)

# ==========================
#   OBUNA TEKSHIRISH CALLBACK
# ==========================
@bot.callback_query_handler(func=lambda c: c.data.startswith("check:"))
def check_subs_callback(call):
    code = call.data.split(":")[1]
    user_id = call.from_user.id

    if not check_required_subs(user_id):
        bot.answer_callback_query(call.id, "❌ Hali hammasiga obuna bo‘lmadingiz!", show_alert=True)
        return

    item = contents.find_one({"code": code})
    if not item:
        bot.answer_callback_query(call.id, "❌ Kontent topilmadi.", show_alert=True)
        return

    send_content(call.message.chat.id, item, code=code)

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

# ==========================
#   /START
# ==========================
@bot.message_handler(commands=["start"])
def start(message):
    save_user(message.from_user.id)

    if len(message.text.split()) == 2:
        return start_with_code(message)

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("📝 Bot Haqida", callback_data="about"),
        InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{message.message_id}")
    )

    bot.reply_to(
        message,
        "<b>Botga xush kelibsiz!\nKontent yuklash uchun start-linklardan foydalaning.</b>",
        reply_markup=kb
    )

# ==========================
#   /START CODE
# ==========================
def start_with_code(message):
    code = message.text.split()[1]
    user_id = message.from_user.id

    item = contents.find_one({"code": code})
    if item:
        if not check_required_subs(user_id):
            kb = get_subscribe_keyboard(user_id, code)
            bot.send_message(message.chat.id, "📌 Iltimos, kanallarga obuna bo‘ling:", reply_markup=kb)
            return

        send_content(message.chat.id, item, code=code)
        return

    referrals.update_one({"key": code}, {"$inc": {"count": 1}}, upsert=True)
    bot.send_message(message.chat.id, "✅ Referal orqali keldingiz.")

# ==========================
#   ABOUT / CREATOR / CLOSE
# ==========================
@bot.callback_query_handler(func=lambda call: True)
def generic_callback(call):
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
            "<b>Botdan foydalanish qo‘llanmasi:\n1. Obuna bo‘ling\n2. Tekshiring\n3. Yuklab oling</b>",
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
            "<b>• Admin: @Shadow_Sxi\n• Kanal: @AniGonUz</b>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )
        return

# ==========================
#   XAVFSIZLIK (KANALDAN CHIQARILSA)
# ==========================
def security_check():
    while True:
        try:
            chans = list(required_channels.find({}))
            for ch in chans:
                cid = ch["channel_id"]
                try:
                    member = bot.get_chat_member(cid, bot.get_me().id)
                    if member.status in ["administrator", "creator"]:
                        continue

                    required_channels.delete_one({"_id": ch["_id"]})
                    bot.send_message(ADMIN_ID, f"⚠️ {ch['name']} kanalidan chiqarildim. O‘chirildi.")
                except:
                    required_channels.delete_one({"_id": ch["_id"]})
                    bot.send_message(ADMIN_ID, f"⚠️ {ch['name']} kanaliga ulanib bo‘lmadi. O‘chirildi.")
        except Exception as e:
            print("Security error:", e)

        time.sleep(30)

threading.Thread(target=security_check, daemon=True).start()
