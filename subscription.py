import random
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import required_channels, optional_channels, contents
from telebot import TeleBot

bot: TeleBot = None


def register_subscription(bot_instance: TeleBot):
    global bot
    bot = bot_instance


# ==========================
#   MAJBURIY OBUNA TEKSHIRISH
# ==========================
def check_required_subs(user_id):
    channels = list(required_channels.find({}))

    for ch in channels:
        try:
            member = bot.get_chat_member(ch["channel_id"], user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False

    return True


# ==========================
#   RANDOM TUGMALAR + RANDOM HAVOLALAR
# ==========================
def get_required_keyboard(user_id, code):
    req = list(required_channels.find({}))
    opt = list(optional_channels.find({}))

    # Avto nomlangan kanallarni ajratamiz
    auto_channels = [c for c in req if c.get("auto")]
    manual_channels = [c for c in req if not c.get("auto")]

    # Avto nomlangan kanallar havolasini random aralashtiramiz
    auto_urls = [c["url"] for c in auto_channels]
    random.shuffle(auto_urls)

    for i, ch in enumerate(auto_channels):
        ch["url"] = auto_urls[i]

    # Tugmalarni yig‘amiz
    buttons = []

    # Majburiy kanallar
    for ch in auto_channels + manual_channels:
        buttons.append(InlineKeyboardButton(ch["name"], url=ch["url"]))

    # Ixtiyoriy kanallar faqat majburiylar bajarilmaganda chiqadi
    if not check_required_subs(user_id):
        for ch in opt:
            buttons.append(InlineKeyboardButton(ch["name"], url=ch["url"]))

    # Tugmalarni random aralashtiramiz
    random.shuffle(buttons)

    kb = InlineKeyboardMarkup(row_width=1)
    for btn in buttons:
        kb.add(btn)

    # Tekshirish tugmasi
    kb.add(InlineKeyboardButton("Tekshirish ♻️", callback_data=f"check:{code}"))

    return kb


# ==========================
#   TEKSHIRISH CALLBACK
# ==========================
def register_check_handler(bot_instance: TeleBot):
    global bot
    bot = bot_instance

    @bot.callback_query_handler(func=lambda c: c.data.startswith("check:"))
    def check_subs(call):
        code = call.data.split(":")[1]

        if check_required_subs(call.from_user.id):
            item = contents.find_one({"code": code})
            if item:
                send_content(call.message.chat.id, item)

            # Majburiy obuna oynasini o‘chirib tashlaymiz
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass

        else:
            bot.answer_callback_query(
                call.id,
                "❌ Hali hammasiga obuna bo‘lmadingiz!",
                show_alert=True
            )


# ==========================
#   KONTENT YUBORISH
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
