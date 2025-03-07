import os
from api.VK_API import VkAPI
import os
import torch
from app import get_embedding_list
from io import BytesIO
from PIL import Image
from aiogram import types, F
from logger import logger
import httpx
from facenet.facenet_module import FaceNet
from app import crop_face

face_net = FaceNet()
# Импорт асинхронного CRUD и сессии
from db.engine import AsyncSessionLocal
from db.cruds.cruds import create_photo
from db.search_engine import search_face

face_net = FaceNet()

async def vk_import():
    logger.info("Команда /vk_import получена. Импорт фотографий из VK и распознавание лиц.")
    token = os.getenv("VK_ACCESS_TOKEN")
    owner_id = os.getenv("OWNER_ID")
    if not token or not owner_id:
        logger.error("Проверьте, что заданы VK_ACCESS_TOKEN, OWNER_ID.")
        return
    try:
        owner_id = int(owner_id)
    except ValueError:
        logger.error("OWNER_ID и ALBUM_ID должны быть числами.")
        return

    vk_api = VkAPI()
    album_list = await vk_api.album_get(token, owner_id)
    album_list = album_list[:2]
    count=0
    for item in album_list:
        count=+1
        try:
            photo_urls = await vk_api.photos_get(token, owner_id, item)
        except Exception as e:
            logger.error("Ошибка при получении фотографий из VK", exc_info=True)
            return

        if not photo_urls:
            logger.info("Фотографии не найдены в указанном альбоме.")
            return

        imported_count = 0
        async with AsyncSessionLocal() as session:
            for url in photo_urls:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(url, timeout=10)
                    if response.status_code != 200:
                        logger.error(f"Ошибка загрузки фото по URL: {url}")
                        continue
                    image_data = BytesIO(response.content)
                    image = Image.open(image_data)
                    boxes = face_net.detect_faces(image)
                    if not boxes:
                        logger.info(f"Лицо не обнаружено на фото: {url}")
                        continue
                    face_img = crop_face(image, boxes[0])
                    embedding = face_net.extract_embeddings(face_img)
                    if isinstance(embedding, torch.Tensor):
                        logger.info(f"Эмбеддинг для фото {url}: тип {type(embedding)}, shape: {embedding.shape}")
                    else:
                        logger.info(f"Эмбеддинг для фото {url}: тип {type(embedding)}")
                    embedding_list = embedding[0].cpu().numpy().tolist()
                    if embedding_list is None:
                        logger.error(f"Ошибка преобразования эмбеддинга для фото {url}")
                        continue
                    photo_id = await create_photo(session, url, embedding_list)
                    await session.commit()
                    imported_count += 1
                except Exception as e:
                    logger.error(f"Ошибка обработки фото {url}: {e}", exc_info=True)
                    await session.rollback()
        logger.info(f"Импорт завершен. Загружено {imported_count} фотографий. {count}")

    
