# Telegram Bot и FastAPI для базы объявлений GunsBroker для калибра .223

Этот проект реализует Telegram-бота для работы с базой объявлений по охотничьему оружию и веб-сервер на FastAPI.

---

## Что делает бот

- Выводит информацию из CSV базы (название, цена, дата)  
- Поддерживает команды: /start, /help, /top, /row, /col, /search, /today, /count_pos, /price  
- Разбивает длинные сообщения на части для Telegram  
- Сортирует объявления по цене  

---

## Установка и запуск

### Требования

- Python 3.8+  
- Библиотеки из `requirements.txt` (fastapi, uvicorn, python-telegram-bot, pandas и прочее)  

### Запуск в режиме разработки

pip install -r requirements.txt
python main.py


Это запустит:

- Telegram-бот (параллельный процесс)  
- FastAPI сервер на порту 8000  

---

## Запуск в продакшн (удалённый сервер)

Рекомендуется запускать FastAPI через Uvicorn с несколькими воркерами:

uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4



Telegram-бот рекомендуется запускать отдельным процессом через systemd или supervisor.

---

## Пример systemd-сервиса для бота

Создайте файл `/etc/systemd/system/telegram_bot.service` с содержимым:



[Unit]
Description=Telegram Bot Service
After=network.target

[Service]
User=youruser
WorkingDirectory=/opt/VDS_Scrapper_Bot
Environment="PATH=/opt/VDS_Scrapper_Bot/bot_venv/bin"
ExecStart=/opt/VDS_Scrapper_Bot/bot_venv/bin/python /opt/VDS_Scrapper_Bot/main.py

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target




Запустите и добавьте автозапуск:

sudo systemctl daemon-reload  
sudo systemctl enable telegram_bot.service  
sudo systemctl start telegram_bot.service  
sudo journalctl -u telegram_bot.service -f  

text

---

## Пример systemd-сервиса для FastAPI

Создайте файл `/etc/systemd/system/fastapi.service` с содержимым:



[Unit]
Description=FastAPI Service
After=network.target

[Service]
User=youruser
WorkingDirectory=/opt/VDS_Scrapper_Bot
Environment="PATH=/opt/VDS_Scrapper_Bot/bot_venv/bin"
ExecStart=/opt/VDS_Scrapper_Bot/bot_venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target




Запустите и добавьте автозапуск:

sudo systemctl daemon-reload  
sudo systemctl enable fastapi.service  
sudo systemctl start fastapi.service  
sudo journalctl -u fastapi.service -f  
