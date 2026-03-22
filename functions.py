import os
import time
import threading
import requests
import io
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Global variables
video_edit_state = {}
text_copy_state = {}
video_queue = {}  # Har bir foydalanuvchi uchun video navbati
video_processing = {}  # Hozir ishlanayotgan videolar

def video_edit_menu(bot, chat_id, message_id=None):
    """Video edit bo'limi menyusi"""
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🖼 Rasm", callback_data="video_edit_image"),
        InlineKeyboardButton("🎬 Video", callback_data="video_edit_video")
    )
    kb.add(
        InlineKeyboardButton("📊 Jarayon", callback_data="video_edit_status"),
        InlineKeyboardButton("🔙 Orqaga", callback_data="video_edit_back")
    )
    
    # Hozirgi navbatdagi videolar soni
    uid = chat_id
    queue_count = len(video_queue.get(uid, []))
    processing_count = 1 if video_processing.get(uid) else 0
    
    status_text = f"\n\n📊 <b>Holat:</b>\n• ⏳ Navbatda: {queue_count} ta\n• 🔄 Ishlanmoqda: {processing_count} ta"
    
    if message_id:
        bot.edit_message_text(
            f"🎬 Video ustiga rasm qo'yish bo'limiga xush kelibsiz!\n\n"
            f"Avval rasm tanlang, so'ng videolarni yuboring.{status_text}",
            chat_id,
            message_id,
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        bot.send_message(
            chat_id,
            f"🎬 Video ustiga rasm qo'yish bo'limiga xush kelibsiz!\n\n"
            f"Avval rasm tanlang, so'ng videolarni yuboring.{status_text}",
            reply_markup=kb,
            parse_mode="HTML"
        )

def start_video_edit(bot, message):
    """Video edit boshlash"""
    uid = message.from_user.id
    video_edit_state[uid] = {"step": "menu", "image_id": None}
    if uid not in video_queue:
        video_queue[uid] = []
    if uid not in video_processing:
        video_processing[uid] = None
    video_edit_menu(bot, message.chat.id, message.message_id)

def start_image_upload(bot, call):
    """Rasm yuklashni boshlash"""
    uid = call.from_user.id
    
    current_image = video_edit_state.get(uid, {}).get("image_id")
    
    kb = InlineKeyboardMarkup()
    if current_image:
        kb.add(InlineKeyboardButton("🗑 Rasmni o'chirish", callback_data="video_edit_delete_image"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="video_edit_back"))
    
    bot.edit_message_text(
        "🖼 Iltimos, yangi rasm yuboring.\n\n"
        f"{'Oldingi rasm mavjud. Yangi rasm eskisini almashtiradi.' if current_image else ''}\n\n"
        f"📌 <b>Eslatma:</b> Bu rasm <b>barcha</b> videolarga qo'llaniladi.",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb,
        parse_mode="HTML"
    )
    
    video_edit_state[uid]["step"] = "waiting_image"

def handle_image_upload(bot, message):
    """Rasmni qabul qilish va saqlash"""
    uid = message.from_user.id
    if video_edit_state.get(uid, {}).get("step") != "waiting_image":
        return False
    
    file_id = message.photo[-1].file_id
    video_edit_state[uid]["image_id"] = file_id
    video_edit_state[uid]["step"] = "menu"
    
    video_edit_menu(bot, message.chat.id)
    bot.send_message(message.chat.id, "✅ Rasm muvaffaqiyatli saqlandi! Endi videolarni yuborishingiz mumkin.")
    return True

def delete_image(bot, call):
    """Rasmni o'chirish"""
    uid = call.from_user.id
    if uid in video_edit_state:
        video_edit_state[uid]["image_id"] = None
    
    video_edit_menu(bot, call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id, "✅ Rasm o'chirildi!")

def format_size(size_bytes):
    """Baytni MB/GB ga o'tkazish"""
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def process_video(bot, uid, video_data, status_msg):
    """Bitta videoni qayta ishlash"""
    video = video_data["video"]
    image_id = video_data["image_id"]
    message = video_data["message"]
    order = video_data["order"]
    total = video_data["total"]
    
    try:
        # Yuklanishni boshlash
        bot.edit_message_text(
            f"📤 <b>Video #{order}/{total}</b> qayta ishlanmoqda...\n\n"
            f"📁 Hajmi: {format_size(video.file_size)}\n"
            f"⬇️ Yuklab olinmoqda... 0%",
            status_msg.chat.id,
            status_msg.message_id,
            parse_mode="HTML"
        )
        
        # Videoni yuklab olish
        file_info = bot.get_file(video.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        bot.edit_message_text(
            f"📤 <b>Video #{order}/{total}</b> qayta ishlanmoqda...\n\n"
            f"📁 Hajmi: {format_size(video.file_size)}\n"
            f"✅ Yuklab olindi!\n"
            f"🎬 Rasm qo'shilmoqda...",
            status_msg.chat.id,
            status_msg.message_id,
            parse_mode="HTML"
        )
        
        # Rasmni olish
        image_info = bot.get_file(image_id)
        image_file = bot.download_file(image_info.file_path)
        
        # Yangi video nomi
        video_name = f"@AniGonUz_{int(time.time())}_{order}.mp4"
        
        # Videoni qayta yuklash
        bot.edit_message_text(
            f"📤 <b>Video #{order}/{total}</b> qayta ishlanmoqda...\n\n"
            f"📁 Hajmi: {format_size(video.file_size)}\n"
            f"⬆️ Telegram'ga yuklanmoqda...",
            status_msg.chat.id,
            status_msg.message_id,
            parse_mode="HTML"
        )
        
        video_io = io.BytesIO(downloaded_file)
        video_io.name = video_name
        
        caption = message.caption if message.caption else ""
        
        thumbnail_io = io.BytesIO(image_file)
        thumbnail_io.name = "thumb.jpg"
        
        sent_video = bot.send_video(
            message.chat.id,
            video_io,
            caption=caption,
            thumbnail=thumbnail_io,
            supports_streaming=True,
            timeout=300
        )
        
        # Tugatish
        bot.edit_message_text(
            f"✅ <b>Video #{order}/{total}</b> tayyor!\n\n"
            f"📹 Video ID: {sent_video.video.file_id}\n"
            f"📁 Hajmi: {format_size(video.file_size)}\n"
            f"🏷 Nomi: {video_name}",
            status_msg.chat.id,
            status_msg.message_id,
            parse_mode="HTML"
        )
        
        # Vaqtinchalik xabarni o'chirish (10 sekunddan keyin)
        def delete_temp():
            time.sleep(10)
            try:
                bot.delete_message(status_msg.chat.id, status_msg.message_id)
            except:
                pass
        threading.Thread(target=delete_temp).start()
        
        return True
        
    except Exception as e:
        bot.edit_message_text(
            f"❌ <b>Video #{order}/{total}</b> xatolik!\n\n{str(e)}",
            status_msg.chat.id,
            status_msg.message_id,
            parse_mode="HTML"
        )
        return False

def process_queue(bot, uid):
    """Navbatdagi videolarni qayta ishlash"""
    if video_processing.get(uid):
        return  # Hozir video ishlanyapti
    
    if not video_queue.get(uid):
        return  # Navbat bo'sh
    
    # Navbatdan keyingi videoni olish
    next_video = video_queue[uid].pop(0)
    video_processing[uid] = next_video
    
    # Progress xabarini yaratish
    status_msg = bot.send_message(
        next_video["message"].chat.id,
        f"🎬 <b>Video #{next_video['order']}/{next_video['total']}</b> ishlanmoqda...",
        parse_mode="HTML"
    )
    
    # Fon threadda ishlatish
    def run():
        result = process_video(bot, uid, next_video, status_msg)
        video_processing[uid] = None
        # Keyingi videoni ishlatish
        process_queue(bot, uid)
        # Menyuni yangilash
        video_edit_menu(bot, next_video["message"].chat.id)
    
    threading.Thread(target=run).start()

def start_video_upload(bot, call):
    """Video yuklashni boshlash (faqat birinchi video uchun)"""
    uid = call.from_user.id
    
    if not video_edit_state.get(uid, {}).get("image_id"):
        bot.answer_callback_query(call.id, "❌ Avval rasm tanlang!", show_alert=True)
        return
    
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="video_edit_back"))
    
    bot.edit_message_text(
        "🎬 Iltimos, videolarni yuboring.\n\n"
        "✅ Bir nechta videolarni ketma-ket yuborishingiz mumkin\n"
        "📊 Har bir video navbatga qo'shiladi va fonda ishlanadi\n"
        "🔄 Jarayonni '📊 Jarayon' tugmasi orqali kuzatishingiz mumkin\n\n"
        "⚠️ Videolar yuborilgandan so'ng avtomatik qayta ishlanadi!",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb
    )
    
    video_edit_state[uid]["step"] = "waiting_video"
    video_edit_state[uid]["video_count"] = 0

def handle_video_upload(bot, message, bot_username):
    """Videoni qabul qilish va navbatga qo'shish"""
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
    
    # Video sonini hisoblash
    if "video_count" not in video_edit_state[uid]:
        video_edit_state[uid]["video_count"] = 0
    
    video_edit_state[uid]["video_count"] += 1
    order = video_edit_state[uid]["video_count"]
    
    # Navbatga qo'shish
    video_data = {
        "video": message.video,
        "image_id": image_id,
        "message": message,
        "order": order,
        "total": 0  # Keyin to'ldiriladi
    }
    
    if uid not in video_queue:
        video_queue[uid] = []
    
    video_queue[uid].append(video_data)
    queue_size = len(video_queue[uid])
    
    bot.reply_to(
        message,
        f"✅ Video #{order} navbatga qo'shildi!\n"
        f"📊 Navbatdagi videolar: {queue_size} ta\n"
        f"🔄 Ishlanmoqda: {1 if video_processing.get(uid) else 0} ta\n\n"
        f"💡 Barcha videolar yuborilgandan so'ng avtomatik ishlanadi."
    )
    
    # Agar hozir hech narsa ishlanmayotgan bo'lsa, darhol ishlatishni boshlash
    if not video_processing.get(uid):
        # Total sonini yangilash
        for i, v in enumerate(video_queue[uid]):
            v["total"] = len(video_queue[uid])
        process_queue(bot, uid)
    
    return True

def get_status_text(uid):
    """Joriy holat matnini qaytarish"""
    queue_count = len(video_queue.get(uid, []))
    processing = video_processing.get(uid)
    
    if processing:
        current = processing["order"]
        total = processing["total"]
        video_name = processing["video"].file_id[:8] + "..."
        size = format_size(processing["video"].file_size)
        status = f"🔄 Ishlanmoqda: Video #{current}/{total}\n   📹 ID: {video_name}\n   📁 Hajmi: {size}"
    else:
        status = "⏸ Hech qanday video ishlanmayapti"
    
    return f"📊 <b>Joriy holat:</b>\n\n{status}\n📋 Navbatda: {queue_count} ta video"

def show_status(bot, call):
    """Jarayon holatini ko'rsatish"""
    uid = call.from_user.id
    
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 Yangilash", callback_data="video_edit_status"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="video_edit_back"))
    
    bot.edit_message_text(
        get_status_text(uid),
        call.message.chat.id,
        call.message.message_id,
        reply_markup=kb,
        parse_mode="HTML"
    )

def back_to_video_edit(bot, call):
    """Orqaga qaytish"""
    uid = call.from_user.id
    video_edit_state[uid]["step"] = "menu"
    video_edit_menu(bot, call.message.chat.id, call.message.message_id)

def cancel_all_videos(bot, call):
    """Barcha videolarni bekor qilish"""
    uid = call.from_user.id
    video_queue[uid] = []
    video_processing[uid] = None
    bot.answer_callback_query(call.id, "✅ Barcha videolar bekor qilindi!")
    video_edit_menu(bot, call.message.chat.id, call.message.message_id)

# ==========================
#   TEXT COPY FUNCTIONS (o'zgarishsiz)
# ==========================

def start_text_copy(bot, chat_id):
    """Text Copy ni boshlash"""
    text_copy_state[chat_id] = {"step": "waiting_text"}
    bot.send_message(
        chat_id,
        "📝 Menga nusxalanishi kerak bo'lgan xabarni yuboring.\n\n"
        "💡 <b>Qo'shimcha ma'lumot:</b>\n"
        "• Xabar ichida <code>{raqam}</code> yozsangiz, men uni 1, 2, 3... deb almashtiraman\n"
        "• Har bir xabar 0.7 sekund interval bilan yuboriladi\n"
        "• Xabarlar kanalga yuboriladi",
        parse_mode="HTML"
    )

def handle_text_copy_message(bot, message):
    """Text Copy uchun xabarni qabul qilish"""
    uid = message.from_user.id
    if text_copy_state.get(uid, {}).get("step") != "waiting_text":
        return False
    
    text_copy_state[uid]["text_template"] = message.text if message.text else message.caption
    text_copy_state[uid]["content_type"] = message.content_type
    text_copy_state[uid]["file_id"] = None
    
    if message.content_type == "photo":
        text_copy_state[uid]["file_id"] = message.photo[-1].file_id
    elif message.content_type == "video":
        text_copy_state[uid]["file_id"] = message.video.file_id
    elif message.content_type == "document":
        text_copy_state[uid]["file_id"] = message.document.file_id
    
    text_copy_state[uid]["step"] = "waiting_count"
    bot.reply_to(message, "🔢 Nechta nusxa kerak? (raqam kiriting):")
    return True

def handle_text_copy_count(bot, message):
    """Nusxa sonini qabul qilish"""
    uid = message.from_user.id
    if text_copy_state.get(uid, {}).get("step") != "waiting_count":
        return False
    
    try:
        count = int(message.text.strip())
        if count < 1 or count > 10000:
            bot.reply_to(message, "❌ 1 dan 10000 gacha son kiriting!")
            return True
    except:
        bot.reply_to(message, "❌ Iltimos, faqat son kiriting!")
        return True
    
    text_copy_state[uid]["count"] = count
    text_copy_state[uid]["step"] = "waiting_channel"
    bot.reply_to(message, "📢 Kanal ID raqamini kiriting (masalan: -1001234567890):")
    return True

def handle_text_copy_channel(bot, message):
    """Kanal ID ni qabul qilish va xabarlarni yuborish"""
    uid = message.from_user.id
    if text_copy_state.get(uid, {}).get("step") != "waiting_channel":
        return False
    
    try:
        channel_id = int(message.text.strip())
    except:
        bot.reply_to(message, "❌ Noto'g'ri kanal ID formati!")
        return True
    
    data = text_copy_state[uid]
    text_template = data["text_template"]
    count = data["count"]
    content_type = data["content_type"]
    file_id = data.get("file_id")
    
    try:
        bot.get_chat(channel_id)
    except:
        bot.reply_to(message, "❌ Bot kanalda admin emas yoki kanal topilmadi!")
        return True
    
    status_msg = bot.reply_to(
        message,
        f"📤 Xabarlar yuborilmoqda...\n"
        f"📝 Jami: {count} ta\n"
        f"✅ 0/{count}"
    )
    
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
                    bot.edit_message_text(
                        f"📤 Xabarlar yuborilmoqda...\n"
                        f"📝 Jami: {count} ta\n"
                        f"✅ {success}/{count} muvaffaqiyatli\n"
                        f"❌ {fail} xatolik",
                        status_msg.chat.id,
                        status_msg.message_id
                    )
                except:
                    pass
            
            time.sleep(0.7)
            
        except Exception as e:
            fail += 1
            print(f"Xatolik: {e}")
    
    bot.edit_message_text(
        f"✅ Xabarlar yuborish tugallandi!\n\n"
        f"✅ Muvaffaqiyatli: {success}\n"
        f"❌ Xatolik: {fail}\n"
        f"📊 Jami: {count} ta",
        status_msg.chat.id,
        status_msg.message_id
    )
    
    def delete_temp():
        time.sleep(10)
        try:
            bot.delete_message(status_msg.chat.id, status_msg.message_id)
        except:
            pass
    threading.Thread(target=delete_temp).start()
    
    text_copy_state[uid] = {}
    
    return True

def cancel_text_copy(bot, message):
    """Text Copy ni bekor qilish"""
    uid = message.from_user.id
    if uid in text_copy_state:
        text_copy_state[uid] = {}
    bot.reply_to(message, "❌ Text Copy bekor qilindi.")

# ... barcha funksiyalar ...

def video_edit_callback(bot, call):
    """Video edit callback'larini boshqarish"""
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
