from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import TeleBot
from subscription import check_required_subs, get_required_keyboard
from database import contents

bot: TeleBot = None


def register_handlers(bot_instance: TeleBot):
    global bot
    bot = bot_instance

    # ==========================
    #   /start (ODDIY)
    # ==========================
    @bot.message_handler(func=lambda m: m.text == "/start")
    def start(message):
        user_msg_id = message.message_id  # foydalanuvchi yuborgan /start

        sent = bot.reply_to(
            message,
            "<b>Bu bot orqali kanaldagi animelarni yuklab olishingiz mumkin.\n\n"
            "❗️Botga habar yozmang❗️</b>"
        )

        bot_msg_id = sent.message_id  # botning javobi

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("📝 Bot Haqida", callback_data=f"about:{user_msg_id}:{bot_msg_id}"),
            InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{user_msg_id}:{bot_msg_id}")
        )

        bot.edit_message_reply_markup(message.chat.id, bot_msg_id, reply_markup=markup)

    # ==========================
    #   /start <code> (KONTENT)
    # ==========================
    @bot.message_handler(func=lambda m: m.text.startswith("/start ") and len(m.text.split()) == 2)
    def start_with_code(message):
        code = message.text.split()[1]

        item = contents.find_one({"code": code})
        if not item:
            bot.send_message(message.chat.id, "❌ Kontent topilmadi yoki o‘chirilgan.")
            return

        if not check_required_subs(message.from_user.id):
            kb = get_required_keyboard(message.from_user.id, code)
            bot.send_message(
                message.chat.id,
                "📌 Iltimos quyidagi kanallarga obuna bo‘ling:",
                reply_markup=kb
            )
            return

        send_content(message.chat.id, item)

    # ==========================
    #   CALLBACK HANDLER
    # ==========================
    @bot.callback_query_handler(func=lambda call: True)
    def callback(call):
        data = call.data

        # ==========================
        #   YOPISH — 3 TA XABARNI O‘CHIRADI
        # ==========================
        if data.startswith("close:"):
            _, user_msg_id, bot_msg_id = data.split(":")
            chat_id = call.message.chat.id

            # 1) Hozirgi bo‘lim xabarini o‘chiramiz
            try:
                bot.delete_message(chat_id, call.message.message_id)
            except:
                pass

            # 2) Botning /start javobi
            try:
                bot.delete_message(chat_id, int(bot_msg_id))
            except:
                pass

            # 3) Foydalanuvchi yuborgan /start komandasi
            try:
                bot.delete_message(chat_id, int(user_msg_id))
            except:
                pass

            return

        # ==========================
        #   BOT HAQIDA
        # ==========================
        if data.startswith("about:"):
            _, user_msg_id, bot_msg_id = data.split(":")

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("👨‍💻 Yaratuvchi", callback_data=f"creator:{user_msg_id}:{bot_msg_id}"),
                InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{user_msg_id}:{bot_msg_id}")
            )

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    "<b>"
                    "Botni ishlatishni bilmaganlar uchun!\n\n"
                    "❏ Botni ishlatish qo'llanmasi:\n"
                    "1. Kanallarga obuna bo'ling!\n"
                    "2. Tekshirish tugmasini bosing ✅\n"
                    "3. Kanaldagi anime post past qismidagi yuklab olish tugmasini bosing\n\n"
                    "📢 Kanal: <i>@AniGonUz</i>"
                    "</b>"
                ),
                reply_markup=markup
            )

        # ==========================
        #   CREATOR
        # ==========================
        if data.startswith("creator:"):
            _, user_msg_id, bot_msg_id = data.split(":")

            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("📝 Bot Haqida", callback_data=f"about:{user_msg_id}:{bot_msg_id}"),
                InlineKeyboardButton("🔒 Yopish", callback_data=f"close:{user_msg_id}:{bot_msg_id}")
            )

            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    "<b>"
                    "• Admin: <i>@Shadow_Sxi</i>\n"
                    "• Asosiy Kanal: <i>@AniGonUz</i>\n"
                    "• Reklama: <i>@AniReklamaUz</i>\n\n"
                    "👨‍💻 Savollar Boʻlsa: <i>@AniManxwaBot</i>"
                    "</b>"
                ),
                reply_markup=markup
            )


# ==========================
#   KONTENT YUBORISH FUNKSIYASI
# ==========================
def send_content(chat_id, item):
    if item["type"] == "text":
        bot.send_message(chat_id, item["text"])

    elif item["type"] == "photo":
        bot.send_photo(chat_id, item["file_id"], caption=item.get("caption"))

    elif item["type"] == "video":
        bot.send_video(chat_id, item["file_id"], caption=item.get("caption"))

    elif item["type"] == "document":
        bot.send_document(chat_id, item["file_id"], caption=item.get("caption"))
