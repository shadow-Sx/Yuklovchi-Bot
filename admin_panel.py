from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot import TeleBot
from database import (
    required_channels,
    optional_channels,
    users,
    referrals,
    settings,
    broadcast,
)
from config import ADMIN_ID

bot: TeleBot = None

admin_state = {}
admin_data = {}


def register_admin_panel(bot_instance: TeleBot):
    global bot
    bot = bot_instance

    @bot.message_handler(commands=["admin"])
    def admin_menu(message):
        if message.from_user.id != ADMIN_ID:
            return

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("➕ Majburiy Kanal", callback_data="req_add"),
            InlineKeyboardButton("➕ Ixtiyoriy Kanal", callback_data="opt_add"),
        )
        markup.add(
            InlineKeyboardButton("📋 Majburiy Ro'yxat", callback_data="req_list"),
            InlineKeyboardButton("📋 Ixtiyoriy Ro'yxat", callback_data="opt_list"),
        )
        markup.add(
            InlineKeyboardButton("📊 Statistika", callback_data="stats"),
            InlineKeyboardButton("🔗 Referal", callback_data="ref_menu"),
        )
        markup.add(
            InlineKeyboardButton("⏱ AVTO O‘CHIRISH", callback_data="auto_delete"),
        )
        markup.add(
            InlineKeyboardButton("📨 Habar yuborish", callback_data="send_menu"),
        )
        markup.add(
            InlineKeyboardButton("❌ Chiqish", callback_data="close_admin"),
        )

        bot.reply_to(message, "<b>Admin Panel</b>", reply_markup=markup)

    @bot.callback_query_handler(
        func=lambda call: True
        and call.from_user.id == ADMIN_ID
    )
    def admin_callbacks(call):
        uid = call.from_user.id
        data = call.data

        if data == "close_admin":
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            return

        if data == "req_add":
            start_required_add(call)

        if data == "opt_add":
            start_optional_add(call)

        if data == "req_list":
            show_required_list(call)

        if data == "opt_list":
            show_optional_list(call)

        if data == "stats":
            count = users.count_documents({})
            bot.edit_message_text(
                f"📊 Barcha foydalanuvchilar: <b>{count}</b>",
                call.message.chat.id,
                call.message.message_id,
            )

        # REFERAL MENYUSI
        if data == "ref_menu":
            markup = InlineKeyboardMarkup()
            markup.add(
                InlineKeyboardButton("➕ Yaratish", callback_data="ref_create"),
                InlineKeyboardButton("📊 Kuzatish", callback_data="ref_view"),
                InlineKeyboardButton("🗑 O‘chirish", callback_data="ref_delete"),
            )
            bot.edit_message_text(
                "Kerakli tugmani tanlang:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup,
            )

        if data == "ref_create":
            admin_state[uid] = "ref_wait_key"
            bot.edit_message_text(
                "Iltimos havola uchun so'z kiriting.\n"
                "Masalan: <code>Yangi_Referal</code>",
                call.message.chat.id,
                call.message.message_id,
            )

        if data == "ref_view":
            items = list(referrals.find({}))
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

            bot.edit_message_text(
                text, call.message.chat.id, call.message.message_id
            )

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

        # HABAR YUBORISH
        if data == "send_menu":
            admin_state[uid] = "wait_broadcast_text"
            broadcast.delete_many({"admin_id": uid})
            bot.edit_message_text(
                "Yuboriladigan habaringizni yuboring:",
                call.message.chat.id,
                call.message.message_id,
            )

        if data == "add_btn":
            admin_state[uid] = "wait_btn_name"
            bot.answer_callback_query(call.id)
            bot.send_message(uid, "Tugma nomini kiriting:")

        if data == "preview":
            item = broadcast.find_one({"admin_id": uid})
            if not item:
                bot.answer_callback_query(
                    call.id, "Hali habar saqlanmagan.", show_alert=True
                )
                return

            text = item["text"]
            markup = InlineKeyboardMarkup()
            for btn in item["buttons"]:
                markup.add(InlineKeyboardButton(btn["name"], url=btn["url"]))

            bot.send_message(
                uid, f"👁 <b>Ko‘rinishi:</b>\n\n{text}", reply_markup=markup
            )

        if data == "cancel_broadcast":
            broadcast.delete_many({"admin_id": uid})
            admin_state.pop(uid, None)
            bot.edit_message_text(
                "❌ Habar yuborish bekor qilindi.",
                call.message.chat.id,
                call.message.message_id,
            )

        if data == "do_broadcast":
            item = broadcast.find_one({"admin_id": uid})
            if not item:
                bot.answer_callback_query(
                    call.id, "Hali habar saqlanmagan.", show_alert=True
                )
                return

            from database import users as users_col

            text = item["text"]
            buttons = item["buttons"]

            markup = InlineKeyboardMarkup()
            for btn in buttons:
                markup.add(InlineKeyboardButton(btn["name"], url=btn["url"]))

            users_list = users_col.find({})
            count = 0
            for u in users_list:
                try:
                    bot.send_message(u["user_id"], text, reply_markup=markup)
                    count += 1
                except:
                    pass

            bot.edit_message_text(
                f"📨 Habar yuborildi!\n"
                f"Yuborilgan foydalanuvchilar: <b>{count}</b>",
                call.message.chat.id,
                call.message.message_id,
            )

            broadcast.delete_many({"admin_id": uid})
            admin_state.pop(uid, None)

    # ==== REFERAL HANDLERLARI ====

    @bot.message_handler(
        func=lambda m: admin_state.get(m.from_user.id) == "ref_wait_key"
        and m.from_user.id == ADMIN_ID
    )
    def ref_create_key(message):
        uid = message.from_user.id
        key = message.text.strip()

        referrals.update_one(
            {"key": key}, {"$set": {"key": key, "count": 0}}, upsert=True
        )

        username = bot.get_me().username
        bot.reply_to(
            message,
            "Sizning referal havolangiz tayyor:\n\n"
            f"<code>https://t.me/{username}?start={key}</code>",
        )

        admin_state.pop(uid, None)

    @bot.message_handler(
        func=lambda m: admin_state.get(m.from_user.id) == "ref_wait_delete"
        and m.from_user.id == ADMIN_ID
    )
    def ref_delete_key(message):
        uid = message.from_user.id
        text = message.text.strip()

        if "start=" in text:
            key = text.split("start=")[1]
        else:
            key = text

        result = referrals.delete_one({"key": key})

        if result.deleted_count == 0:
            bot.reply_to(message, "❌ Bunday referal topilmadi.")
        else:
            bot.reply_to(message, "✅ Referal o‘chirildi.")

        admin_state.pop(uid, None)

    # ==== AVTO O‘CHIRISH VAQTI ====

    @bot.message_handler(
        func=lambda m: admin_state.get(m.from_user.id) == "wait_auto_time"
        and m.from_user.id == ADMIN_ID
    )
    def set_auto_time(message):
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

        settings.update_one(
            {"key": "auto_delete"},
            {"$set": {"time": total_seconds}},
            upsert=True,
        )

        bot.reply_to(message, f"✅ Avto o‘chirish faollashtirildi: {text}")
        admin_state.pop(uid, None)

    # ==== HABAR YUBORISH MATNI ====

    @bot.message_handler(
        func=lambda m: admin_state.get(m.from_user.id) == "wait_broadcast_text"
        and m.from_user.id == ADMIN_ID
    )
    def broadcast_text(message):
        uid = message.from_user.id

        broadcast.insert_one(
            {"admin_id": uid, "text": message.text, "buttons": []}
        )

        admin_state[uid] = "broadcast_menu"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Tugma qo‘shish", callback_data="add_btn"))
        markup.add(
            InlineKeyboardButton("👁 Ko‘rish", callback_data="preview"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_broadcast"),
            InlineKeyboardButton("📨 Yuborish", callback_data="do_broadcast"),
        )

        bot.reply_to(
            message,
            "Habar saqlandi. Endi tugmalarni qo‘shishingiz mumkin:",
            reply_markup=markup,
        )

    @bot.message_handler(
        func=lambda m: admin_state.get(m.from_user.id) == "wait_btn_name"
        and m.from_user.id == ADMIN_ID
    )
    def btn_name(message):
        uid = message.from_user.id
        admin_data[uid] = {"btn_name": message.text}
        admin_state[uid] = "wait_btn_url"
        bot.reply_to(message, "Endi tugma uchun URL yuboring:")

    @bot.message_handler(
        func=lambda m: admin_state.get(m.from_user.id) == "wait_btn_url"
        and m.from_user.id == ADMIN_ID
    )
    def btn_url(message):
        uid = message.from_user.id
        name = admin_data[uid]["btn_name"]
        url = message.text.strip()

        broadcast.update_one(
            {"admin_id": uid},
            {"$push": {"buttons": {"name": name, "url": url}}},
        )

        admin_state[uid] = "broadcast_menu"

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("➕ Tugma qo‘shish", callback_data="add_btn"))
        markup.add(
            InlineKeyboardButton("👁 Ko‘rish", callback_data="preview"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_broadcast"),
            InlineKeyboardButton("📨 Yuborish", callback_data="do_broadcast"),
        )

        bot.reply_to(
            message, f"✅ Tugma qo‘shildi: {name}", reply_markup=markup
        )


def start_required_add(call):
    uid = call.from_user.id
    admin_state[uid] = "req_wait_post_link"
    admin_data[uid] = {}

    bot.edit_message_text(
        "➕ Majburiy kanal qo‘shish boshlandi.\n\n"
        "📌 Iltimos kanal ichidagi istalgan POST HAVOLASINI yuboring.",
        call.message.chat.id,
        call.message.message_id,
    )


def start_optional_add(call):
    uid = call.from_user.id
    admin_state[uid] = "opt_wait_link"
    admin_data[uid] = {}

    bot.edit_message_text(
        "➕ Ixtiyoriy kanal qo‘shish.\n\n"
        "🔗 Kanal havolasini yuboring:",
        call.message.chat.id,
        call.message.message_id,
    )


def show_required_list(call):
    channels = list(required_channels.find({}))

    if not channels:
        bot.answer_callback_query(
            call.id, "Majburiy kanallar yo‘q.", show_alert=True
        )
        return

    text = "<b>📋 Majburiy kanallar:</b>\n\n"
    for ch in channels:
        text += f"• {ch['name']} — {ch['url']}\n"

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)


def show_optional_list(call):
    channels = list(optional_channels.find({}))

    if not channels:
        bot.answer_callback_query(
            call.id, "Ixtiyoriy kanallar yo‘q.", show_alert=True
        )
        return

    text = "<b>📋 Ixtiyoriy kanallar:</b>\n\n"
    for ch in channels:
        text += f"• {ch['name']} — {ch['url']}\n"

    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
