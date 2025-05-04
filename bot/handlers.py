# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re

import database as db
from bot.utils import extract_channel_info

router = Router()

# Определение состояний для FSM (Finite State Machine)
class AddChannelStates(StatesGroup):
    waiting_for_channel = State()

# Обработчик команды /start
@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Добавляем пользователя в базу данных
    db.add_user(user_id, username, first_name, last_name)
    
    # Отправляем приветственное сообщение
    await message.answer(
        f"Привет, {first_name}! 👋\n\n"
        "Я бот для суммаризации контента из Telegram каналов. "
        "Я буду отслеживать указанные вами каналы и периодически отправлять "
        "суммаризированную информацию из них.\n\n"
        "Доступные команды:\n"
        "/add_channel - Добавить канал для отслеживания\n"
        "/list_channels - Показать список отслеживаемых каналов\n"
        "/remove_channel - Удалить канал из отслеживаемых\n\n"
        "Чтобы начать, добавьте канал с помощью команды /add_channel."
    )

# Обработчик команды /add_channel
@router.message(Command("add_channel"))
async def cmd_add_channel(message: Message, state: FSMContext):
    """Обработчик команды /add_channel"""
    # Проверяем, есть ли аргументы в команде
    command_args = message.text.split(maxsplit=1)
    
    if len(command_args) > 1:
        # Если аргумент есть, пытаемся добавить канал сразу
        channel_url = command_args[1].strip()
        await process_channel_url(message, channel_url)
    else:
        # Если аргумента нет, переходим в состояние ожидания ссылки на канал
        await message.answer(
            "Пожалуйста, отправьте ссылку на Telegram канал, который вы хотите отслеживать.\n"
            "Например: https://t.me/channel_name или @channel_name"
        )
        await state.set_state(AddChannelStates.waiting_for_channel)

# Обработчик ввода ссылки на канал
@router.message(AddChannelStates.waiting_for_channel)
async def process_channel_input(message: Message, state: FSMContext):
    """Обработчик ввода ссылки на канал"""
    await state.clear()
    await process_channel_url(message, message.text)

async def process_channel_url(message: Message, channel_url: str):
    """Обработка ссылки на канал и добавление его в базу данных"""
    user_id = message.from_user.id
    
    # Извлекаем информацию о канале из ссылки
    channel_info = await extract_channel_info(channel_url)
    
    if not channel_info:
        await message.answer(
            "Не удалось получить информацию о канале. Пожалуйста, проверьте ссылку и попробуйте снова.\n"
            "Формат ссылки должен быть: https://t.me/channel_name или @channel_name"
        )
        return
    
    # Добавляем канал в базу данных
    channel_id = db.add_channel(user_id, channel_info['title'], channel_info['username'])
    
    await message.answer(
        f"Канал \"{channel_info['title']}\" успешно добавлен для отслеживания! ✅\n\n"
        f"Я буду периодически проверять новые сообщения в этом канале и отправлять вам суммаризированную информацию."
    )

# Обработчик команды /list_channels
@router.message(Command("list_channels"))
async def cmd_list_channels(message: Message):
    """Обработчик команды /list_channels"""
    user_id = message.from_user.id
    
    # Получаем список каналов пользователя
    channels = db.get_channels(user_id)
    
    if not channels:
        await message.answer(
            "У вас пока нет отслеживаемых каналов. "
            "Используйте команду /add_channel, чтобы добавить канал."
        )
        return
    
    # Формируем сообщение со списком каналов
    channels_text = "Ваши отслеживаемые каналы:\n\n"
    
    for i, channel in enumerate(channels, 1):
        channels_text += f"{i}. {channel['channel_name']} (@{channel['channel_url']})\n"
    
    channels_text += "\nЧтобы удалить канал, используйте команду /remove_channel"
    
    await message.answer(channels_text)

# Обработчик команды /remove_channel
@router.message(Command("remove_channel"))
async def cmd_remove_channel(message: Message):
    """Обработчик команды /remove_channel"""
    user_id = message.from_user.id
    
    # Получаем список каналов пользователя
    channels = db.get_channels(user_id)
    
    if not channels:
        await message.answer(
            "У вас нет отслеживаемых каналов для удаления."
        )
        return
    
    # Формируем сообщение со списком каналов для удаления
    channels_text = "Выберите канал для удаления, отправив его номер:\n\n"
    
    for i, channel in enumerate(channels, 1):
        channels_text += f"{i}. {channel['channel_name']} (@{channel['channel_url']})\n"
    
    # Сохраняем список каналов в состоянии пользователя для последующего использования
    await message.answer(channels_text)

# Обработчик команды /summarize
@router.message(Command("summarize"))
async def cmd_summarize(message: Message):
    """Обработчик команды /summarize"""
    user_id = message.from_user.id
    
    # Получаем сообщения за последний час
    messages = db.get_messages_last_hour()
    
    if not messages:
        await message.answer("Нет новых сообщений за последний час.")
        return
    
    # Удаляем дублирующийся контент
    from summarizer.deduplicator import find_similar_messages
    unique_messages = find_similar_messages(messages)
    
    # Формируем итоговую суммаризацию
    summary_text = "Суммаризация за последний час:\n\n"
    for msg in unique_messages:
        summary_text += f"- {msg['message_text']}\n"
    
    await message.answer(summary_text)
