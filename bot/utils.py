# -*- coding: utf-8 -*-
import asyncio
import re
from telethon import TelegramClient
from telethon.tl.functions.channels import GetFullChannelRequest, JoinChannelRequest
from telethon.tl.types import Channel, Chat
import logging

from config import API_ID, API_HASH

# Настройка клиента Telegram API
api_client = None

async def get_api_client():
    """Получение или создание клиента Telegram API"""
    global api_client
    
    if api_client is None:
        try:
            api_client = TelegramClient('api_session', API_ID, API_HASH)
            await api_client.start()
            logger.info(f"Пользователь с номером {phone_number} успешно авторизован.")
        except Exception as e:
            logger.error(f"Ошибка при создании клиента Telegram API: {e}")
            return None
    
    return api_client

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Клиент Telethon для работы с API Telegram

user_client = None

async def get_user_client(phone_number: str = "+79996559005"):
    """Получение или создание клиента Telethon для пользователя"""
    global user_client
    
    if user_client is None:
        try:
            loop = asyncio.get_event_loop()
            user_client = TelegramClient('user_session', API_ID, API_HASH, loop=loop)
            logger.info(f"Попытка авторизации с номером {phone_number}")
            await user_client.start(phone=phone_number)
        except Exception as e:
            logger.error(f"Ошибка при создании клиента пользователя Telethon: {e}")
            return None
    
    return user_client
client = None

async def get_telethon_client():
    """Получение или создание клиента Telethon"""
    global client
    
    if client is None:
        try:
            client = TelegramClient('channel_fetcher_session', API_ID, API_HASH)
            await client.start()
        except Exception as e:
            logger.error(f"Ошибка при создании клиента Telethon: {e}")
            return None
    
    return client

async def extract_channel_info(channel_url):
    """
    Извлечение информации о канале из ссылки
    
    Args:
        channel_url (str): Ссылка на канал в формате https://t.me/channel_name или @channel_name
        
    Returns:
        dict: Словарь с информацией о канале (title, username) или None в случае ошибки
    """
    # Извлекаем username из ссылки
    username = None
    
    # Проверяем формат @username
    if channel_url.startswith('@'):
        username = channel_url[1:]
    
    # Проверяем формат https://t.me/username
    elif re.match(r'https?://t\.me/\+', channel_url):
        logger.warning(f"Ссылка {channel_url} не поддерживается ботом.")
        return None
    else:
        match = re.match(r'https?://t\.me/([a-zA-Z0-9_]+)', channel_url)
        if match:
            username = match.group(1)
    
    if not username:
        logger.warning(f"Не удалось извлечь username из ссылки: {channel_url}")
        return None
    
    # Получаем информацию о канале через Telethon
    try:
        client = await get_telethon_client()
        if not client:
            return None
        
        # Получаем информацию о канале
        entity = await client.get_entity(username)
        
        # Проверяем, что это канал или группа
        if isinstance(entity, (Channel, Chat)):
            # Получаем полную информацию о канале
            full_channel = await client(GetFullChannelRequest(entity))
            
            return {
                'title': entity.title,
                'username': username,
                'id': entity.id,
                'participants_count': getattr(full_channel.full_chat, 'participants_count', 0),
                'about': getattr(full_channel.full_chat, 'about', None)
            }
        else:
            logger.warning(f"Сущность {username} не является каналом или группой")
            return None
    
    except Exception as e:
        logger.error(f"Ошибка при получении информации о канале {username}: {e}")
        return None

async def close_telethon_client():
    """Закрытие клиента Telethon"""
    global client
    
    if client:
        await client.disconnect()
        client = None
