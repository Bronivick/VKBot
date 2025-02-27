"""
Модуль async_crud.py

Асинхронные функции для операций CRUD над моделью Photo.
"""
from sqlalchemy.dialects.postgresql import array
from logger import logger
from db.models.models import Photo 
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

async def create_photo(session, url, embedding_list: list[float]):
    logger.info("Проверяем существование записи Photo с URL: %s", url)
    try:
        # Проверка на существование записи с таким же URL
        result = await session.execute(select(Photo).where(Photo.url == url))
        existing_photo = result.scalars().first()

        if existing_photo:
            logger.info("Запись с таким URL уже существует, ID: %s", existing_photo.id)
            return existing_photo.id

        # Если записи нет, создаём новую
        logger.info("Создаем новую запись Photo с URL: %s", url)
        photo = Photo(url=url, embedding=embedding_list)
        session.add(photo)

        await session.flush()
        logger.info("Запись успешно создана с ID: %s", photo.id)
        return photo.id

    except IntegrityError as e:
        logger.error("Нарушение уникальности URL при создании Photo: %s", e, exc_info=True)
        await session.rollback()
        raise e
    except Exception as e:
        logger.error("Ошибка при создании записи Photo: %s", e, exc_info=True)
        await session.rollback()
        raise e
