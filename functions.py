import os
import time
import threading
import io
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Global variables
video_edit_state = {}
video_queue = {}
video_processing = {}

ADMIN_ID = 7797502113
BOT_USERNAME = None

def set_bot_username(username):
    global BOT_USERNAME
    BOT_USERNAME = username

# ==========================
#   PREMIUM FUNCTIONS
# ==========================
def add_premium_reaction(bot, chat_id, message_id, emoji="🎉"):
    try:
        time.sleep(0.3)
        bot.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=[{"type": "emoji", "emoji": emoji}],
            is_big=True
        )
        return True
    except Exception as e:
        print(f"Reaksiya xatosi: {e}")
        return False

def add_multiple_reactions(bot, chat_id, message_id, emojis=["🔥", "🎉"]):
    for emoji in emojis:
        try:
            bot.set_message_reaction(
                chat_id=chat_id,
                message_id=message_id,
                reaction=[{"type": "emoji", "emoji": emoji}],
                is_big=True
            )
            time.sleep(0.2)
        except:
            pass
    return True

# ==========================
#   VIDEO EDIT FUNCTIONS
# ==========================
def video_edit_menu(bot, chat_id, message_id=None):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🖼 Rasm", callback_data="video_edit_image"),
           InlineKeyboardButton("🎬 Video", callback_data="video_edit_video"))
    kb.add(InlineKeyboardButton("📊 Jarayon", callback_data="video_edit_status"),
           InlineKeyboardButton("🔙 Orqaga", callback_data="video_edit_back"))

    uid = chat_id
    queue_count = len(video_queue.get(uid, []))
    processing_count = 1 if video_processing.get(uid) else 0
    status_text = f"\n\n📊 <b>Holat:</b>\n• ⏳ Navbatda: {queue_count} ta\n• 🔄 Ishlanmoqda: {processing_count} ta"

    if message_id:
        try:
            bot.edit_message_text(
                f"🎬 Video ustiga rasm qo'yish bo'limiga xush kelibsiz!\n\n"
                f"Avval rasm tanlang, so'ng videolarni yuboring.{status_text}",
                chat_id, message_id, reply_markup=kb, parse_mode="HTML")
        except:
            pass
    else:
        bot.send_message(chat_id,
            f"🎬 Video ustiga rasm qo'yish bo'limiga xush kelibsiz!\n\n"
            f"Avval rasm tanlang, so'ng videolarni yuboring.{status_text}",
            reply_markup=kb, parse_mode="HTML")

def start_video_edit(bot, message):
    uid = message.from_user.id
    video_edit_state[uid] = {"step": "menu", "image_id": None}
    if uid not in video_queue:
        video_queue[uid] = []
    if uid not in video_processing:
        video_processing[uid] = None
    video_edit_menu(bot, message.chat.id, message.message_id)
    add_premium_reaction(bot, message.chat.id, message.message_id, "🎬")

def start_image_upload(bot, call):
    uid = call.from_user.id
    current_image = video_edit_state.get(uid, {}).get("image_id")
    kb = InlineKeyboardMarkup()
    if current_image:
        kb.add(InlineKeyboardButton("🗑 Rasmni o'chirish", callback_data="video_edit_delete_image"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="video_edit_back"))
    try:
        bot.edit_message_text(
            "🖼 Iltimos, yangi rasm yuboring.\n\n"
            f"{'Oldingi rasm mavjud. Yangi rasm eskisini almashtiradi.' if current_image else ''}\n\n"
            f"📌 <b>Eslatma:</b> Bu rasm <b>barcha</b> videolarga qo'llaniladi.",
            call.message.chat.id, call.message.message_id, reply_markup=kb, parse_mode="HTML")
    except:
        pass
    video_edit_state[uid]["step"] = "waiting_image"

def handle_image_upload(bot, message):
    uid = message.from_user.id
    if video_edit_state.get(uid, {}).get("step") != "waiting_image":
        return False
    if not message.photo:
        bot.reply_to(message, "❌ Iltimos, rasm yuboring!")
        return True
    file_id = message.photo[-1].file_id
    video_edit_state[uid]["image_id"] = file_id
    video_edit_state[uid]["step"] = "menu"
    video_edit_menu(bot, message.chat.id)
    sent = bot.send_message(message.chat.id, "✅ Rasm muvaffaqiyatli saqlandi! Endi videolarni yuborishingiz mumkin.")
    add_premium_reaction(bot, sent.chat.id, sent.message_id, "✅")
    return True

def delete_image(bot, call):
    uid = call.from_user.id
    if uid in video_edit_state:
        video_edit_state[uid]["image_id"] = None
    try:
        video_edit_menu(bot, call.message.chat.id, call.message.message_id)
    except:
        pass
    bot.answer_callback_query(call.id, "✅ Rasm o'chirildi!")

def format_size(size_bytes):
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def process_video(bot, uid, video_data, status_msg):
    video = video_data["video"]
    image_id = video_data["image_id"]
    message = video_data["message"]
    order = video_data["order"]
    total = video_data["total"]

    try:
        bot.edit_message_text(
            f"📤 <b>Video #{order}/{total}</b> qayta ishlanmoqda...\n\n"
            f"📁 Hajmi: {format_size(video.file_size)}\n⬇️ Yuklab olinmoqda...",
            status_msg.chat.id, status_msg.message_id, parse_mode="HTML")

        file_info = bot.get_file(video.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        bot.edit_message_text(
            f"📤 <b>Video #{order}/{total}</b> qayta ishlanmoqda...\n\n"
            f"📁 Hajmi: {format_size(video.file_size)}\n✅ Yuklab olindi!\n🎬 Rasm qo'shilmoqda...",
            status_msg.chat.id, status_msg.message_id, parse_mode="HTML")

        image_info = bot.get_file(image_id)
        image_file = bot.download_file(image_info.file_path)

        video_name = f"@AniGonUz_{int(time.time())}_{order}.mp4"

        bot.edit_message_text(
            f"📤 <b>Video #{order}/{total}</b> qayta ishlanmoqda...\n\n"
            f"📁 Hajmi: {format_size(video.file_size)}\n⬆️ Telegram'ga yuklanmoqda...",
            status_msg.chat.id, status_msg.message_id, parse_mode="HTML")

        video_io = io.BytesIO(downloaded_file)
        video_io.name = video_name
        caption = message.caption if message.caption else ""
        thumbnail_io = io.BytesIO(image_file)
        thumbnail_io.name = "thumb.jpg"

        sent_video = bot.send_video(
            message.chat.id, video_io,
            caption=caption,
            thumbnail=thumbnail_io,
            supports_streaming=True,
            timeout=300
        )

        bot.edit_message_text(
            f"✅ <b>Video #{order}/{total}</b> tayyor!\n\n"
            f"📹 Video ID: {sent_video.video.file_id[:20]}...\n📁 Hajmi: {format_size(video.file_size)}",
            status_msg.chat.id, status_msg.message_id, parse_mode="HTML")

        add_premium_reaction(bot, sent_video.chat.id, sent_video.message_id, "🎬")

        def delete_temp():
            time.sleep(5)
            try:
                bot.delete_message(status_msg.chat.id, status_msg.message_id)
            except:
                pass
        threading.Thread(target=delete_temp).start()
        return True

    except Exception as e:
        try:
            bot.edit_message_text(
                f"❌ <b>Video #{order}/{total}</b> xatolik!\n\n{str(e)}",
                status_msg.chat.id, status_msg.message_id, parse_mode="HTML")
        except:
            pass
        return False

def process_queue(bot, uid):
    if video_processing.get(uid):
        return
    if not video_queue.get(uid):
        return
    next_video = video_queue[uid].pop(0)
    video_processing[uid] = next_video
    status_msg = bot.send_message(
        next_video["message"].chat.id,
        f"🎬 <b>Video #{next_video['order']}/{next_video['total']}</b> ishlanmoqda...",
        parse_mode="HTML")
    def run():
        process_video(bot, uid, next_video, status_msg)
        video_processing[uid] = None
        process_queue(bot, uid)
        video_edit_menu(bot, next_video["message"].chat.id)
    threading.Thread(target=run).start()

def start_video_upload(bot, call):
    uid = call.from_user.id
    if not video_edit_state.get(uid, {}).get("image_id"):
        bot.answer_callback_query(call.id, "❌ Avval rasm tanlang!", show_alert=True)
        return
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="video_edit_back"))
    try:
        bot.edit_message_text(
            "🎬 Iltimos, videolarni yuboring.\n\n"
            "✅ Bir nechta videolarni ketma-ket yuborishingiz mumkin\n"
            "📊 Har bir video navbatga qo'shiladi va fonda ishlanadi\n"
            "🔄 Jarayonni '📊 Jarayon' tugmasi orqali kuzatishingiz mumkin",
            call.message.chat.id, call.message.message_id, reply_markup=kb)
    except:
        pass
    video_edit_state[uid]["step"] = "waiting_video"
    video_edit_state[uid]["video_count"] = 0

def handle_video_upload(bot, message, bot_username):
    uid = message.from_user.id
    if video_edit_state.get(uid, {}).get("step") != "waiting_video":
        return False
    if not message.video:
        bot.reply_to(message, "❌ Iltimos, video fayl yuboring!")
        return True
    image_id = video_edit_state[uid].get("image_id")
    if not image_id:
        bot.reply_to(message, "❌ Rasm topilmadi! Avval rasm tanlang.")
        return True
    if "video_count" not in video_edit_state[uid]:
        video_edit_state[uid]["video_count"] = 0
    video_edit_state[uid]["video_count"] += 1
    order = video_edit_state[uid]["video_count"]
    video_data = {
        "video": message.video,
        "image_id": image_id,
        "message": message,
        "order": order,
        "total": 0
    }
    if uid not in video_queue:
        video_queue[uid] = []
    video_queue[uid].append(video_data)
    queue_size = len(video_queue[uid])
    bot.reply_to(
        message,
        f"✅ Video #{order} navbatga qo'shildi!\n"
        f"📊 Navbatdagi videolar: {queue_size} ta\n"
        f"🔄 Ishlanmoqda: {1 if video_processing.get(uid) else 0} ta")
    if not video_processing.get(uid):
        for i, v in enumerate(video_queue[uid]):
            v["total"] = len(video_queue[uid])
        process_queue(bot, uid)
    return True

def get_status_text(uid):
    queue_count = len(video_queue.get(uid, []))
    processing = video_processing.get(uid)
    if processing:
        current = processing["order"]
        total = processing["total"]
        status = f"🔄 Ishlanmoqda: Video #{current}/{total}"
    else:
        status = "⏸ Hech qanday video ishlanmayapti"
    return f"📊 <b>Joriy holat:</b>\n\n{status}\n📋 Navbatda: {queue_count} ta video"

def show_status(bot, call):
    uid = call.from_user.id
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 Yangilash", callback_data="video_edit_status"),
           InlineKeyboardButton("🔙 Orqaga", callback_data="video_edit_back"))
    try:
        bot.edit_message_text(get_status_text(uid), call.message.chat.id, call.message.message_id,
                              reply_markup=kb, parse_mode="HTML")
    except:
        pass

def back_to_video_edit(bot, call):
    uid = call.from_user.id
    if uid in video_edit_state:
        video_edit_state[uid]["step"] = "menu"
    video_edit_menu(bot, call.message.chat.id, call.message.message_id)

def video_edit_callback(bot, call):
    data = call.data
    if data == "video_edit_image":
        start_image_upload(bot, call)
    elif data == "video_edit_video":
        start_video_upload(bot, call)
    elif data == "video_edit_delete_image":
        delete_image(bot, call)
    elif data == "video_edit_status":
        show_status(bot, call)
    elif data == "video_edit_back":
        back_to_video_edit(bot, call)
