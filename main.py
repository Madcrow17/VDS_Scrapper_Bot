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

API_TOKEN = "7489579759:AAHj0phmAr37wvE7EmRx6VNce2WkIrrGVq0" # токен телеграм бота
CSV_PATH = "/opt/VDS_Scrapper/guns_data_223.csv"  # путь к CSV с 3 колонками

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
	    BotCommand("price", "Выводит весь список, отсортированный по цене от меньшего к большему")
    ]
    await application.bot.set_my_commands(commands)

#Функция выводит приветственную информацию при написании команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот для работы с базой данных объявлений (охотничье нарезное оружие в калибре .223) с сайта guns-broker.ru. База данных содержит три колонки с данными (Название объявления / Цена / Дата публикации). База обновляется 1 раз в сутки в 3:00 АМ по МСК\n\n"
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
        	"/col <имя_столбца> — показать данные столбца по названию. Например, /col Price\n"
		"/search <Ключевое слово/а> — осуществляет поиск объявлений по ключевому слову (из названия)\n"
		"/today — выводит все объявления, опубликованные сегодня\n"
		"/count_pos — выводит общее количество позиций в базе\n"
		"/price — выводит весь список, отсортированный по цене от меньшего к большему\n"
    )
    await update.message.reply_text(help_text)

#Функция, разбивающая вывод на подсообщения длиной не более 4000 символов
async def send_long_message(update, text, chunk_size=4000):
    # Разбиваем текст на части длиной не более chunk_size
    start = 0
    text_length = len(text)
    while start < text_length:
        end = start + chunk_size
        if end < text_length:
            # Чтобы не разрывать строку, ищем последний перенос строки до end
            end = text.rfind('\n', start, end)
            if end == -1 or end <= start:
                end = start + chunk_size  # на случай, если переносов нет
        else:
            end = text_length

        part = text[start:end]
        await update.message.reply_text(part, parse_mode='html')
        await asyncio.sleep(0.3)  # небольшая пауза, чтобы избежать таймаута
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
    columns = df_slice.columns.tolist()
    lines = []


    for idx, row in df_slice.iterrows():
        # Для каждой строки создаём блок с каждой ячейкой на новой строке и пустой строкой между
        cell_text = []
        cell_text.append(f"<b>№ {idx + 1}</b>")  # добавляем номер позиции (индекс + 1 для человеческого счёта)
        for col in columns:
            cell_text.append(f"<b>{col}</b>: {row[col]}")
        lines.append("\n".join(cell_text))

    text = "\n\n\n".join(lines)
    await send_long_message(update, f"Первые {count} позиций из базы:\n\n{text}")

#Функция, которая выводит конкретный столбец из базы (по его названию)
async def col(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import csv
    try:
        requested_col = context.args[0].strip()
    except IndexError:
        await update.message.reply_text("Ошибка! Укажите имя столбца. Например: /col title")
        return

    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        if requested_col not in headers:
            await update.message.reply_text(
                f"Столбец \"{requested_col}\" не найден.\n"
                f"Доступные столбцы: {', '.join(headers)}"
            )
            return

        col_index = headers.index(requested_col)
        col_data = []
        line_nums = []

        for line_num, row in enumerate(reader, start=2):  # start=2, т.к. 1-я - заголовок
            value = row[col_index] if len(row) > col_index else ""
            col_data.append(value)
            line_nums.append(line_num - 1)  # реальный номер строки в CSV без заголовка

    result_texts = []
    for num, val in zip(line_nums, col_data):
        result_texts.append(f"<b>№ {num}</b>\n{val}")

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
        reader = csv.reader(f)
        headers = next(reader)

        # Переменная для хранения искомой строки
        target_row = None
        for line_num, row in enumerate(reader, start=2):  # start=2, так как первая - заголовок (1)
            if line_num - 1 == requested_idx:  # вычитаем 1, чтобы учесть заголовок
                target_row = row
                break

    if not target_row:
        await update.message.reply_text(f"Строка с номером {requested_idx} не найдена.")
        return

    cell_text = [f"<b>№ {requested_idx}</b>"]
    for i in range(len(headers)):
        value = target_row[i] if i < len(target_row) else ""
        cell_text.append(f"<b>{headers[i]}</b>: {value}")

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
        reader = csv.reader(f)
        headers = next(reader)
        for row in reader:
            if len(row) > 0 and query in row[0].lower():
                matched_rows.append(row)
                matched_line_nums.append(reader.line_num - 1)  # номер строки без заголовка

    if not matched_rows:
        await update.message.reply_text(f"Совпадений с \"{query}\" не найдено.")
        return

    result_texts = []
    for line_num, row in zip(matched_line_nums, matched_rows):
        cell_text = []
        cell_text.append(f"<b>№ {line_num}</b>")  # номер строки из CSV
        for i in range(len(headers)):
            value = row[i] if i < len(row) else ""
            cell_text.append(f"<b>{headers[i]}</b>: {value}")
        result_texts.append("\n".join(cell_text))

    text = "\n\n\n".join(result_texts)
    await send_long_message(update, f"Результаты поиска по слову '{query}':\n\n{text}")

#Функция, которая выводит все объявления, опубликованные сегодня
async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)
        if "date" not in headers:
            await update.message.reply_text("В CSV нет столбца 'date'")
            return
        date_index = headers.index("date")
        matched_rows = []
        matched_line_nums = []  # для хранения номеров строк

        for row in reader:
            if len(row) > date_index and "сегодня" in row[date_index].lower():
                matched_rows.append(row)
                matched_line_nums.append(reader.line_num)  # номер строки в файле

    if not matched_rows:
        await update.message.reply_text("Сегодняшних объявлений нет.")
        return

    result_texts = []
    for line_num, row in zip(matched_line_nums, matched_rows):
        cell_text = []
        cell_text.append(f"<b>№ {line_num - 1}</b>")  # номер строки в CSV файле
        for i in range(len(headers)):
            value = row[i] if i < len(row) else ""
            cell_text.append(f"<b>{headers[i]}</b>: {value}")
        result_texts.append("\n".join(cell_text))

    text = "\n\n\n".join(result_texts)
    await send_long_message(update, f"Сегодняшние объявления:\n\n{text}")

#Функция, считающая общее количество позиций в базе
async def count_pos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)  # пропускаем заголовок
        row_count = sum(1 for _ in reader)  # считаем строки данных

    await update.message.reply_text(
        f"Всего позиций в базе: <b>{row_count}</b>",
        parse_mode='HTML'
    )

#Функция сортировки по цене от меньшей к большей
async def sort_by_price(update: Update, context: ContextTypes.DEFAULT_TYPE):

    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)

        if "price" not in [h.lower() for h in headers]:
            await update.message.reply_text("В CSV нет столбца 'price'")
            return

        price_index = [h.lower() for h in headers].index("price")

        rows_with_line_nums = []
        for line_num, row in enumerate(reader, start=2):
            rows_with_line_nums.append((line_num - 1, row))

    # Функция для преобразования цены из строки в число
    def parse_price(price_str):
        if not isinstance(price_str, str):
            return float('inf')
        cleaned = re.sub(r"[^\d.,]", "", price_str)
        cleaned = cleaned.replace(",", ".").replace(" ", "")
        try:
            return float(cleaned)
        except ValueError:
            return float('inf')

    # Сортируем по цене
    rows_with_line_nums.sort(key=lambda x: parse_price(x[1][price_index]))

    # Формируем вывод
    result_texts = []
    for line_num, row in rows_with_line_nums:
        cell_text = [f"<b>№ {line_num}</b>"]
        for i in range(len(headers)):
            value = row[i] if i < len(row) else ""
            cell_text.append(f"<b>{headers[i]}</b>: {value}")
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
