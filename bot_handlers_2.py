from bot_handlers_1 import bot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from utils import (
    BOT_USERNAME, ADMIN_ID,
    contents, required_channels, optional_channels,
    referrals, settings, users,
    admin_state, admin_data,
    generate_code, save_user, schedule_delete
)
import random
import threading
import time

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
#   BROADCAST CALLBACKLAR
# ==========================
@bot.callback_query_handler(func=lambda c: c.from_user.id == ADMIN_ID and c.data.startswith("bc_"))
def broadcast_callbacks(call):
    uid = call.from_user.id
    data = call.data

    if data == "bc_add_btn":
        admin_state[uid] = "bc_wait_btn_name"
        bot.answer_callback_query(call.id)
        bot.send_message(uid, "Tugma nomini kiriting:")
        return

    if data == "bc_preview":
        bot.answer_callback_query(call.id)
        show_broadcast_preview(uid, call.message.chat.id)
        return

    if data == "bc_send":
        bot.answer_callback_query(call.id)
        send_broadcast(uid, call.message.chat.id)
        return

    if data == "bc_cancel":
        admin_state[uid] = None
        admin_data[uid] = {}
        bot.answer_callback_query(call.id, "Bekor qilindi.")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        return

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

def show_broadcast_preview(uid, chat_id):
    data = admin_data.get(uid)
    if not data or "broadcast" not in data:
        bot.send_message(chat_id, "❌ Broadcast xabari topilmadi.")
        return

    doc = data["broadcast"]
    kb = InlineKeyboardMarkup()
    for btn in data.get("buttons", []):
        kb.add(InlineKeyboardButton(btn["name"], url=btn["url"]))

    t = doc["type"]
    if t == "text":
        bot.send_message(chat_id, doc["text"], reply_markup=kb)
    elif t == "photo":
        bot.send_photo(chat_id, doc["file_id"], caption=doc.get("caption"), reply_markup=kb)
    elif t == "video":
        bot.send_video(chat_id, doc["file_id"], caption=doc.get("caption"), reply_markup=kb)
    elif t == "document":
        bot.send_document(chat_id, doc["file_id"], caption=doc.get("caption"), reply_markup=kb)
    elif t == "audio":
        bot.send_audio(chat_id, doc["file_id"], caption=doc.get("caption"), reply_markup=kb)
    elif t == "voice":
        bot.send_voice(chat_id, doc["file_id"], caption=doc.get("caption"), reply_markup=kb)
    elif t == "animation":
        bot.send_animation(chat_id, doc["file_id"], caption=doc.get("caption"), reply_markup=kb)

def send_broadcast(uid, chat_id):
    data = admin_data.get(uid)
    if not data or "broadcast" not in data:
        bot.send_message(chat_id, "❌ Broadcast xabari topilmadi.")
        return

    doc = data["broadcast"]
    kb = InlineKeyboardMarkup()
    for btn in data.get("buttons", []):
        kb.add(InlineKeyboardButton(btn["name"], url=btn["url"]))

    t = doc["type"]
    total = users.count_documents({})
    sent = 0

    for user in users.find({}):
        u_id = user["user_id"]
        try:
            if t == "text":
                bot.send_message(u_id, doc["text"], reply_markup=kb)
            elif t == "photo":
                bot.send_photo(u_id, doc["file_id"], caption=doc.get("caption"), reply_markup=kb)
            elif t == "video":
                bot.send_video(u_id, doc["file_id"], caption=doc.get("caption"), reply_markup=kb)
            elif t == "document":
                bot.send_document(u_id, doc["file_id"], caption=doc.get("caption"), reply_markup=kb)
            elif t == "audio":
                bot.send_audio(u_id, doc["file_id"], caption=doc.get("caption"), reply_markup=kb)
            elif t == "voice":
                bot.send_voice(u_id, doc["file_id"], caption=doc.get("caption"), reply_markup=kb)
            elif t == "animation":
                bot.send_animation(u_id, doc["file_id"], caption=doc.get("caption"), reply_markup=kb)
            sent += 1
        except:
            continue

    bot.send_message(chat_id, f"✅ Broadcast yakunlandi.\nYuborildi: <b>{sent}</b> / {total}")

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
