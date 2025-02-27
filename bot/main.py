"""
Точка входа для запуска бота.
"""
import asyncio
from bot.bot import start_bot 

if __name__ == "__main__":
    asyncio.run(start_bot())