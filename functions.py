import os
import time
import threading
import requests
import io
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Global variables
video_edit_state = {}
text_copy_state = {}
video_queue = {}
video_processing = {}
post_edit_state = {}

# ADMIN ID (functions.py uchun global)
ADMIN_ID = 7797502113
BOT_USERNAME = None  # main.py dan set qilinadi

def set_bot_username(username):
    """Bot username ni set qilish"""
    global BOT_USERNAME
    BOT_USERNAME = username

# ==========================
#   PREMIUM FUNCTIONS
# ==========================

def add_premium_reaction(bot, chat_id, message_id, emoji="🎉"):
    """Premium reaksiya qo'shish"""
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
    """Bir nechta reaksiya qo'shish"""
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
#   POST EDITOR FUNCTIONS
# ==========================

def start_post_editor(bot, message):
    """Post tayyorlashni boshlash"""
    uid = message.from_user.id
    post_edit_state[uid] = {"step": "waiting_post_link", "buttons": []}
    bot.reply_to(
        message,
        "📝 <b>Post tayyorlash bo'limiga xush kelibsiz!</b>\n\n"
        "1. Avval post havolasini yuboring (kanaldagi post)\n"
        "2. So'ng tugmalar qo'shishingiz mumkin\n"
        "3. Tugatish uchun /done buyrug'ini yuboring\n\n"
        "⚠️ Bot kanalda admin bo'lishi kerak!",
        parse_mode="HTML"
    )

def handle_post_link(bot, message):
    """Post havolasini qabul qilish"""
    uid = message.from_user.id
    if post_edit_state.get(uid, {}).get("step") != "waiting_post_link":
        return False
    
    post_url = message.text.strip()
    
    try:
        if "t.me/" in post_url:
            parts = post_url.split("/")
            username = parts[-2]
            msg_id = int(parts[-1])
            
            chat = bot.get_chat(f"@{username}")
            chat_id = chat.id
            
            post = bot.forward_message(chat_id, chat_id, msg_id)
            
            post_edit_state[uid]["chat_id"] = chat_id
            post_edit_state[uid]["message_id"] = msg_id
            post_edit_state[uid]["content"] = {
                "text": post.text if post.text else "",
                "caption": post.caption if post.caption else "",
                "photo": post.photo[-1].file_id if post.photo else None,
                "video": post.video.file_id if post.video else None,
                "document": post.document.file_id if post.document else None
            }
            
            bot.reply_to(message, "✅ Post topildi! Endi tugmalar qo'shishingiz mumkin.\n\n"
                         "Tugma qo'shish uchun format:\n"
                         "<code>tugma_nomi | havola</code>\n\n"
                         "Masalan:\n"
                         "<code>Kanalimiz | https://t.me/kanal</code>\n\n"
                         "Tugatish uchun /done yuboring")
            
            post_edit_state[uid]["step"] = "waiting_buttons"
            return True
            
    except Exception as e:
        bot.reply_to(message, f"❌ Xatolik: {str(e)}\n\nIltimos, to'g'ri post havolasini yuboring!")
        return True

def add_button_to_post(bot, message):
    """Postga tugma qo'shish"""
    uid = message.from_user.id
    if post_edit_state.get(uid, {}).get("step") != "waiting_buttons":
        return False
    
    text = message.text.strip()
    if "|" not in text:
        bot.reply_to(message, "❌ Noto'g'ri format! Tugma nomi va havolani '|' bilan ajrating.\n"
                     "Masalan: <code>Kanalimiz | https://t.me/kanal</code>")
        return True
    
    button_name, button_url = text.split("|", 1)
    button_name = button_name.strip()
    button_url = button_url.strip()
    
    if not button_url.startswith(("http://", "https://")):
        button_url = "https://" + button_url
    
    post_edit_state[uid]["buttons"].append({
        "name": button_name,
        "url": button_url
    })
    
    current_buttons = "\n".join([f"• {b['name']} -> {b['url']}" for b in post_edit_state[uid]["buttons"]])
    bot.reply_to(
        message,
        f"✅ Tugma qo'shildi!\n\n"
        f"📋 <b>Joriy tugmalar:</b>\n{current_buttons}\n\n"
        f"Yana tugma qo'shishingiz mumkin yoki /done bilan tugating.",
        parse_mode="HTML"
    )
    return True

def finish_post_editor(bot, message):
    """Postni tugmalar bilan qayta yuborish"""
    uid = message.from_user.id
    if uid not in post_edit_state:
        bot.reply_to(message, "❌ Hech qanday faol jarayon yo'q!")
        return
    
    data = post_edit_state[uid]
    if not data.get("buttons"):
        bot.reply_to(message, "❌ Hech qanday tugma qo'shilmagan!")
        return
    
    kb = InlineKeyboardMarkup(row_width=1)
    for btn in data["buttons"]:
        kb.add(InlineKeyboardButton(btn["name"], url=btn["url"]))
    
    try:
        bot.delete_message(data["chat_id"], data["message_id"])
        
        content = data["content"]
        if content["photo"]:
            sent = bot.send_photo(
                data["chat_id"],
                content["photo"],
                caption=content["caption"] or content["text"],
                reply_markup=kb
            )
        elif content["video"]:
            sent = bot.send_video(
                data["chat_id"],
                content["video"],
                caption=content["caption"] or content["text"],
                reply_markup=kb
            )
        else:
            sent = bot.send_message(
                data["chat_id"],
                content["text"] or content["caption"],
                reply_markup=kb,
                parse_mode="HTML"
            )
        
        bot.reply_to(message, "✅ Post muvaffaqiyatli yangilandi va tugmalar qo'shildi!")
        add_premium_reaction(bot, sent.chat.id, sent.message_id, "📝")
        
    except Exception as e:
        bot.reply_to(message, f"❌ Xatolik: {str(e)}")
    
    post_edit_state[uid] = {}

def cancel_post_editor(bot, message):
    """Post tayyorlashni bekor qilish"""
    uid = message.from_user.id
    if uid in post_edit_state:
        post_edit_state[uid] = {}
    bot.reply_to(message, "❌ Post tayyorlash bekor qilindi.")

# ==========================
#   VIDEO EDIT FUNCTIONS
# ==========================

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
    
    uid = chat_id
    queue_count = len(video_queue.get(uid, []))
    processing_count = 1 if video_processing.get(uid) else 0
    
    status_text = f"\n\n📊 <b>Holat:</b>\n• ⏳ Navbatda: {queue_count} ta\n• 🔄 Ishlanmoqda: {processing_count} ta"
    
    if message_id:
        try:
            bot.edit_message_text(
                f"🎬 Video ustiga rasm qo'yish bo'limiga xush kelibsiz!\n\n"
                f"Avval rasm tanlang, so'ng videolarni yuboring.{status_text}",
                chat_id,
                message_id,
                reply_markup=kb,
                parse_mode="HTML"
            )
        except:
            pass
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
    add_premium_reaction(bot, message.chat.id, message.message_id, "🎬")

def start_image_upload(bot, call):
    """Rasm yuklashni boshlash"""
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
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except:
        pass
    
    video_edit_state[uid]["step"] = "waiting_image"

def handle_image_upload(bot, message):
    """Rasmni qabul qilish va saqlash"""
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
    """Rasmni o'chirish"""
    uid = call.from_user.id
    if uid in video_edit_state:
        video_edit_state[uid]["image_id"] = None
    
    try:
        video_edit_menu(bot, call.message.chat.id, call.message.message_id)
    except:
        pass
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
        bot.edit_message_text(
            f"📤 <b>Video #{order}/{total}</b> qayta ishlanmoqda...\n\n"
            f"📁 Hajmi: {format_size(video.file_size)}\n"
            f"⬇️ Yuklab olinmoqda...",
            status_msg.chat.id,
            status_msg.message_id,
            parse_mode="HTML"
        )
        
        file_info = bot.get_file(video.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        bot.edit_message_text(
            f"📤 <b>Video #{order}/{total}</b> qayta ishlanmoqda...\n\n"
            f"📁 Hajmi: {format_size(video.file_size)}\n"
            f"✅ Yuklab olindi!\n🎬 Rasm qo'shilmoqda...",
            status_msg.chat.id,
            status_msg.message_id,
            parse_mode="HTML"
        )
        
        image_info = bot.get_file(image_id)
        image_file = bot.download_file(image_info.file_path)
        
        video_name = f"@AniGonUz_{int(time.time())}_{order}.mp4"
        
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
        
        bot.edit_message_text(
            f"✅ <b>Video #{order}/{total}</b> tayyor!\n\n"
            f"📹 Video ID: {sent_video.video.file_id[:20]}...\n"
            f"📁 Hajmi: {format_size(video.file_size)}",
            status_msg.chat.id,
            status_msg.message_id,
            parse_mode="HTML"
        )
        
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
                status_msg.chat.id,
                status_msg.message_id,
                parse_mode="HTML"
            )
        except:
            pass
        return False

def process_queue(bot, uid):
    """Navbatdagi videolarni qayta ishlash"""
    if video_processing.get(uid):
        return
    
    if not video_queue.get(uid):
        return
    
    next_video = video_queue[uid].pop(0)
    video_processing[uid] = next_video
    
    status_msg = bot.send_message(
        next_video["message"].chat.id,
        f"🎬 <b>Video #{next_video['order']}/{next_video['total']}</b> ishlanmoqda...",
        parse_mode="HTML"
    )
    
    def run():
        process_video(bot, uid, next_video, status_msg)
        video_processing[uid] = None
        process_queue(bot, uid)
        video_edit_menu(bot, next_video["message"].chat.id)
    
    threading.Thread(target=run).start()

def start_video_upload(bot, call):
    """Video yuklashni boshlash"""
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
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )
    except:
        pass
    
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
        f"🔄 Ishlanmoqda: {1 if video_processing.get(uid) else 0} ta"
    )
    
    if not video_processing.get(uid):
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
        status = f"🔄 Ishlanmoqda: Video #{current}/{total}"
    else:
        status = "⏸ Hech qanday video ishlanmayapti"
    
    return f"📊 <b>Joriy holat:</b>\n\n{status}\n📋 Navbatda: {queue_count} ta video"

def show_status(bot, call):
    """Jarayon holatini ko'rsatish"""
    uid = call.from_user.id
    
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 Yangilash", callback_data="video_edit_status"))
    kb.add(InlineKeyboardButton("🔙 Orqaga", callback_data="video_edit_back"))
    
    try:
        bot.edit_message_text(
            get_status_text(uid),
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb,
            parse_mode="HTML"
        )
    except:
        pass

def back_to_video_edit(bot, call):
    """Orqaga qaytish"""
    uid = call.from_user.id
    if uid in video_edit_state:
        video_edit_state[uid]["step"] = "menu"
    video_edit_menu(bot, call.message.chat.id, call.message.message_id)

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

# ==========================
#   TEXT COPY FUNCTIONS
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
            
            time.sleep(0.8)
            
        except Exception as e:
            fail += 1
            print(f"Xatolik ({i}): {e}")
    
    bot.edit_message_text(
        f"✅ Xabarlar yuborish tugallandi!\n\n"
        f"✅ Muvaffaqiyatli: {success}\n"
        f"❌ Xatolik: {fail}\n"
        f"📊 Jami: {count} ta",
        status_msg.chat.id,
        status_msg.message_id
    )
    
    def delete_temp():
        time.sleep(5)
        try:
            bot.delete_message(status_msg.chat.id, status_msg.message_id)
        except:
            pass
    threading.Thread(target=delete_temp).start()
    
    text_copy_state[uid] = {}
    add_premium_reaction(bot, message.chat.id, message.message_id, "✅")
    
    return True

def cancel_text_copy(bot, message):
    """Text Copy ni bekor qilish"""
    uid = message.from_user.id
    if uid in text_copy_state:
        text_copy_state[uid] = {}
    bot.reply_to(message, "❌ Text Copy bekor qilindi.")
