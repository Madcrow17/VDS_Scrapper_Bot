import multiprocessing
import uvicorn
import pandas as pd
from fastapi import FastAPI
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
from telegram import BotCommand
import asyncio
import csv
import re

API_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN" # токен телеграм бота
CSV_PATH = "/opt/VDS_Scrapper/guns_data_308.csv"  # путь к CSV с 3 колонками

app = FastAPI()
application = Application.builder().token(API_TOKEN).build()

#Функция, которая подгружает базу данных
def load_csv():
    return pd.read_csv(CSV_PATH)

#Функция для вывода подсказок при написании команд
async def set_bot_commands():
    commands = [
        BotCommand("start", "Выводит приветственную информацию и описание бота"),
        BotCommand("help", "Выводит список доступных команд с описанием"),
        BotCommand("top", "Показывает первые N позиций, количество указывается пользователем, по умолчанию 20"),
        BotCommand("row", "Показывает конкретную строку по ее номеру"),
        BotCommand("col", "Показывает столбец по его имени"),
	BotCommand("search", "Осуществялет поиск по названиям по ключевому слову"),
	BotCommand("today", "Выводит все объявления, опубликованные сегодня"),
	BotCommand("count_pos", "Выводит общее количество позиций в базе"),
	BotCommand("price", "Выводит весь список, отсортированный по цене от меньшей к большей")
    ]
    await application.bot.set_my_commands(commands)

#Функция выводит приветственную информацию при написании команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот для работы с базой данных объявлений (охотничье нарезное оружие в калибре .308Win) с сайта guns-broker.ru. База данных содержит три колонки с данными (Порядковый номер / Название объявления / Цена / Дата публикации / Ссылка на объявление / Локация). База обновляется каждые 2 часа\n\n"
        "Вот что я умею:\n"
	"1. Вывести N первых объявлений, по умолчанию 20 объявлений\n"
	"2. Вывести конкретную строку\n"
	"3. Вывести конкретный столбец\n"
	"4. Поиск по ключевому слову в названии\n"
	"5. Вывод всех сегодняшних объявлений\n"
	"6. Вывод общего количества позиций в базе\n"
	"7. Вывод всего списка, отсортированного по цене от меньшего к большему\n"
)

#Функция выводит список доступных команд /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "Список доступных команд:\n"
        	"/start — показать описание бота\n"
        	"/help — показать список доступных команд с их синтаксисом\n"
        	"/top <число>— показать первые N позиций из базы, по умолчанию 20\n"
        	"/row <номер> — показать строку под указанным номером. Например, /row 5\n"
        	"/col <имя_столбца> — показать данные столбца по названию. Например, /col position/title/price/date/link/location\n"
		"/search <Ключевое слово/а> — осуществляет поиск объявлений по ключевому слову (из названия)\n"
		"/today — выводит все объявления, опубликованные сегодня\n"
		"/count_pos — выводит общее количество позиций в базе\n"
		"/price — выводит весь список, отсортированный по цене от меньшего к большему\n"
    )
    await update.message.reply_text(help_text)

#Функция, разбивающая вывод на подсообщения длиной не более 4000 символов
async def send_long_message(update, text, chunk_size=4000):
    # Разбиваем текст на части длиной не более chunk_size, пытаясь разрывать по логичным точкам (двойной перевод строки)
    start = 0
    text_length = len(text)
    while start < text_length:
        end = start + chunk_size
        if end < text_length:
            # Ищем последний двойной перенос строки до end, чтобы не разрывать запись
            end = text.rfind('\n\n', start, end)
            if end == -1 or end <= start:
                end = start + chunk_size  # на случай, если переносов нет или они слишком далеко
        else:
            end = text_length

        part = text[start:end].strip()
        if part:
            await update.message.reply_text(part, parse_mode='HTML')
            await asyncio.sleep(0.3)  # Пауза, чтобы избежать ограничения Telegram
        start = end

#Функция, которая выводит первые N объявлений, по умолчанию - 20
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(context.args[0])
        if count <= 0:
            raise ValueError
    except (IndexError, ValueError):
        count = 20

    df = load_csv()
    df_slice = df.head(count)
    columns = ['position', 'title', 'price', 'date', 'location', 'link']
    lines = []

    for _, row in df_slice.iterrows():
        cell_text = []
        cell_text.append(f"<b>№ {row['position']}</b>")  # номер позиции из CSV
        cell_text.append(f"<b>Название</b>: {row['title']}")
        cell_text.append(f"<b>Цена</b>: {row['price']}")
        cell_text.append(f"<b>Дата</b>: {row['date']}")
        cell_text.append(f"<b>Местоположение</b>: {row['location']}")
        cell_text.append(f"<b>Ссылка</b>: {row['link']}")
        lines.append("\n".join(cell_text))

    text = "\n\n\n".join(lines)
    await send_long_message(update, f"Первые {count} позиций из базы:\n\n{text}")


#Функция, которая выводит конкретный столбец из базы (по его названию)
async def col(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        requested_col = context.args[0].strip().lower()
    except IndexError:
        await update.message.reply_text("Ошибка! Укажите имя столбца. Например: /col title")
        return

    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = [h.lower() for h in reader.fieldnames]

        if requested_col not in headers:
            await update.message.reply_text(
                f"Столбец \"{requested_col}\" не найден.\n"
                f"Доступные столбцы: {', '.join(headers)}"
            )
            return

        result_texts = []
        for line_num, row in enumerate(reader, start=1):
            value = row.get(requested_col, "")
            result_texts.append(f"<b>№ {line_num}</b>\n{value}")

    text = "\n\n".join(result_texts)
    await send_long_message(update, f"Данные столбца \"{requested_col}\":\n\n{text}")

#Функция, которая выводит конкретную строку из базы (по ее номеру)
async def row(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        requested_idx = int(context.args[0])
        if requested_idx < 1:
            raise IndexError
    except (ValueError, IndexError):
        await update.message.reply_text("Ошибка! Используйте /row <номер_строки> (число от 1 и выше)")
        return

    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        target_row = None
        for line_num, row in enumerate(reader, start=1):
            if line_num == requested_idx:
                target_row = row
                break

    if not target_row:
        await update.message.reply_text(f"Строка с номером {requested_idx} не найдена.")
        return

    col_names = {
        'position': '№',
        'title': 'Название',
        'price': 'Цена',
        'date': 'Дата',
        'location': 'Местоположение',
        'link': 'Ссылка'
    }

    cell_text = []
    for key, rus_name in col_names.items():
        value = target_row.get(key, "")
        cell_text.append(f"<b>{rus_name}</b>: {value}")

    text = "\n".join(cell_text)
    await update.message.reply_text(text, parse_mode='HTML')

#Функция, осуществляющая поиск по колонке title и выводящая строки где есть совпадение
async def search_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = context.args[0].strip().lower()
    except IndexError:
        await update.message.reply_text("Ошибка! Укажите слово для поиска. Например: /search title")
        return

    matched_rows = []
    matched_line_nums = []

    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'title' in row and query in row['title'].lower():
                matched_rows.append(row)
                matched_line_nums.append(row.get('position', 'N/A'))

    if not matched_rows:
        await update.message.reply_text(f"Совпадений с \"{query}\" не найдено.")
        return

    result_texts = []
    for row in matched_rows:
        cell_text = []
        cell_text.append(f"<b>№ {row.get('position', 'N/A')}</b>")
        cell_text.append(f"<b>Название</b>: {row.get('title', '')}")
        cell_text.append(f"<b>Цена</b>: {row.get('price', '')}")
        cell_text.append(f"<b>Дата</b>: {row.get('date', '')}")
        cell_text.append(f"<b>Местоположение</b>: {row.get('location', '')}")
        cell_text.append(f"<b>Ссылка</b>: {row.get('link', '')}")
        result_texts.append("\n".join(cell_text))

    text = "\n\n\n".join(result_texts)
    await send_long_message(update, f"Результаты поиска по слову '{query}':\n\n{text}")

#Функция, которая выводит все объявления, опубликованные сегодня
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if 'date' not in reader.fieldnames:
            await update.message.reply_text("В CSV нет столбца 'date'")
            return
        matched_rows = []
        for row in reader:
            row_date = row.get('date', '').lower()
            if 'сегодня' in row_date:
                matched_rows.append(row)

    if not matched_rows:
        await update.message.reply_text("Сегодняшних объявлений нет.")
        return

    col_names = {
        'position': '№',
        'title': 'Название',
        'price': 'Цена',
        'date': 'Дата',
        'location': 'Местоположение',
        'link': 'Ссылка'
    }

    result_texts = []
    for row in matched_rows:
        cell_text = []
        for key, rus_name in col_names.items():
            value = row.get(key, "")
            cell_text.append(f"<b>{rus_name}</b>: {value}")
        result_texts.append("\n".join(cell_text))

    text = "\n\n\n".join(result_texts)
    await send_long_message(update, f"Сегодняшние объявления:\n\n{text}")

#Функция, считающая общее количество позиций в базе
async def count_pos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        row_count = sum(1 for _ in reader)  # считаем количество строк данных

    await update.message.reply_text(
        f"Всего позиций в базе: <b>{row_count}</b>",
        parse_mode='HTML'
    )

#Функция сортировки по цене от меньшей к большей
async def sort_by_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        if not headers or "price" not in [h.lower() for h in headers]:
            await update.message.reply_text("В CSV нет столбца 'price'")
            return

        rows = list(reader)

    def parse_price(price_str):
        if not isinstance(price_str, str):
            return float('inf')
        cleaned = re.sub(r"[^\d.,]", "", price_str)
        cleaned = cleaned.replace(",", ".").replace(" ", "")
        try:
            return float(cleaned)
        except ValueError:
            return float('inf')

    sorted_rows = sorted(rows, key=lambda r: parse_price(r.get('price', '')))

    col_names = {
        'position': '№',
        'title': 'Название',
        'price': 'Цена',
        'date': 'Дата',
        'location': 'Местоположение',
        'link': 'Ссылка'
    }

    result_texts = []
    for row in sorted_rows:
        cell_text = []
        for key, rus_name in col_names.items():
            value = row.get(key, "")
            cell_text.append(f"<b>{rus_name}</b>: {value}")
        result_texts.append("\n".join(cell_text))

    text = "\n\n\n".join(result_texts)

    if not text.strip():
        await update.message.reply_text("Нет данных для отображения после сортировки.")
        return

    await send_long_message(update, f"Позиции, отсортированные по цене:\n\n{text}")

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("top", top))
application.add_handler(CommandHandler("row", row))
application.add_handler(CommandHandler("col", col))
application.add_handler(CommandHandler("search", search_title))
application.add_handler(CommandHandler("today", today))
application.add_handler(CommandHandler("count_pos", count_pos))
application.add_handler(CommandHandler("price", sort_by_price))

#Функция запуска бота
def run_bot():

    application.run_polling()

#Инициализация
if __name__ == "__main__":
    multiprocessing.set_start_method("spawn")

    asyncio.run(set_bot_commands())

    bot_process = multiprocessing.Process(target=run_bot)
    bot_process.start()

    uvicorn.run(app, host="0.0.0.0", port=8000)
