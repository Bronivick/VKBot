import os
import asyncio
import httpx
import torch
from io import BytesIO
from PIL import Image
from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from logger import logger
from facenet.facenet_module import FaceNet
import logging
from db.engine import AsyncSessionLocal
from db.cruds.cruds import create_photo
from db.search_engine import search_face
# Импорт асинхронного VK API
from api.VK_API import VkAPI

# Инициализация FaceNet (если он синхронный, его можно оставить таким же)
face_net = FaceNet()
logger = logging.getLogger(__name__)
router = Router()


def crop_face(image, box):
    """Вырезает лицо из изображения по координатам."""
    left, top, right, bottom = box
    return image.crop((left, top, right, bottom))


def get_embedding_list(embeddings):
    
    """
    Преобразует эмбеддинг, полученный из face_net.extract_embeddings, в список чисел.
    Гарантируется, что если embeddings – тензор, его форма [1, D].
    Если embeddings не тензор (например, float), оборачивает его в список.
    """
    if isinstance(embeddings, torch.Tensor):
        # Если форма не [1, D] – берем первый вектор, иначе работаем напрямую.
        embedding_tensor = embeddings[0] if embeddings.ndim > 1 else embeddings
        try:
            np_emb = embedding_tensor.cpu().detach().numpy()
            # Если np_emb — скаляр (его shape равен ()), оборачиваем в список
            if np_emb.shape == ():
                return [np_emb.item()]
            else:
                return np_emb.tolist()
        except Exception as e:
            logger.error(f"Ошибка при преобразовании эмбеддинга: {e}")
            return None
    else:
        return [embeddings]
    
    
@router.message(F.photo)
async def photo_message_handler(message: types.Message):
    logger.info("Получено фото")
    
    # Достаём файл
    photo_obj = message.photo[-1]
    bot = message.bot
    file = await bot.get_file(photo_obj.file_id)
    file_content = await bot.download_file(file.file_path)

    # Безопасно оборачиваем данные в BytesIO
    file_buffer = file_content if hasattr(file_content, "read") else BytesIO(file_content)

    # Пробуем открыть как изображение
    try:
        image = Image.open(file_buffer)
    except Exception as e:
        logger.error(f"Ошибка открытия изображения: {e}")
        await message.answer("Не удалось открыть изображение. Убедитесь, что это фото/картинка.")
        return

    # Детектируем лица
    boxes = face_net.detect_faces(image)
    if not boxes:
        logger.warning("Лицо не обнаружено")
        await message.answer("Лицо не обнаружено. Попробуйте другое фото.")
        return

    if len(boxes) > 1:
        logger.warning("Обнаружено несколько лиц")
        await message.answer("Обнаружено несколько лиц. Пришлите фото с одним лицом.")
        return

    # Вырезаем лицо, получаем эмбеддинг
    face_image = crop_face(image, boxes[0])
    embedding = face_net.extract_embeddings(face_image)
    logger.info(f"Embedding shape: {embedding.shape}, type: {type(embedding)}")

    # Ищем совпадения в БД
    async with AsyncSessionLocal() as session:
        matches = await search_face(embedding, session)

    if not matches:
        logger.info("Совпадений не найдено")
        await message.answer("Совпадений не найдено.")
        return

    # Формируем простой HTML-отчёт
    html_content = "<html><body><h2>Найденные совпадения</h2><ul>"
    for match_photo, dist in matches:
        html_content += f'<li><a href="{match_photo.url}">{match_photo.url}</a> (расстояние: {dist:.2f})</li>'
    html_content += "</ul></body></html>"

    html_bytes = html_content.encode('utf-8')
    html_file = BufferedInputFile(html_bytes, filename="results.html")
    await message.answer_document(html_file, caption="Найденные совпадения")    


# Обработчик для текстовых сообщений (если не команда и не фото)
async def text_handler(message: types.Message):
    logger.info("Получен текст, не являющийся фото")
    if message.text and message.text.startswith("/"):
        return
    await message.answer("Пожалуйста, отправь фото с одним лицом. Для справки пиши /help.")

# Глобальный обработчик ошибок
async def error_handler(update: types.Update, exception: Exception = None) -> bool:
    logger.error(f"Ошибка при обработке обновления: {update}\nОшибка: {exception}")
    return True

# Регистрация обработчиков
def register_handlers(dp):
    dp.message.register(text_handler, F.text & ~F.text.startswith("/"))
    dp.errors.register(error_handler)
    dp.message.register(photo_message_handler, F.photo)

