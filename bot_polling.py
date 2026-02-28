import telebot

TOKEN = "7734132869:AAEAs3HOC8K5uVJ_GmKCysMpwJHvrt2KlDs"
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Salom! Bot polling orqali ishlayapti 😊")

bot.infinity_polling()
