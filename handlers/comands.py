
from aiogram import types, F, Router
from aiogram.filters import Command
from logger import logger
from facenet.facenet_module import FaceNet


router = Router()
face_net = FaceNet()

async def start_handler(message: types.Message):
    logger.info("Стартовая команда получена")
    await message.answer("Привет! Пришли фото для поиска похожих лиц.\nДля помощи отправь /help.")

async def help_handler(message: types.Message):
    logger.info("Команда /help получена")
    help_text = (
        "Я бот для поиска похожих лиц.\n"
        "Просто пришли фото с одним лицом, и я попробую найти похожие в базе данных.\n"
        "Если у тебя есть вопросы, пиши!"
    )
    await message.answer(help_text)

async def photo_command_handler(message: types.Message):
    """
    Хендлер для команды /photo.
    Здесь мы просто просим пользователя отправить фото.
    """
    await message.answer("Пришли мне фото — я попробую найти совпадения.")

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
    dp.message.register(start_handler, Command("start"))
    dp.message.register(help_handler, Command("help"))
    dp.message.register(text_handler, F.text & ~F.text.startswith("/"))
    dp.errors.register(error_handler)
    dp.message.register(photo_command_handler, F.text)

