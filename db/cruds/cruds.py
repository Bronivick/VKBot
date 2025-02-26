from sqlalchemy.dialects.postgresql import array
from logger import logger
from db.models.models import Photo  # убедитесь, что импортируете вашу модель Photo

async def create_photo(session, url, embedding_list: list[float]):
    logger.info("Создаем новую запись Photo с URL: %s", url)
    photo = Photo(url=url, embedding=embedding_list)
    session.add(photo)
    try:
        await session.flush()
        logger.info("Запись успешно создана с ID: %s", photo.id)
    except Exception as e:
        logger.error("Ошибка при создании записи Photo: %s", e, exc_info=True)
        await session.rollback()
        raise e
    return photo.id

