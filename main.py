import os
import time
import ccxt
import requests
from flask import Flask, request
from dotenv import load_dotenv

# Загрузка .env
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Инициализация Flask
app = Flask(__name__)

# Инициализация MEXC
exchange = ccxt.mexc({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True
})

# Глобальные флаги
is_searching = {}
last_start_time = {}

# Настройки фильтра
MIN_VOLUME_USDT = 10_000
MAX_VOLUME_USDT = 1_000_000
MIN_SPREAD_PERCENT = 0.5

# Функция отправки сообщений
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"[Telegram] Ошибка при отправке: {e}")

# Фильтр по монетам
def scan_spread_opportunities(limit=10):
    result = []
    try:
        markets = exchange.load_markets()
    except Exception as e:
        print(f"[MEXC] Ошибка загрузки рынков: {e}")
        return result

    for symbol in markets:
        if not symbol.endswith("/USDT"):
            continue

        try:
            orderbook = exchange.fetch_order_book(symbol)
            ticker = exchange.fetch_ticker(symbol)
        except Exception:
            continue

        if not orderbook['bids'] or not orderbook['asks']:
            continue

        best_bid = orderbook['bids'][0][0]
        best_ask = orderbook['asks'][0][0]
        mid_price = (best_bid + best_ask) / 2
        spread = (best_ask - best_bid) / mid_price * 100
        volume = ticker.get('quoteVolume', 0)

        if (
            spread >= MIN_SPREAD_PERCENT and
            MIN_VOLUME_USDT <= volume <= MAX_VOLUME_USDT
        ):
            result.append(f"{symbol} | Spread: {spread:.2f}% | Volume: {volume:.0f}")
            if len(result) >= limit:
                break
    return result

# Webhook обработчик
@app.route('/webhook', methods=["POST"])
def webhook():
    data = request.get_json()

    if "message" not in data:
        return "ok"

    message = data["message"]
    chat_id = message["chat"]["id"]
    text = message.get("text", "")
    user_id = str(chat_id)

    print(f"[Telegram] Получено сообщение: {text} от {chat_id}")

    # Проверка на команду /start
    if text == "/start":
        now = time.time()

        if is_searching.get(user_id, False):
            send_message(chat_id, "⏳ Подождите, поиск уже идёт...")
            return "ok"

        if user_id in last_start_time and now - last_start_time[user_id] < 120:
            send_message(chat_id, "❗ Вы можете повторно начать поиск только через 2 минуты.")
            return "ok"

        is_searching[user_id] = True
        last_start_time[user_id] = now
        send_message(chat_id, "🔍 Начинаю поиск монет...")

        results = scan_spread_opportunities()

        if results:
            for line in results:
                send_message(chat_id, line)
        else:
            send_message(chat_id, "😔 Подходящих монет не найдено.")

        is_searching[user_id] = False
        return "ok"

    # Обработка /stop
    if text == "/stop":
        if is_searching.get(user_id, False):
            is_searching[user_id] = False
            send_message(chat_id, "⛔ Поиск остановлен.")
        else:
            send_message(chat_id, "🚫 Сейчас ничего не ищу.")
        return "ok"

    return "ok"

# Запуск Flask
if __name__ == "__main__":
    app.run(port=8000)
