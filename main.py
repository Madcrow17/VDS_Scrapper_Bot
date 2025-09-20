from contextlib import asynccontextmanager
from http import HTTPStatus

from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

API_TOKEN = "7489579759:AAHj0phmAr37wvE7EmRx6VNce2WkIrrGVq0"
WEBHOOK_URL = "http://94.183.234.155/"  # Ваш публичный URL для webhook

# Инициализация бота и приложения
application = (
    Application.builder()
    .token(API_TOKEN)
    .build()
)

# Async context manager для lifecycle FastAPI + PTB
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Установка webhook при старте
    await application.bot.set_webhook(WEBHOOK_URL)
    # Запуск приложения python-telegram-bot
    await application.start()
    yield
    # Остановка приложения
    await application.stop()

app = FastAPI(lifespan=lifespan)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот на FastAPI и python-telegram-bot v20+")

application.add_handler(CommandHandler("start", start))

# Точка входа webhook
@app.post("/webhook")
async def telegram_webhook(request: Request):
    json_data = await request.json()
    update = Update.de_json(json_data, application.bot)
    await application.process_update(update)
    return Response(status_code=HTTPStatus.OK)
