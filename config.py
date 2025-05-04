# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Токен Telegram бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

# API ID и API Hash для Telethon (для работы с каналами)
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')

# Настройки базы данных
DATABASE_NAME = 'telegram_summarizer.db'

# Настройки суммаризации
SUMMARIZATION_INTERVAL = 60 * 60  # 1 час в секундах
SIMILARITY_THRESHOLD = 0.7  # Порог сходства для определения похожего контента
MAX_IMAGES_PER_POST = 2  # Максимальное количество изображений в посте
