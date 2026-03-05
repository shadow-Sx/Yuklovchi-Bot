import os
import time
import threading
import uuid
import requests
from typing import Optional, Dict, Any

import telebot
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery,
)
from pymongo import MongoClient

# ==========================
#   CONFIG (ENV VARIABLES)
# ==========================

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or "0")
KEEP_ALIVE_URL = os.getenv("KEEP_ALIVE_URL", "")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI environment variable is not set")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# ==========================
#   KEEP ALIVE (RENDER)
# ==========================

def keep_alive():
    if not KEEP_ALIVE_URL:
        return

    def ping():
        while True:
            try:
                requests.get(KEEP_ALIVE_URL, timeout=5)
            except:
                pass
            time.sleep(60)

    threading.Thread(target=ping, daemon=True).start()

# ==========================
#   DATABASE
# ==========================

client = MongoClient(MONGO_URI)
db = client["bot"]

users_col = db["users"]
required_channels_col = db["required_channels"]
optional_channels_col = db["optional_channels"]
contents_col = db["contents"]
referrals_col = db["referrals"]
settings_col = db["settings"]
broadcast_col = db["broadcast"]

# ==========================
#   ADMIN STATE
# ==========================

admin_state: Dict[int, str] = {}
admin_data: Dict[int, Dict[str, Any]] = {}

# ==========================
#   HELPERS
# ==========================

def gen_code(prefix: str = "c") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def save_user(user_id: int):
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id}},
        upsert=True,
    )

def get_auto_delete_seconds() -> Optional[int]:
    doc = settings_col.find_one({"key": "auto_delete"})
    if not doc:
        return None
    return int(doc.get("time", 0)) or None

def send_and_schedule_delete(chat_id: int, msg: Message, code: Optional[str] = None):
    seconds = get_auto_delete_seconds()
    if not seconds:
        return

    # Eslatma
    note = bot.send_message(
        chat_id,
        f"⚠️ESLATMA⚠️\n"
        f"Ushbu habar {seconds // 60}:{seconds % 60:02d} dan so‘ng o‘chirilib yuboriladi.\n"
        f"Tezda saqlab oling.",
    )
    note_id = note.message_id

    def worker():
        time.sleep(seconds)

        # Kontentni o‘chiramiz
        try:
            bot.delete_message(chat_id, msg.message_id)
        except:
            pass

        # Eslatmani o‘zgartiramiz
        markup = None
        if code:
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton(
                    "Qayta tiklash ♻️",
                    url=f"https://t.me/{bot.get_me().username}?start={code}",
                )
            )

        try:
            bot.edit_message_text(
                "Ulgurmay qolgan bo‘lsangiz afsusdaman.\n"
                "Pastdagi tugma orqali yana yuklab olishingiz mumkin.",
                chat_id,
                note_id,
                reply_markup=markup,
            )
        except:
            pass

    threading.Thread(target=worker, daemon=True).start()

def send_content_by_doc(chat_id: int, doc: Dict[str, Any]):
    ctype = doc.get("type")
    code = doc.get("code")
    sent = None

    if ctype == "text":
        sent = bot.send_message(chat_id, doc.get("text", ""))
    elif ctype == "photo":
        sent = bot.send_photo(
            chat_id,
            doc.get("file_id"),
            caption=doc.get("caption"),
        )
    elif ctype == "video":
        sent = bot.send_video(
            chat_id,
            doc.get("file_id"),
            caption=doc.get("caption"),
        )
    elif ctype == "document":
        sent = bot.send_document(
            chat_id,
            doc.get("file_id"),
            caption=doc.get("caption"),
        )
    elif ctype == "audio":
        sent = bot.send_audio(
            chat_id,
            doc.get("file_id"),
            caption=doc.get("caption"),
        )
    elif ctype == "voice":
        sent = bot.send_voice(
            chat_id,
            doc.get("file_id"),
            caption=doc.get("caption"),
        )
    elif ctype == "animation":
        sent = bot.send_animation(
            chat_id,
            doc.get("file_id"),
            caption=doc.get("caption"),
        )

    if sent:
        send_and_schedule_delete(chat_id, sent, code=code)

# ==========================
#   SUBSCRIPTION CHECK
# ==========================

def check_subscription(user_id: int) -> bool:
    required = list(required_channels_col.find({}))
    if not required:
        return True

    not_joined = []
    for ch in required:
        chat_id = ch.get("chat_id")
        if not chat_id:
            continue
        try:
            member = bot.get_chat_member(chat_id, user_id)
            if member.status in ("left", "kicked"):
                not_joined.append(ch)
        except:
            not_joined.append(ch)

    if not not_joined:
        return True

    markup = InlineKeyboardMarkup()
    for ch in not_joined:
        markup.add(
            InlineKeyboardButton(
                ch.get("name", "Kanal"),
                url=ch.get("url", ""),
            )
        )
    markup.add(
        InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")
    )

    bot.send_message(
        user_id,
        "Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:",
        reply_markup=markup,
    )
    return False

@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def cb_check_sub(call: CallbackQuery):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi!", show_alert=True)
        bot.send_message(call.from_user.id, "Rahmat! Endi botdan foydalanishingiz mumkin.")
    else:
        bot.answer_callback_query(call.id, "Hali hammasiga obuna bo‘lmadingiz.", show_alert=True)

# ==========================
#   /START HANDLER
# ==========================

@bot.message_handler(commands=["start"])
def cmd_start(message: Message):
    user_id = message.from_user.id
    save_user(user_id)

    args = message.text.split()
    if len(args) == 2:
        param = args[1]

        # 1) Avval kontent kodi sifatida qidiramiz
        doc = contents_col.find_one({"code": param})
        if doc:
            if not check_subscription(user_id):
                return
            send_content_by_doc(message.chat.id, doc)
            return

        # 2) Aks holda referal sifatida hisoblaymiz
        referrals_col.update_one(
            {"key": param},
            {"$inc": {"count": 1}},
            upsert=True,
        )

    bot.reply_to(
        message,
        "Assalomu alaykum!\n"
        "Botga xush kelibsiz.",
    )

# ==========================
#   ADMIN PANEL
# ==========================

def admin_menu_markup() -> InlineKeyboardMarkup:
    m = InlineKeyboardMarkup()
    m.add(
        InlineKeyboardButton("➕ Majburiy Kanal", callback_data="req_add"),
        InlineKeyboardButton("➕ Ixtiyoriy Kanal", callback_data="opt_add"),
    )
    m.add(
        InlineKeyboardButton("📋 Majburiy Ro'yxat", callback_data="req_list"),
        InlineKeyboardButton("📋 Ixtiyoriy Ro'yxat", callback_data="opt_list"),
    )
    m.add(
        InlineKeyboardButton("📊 Statistika", callback_data="stats"),
        InlineKeyboardButton("🔗 Referal", callback_data="ref_menu"),
    )
    m.add(
        InlineKeyboardButton("⏱ AVTO O‘CHIRISH", callback_data="auto_delete"),
    )
    m.add(
        InlineKeyboardButton("📨 Habar yuborish", callback_data="send_menu"),
    )
    m.add(
        InlineKeyboardButton("📥 Kontent qo‘shish", callback_data="add_content"),
    )
    m.add(
        InlineKeyboardButton("❌ Chiqish", callback_data="close_admin"),
    )
    return m

@bot.message_handler(commands=["admin"])
def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    bot.reply_to(message, "<b>Admin Panel</b>", reply_markup=admin_menu_markup())

@bot.callback_query_handler(func=lambda c: is_admin(c.from_user.id))
def admin_callbacks(call: CallbackQuery):
    uid = call.from_user.id
    data = call.data

    if data == "close_admin":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        return

    # Majburiy kanal qo‘shish (post havolasi orqali)
    if data == "req_add":
        admin_state[uid] = "req_wait_post_link"
        admin_data[uid] = {}
        bot.edit_message_text(
            "➕ Majburiy kanal qo‘shish boshlandi.\n\n"
            "📌 Iltimos kanal ichidagi istalgan POST HAVOLASINI yuboring.",
            call.message.chat.id,
            call.message.message_id,
        )
        return

    # Ixtiyoriy kanal qo‘shish
    if data == "opt_add":
        admin_state[uid] = "opt_wait_post_link"
        admin_data[uid] = {}
        bot.edit_message_text(
            "➕ Ixtiyoriy kanal qo‘shish.\n\n"
            "📌 Iltimos kanal ichidagi istalgan POST HAVOLASINI yuboring.",
            call.message.chat.id,
            call.message.message_id,
        )
        return

    # Majburiy ro‘yxat
    if data == "req_list":
        channels = list(required_channels_col.find({}))
        if not channels:
            bot.answer_callback_query(call.id, "Majburiy kanallar yo‘q.", show_alert=True)
            return
        text = "<b>📋 Majburiy kanallar:</b>\n\n"
        for ch in channels:
            text += f"• {ch.get('name','Kanal')} — {ch.get('url','')}\n"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
        return

    # Ixtiyoriy ro‘yxat
    if data == "opt_list":
        channels = list(optional_channels_col.find({}))
        if not channels:
            bot.answer_callback_query(call.id, "Ixtiyoriy kanallar yo‘q.", show_alert=True)
            return
        text = "<b>📋 Ixtiyoriy kanallar:</b>\n\n"
        for ch in channels:
            text += f"• {ch.get('name','Kanal')} — {ch.get('url','')}\n"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
        return

    # Statistika
    if data == "stats":
        count = users_col.count_documents({})
        bot.edit_message_text(
            f"📊 Barcha foydalanuvchilar: <b>{count}</b>",
            call.message.chat.id,
            call.message.message_id,
        )
        return

    # REFERAL MENYUSI
    if data == "ref_menu":
        m = InlineKeyboardMarkup()
        m.add(
            InlineKeyboardButton("➕ Yaratish", callback_data="ref_create"),
            InlineKeyboardButton("📊 Kuzatish", callback_data="ref_view"),
            InlineKeyboardButton("🗑 O‘chirish", callback_data="ref_delete"),
        )
        bot.edit_message_text(
            "Kerakli tugmani tanlang:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=m,
        )
        return

    if data == "ref_create":
        admin_state[uid] = "ref_wait_key"
        bot.edit_message_text(
            "Iltimos havola uchun so'z kiriting.\n"
            "Masalan: <code>Yangi_Referal</code>",
            call.message.chat.id,
            call.message.message_id,
        )
        return

    if data == "ref_view":
        items = list(referrals_col.find({}))
        if not items:
            bot.edit_message_text(
                "Hali referallar yo‘q.",
                call.message.chat.id,
                call.message.message_id,
            )
            return
        text = "📊 Referallar ro‘yxati:\n\n"
        username = bot.get_me().username
        for i, r in enumerate(items, 1):
            text += (
                f"{i}. https://t.me/{username}?start={r['key']} "
                f"({r.get('count', 0)})\n"
            )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
        return

    if data == "ref_delete":
        admin_state[uid] = "ref_wait_delete"
        bot.edit_message_text(
            "O‘chirmoqchi bo‘lgan referal havolangizni yuboring.\n"
            "Masalan:\n"
            "https://t.me/Bot?start=YangiHavola\n"
            "yoki shunchaki: YangiHavola",
            call.message.chat.id,
            call.message.message_id,
        )
        return

    # AVTO O‘CHIRISH
    if data == "auto_delete":
        admin_state[uid] = "wait_auto_time"
        bot.edit_message_text(
            "Iltimos vaqt kiriting masalan <code>1:00</code>\n"
            "Bu degani kontent yuborilgandan 1 daqiqa o‘tib o‘chiriladi.\n\n"
            "Agar o‘chirib tashlamoqchi bo‘lsangiz: /delettime",
            call.message.chat.id,
            call.message.message_id,
        )
        return

    # HABAR YUBORISH (UNIVERSAL)
    if data == "send_menu":
        admin_state[uid] = "wait_broadcast_content"
        broadcast_col.delete_many({"admin_id": uid})
        bot.edit_message_text(
            "Broadcast uchun xabar yuboring.\n"
            "Bu matn, foto, video, fayl va hokazo bo‘lishi mumkin.\n"
            "Keyin tugmalar qo‘shish bosqichiga o‘tamiz.",
            call.message.chat.id,
            call.message.message_id,
        )
        return

    if data == "add_btn":
        admin_state[uid] = "wait_btn_name"
        bot.answer_callback_query(call.id)
        bot.send_message(uid, "Tugma nomini kiriting:")
        return

    if data == "preview":
        item = broadcast_col.find_one({"admin_id": uid})
        if not item:
            bot.answer_callback_query(call.id, "Hali habar saqlanmagan.", show_alert=True)
            return
        markup = InlineKeyboardMarkup()
        for btn in item.get("buttons", []):
            markup.add(InlineKeyboardButton(btn["name"], url=btn["url"]))

        # Kontent turiga qarab preview
        ctype = item.get("type")
        if ctype == "text":
            bot.send_message(uid, f"👁 <b>Ko‘rinishi:</b>\n\n{item['text']}", reply_markup=markup)
        elif ctype == "photo":
            bot.send_photo(uid, item["file_id"], caption=item.get("caption"), reply_markup=markup)
        elif ctype == "video":
            bot.send_video(uid, item["file_id"], caption=item.get("caption"), reply_markup=markup)
        elif ctype == "document":
            bot.send_document(uid, item["file_id"], caption=item.get("caption"), reply_markup=markup)
        elif ctype == "audio":
            bot.send_audio(uid, item["file_id"], caption=item.get("caption"), reply_markup=markup)
        elif ctype == "voice":
            bot.send_voice(uid, item["file_id"], caption=item.get("caption"), reply_markup=markup)
        elif ctype == "animation":
            bot.send_animation(uid, item["file_id"], caption=item.get("caption"), reply_markup=markup)

        return

    if data == "cancel_broadcast":
        broadcast_col.delete_many({"admin_id": uid})
        admin_state.pop(uid, None)
        bot.edit_message_text(
            "❌ Habar yuborish bekor qilindi.",
            call.message.chat.id,
            call.message.message_id,
        )
        return

    if data == "do_broadcast":
        item = broadcast_col.find_one({"admin_id": uid})
        if not item:
            bot.answer_callback_query(call.id, "Hali habar saqlanmagan.", show_alert=True)
            return

        markup = InlineKeyboardMarkup()
        for btn in item.get("buttons", []):
            markup.add(InlineKeyboardButton(btn["name"], url=btn["url"]))

        users_list = users_col.find({})
        sent_count = 0

        for u in users_list:
            chat_id = u["user_id"]
            try:
                ctype = item.get("type")
                if ctype == "text":
                    bot.send_message(chat_id, item["text"], reply_markup=markup)
                elif ctype == "photo":
                    bot.send_photo(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=markup)
                elif ctype == "video":
                    bot.send_video(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=markup)
                elif ctype == "document":
                    bot.send_document(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=markup)
                elif ctype == "audio":
                    bot.send_audio(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=markup)
                elif ctype == "voice":
                    bot.send_voice(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=markup)
                elif ctype == "animation":
                    bot.send_animation(chat_id, item["file_id"], caption=item.get("caption"), reply_markup=markup)
                sent_count += 1
            except:
                pass

        bot.edit_message_text(
            f"📨 Habar yuborildi!\n"
            f"Yuborilgan foydalanuvchilar: <b>{sent_count}</b>",
            call.message.chat.id,
            call.message.message_id,
        )

        broadcast_col.delete_many({"admin_id": uid})
        admin_state.pop(uid, None)
        return

    # Kontent qo‘shish
    if data == "add_content":
        admin_state[uid] = "wait_content"
        bot.edit_message_text(
            "Kontent yuboring (matn, foto, video, fayl va hokazo).\n"
            "Bot uni saqlaydi va sizga start-havola beradi.",
            call.message.chat.id,
            call.message.message_id,
        )
        return

# ==========================
#   ADMIN MESSAGE HANDLERS
# ==========================

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and admin_state.get(m.from_user.id) == "req_wait_post_link")
def admin_req_post_link(message: Message):
    uid = message.from_user.id
    link = message.text.strip()

    # linkdan chat_id va url topishga harakat qilamiz
    # Minimal: faqat url saqlaymiz, nomini get_chat orqali olamiz
    try:
        chat = bot.get_chat(link)
        chat_id = chat.id
        name = chat.title or chat.username or "Kanal"
    except:
        bot.reply_to(message, "❌ Havoladan kanalni aniqlab bo‘lmadi. Bot kanalga admin qilinganmi?")
        return

    required_channels_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "name": name, "url": link}},
        upsert=True,
    )

    bot.reply_to(
        message,
        f"✅ Majburiy kanal qo‘shildi:\n\n"
        f"Nom: <b>{name}</b>\n"
        f"Havola: {link}",
    )
    admin_state.pop(uid, None)

@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and admin_state.get(m.from_user.id) == "opt_wait_post_link")
def admin_opt_post_link(message: Message):
    uid = message.from_user.id
    link = message.text.strip()

    try:
        chat = bot.get_chat(link)
        chat_id = chat.id
        name = chat.title or chat.username or "Kanal"
    except:
        bot.reply_to(message, "❌ Havoladan kanalni aniqlab bo‘lmadi. Bot kanalga admin qilinganmi?")
        return

    optional_channels_col.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id, "name": name, "url": link}},
        upsert=True,
    )

    bot.reply_to(
        message,
        f"✅ Ixtiyoriy kanal qo‘shildi:\n\n"
        f"Nom: <b>{name}</b>\n"
        f"Havola: {link}",
    )
    admin_state.pop(uid, None)

# REFERAL YARATISH
@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and admin_state.get(m.from_user.id) == "ref_wait_key")
def admin_ref_wait_key(message: Message):
    uid = message.from_user.id
    key = message.text.strip()

    referrals_col.update_one(
        {"key": key},
        {"$set": {"key": key, "count": 0}},
        upsert=True,
    )

    username = bot.get_me().username
    bot.reply_to(
        message,
        "Sizning referal havolangiz tayyor:\n\n"
        f"<code>https://t.me/{username}?start={key}</code>",
    )
    admin_state.pop(uid, None)

# REFERAL O‘CHIRISH
@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and admin_state.get(m.from_user.id) == "ref_wait_delete")
def admin_ref_wait_delete(message: Message):
    uid = message.from_user.id
    text = message.text.strip()

    if "start=" in text:
        key = text.split("start=")[1]
    else:
        key = text

    result = referrals_col.delete_one({"key": key})
    if result.deleted_count == 0:
        bot.reply_to(message, "❌ Bunday referal topilmadi.")
    else:
        bot.reply_to(message, "✅ Referal o‘chirildi.")
    admin_state.pop(uid, None)

# AVTO O‘CHIRISH VAQTI
@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and admin_state.get(m.from_user.id) == "wait_auto_time")
def admin_wait_auto_time(message: Message):
    uid = message.from_user.id
    text = message.text.strip()

    if ":" not in text:
        bot.reply_to(message, "❌ To‘g‘ri formatda kiriting. Masalan: 5:00")
        return

    minutes, seconds = text.split(":")
    if not minutes.isdigit() or not seconds.isdigit():
        bot.reply_to(message, "❌ Faqat raqam kiriting. Masalan: 3:00")
        return

    total_seconds = int(minutes) * 60 + int(seconds)

    settings_col.update_one(
        {"key": "auto_delete"},
        {"$set": {"time": total_seconds}},
        upsert=True,
    )

    bot.reply_to(message, f"✅ Avto o‘chirish faollashtirildi: {text}")
    admin_state.pop(uid, None)

# AVTO O‘CHIRISHNI O‘CHIRISH
@bot.message_handler(commands=["delettime"])
def cmd_delettime(message: Message):
    if not is_admin(message.from_user.id):
        return
    settings_col.delete_one({"key": "auto_delete"})
    bot.reply_to(message, "❌ Avto o‘chirish o‘chirildi.")

# BROADCAST KONTENT QABUL QILISH (UNIVERSAL)
@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and admin_state.get(m.from_user.id) == "wait_broadcast_content", content_types=["text", "photo", "video", "document", "audio", "voice", "animation"])
def admin_broadcast_content(message: Message):
    uid = message.from_user.id

    doc: Dict[str, Any] = {"admin_id": uid, "buttons": []}

    if message.content_type == "text":
        doc["type"] = "text"
        doc["text"] = message.text
    elif message.content_type == "photo":
        doc["type"] = "photo"
        doc["file_id"] = message.photo[-1].file_id
        doc["caption"] = message.caption
    elif message.content_type == "video":
        doc["type"] = "video"
        doc["file_id"] = message.video.file_id
        doc["caption"] = message.caption
    elif message.content_type == "document":
        doc["type"] = "document"
        doc["file_id"] = message.document.file_id
        doc["caption"] = message.caption
    elif message.content_type == "audio":
        doc["type"] = "audio"
        doc["file_id"] = message.audio.file_id
        doc["caption"] = message.caption
    elif message.content_type == "voice":
        doc["type"] = "voice"
        doc["file_id"] = message.voice.file_id
        doc["caption"] = message.caption
    elif message.content_type == "animation":
        doc["type"] = "animation"
        doc["file_id"] = message.animation.file_id
        doc["caption"] = message.caption

    broadcast_col.delete_many({"admin_id": uid})
    broadcast_col.insert_one(doc)

    admin_state[uid] = "broadcast_menu"

    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("➕ Tugma qo‘shish", callback_data="add_btn"))
    m.add(
        InlineKeyboardButton("👁 Ko‘rish", callback_data="preview"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_broadcast"),
        InlineKeyboardButton("📨 Yuborish", callback_data="do_broadcast"),
    )

    bot.reply_to(
        message,
        "Habar saqlandi. Endi tugmalarni qo‘shishingiz mumkin:",
        reply_markup=m,
    )

# BROADCAST TUGMA NOMI
@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and admin_state.get(m.from_user.id) == "wait_btn_name")
def admin_btn_name(message: Message):
    uid = message.from_user.id
    admin_data[uid] = {"btn_name": message.text}
    admin_state[uid] = "wait_btn_url"
    bot.reply_to(message, "Endi tugma uchun URL yuboring:")

# BROADCAST TUGMA URL
@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and admin_state.get(m.from_user.id) == "wait_btn_url")
def admin_btn_url(message: Message):
    uid = message.from_user.id
    name = admin_data[uid]["btn_name"]
    url = message.text.strip()

    broadcast_col.update_one(
        {"admin_id": uid},
        {"$push": {"buttons": {"name": name, "url": url}}},
    )

    admin_state[uid] = "broadcast_menu"

    m = InlineKeyboardMarkup()
    m.add(InlineKeyboardButton("➕ Tugma qo‘shish", callback_data="add_btn"))
    m.add(
        InlineKeyboardButton("👁 Ko‘rish", callback_data="preview"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_broadcast"),
        InlineKeyboardButton("📨 Yuborish", callback_data="do_broadcast"),
    )

    bot.reply_to(
        message,
        f"✅ Tugma qo‘shildi: {name}",
        reply_markup=m,
    )

# KONTENT QO‘SHISH (UNIVERSAL, MONGODB)
@bot.message_handler(func=lambda m: is_admin(m.from_user.id) and admin_state.get(m.from_user.id) == "wait_content", content_types=["text", "photo", "video", "document", "audio", "voice", "animation"])
def admin_add_content(message: Message):
    uid = message.from_user.id

    doc: Dict[str, Any] = {}
    code = gen_code("c")
    doc["code"] = code

    if message.content_type == "text":
        doc["type"] = "text"
        doc["text"] = message.text
    elif message.content_type == "photo":
        doc["type"] = "photo"
        doc["file_id"] = message.photo[-1].file_id
        doc["caption"] = message.caption
    elif message.content_type == "video":
        doc["type"] = "video"
        doc["file_id"] = message.video.file_id
        doc["caption"] = message.caption
    elif message.content_type == "document":
        doc["type"] = "document"
        doc["file_id"] = message.document.file_id
        doc["caption"] = message.caption
    elif message.content_type == "audio":
        doc["type"] = "audio"
        doc["file_id"] = message.audio.file_id
        doc["caption"] = message.caption
    elif message.content_type == "voice":
        doc["type"] = "voice"
        doc["file_id"] = message.voice.file_id
        doc["caption"] = message.caption
    elif message.content_type == "animation":
        doc["type"] = "animation"
        doc["file_id"] = message.animation.file_id
        doc["caption"] = message.caption

    contents_col.insert_one(doc)

    username = bot.get_me().username
    link = f"https://t.me/{username}?start={code}"

    bot.reply_to(
        message,
        "✅ Kontent saqlandi.\n\n"
        f"Start havola:\n"
        f"<code>{link}</code>",
    )

    admin_state.pop(uid, None)

# ==========================
#   SECURITY (KANALDAN O‘CHIRILSA)
# ==========================

@bot.my_chat_member_handler()
def my_chat_member_update(message):
    """
    Agar bot kanalga qo‘shilsa yoki chiqarib yuborilsa,
    shu yerda kuzatish mumkin.
    Hozir minimal: agar bot kanalga 'kicked' bo‘lsa,
    required/optional ro‘yxatdan o‘chirib tashlaymiz.
    """
    chat = message.chat
    new_status = message.new_chat_member.status

    if chat.type in ("channel", "supergroup", "group"):
        if new_status in ("kicked", "left"):
            required_channels_col.delete_one({"chat_id": chat.id})
            optional_channels_col.delete_one({"chat_id": chat.id})
            if ADMIN_ID:
                try:
                    bot.send_message(
                        ADMIN_ID,
                        f"⚠️ Bot kanal yoki guruhdan chiqarib yuborildi:\n"
                        f"<b>{chat.title or chat.username or chat.id}</b>\n"
                        f"U ro‘yxatdan o‘chirildi.",
                    )
                except:
                    pass

# ==========================
#   MAIN
# ==========================

def main():
    bot.delete_webhook(drop_pending_updates=True)
    keep_alive()
    bot.infinity_polling(skip_pending=True)

if __name__ == "__main__":
    main()
