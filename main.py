import telebot
from telebot import TeleBot
from config import BOT_TOKEN, KEEP_ALIVE_URL
from handlers import register_handlers
from subscription import register_subscription, register_check_handler
from admin_panel import register_admin_panel
from security import register_security
import threading
import time
import requests


# ==========================
#   KEEP ALIVE (Render Free)
# ==========================
def keep_alive():
    if not KEEP_ALIVE_URL:
        return

    def ping():
        while True:
            try:
                requests.get(KEEP_ALIVE_URL)
            except:
                pass
            time.sleep(60)

    thread = threading.Thread(target=ping, daemon=True)
    thread.start()


# ==========================
#   BOT START
# ==========================
bot = TeleBot(BOT_TOKEN, parse_mode="HTML")


def main():
    # Keep Alive ishga tushiramiz
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
