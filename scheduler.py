# -*- coding: utf-8 -*-
import logging
import asyncio
import schedule
import time
from threading import Thread

from channel_manager.manager import update_all_channels
from summarizer.summarizer import process_new_messages, schedule_summarization
from config import SUMMARIZATION_INTERVAL

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_scheduler():
    """Запуск планировщика задач в отдельном потоке"""
    def run_schedule():
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    # Создаем и запускаем поток
    scheduler_thread = Thread(target=run_schedule)
    scheduler_thread.daemon = True
    scheduler_thread.start()

def setup_scheduler(bot):
    """
    Настройка планировщика задач
    
    Args:
        bot: Объект бота для отправки сообщений
    """
    # Запускаем планировщик
    run_scheduler()
    
    # Запускаем периодическое обновление каналов
    schedule.every(1).minutes.do(lambda: asyncio.run(update_all_channels()))
    
    # Запускаем периодическую суммаризацию в асинхронном режиме
    asyncio.create_task(schedule_summarization(bot))
    
    logger.info("Планировщик задач успешно настроен")

async def manual_update_channels():
    """Ручное обновление каналов"""
    try:
        logger.info("Запуск ручного обновления каналов")
        
        # Обновляем каналы
        new_messages_count = await update_all_channels()
        
        logger.info(f"Получено {new_messages_count} новых сообщений")
        
        return new_messages_count
    
    except Exception as e:
        logger.error(f"Ошибка при ручном обновлении каналов: {e}")
        return 0

async def manual_process_messages():
    """Ручная обработка сообщений"""
    try:
        logger.info("Запуск ручной обработки сообщений")
        
        # Обрабатываем сообщения
        summaries = await process_new_messages()
        
        logger.info(f"Создано {len(summaries)} суммаризаций")
        
        return summaries
    
    except Exception as e:
        logger.error(f"Ошибка при ручной обработке сообщений: {e}")
        return []
