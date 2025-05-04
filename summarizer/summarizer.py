# -*- coding: utf-8 -*-
import logging
import nltk
import asyncio
from datetime import datetime, timedelta
import re
from collections import Counter
from string import punctuation
import heapq

import database as db
from summarizer.deduplicator import find_similar_messages
from channel_manager.fetcher import get_best_images

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загружаем необходимые ресурсы для NLTK
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('punkt')
    nltk.download('stopwords')

# Получаем стоп-слова для русского языка
try:
    stop_words = set(nltk.corpus.stopwords.words('russian'))
except:
    stop_words = set()
    logger.warning("Не удалось загрузить стоп-слова для русского языка")

async def summarize_messages(messages, sentences_count=5):
    """
    Суммаризация текста сообщений с использованием частотного анализа
    
    Args:
        messages (list): Список сообщений для суммаризации
        sentences_count (int): Количество предложений в суммаризации
        
    Returns:
        str: Суммаризированный текст
    """
    try:
        # Объединяем тексты всех сообщений
        combined_text = "\n\n".join([m['message_text'] for m in messages if m['message_text']])
        
        if not combined_text.strip():
            logger.warning("Нет текста для суммаризации")
            return "Нет доступного текста для суммаризации."
        
        # Проверяем длину текста
        if len(combined_text.split()) < 10:
            logger.warning("Текст слишком короткий для суммаризации")
            return combined_text
        
        # Разбиваем текст на предложения
        sentences = nltk.sent_tokenize(combined_text)
        
        # Если предложений меньше, чем требуется для суммаризации, возвращаем весь текст
        if len(sentences) <= sentences_count:
            return combined_text
        
        # Очищаем текст от пунктуации и стоп-слов
        clean_text = re.sub(r'[^\w\s]', '', combined_text.lower())
        word_tokens = nltk.word_tokenize(clean_text)
        filtered_text = [word for word in word_tokens if word not in stop_words]
        
        # Считаем частоту слов
        word_frequencies = Counter(filtered_text)
        
        # Нормализуем частоты
        max_frequency = max(word_frequencies.values()) if word_frequencies else 1
        for word in word_frequencies:
            word_frequencies[word] = word_frequencies[word] / max_frequency
        
        # Считаем веса предложений
        sentence_scores = {}
        for sentence in sentences:
            for word in nltk.word_tokenize(sentence.lower()):
                if word in word_frequencies:
                    if len(sentence.split()) < 30:  # Игнорируем слишком длинные предложения
                        if sentence not in sentence_scores:
                            sentence_scores[sentence] = 0
                        sentence_scores[sentence] += word_frequencies[word]
        
        # Выбираем предложения с наибольшим весом
        summary_sentences = heapq.nlargest(sentences_count, sentence_scores, key=sentence_scores.get)
        
        # Восстанавливаем порядок предложений в исходном тексте
        ordered_summary = []
        for sentence in sentences:
            if sentence in summary_sentences:
                ordered_summary.append(sentence)
                if len(ordered_summary) == sentences_count:
                    break
        
        # Объединяем предложения в текст
        summary = " ".join(ordered_summary)
        
        return summary
    
    except Exception as e:
        logger.error(f"Ошибка при суммаризации сообщений: {e}")
        return "Не удалось создать суммаризацию из-за ошибки."

async def process_new_messages():
    """
    Обработка новых сообщений и создание суммаризаций
    
    Returns:
        list: Список созданных суммаризаций
    """
    try:
        # Получаем необработанные сообщения
        messages = db.get_unprocessed_messages(limit=100)
        
        if not messages:
            logger.info("Нет новых сообщений для обработки")
            return []
        
        # Группируем похожие сообщения
        message_groups = find_similar_messages(messages)
        
        # Создаем суммаризации для каждой группы
        summaries = []
        
        for group in message_groups:
            # Получаем сообщения группы
            group_messages = [m for m in messages if m['message_id'] in group]
            
            # Создаем суммаризацию
            summary_text = await summarize_messages(group_messages)
            
            # Получаем лучшие изображения для группы
            image_paths = await get_best_images(group)
            
            # Получаем пользователей, которым нужно отправить суммаризацию
            user_ids = await get_users_for_messages(group_messages)
            
            # Сохраняем суммаризацию для каждого пользователя
            for user_id in user_ids:
                summary_id = db.add_summary(
                    user_id,
                    summary_text,
                    group,
                    image_paths
                )
                
                summaries.append({
                    'summary_id': summary_id,
                    'user_id': user_id,
                    'text': summary_text,
                    'images': image_paths
                })
            
            # Отмечаем сообщения как обработанные
            db.mark_messages_as_processed(group)
        
        return summaries
    
    except Exception as e:
        logger.error(f"Ошибка при обработке новых сообщений: {e}")
        return []

async def get_users_for_messages(messages):
    """
    Получение списка пользователей, которым нужно отправить суммаризацию
    
    Args:
        messages (list): Список сообщений
        
    Returns:
        list: Список ID пользователей
    """
    try:
        # Получаем ID каналов из сообщений
        channel_ids = set([m['channel_id'] for m in messages])
        
        # Получаем всех пользователей
        users = []
        
        # Для каждого канала получаем пользователей, которые его отслеживают
        for channel_id in channel_ids:
            # Получаем каналы всех пользователей
            all_channels = db.get_channels(None)
            
            # Фильтруем каналы по ID
            channel_users = set([
                channel['user_id'] for channel in all_channels
                if channel['channel_id'] == channel_id
            ])
            
            users.extend(channel_users)
        
        # Удаляем дубликаты
        return list(set(users))
    
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей для сообщений: {e}")
        return []

async def schedule_summarization(bot):
    """
    Планирование периодической суммаризации
    
    Args:
        bot: Объект бота для отправки сообщений
    """
    while True:
        try:
            logger.info("Запуск периодической суммаризации")
            
            # Обрабатываем новые сообщения
            summaries = await process_new_messages()
            
            # Отправляем суммаризации пользователям
            for summary in summaries:
                try:
                    # Получаем информацию о пользователе
                    user_id = summary['user_id']
                    
                    # Формируем сообщение
                    message_text = summary['text']
                    
                    # Отправляем сообщение
                    if summary['images']:
                        # Если есть изображения, отправляем их с текстом
                        for image_path in summary['images']:
                            await bot.send_photo(
                                chat_id=user_id,
                                photo=open(image_path, 'rb'),
                                caption=message_text if image_path == summary['images'][0] else None
                            )
                    else:
                        # Если нет изображений, отправляем только текст
                        await bot.send_message(
                            chat_id=user_id,
                            text=message_text
                        )
                    
                    logger.info(f"Суммаризация отправлена пользователю {user_id}")
                
                except Exception as e:
                    logger.error(f"Ошибка при отправке суммаризации пользователю {summary['user_id']}: {e}")
            
            logger.info(f"Отправлено {len(summaries)} суммаризаций")
        
        except Exception as e:
            logger.error(f"Ошибка при выполнении периодической суммаризации: {e}")
        
        # Ждем 1 час перед следующей суммаризацией
        await asyncio.sleep(60 * 60)  # 1 час в секундах
