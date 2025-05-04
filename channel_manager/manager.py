# -*- coding: utf-8 -*-
import logging
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest, JoinChannelRequest
from telethon.tl.types import Channel, Chat
import asyncio

import database as db
from bot.utils import get_telethon_client
from channel_manager.fetcher import fetch_new_messages

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_channel_exists(channel_url):
    """
    Проверка существования канала
    
    Args:
        channel_url (str): URL канала или username
        
    Returns:
        bool: True, если канал существует, иначе False
    """
    try:
        client = await get_telethon_client()
        if not client:
            return False
        
        # Извлекаем username из URL
        username = channel_url
        if channel_url.startswith('@'):
            username = channel_url[1:]
        
        # Пытаемся подписаться на канал перед получением информации
        try:
            await client(JoinChannelRequest(username))
            logger.info(f"Подписался на канал {username}")
        except Exception as e:
            logger.warning(f"Не удалось подписаться на канал {username}: {e}")
        
        # Пытаемся получить информацию о канале
        entity = await client.get_entity(username)
        
        # Проверяем, что это канал или группа
        return isinstance(entity, (Channel, Chat))
    
    except Exception as e:
        logger.error(f"Ошибка при проверке канала {channel_url}: {e}")
        return False

async def get_channel_info(channel_id):
    """
    Получение информации о канале из базы данных и Telegram API
    
    Args:
        channel_id (int): ID канала в базе данных
        
    Returns:
        dict: Словарь с информацией о канале или None в случае ошибки
    """
    try:
        # Получаем информацию о канале из базы данных
        channels = db.get_channels(None)  # Получаем все каналы
        channel_info = None
        
        for channel in channels:
            if channel['channel_id'] == channel_id:
                channel_info = channel
                break
        
        if not channel_info:
            logger.warning(f"Канал с ID {channel_id} не найден в базе данных")
            return None
        
        # Получаем дополнительную информацию через Telethon
        client = await get_telethon_client()
        if not client:
            return channel_info
        
        try:
            # Извлекаем username из URL
            username = channel_info['channel_url']
            
            # Пытаемся подписаться на канал перед получением информации
            try:
                await client(JoinChannelRequest(username))
                logger.info(f"Подписался на канал {username}")
            except Exception as e:
                logger.warning(f"Не удалось подписаться на канал {username}: {e}")
            
            entity = await client.get_entity(username)
            
            # Добавляем информацию из Telegram API
            if isinstance(entity, (Channel, Chat)):
                full_channel = await client(GetFullChannelRequest(entity))
                
                channel_info.update({
                    'title': entity.title,
                    'id': entity.id,
                    'participants_count': getattr(full_channel.full_chat, 'participants_count', 0),
                    'about': getattr(full_channel.full_chat, 'about', None)
                })
        
        except Exception as e:
            logger.warning(f"Не удалось получить дополнительную информацию о канале {channel_id}: {e}")
        
        return channel_info
    
    except Exception as e:
        logger.error(f"Ошибка при получении информации о канале {channel_id}: {e}")
        return None

async def update_all_channels():
    """
    Обновление всех каналов - получение новых сообщений
    
    Returns:
        int: Количество новых сообщений
    """
    try:
        # Получаем все каналы
        channels = db.get_channels(None)  # Получаем все каналы
        
        if not channels:
            logger.info("Нет каналов для обновления")
            return 0
        
        total_new_messages = 0
        
        # Обновляем каждый канал
        for channel in channels:
            try:
                # Получаем новые сообщения
                new_messages = await fetch_new_messages(
                    channel['channel_id'],
                    channel['channel_url'],
                    channel['last_checked_message_id']
                )
                
                total_new_messages += len(new_messages)
                
                logger.info(f"Получено {len(new_messages)} новых сообщений из канала {channel['channel_name']}")
            
            except Exception as e:
                logger.error(f"Ошибка при обновлении канала {channel['channel_name']}: {e}")
        
        return total_new_messages
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении каналов: {e}")
        return 0
