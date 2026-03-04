from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import TeleBot
from database import required_channels, optional_channels
from config import ADMIN_ID

bot: TeleBot = None

# Admin holatlari
admin_state = {}
admin_data = {}


def register_admin_panel(bot_instance: TeleBot):
    global bot
    bot = bot_instance

    # ==========================
    #   /admin
    # ==========================
    @bot.message_handler(commands=["admin"])
    def admin_menu(message):
        if message.from_user.id != ADMIN_ID:
            return

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("➕ Majburiy Kanal Qo‘shish", callback_data="req_add"),
            InlineKeyboardButton("➕ Ixtiyoriy Kanal Qo‘shish", callback_data="opt_add")
        )
        markup.add(
            InlineKeyboardButton("📋 Majburiy Ro‘yxat", callback_data="req_list"),
            InlineKeyboardButton("📋 Ixtiyoriy Ro‘yxat", callback_data="opt_list")
        )
        markup.add(
            InlineKeyboardButton("❌ Chiqish", callback_data="close_admin")
        )

        bot.reply_to(message, "<b>Admin Panel</b>", reply_markup=markup)

    # ==========================
    #   CALLBACK HANDLER
    # ==========================
    @bot.callback_query_handler(func=lambda call: call.data.startswith(("req_", "opt_", "close_admin")))
    def callback(call):
        if call.from_user.id != ADMIN_ID:
            return

        data = call.data

        # --------------------------
        #   ADMIN PANELNI YOPISH
        # --------------------------
        if data == "close_admin":
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            return

        # --------------------------
        #   MAJBURIY KANAL QO‘SHISH
        # --------------------------
        if data == "req_add":
            start_required_add(call)

        # --------------------------
        #   IXTİYORIY KANAL QO‘SHISH
        # --------------------------
        if data == "opt_add":
            start_optional_add(call)

        # --------------------------
        #   RO‘YXATLARNI KO‘RISH
        # --------------------------
        if data == "req_list":
            show_required_list(call)

        if data == "opt_list":
            show_optional_list(call)


# ============================================================
#   MAJBURIY KANAL QO‘SHISH — POST HAVOLASI ORQALI
# ============================================================

def start_required_add(call):
    uid = call.from_user.id
    admin_state[uid] = "req_wait_post_link"
    admin_data[uid] = {}

    bot.edit_message_text(
        "➕ Majburiy kanal qo‘shish boshlandi.\n\n"
        "📌 Iltimos kanal ichidagi istalgan POST HAVOLASINI yuboring.\n"
        "Bu public yoki private kanal bo‘lishi mumkin.",
        call.message.chat.id,
        call.message.message_id
    )


@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_wait_post_link")
def req_get_post_link(message):
    uid = message.from_user.id
    url = message.text.strip()

    if "t.me/" not in url:
        bot.reply_to(message, "❌ To‘g‘ri post havolasini yuboring.")
        return

    # PRIVATE KANAL: https://t.me/c/123456789/55
    if "/c/" in url:
        try:
            parts = url.split("/c/")[1].split("/")
            internal_id = int(parts[0])
            channel_id = -1000000000000 + internal_id
        except:
            bot.reply_to(message, "❌ Post havolasidan kanal ID ni aniqlab bo‘lmadi.")
            return

        try:
            chat = bot.get_chat(channel_id)
        except:
            bot.reply_to(message, "❌ Bot kanalga kira olmadi. Bot admin emas.")
            return

    else:
        # PUBLIC KANAL: https://t.me/username/55
        username = url.split("t.me/")[1].split("/")[0]
        try:
            chat = bot.get_chat(username)
            channel_id = chat.id
        except:
            bot.reply_to(message, "❌ Kanalga kira olmadim. Bot admin emas.")
            return

    # Bot shu kanalda adminmi?
    try:
        member = bot.get_chat_member(channel_id, bot.get_me().id)
        if member.status not in ["administrator", "creator"]:
            bot.reply_to(message, "❌ Bot bu kanalda admin emas. Avval botni admin qiling.")
            return
    except:
        bot.reply_to(message, "❌ Kanalga kira olmadim.")
        return

    # Ma’lumotlarni saqlaymiz
    admin_data[uid]["channel_id"] = channel_id
    admin_data[uid]["name"] = chat.title

    # Endi majburiy obuna uchun havola so‘raymiz
    admin_state[uid] = "req_wait_public_link"
    bot.reply_to(message, "🔗 Endi majburiy obuna uchun havola yuboring:")


@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_wait_public_link")
def req_get_public_link(message):
    uid = message.from_user.id
    url = message.text.strip()

    if "t.me/" not in url:
        bot.reply_to(message, "❌ To‘g‘ri havola yuboring.")
        return

    admin_data[uid]["url"] = url

    admin_state[uid] = "req_add_count"
    bot.reply_to(message, "👥 Ushbu kanalga qancha obunachi qo‘shmoqchisiz?")


@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_count")
def req_get_count(message):
    uid = message.from_user.id

    if not message.text.isdigit():
        bot.reply_to(message, "❌ Faqat raqam kiriting.")
        return

    admin_data[uid]["count"] = int(message.text)

    admin_state[uid] = "req_add_name"
    bot.reply_to(message, "📛 Kanal nomini kiriting yoki 'auto' deb yozing.")


@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "req_add_name")
def req_get_name(message):
    uid = message.from_user.id
    name = message.text.strip()

    if name.lower() == "auto":
        name = admin_data[uid]["name"]

    admin_data[uid]["name"] = name

    required_channels.insert_one(admin_data[uid])

    bot.reply_to(message, "✅ Majburiy kanal muvaffaqiyatli qo‘shildi!")

    admin_state.pop(uid, None)
    admin_data.pop(uid, None)


# ============================================================
#   IXTİYORIY KANAL QO‘SHISH (oddiy)
# ============================================================

def start_optional_add(call):
    uid = call.from_user.id
    admin_state[uid] = "opt_wait_link"
    admin_data[uid] = {}

    bot.edit_message_text(
        "➕ Ixtiyoriy kanal qo‘shish.\n\n"
        "🔗 Kanal havolasini yuboring:",
        call.message.chat.id,
        call.message.message_id
    )


@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_wait_link")
def opt_get_link(message):
    uid = message.from_user.id
    url = message.text.strip()

    if "t.me/" not in url:
        bot.reply_to(message, "❌ To‘g‘ri havola yuboring.")
        return

    admin_data[uid]["url"] = url

    admin_state[uid] = "opt_wait_name"
    bot.reply_to(message, "📛 Kanal nomini kiriting:")


@bot.message_handler(func=lambda m: admin_state.get(m.from_user.id) == "opt_wait_name")
def opt_get_name(message):
    uid = message.from_user.id
    name = message.text.strip()

    admin_data[uid]["name"] = name

    optional_channels.insert_one(admin_data[uid])

    bot.reply_to(message, "✅ Ixtiyoriy kanal qo‘shildi!")

    admin_state.pop(uid, None)
    admin_data.pop(uid, None)


# ============================================================
#   RO‘YXATLARNI KO‘RISH
# ============================================================

def show_required_list(call):
    channels = list(required_channels.find({}))

    if not channels:
        bot.answer_callback_query(call.id, "Majburiy kanallar yo‘q.", show_alert=True)
        return

    text = "<b>📋 Majburiy kanallar:</b>\n\n"
    for ch in channels:
        text += f"• {ch['name']} — {ch['url']}\n"

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)


def show_optional_list(call):
    channels = list(optional_channels.find({}))

    if not channels:
        bot.answer_callback_query(call.id, "Ixtiyoriy kanallar yo‘q.", show_alert=True)
        return

    text = "<b>📋 Ixtiyoriy kanallar:</b>\n\n"
    for ch in channels:
        text += f"• {ch['name']} — {ch['url']}\n"

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
