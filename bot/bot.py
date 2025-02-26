import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from db.engine import init_db
from handlers.comands import register_handlers
from vk_parser import vk_import  # Предполагается, что это async def
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в переменных окружения!")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(bot=bot)  # Лучше явно указать bot при создании Dispatcher

async def setup_bot():
    print("[*] Инициализация базы данных...")
    await init_db()

    print("[*] Регистрация хендлеров...")
    register_handlers(dp)

    print("[*] Ожидание 15 секунд...")
    await asyncio.sleep(15)  # Используем неблокирующий sleep

    print("[*] Импорт фотографий из ВК...")
    await vk_import()  # Предполагается, что vk_import тоже async

    print("[✅] Настройка бота завершена.")

async def start_bot():
    await setup_bot()  # Используем await
    print("[🚀] Бот запущен и ожидает события.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        print("[❌] Бот остановлен.")
