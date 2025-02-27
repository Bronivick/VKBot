"""
Модуль bot.py

Инициализация бота и диспетчера, регистрация обработчиков, запуск polling.
"""

import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from db.engine import init_db
from handlers.comands import register_handlers
from vk_parser import vk_import  
from app import router as photo_router
from aiogram.client.session.aiohttp import AiohttpSession


load_dotenv()


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в переменных окружения!")


session = AiohttpSession(timeout=15)
bot = Bot(token=TELEGRAM_BOT_TOKEN, session=session)
dp = Dispatcher(bot=bot)  

dp.include_router(photo_router)


async def setup_bot():
    print("[*] Инициализация базы данных...")
    await init_db()

    print("[*] Регистрация хендлеров...")
    register_handlers(dp)

    print("[*] Ожидание 15 секунд...")
    await asyncio.sleep(15)  

    print("[*] Импорт фотографий из ВК...")
    await vk_import()  

    print("[✅] Настройка бота завершена.")

async def start_bot():
    await setup_bot() 
    print("[🚀] Бот запущен и ожидает события.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        print("[❌] Бот остановлен.")
