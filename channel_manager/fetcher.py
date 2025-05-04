# -*- coding: utf-8 -*-
import logging
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
from telethon.tl.functions.channels import JoinChannelRequest
import os
from datetime import datetime
import asyncio

import database as db
from bot.utils import get_telethon_client
from config import MAX_IMAGES_PER_POST

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Директория для сохранения медиафайлов
MEDIA_DIR = 'media'

# Создаем директорию для медиафайлов, если она не существует
os.makedirs(MEDIA_DIR, exist_ok=True)

async def fetch_new_messages(channel_id, channel_url, last_message_id=0):
    """
    Получение новых сообщений из канала
    
    Args:
        channel_id (int): ID канала в базе данных
        channel_url (str): URL канала или username
        last_message_id (int): ID последнего проверенного сообщения
        
    Returns:
        list: Список новых сообщений
    """
    try:
        from bot.utils import get_user_client
        client = await get_user_client(phone_number="YOUR_PHONE_NUMBER")
        if not client:
            return []
        
        # Извлекаем username из URL
        username = channel_url
        if channel_url.startswith('@'):
            username = channel_url[1:]
        
        # Получаем канал
        entity = await client.get_entity(username)
        
        # Получаем новые сообщения
        messages = await client.get_messages(
            entity,
            limit=100,  # Ограничиваем количество сообщений
            min_id=last_message_id  # Получаем сообщения с ID больше last_message_id
        )
        
        if not messages:
            logger.info(f"Нет новых сообщений в канале {channel_url}")
            return []
        
        # Обрабатываем полученные сообщения
        processed_messages = []
        max_message_id = last_message_id
        
        for message in messages:
            # Пропускаем пустые сообщения
            if not message.text and not message.media:
                continue
            
            # Обновляем максимальный ID сообщения
            if message.id > max_message_id:
                max_message_id = message.id
            
            # Сохраняем сообщение в базу данных
            message_text = message.text if message.text else ""
            message_date = message.date
            
            # Добавляем сообщение в базу данных
            message_id = db.add_message(
                channel_id,
                message_text,
                message_date.strftime('%Y-%m-%d %H:%M:%S')
            )
            
            # Обрабатываем медиафайлы
            media_files = []
            
            if message.media:
                media_files = await process_media(message, message_id)
            
            # Добавляем обработанное сообщение в список
            processed_messages.append({
                'message_id': message_id,
                'text': message_text,
                'date': message_date,
                'media_files': media_files
            })
        
        # Обновляем последний проверенный ID сообщения
        if max_message_id > last_message_id:
            db.update_last_checked_message_id(channel_id, max_message_id)
        
        return processed_messages
    
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений из канала {channel_url}: {e}")
        return []

async def process_media(message, message_id):
    """
    Обработка медиафайлов в сообщении
    
    Args:
        message: Объект сообщения Telethon
        message_id (int): ID сообщения в базе данных
        
    Returns:
        list: Список словарей с информацией о медиафайлах
    """
    media_files = []
    
    try:
        # Проверяем тип медиа
        if isinstance(message.media, MessageMediaPhoto):
            # Обрабатываем фото
            media_type = 'photo'
            
            # Создаем директорию для фото, если она не существует
            photo_dir = os.path.join(MEDIA_DIR, 'photos')
            os.makedirs(photo_dir, exist_ok=True)
            
            # Генерируем имя файла
            file_name = f"photo_{message_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
            file_path = os.path.join(photo_dir, file_name)
            
            # Скачиваем фото
            client = await get_telethon_client()
            if client:
                await message.download_media(file_path)
                
                # Добавляем информацию о медиафайле в базу данных
                media_id = db.add_media(
                    message_id,
                    media_type,
                    f"https://t.me/{message.chat.username}/{message.id}",
                    file_path
                )
                
                media_files.append({
                    'media_id': media_id,
                    'type': media_type,
                    'path': file_path
                })
        
        elif isinstance(message.media, MessageMediaDocument):
            # Проверяем, является ли документ изображением
            if message.media.document.mime_type.startswith('image/'):
                media_type = 'photo'
                
                # Создаем директорию для фото, если она не существует
                photo_dir = os.path.join(MEDIA_DIR, 'photos')
                os.makedirs(photo_dir, exist_ok=True)
                
                # Генерируем имя файла
                file_ext = message.media.document.mime_type.split('/')[1]
                file_name = f"photo_{message_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file_ext}"
                file_path = os.path.join(photo_dir, file_name)
                
                # Скачиваем фото
                client = await get_telethon_client()
                if client:
                    await message.download_media(file_path)
                    
                    # Добавляем информацию о медиафайле в базу данных
                    media_id = db.add_media(
                        message_id,
                        media_type,
                        f"https://t.me/{message.chat.username}/{message.id}",
                        file_path
                    )
                    
                    media_files.append({
                        'media_id': media_id,
                        'type': media_type,
                        'path': file_path
                    })
    
    except Exception as e:
        logger.error(f"Ошибка при обработке медиафайла в сообщении {message_id}: {e}")
    
    return media_files

async def get_best_images(message_ids, max_images=MAX_IMAGES_PER_POST):
    """
    Получение лучших изображений для группы сообщений
    
    Args:
        message_ids (list): Список ID сообщений
        max_images (int): Максимальное количество изображений
        
    Returns:
        list: Список путей к изображениям
    """
    try:
        all_media = []
        
        # Получаем все медиафайлы для сообщений
        for message_id in message_ids:
            media = db.get_media_for_message(message_id)
            all_media.extend(media)
        
        # Фильтруем только изображения
        images = [m for m in all_media if m['media_type'] == 'photo']
        
        # Если изображений нет, возвращаем пустой список
        if not images:
            return []
        
        # Сортируем изображения по дате создания (от новых к старым)
        images.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Выбираем лучшие изображения (пока просто берем первые max_images)
        best_images = images[:max_images]
        
        return [img['local_path'] for img in best_images if img['local_path']]
    
    except Exception as e:
        logger.error(f"Ошибка при получении лучших изображений: {e}")
        return []
