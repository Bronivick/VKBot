import os
import asyncio
import httpx
import torch
from io import BytesIO
from PIL import Image
from aiogram import types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from logger import logger
from facenet.facenet_module import FaceNet

# Импорт асинхронного CRUD и сессии
from db.engine import AsyncSessionLocal
from db.cruds.cruds import create_photo
from db.search_engine import search_face

# Импорт асинхронного VK API
from api.VK_API import VkAPI

# Инициализация FaceNet (если он синхронный, его можно оставить таким же)
face_net = FaceNet()

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

async def photo_handler(message: types.Message):
    logger.info("Получено фото")
    photo_obj = message.photo[-1]
    bot = message.bot
    file = await bot.get_file(photo_obj.file_id)
    file_content = await bot.download_file(file.file_path)
    file_buffer = file_content if hasattr(file_content, "read") else BytesIO(file_content)

    try:
        image = Image.open(file_buffer)
    except Exception as e:
        logger.error(f"Ошибка открытия изображения: {e}")
        await message.answer("Не удалось открыть изображение. Проверь формат.")
        return

    boxes = face_net.detect_faces(image)
    if not boxes:
        logger.warning("Лицо не обнаружено")
        await message.answer("Лицо не обнаружено. Попробуй другое фото.")
        return
    if len(boxes) > 1:
        logger.warning("Обнаружено несколько лиц")
        await message.answer("Обнаружено несколько лиц. Пришли фото с одним лицом.")
        return

    face_image = crop_face(image, boxes[0])
    embedding = face_net.extract_embeddings(face_image)
    logger.info(f"embedding shape: {embedding.shape}, embedding type: {type(embedding)}")




    async with AsyncSessionLocal() as session:
        matches = await search_face(embedding, session)

    if not matches:
        logger.info("Совпадений не найдено")
        await message.answer("Совпадений не найдено.")
        return

    html_content = "<html><body><h2>Найденные совпадения</h2><ul>"
    for match_photo, dist in matches:
        html_content += f'<li><a href="{match_photo.url}">{match_photo.url}</a> (расстояние: {dist:.2f})</li>'
    html_content += "</ul></body></html>"
    html_bytes = html_content.encode('utf-8')
    html_file = FSInputFile(BytesIO(html_bytes), filename="results.html")
    await message.answer_document(html_file, caption="Найденные совпадения")


async def vk_albums_handler(message: types.Message):
    logger.info("Получена команда /vk_albums")
    token = os.getenv("VK_ACCESS_TOKEN")
    owner_id = os.getenv("OWNER_ID")
    if not token or not owner_id:
        await message.answer("Не заданы VK_ACCESS_TOKEN или OWNER_ID.")
        return
    try:
        owner_id = int(owner_id)
    except ValueError:
        await message.answer("OWNER_ID должен быть числом.")
        return

    vk_api = VkAPI()
    try:
        albums = await vk_api.album_get(token, owner_id)
    except Exception as e:
        logger.error("Ошибка при получении альбомов", exc_info=True)
        await message.answer(f"Ошибка при получении альбомов: {e}")
        return

    if not albums:
        await message.answer("Альбомы не найдены.")
    else:
        album_list = "\n".join(str(a) for a in albums)
        # Если сообщение слишком длинное, можно отправить его как файл
        if len(album_list) > 4000:
            bio = BytesIO(album_list.encode('utf-8'))
            bio.seek(0)
            await message.answer_document(
                FSInputFile(bio, filename="albums.txt"),
                caption="Найденные альбомы (см. файл)"
            )
        else:
            await message.answer(f"Найденные альбомы:\n{album_list}")

async def vk_photos_handler(message: types.Message):
    logger.info("Получена команда /vk_photos")
    token = os.getenv("VK_ACCESS_TOKEN")
    owner_id = os.getenv("OWNER_ID")
    album_id = os.getenv("ALBUM_ID")
    if not token or not owner_id or not album_id:
        await message.answer("Проверьте, что заданы VK_ACCESS_TOKEN, OWNER_ID и ALBUM_ID.")
        return
    try:
        owner_id = int(owner_id)
        album_id = int(album_id)
    except ValueError:
        await message.answer("OWNER_ID и ALBUM_ID должны быть числами.")
        return

    vk_api = VkAPI()
    try:
        photos = await vk_api.photos_get(token, owner_id, album_id)
    except Exception as e:
        logger.error("Ошибка при получении фотографий", exc_info=True)
        await message.answer(f"Ошибка при получении фотографий: {e}")
        return

    if not photos:
        await message.answer("Фотографии не найдены.")
    else:
        photo_list = "\n".join(photos)
        if len(photo_list) > 4000:
            bio = BytesIO(photo_list.encode('utf-8'))
            bio.seek(0)
            await message.answer_document(
                FSInputFile(bio, filename="photos.txt"),
                caption="Найденные фото (см. файл)"
            )
        else:
            await message.answer(f"Найденные фото:\n{photo_list}")

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
    dp.message.register(photo_handler, F.photo)
    dp.message.register(text_handler, F.text & ~F.text.startswith("/"))
    dp.errors.register(error_handler)
    dp.message.register(vk_photos_handler, Command("vk_photos"))
    dp.message.register(vk_albums_handler, Command("vk_albums"))
