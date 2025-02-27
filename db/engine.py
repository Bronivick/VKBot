"""
Модуль async_engine.py

Создаёт асинхронный движок SQLAlchemy и предоставляет фабрику асинхронных сессий.

Переменная окружения:
    DATABASE_URL: строка подключения к базе данных, например:
        "postgresql+asyncpg://username:password@db:5432/vkfaces"
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from logger import logger

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://username:password@db:5432/vkfaces")

if DATABASE_URL is None:
    raise ValueError("Переменная окружения DATABASE_URL не задана!")
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    from db.models.models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created (if not exist).")

