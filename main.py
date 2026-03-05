import telebot
from config import BOT_TOKEN
from keep_alive import keep_alive
from handlers import register_handlers
from subscription import register_subscription, register_check_handler
from admin_panel import register_admin_panel
from security import register_security


bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")


def main():
    # Webhookni o'chiramiz (polling ishlashi uchun)
    bot.delete_webhook(drop_pending_updates=True)

    # Render Free uchun
    keep_alive()

    # Modullarni ulaymiz
    register_handlers(bot)
    register_subscription(bot)
    register_check_handler(bot)
    register_admin_panel(bot)
    register_security(bot)

    # Botni ishga tushiramiz
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()
