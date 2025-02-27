"""
Модуль vk_api.py

Асинхронный класс для работы с VK API с использованием httpx.
"""
from logger import logger

from time import sleep
import requests 

import asyncio
import httpx
from logger import logger


class VkAPI:
    async def exponentBackoff(self, attempt):
        delay = min(5, 1 * 2 ** attempt)
        logger.info(f"Ожидание {delay} секунд перед повторной попыткой...")
        await asyncio.sleep(delay)
    
    def _predict_data(self, token):
        predicted_data = {
            'access_token': token,
            'v': '5.199'
        }
        api = 'https://api.vk.com/method/'
        return predicted_data, api
    
    async def VKRequest(self, api: str, method: str, data: dict, attempt: int = 0):
        url = f"{api}{method}"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, data=data)
            data = resp.json()
        except Exception as e:
            logger.error("UNKNOWN ERROR", exc_info=True)
            if attempt < 5:
                await self.exponentBackoff(attempt)
                return await self.VKRequest(api=api, method=method, data=data, attempt=attempt+1)
            else:
                raise e
        if 'error' in data:
            error_code = data['error'].get('error_code')
            if error_code in (6, 9, 603):
                logger.info(f"RETRY {error_code}")
                attempt += 1
                await self.exponentBackoff(attempt)
                return await self.VKRequest(api=api, method=method, data=data, attempt=attempt)
        return data
    
    def parse_sizes(self, data: list):
        SIZES = ['s', 'm', 'x', 'o', 'p', 'q', 'r', 'y', 'z', 'w']
        max_size = data[0]
        for i in data:
            index = SIZES.index(i.get('type'))
            if index > SIZES.index(max_size.get('type')):
                max_size = i
        return max_size.get('url')
    
    async def photos_get(self, token, owner_id, album_id):
        _post_data, api = self._predict_data(token)
        method = 'photos.get'
        _post_data['owner_id'] = -owner_id  # Отрицательный ID для сообществ
        _post_data['album_id'] = album_id  # Теперь "wall" будет подставляться автоматически 
        _post_data['count'] = 1000
        response = await self.VKRequest(api=api, method=method, data=_post_data)
        if 'error' in response:
            raise Exception(f"Ошибка: {response['error']}")
        photo_urls = [self.parse_sizes(photo['sizes']) for photo in response['response']['items']]
        return photo_urls
    
    async def album_get(self, token, owner_id):
        _post_data, api = self._predict_data(token)
        method = 'photos.getAlbums'
        _post_data['owner_id'] = -owner_id
        response = await self.VKRequest(api=api, method=method, data=_post_data)
        if 'response' in response and 'items' in response['response']:
            album_ids = [album['id'] for album in response['response']['items']]
            return album_ids
        else:
            return []
