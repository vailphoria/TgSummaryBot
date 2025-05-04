# -*- coding: utf-8 -*-
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums.parse_mode import ParseMode

import database as db
from config import BOT_TOKEN
from bot.handlers import router
from scheduler import setup_scheduler
from bot.utils import close_telethon_client

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрация роутеров
dp.include_router(router)

async def on_startup():
    """Действия при запуске бота"""
    # Инициализация базы данных
    db.init_db()
    logger.info("База данных инициализирована")
    
    # Настройка планировщика задач
    setup_scheduler(bot)
    logger.info("Планировщик задач настроен")
    
    logger.info("Бот запущен и готов к работе!")

async def on_shutdown():
    """Действия при остановке бота"""
    # Закрываем клиент Telethon
    await close_telethon_client()
    logger.info("Клиент Telethon закрыт")
    
    logger.info("Бот остановлен")

async def main():
    """Основная функция запуска бота"""
    try:
        # Вызываем функцию on_startup
        await on_startup()
        
        # Запускаем поллинг
        await dp.start_polling(bot)
    
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    
    finally:
        # Вызываем функцию on_shutdown
        await on_shutdown()

if __name__ == "__main__":
    try:
        # Запускаем основную функцию
        asyncio.run(main())
    
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен")
