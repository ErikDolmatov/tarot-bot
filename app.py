import os
import asyncio
import logging
import random
import sqlite3
from datetime import datetime
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- Логування ---
logging.basicConfig(level=logging.INFO)

# --- Конфігурація ---
TOKEN = os.environ.get("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8000))
URL = os.environ.get("RENDER_EXTERNAL_URL", "https://your-app-name.onrender.com")

# --- База даних (без змін, залишаємо ту саму логіку) ---
def init_db():
    conn = sqlite3.connect('tarot_bot.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, name TEXT, birth_date TEXT, zodiac TEXT, registered_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS readings (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, question TEXT, card_name TEXT, card_image_url TEXT, prediction TEXT, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS context (user_id INTEGER PRIMARY KEY, last_question TEXT, last_card_name TEXT, last_prediction TEXT)''')
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    c = conn.cursor()
    c.execute("SELECT name, zodiac FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def save_user(user_id, name, birth_date, zodiac):
    conn = sqlite3.connect('tarot_bot.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, name, birth_date, zodiac, registered_at) VALUES (?, ?, ?, ?, ?)",
              (user_id, name, birth_date, zodiac, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def save_reading(user_id, question, card_name, card_image_url, prediction):
    conn = sqlite3.connect('tarot_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO readings (user_id, question, card_name, card_image_url, prediction, date) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, question, card_name, card_image_url, prediction, datetime.now().isoformat()))
    conn.commit()
    c.execute("INSERT OR REPLACE INTO context (user_id, last_question, last_card_name, last_prediction) VALUES (?, ?, ?, ?)",
              (user_id, question, card_name, prediction))
    conn.commit()
    conn.close()

def get_context(user_id):
    conn = sqlite3.connect('tarot_bot.db')
    c = conn.cursor()
    c.execute("SELECT last_question, last_card_name, last_prediction FROM context WHERE user_id = ?", (user_id,))
    ctx = c.fetchone()
    conn.close()
    return ctx

CARDS = [
    {"name": "Шут", "image": "https://i.imgur.com/YXk8QvI.jpeg"},
    {"name": "Маг", "image": "https://i.imgur.com/VZ7cYxT.jpeg"},
    {"name": "Верховна Жриця", "image": "https://i.imgur.com/WLpN4lM.jpeg"},
    {"name": "Імператриця", "image": "https://i.imgur.com/C6Z9xRn.jpeg"},
    {"name": "Імператор", "image": "https://i.imgur.com/oEj3XpD.jpeg"},
    {"name": "Ієрофант", "image": "https://i.imgur.com/ZGPdJNc.jpeg"},
    {"name": "Закохані", "image": "https://i.imgur.com/KYVc1sR.jpeg"},
    {"name": "Колісниця", "image": "https://i.imgur.com/mZJ3CsQ.jpeg"},
    {"name": "Сила", "image": "https://i.imgur.com/4NxVpLQ.jpeg"},
    {"name": "Відлюдник", "image": "https://i.imgur.com/3VyBctL.jpeg"},
    {"name": "Колесо Фортуни", "image": "https://i.imgur.com/bnvN3xM.jpeg"},
    {"name": "Справедливість", "image": "https://i.imgur.com/RhZc9sV.jpeg"},
    {"name": "Повішений", "image": "https://i.imgur.com/C1kFfqT.jpeg"},
    {"name": "Смерть", "image": "https://i.imgur.com/rYkzMjl.jpeg"},
    {"name": "Помірність", "image": "https://i.imgur.com/6NxVh4R.jpeg"},
    {"name": "Диявол", "image": "https://i.imgur.com/qWzXc4L.jpeg"},
    {"name": "Вежа", "image": "https://i.imgur.com/7NxVbYp.jpeg"},
    {"name": "Зірка", "image": "https://i.imgur.com/9NxVh7T.jpeg"},
    {"name": "Місяць", "image": "https://i.imgur.com/2NxVc3R.jpeg"},
    {"name": "Сонце", "image": "https://i.imgur.com/5NxVb2L.jpeg"},
    {"name": "Суд", "image": "https://i.imgur.com/8NxVh9Y.jpeg"},
    {"name": "Світ", "image": "https://i.imgur.com/0NxVc6W.jpeg"},
]

def random_card():
    return random.choice(CARDS)

def make_prediction(name, zodiac, question, card_name):
    return (f"✨ *{name}*, карта *{card_name}* відкриває таємницю.\n\nТвоє питання: _{question}_\n\nЯ бачу, для {zodiac} настає час. {card_name} каже: прислухайся до себе. Не бійся кроку.\n\n🌙 Порада: довірся інтуїції.")

# --- ОБРОБНИКИ БОТА (без змін) ---
async def start(update: Update, context):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        context.user_data['awaiting_name'] = True
        await update.message.reply_text("🃜 Вітаю! Як тебе звати?", parse_mode="Markdown")
    else:
        name, zodiac = user
        await update.message.reply_text(f"✨ З поверненням, {name}! Задай питання.", parse_mode="Markdown")

async def handle_message(update: Update, context):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if context.user_data.get('awaiting_name'):
        context.user_data['name'] = text
        context.user_data['awaiting_name'] = False
        context.user_data['awaiting_birth'] = True
        await update.message.reply_text("📅 Дату народження (наприклад: 15.05.1990)")
        return
    if context.user_data.get('awaiting_birth'):
        context.user_data['birth_date'] = text
        context.user_data['awaiting_birth'] = False
        context.user_data['awaiting_zodiac'] = True
        await update.message.reply_text("♈ Знак зодіаку? (Овен, Телець, ...)")
        return
    if context.user_data.get('awaiting_zodiac'):
        zodiac = text.capitalize()
        save_user(user_id, context.user_data['name'], context.user_data['birth_date'], zodiac)
        name = context.user_data['name']
        context.user_data.clear()
        await update.message.reply_text(f"🌟 Дякую, {name}! Тепер задай питання.", parse_mode="Markdown")
        return

    ctx = get_context(user_id)
    if ctx:
        last_q, last_card, last_pred = ctx
        await update.message.reply_text(f"🔮 Уточнення:\n\n{last_card} каже: {last_pred[:150]}… Довірся.", parse_mode="Markdown")
        return

    context.user_data['pending_question'] = text
    keyboard = [[InlineKeyboardButton("🎴 Витягнути карту", callback_data="draw_card")]]
    await update.message.reply_text(f"🃟 Твоє питання: {text}\nНатисни кнопку.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

async def draw_card_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    question = context.user_data.get('pending_question')
    if not question:
        await query.edit_message_text("❓ Напиши питання спочатку.")
        return
    user = get_user(user_id)
    if not user:
        await query.edit_message_text("Напиши /start")
        return
    name, zodiac = user
    card = random_card()
    prediction = make_prediction(name, zodiac, question, card["name"])
    save_reading(user_id, question, card["name"], card["image"], prediction)
    await query.edit_message_text(f"🔮 Твоя карта: {card['name']}", parse_mode="Markdown")
    await update.effective_message.reply_photo(photo=card["image"], caption=f"🃟 {card['name']}")
    await update.effective_message.reply_text(prediction, parse_mode="Markdown")
    context.user_data['pending_question'] = None

async def help_command(update: Update, context):
    await update.message.reply_text("/start – почати\n/help – довідка\nНапиши питання і натисни кнопку.")

# --- ОСНОВНА ФУНКЦІЯ ДЛЯ ВЕБ-ХУКА ---
async def main():
    # Ініціалізуємо базу даних
    init_db()

    # Створюємо екземпляр бота (Application)
    app = Application.builder().token(TOKEN).build()

    # Додаємо обробники
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(draw_card_callback, pattern="draw_card"))

    # Встановлюємо веб-хук
    webhook_url = f"{URL}/telegram"
    await app.bot.set_webhook(webhook_url, allowed_updates=Update.ALL_TYPES)
    logging.info(f"Webhook set to {webhook_url}")

    # Створюємо Starlette додаток
    async def telegram_webhook(request):
        try:
            # Отримуємо JSON дані з запиту
            json_data = await request.json()
            # Створюємо об'єкт Update
            update = Update.de_json(json_data, app.bot)
            # Додаємо оновлення в чергу для обробки ботом
            await app.update_queue.put(update)
            return Response()
        except Exception as e:
            logging.error(f"Error in webhook: {e}")
            return Response(status_code=500)

    async def healthcheck(request):
        return PlainTextResponse("OK")

    starlette_app = Starlette(routes=[
        Route("/telegram", telegram_webhook, methods=["POST"]),
        Route("/healthcheck", healthcheck, methods=["GET"]),
        Route("/health", healthcheck, methods=["GET"]),
    ])

    # Запускаємо веб-сервер, передаючи йому додаток Telegram
    config = uvicorn.Config(starlette_app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)

    logging.info("Starting bot web server...")
    await server.serve()

# Точка входу
if __name__ == "__main__":
    asyncio.run(main())
