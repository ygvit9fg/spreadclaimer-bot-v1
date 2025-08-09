from flask import Flask, request
import telebot
import os

API_TOKEN = '8498360203:AAH2fBwPUxQz54RhOGObiNz9OMZ_hv-afr4'

bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id, "Привет! Я готов искать монеты 🔍")

@app.route('/' + API_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'ok'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
