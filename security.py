import time
import threading
from telebot import TeleBot
from database import required_channels
from config import ADMIN_ID

bot: TeleBot = None


# ==========================
#   SECURITY MODULE INIT
# ==========================
def register_security(bot_instance: TeleBot):
    global bot
    bot = bot_instance

    # Fon jarayonni ishga tushiramiz
    thread = threading.Thread(target=security_check, daemon=True)
    thread.start()


# ==========================
#   BOT ADMIN EMAS BO‘LSA → KANALNI O‘CHIRISH
# ==========================
def security_check():
    while True:
        try:
            channels = list(required_channels.find({}))

            for ch in channels:
                channel_id = ch["channel_id"]

                try:
                    member = bot.get_chat_member(channel_id, bot.get_me().id)

                    # Bot admin bo‘lsa → davom
                    if member.status in ["administrator", "creator"]:
                        continue

                    # Bot admin emas → kanalni o‘chirib tashlaymiz
                    required_channels.delete_one({"_id": ch["_id"]})

                    bot.send_message(
                        ADMIN_ID,
                        f"⚠️ <b>{ch['name']}</b> kanalidan chiqarildim.\n"
                        f"Kanal majburiy ro‘yxatdan o‘chirildi.\n\n"
                        f"Iltimos meni yana admin qiling."
                    )

                except:
                    # Kanalga ulanib bo‘lmasa ham o‘chiramiz
                    required_channels.delete_one({"_id": ch["_id"]})

                    bot.send_message(
                        ADMIN_ID,
                        f"⚠️ <b>{ch['name']}</b> kanaliga ulanib bo‘lmadi.\n"
                        f"Kanal majburiy ro‘yxatdan o‘chirildi."
                    )

        except Exception as e:
            print("Security error:", e)

        time.sleep(20)  # har 20 soniyada tekshiradi
