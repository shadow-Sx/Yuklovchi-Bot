from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import users, referrals, settings
import threading
import time


bot: TeleBot = None


def register_handlers(bot_instance: TeleBot):
    global bot
    bot = bot_instance

    # /start — foydalanuvchini saqlash + referal hisoblash
    @bot.message_handler(commands=["start"])
    def start(message):
        args = message.text.split()

        # Foydalanuvchini ro'yxatga olish
        users.update_one(
            {"user_id": message.from_user.id},
            {"$set": {"user_id": message.from_user.id}},
            upsert=True,
        )

        # REFERAL BORMI?
        if len(args) == 2:
            ref_key = args[1]
            referrals.update_one(
                {"key": ref_key},
                {"$inc": {"count": 1}},
                upsert=True,
            )

        bot.reply_to(
            message,
            "Assalomu alaykum!\n"
            "Botga xush kelibsiz.",
        )

    # Avto o'chirishni o'chirish uchun /delettime
    @bot.message_handler(commands=["delettime"])
    def delete_auto_time(message):
        settings.delete_one({"key": "auto_delete"})
        bot.reply_to(message, "❌ Avto o‘chirish o‘chirildi.")

    # Test uchun oddiy kontent yuborish (namuna)
    @bot.message_handler(commands=["testcontent"])
    def test_content(message):
        """
        Bu faqat namuna uchun.
        Haqiqiy loyihangda kontent yuboradigan joyda
        send_content() funksiyasini ishlatasan.
        """
        code = "TEST_CODE"  # odatda bu yerda fayl kodi yoki shunga o'xshash narsa bo'ladi
        send_content(message.chat.id, {"type": "text", "text": "Bu test kontent", "code": code})


def send_content(chat_id, item: dict):
    """
    item:
      type: text/photo/video/document
      text/caption/file_id
      code: qayta tiklash uchun start param
    """
    sent = None

    if item["type"] == "text":
        sent = bot.send_message(chat_id, item["text"])

    elif item["type"] == "photo":
        sent = bot.send_photo(chat_id, item["file_id"], caption=item.get("caption"))

    elif item["type"] == "video":
        sent = bot.send_video(chat_id, item["file_id"], caption=item.get("caption"))

    elif item["type"] == "document":
        sent = bot.send_document(chat_id, item["file_id"], caption=item.get("caption"))

    if not sent:
        return

    # AVTO O‘CHIRISH YOQILGANMI?
    auto = settings.find_one({"key": "auto_delete"})
    if auto:
        seconds = auto["time"]
        start_auto_delete(chat_id, sent.message_id, seconds, item.get("code", ""))


def start_auto_delete(chat_id, msg_id, seconds, code):
    # Eslatma yuboramiz
    note = bot.send_message(
        chat_id,
        f"⚠️ESLATMA⚠️\n"
        f"Ushbu habar {seconds // 60}:{seconds % 60:02d} dan so‘ng o‘chirilib yuboriladi.\n"
        f"Tezda saqlab oling.",
    )
    note_id = note.message_id

    def delete_later():
        time.sleep(seconds)

        # Kontentni o‘chiramiz
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass

        # Eslatmani o‘zgartiramiz
        markup = InlineKeyboardMarkup()
        if code:
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
                reply_markup=markup if code else None,
            )
        except:
            pass

    threading.Thread(target=delete_later, daemon=True).start()
