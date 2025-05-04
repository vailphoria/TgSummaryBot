# -*- coding: utf-8 -*-
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from config import SIMILARITY_THRESHOLD

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_similar_messages(messages):
    """
    Группировка похожих сообщений
    
    Args:
        messages (list): Список сообщений для группировки
        
    Returns:
        list: Список групп похожих сообщений (каждая группа - список ID сообщений)
    """
    try:
        if not messages:
            return []
        
        # Извлекаем тексты сообщений
        texts = [m['message_text'] for m in messages]
        message_ids = [m['message_id'] for m in messages]
        
        # Если сообщений меньше 2, возвращаем одну группу
        if len(texts) < 2:
            return [message_ids]
        
        # Создаем векторизатор TF-IDF
        vectorizer = TfidfVectorizer(stop_words='english')
        
        # Преобразуем тексты в векторы TF-IDF
        try:
            tfidf_matrix = vectorizer.fit_transform(texts)
        except Exception as e:
            logger.error(f"Ошибка при векторизации текстов: {e}")
            # В случае ошибки векторизации возвращаем каждое сообщение как отдельную группу
            return [[message_id] for message_id in message_ids]
        
        # Вычисляем матрицу сходства
        similarity_matrix = cosine_similarity(tfidf_matrix)
        
        # Группируем похожие сообщения
        groups = []
        processed = set()
        
        for i in range(len(messages)):
            if i in processed:
                continue
            
            # Создаем новую группу
            group = [message_ids[i]]
            processed.add(i)
            
            # Ищем похожие сообщения
            for j in range(len(messages)):
                if j in processed or i == j:
                    continue
                
                # Если сходство выше порогового значения, добавляем в группу
                if similarity_matrix[i, j] >= SIMILARITY_THRESHOLD:
                    group.append(message_ids[j])
                    processed.add(j)
            
            groups.append(group)
        
        return groups
    
    except Exception as e:
        logger.error(f"Ошибка при поиске похожих сообщений: {e}")
        # В случае ошибки возвращаем каждое сообщение как отдельную группу
        return [[m['message_id']] for m in messages]

def calculate_text_similarity(text1, text2):
    """
    Вычисление сходства между двумя текстами
    
    Args:
        text1 (str): Первый текст
        text2 (str): Второй текст
        
    Returns:
        float: Значение сходства (от 0 до 1)
    """
    try:
        # Создаем векторизатор TF-IDF
        vectorizer = TfidfVectorizer(stop_words='english')
        
        # Преобразуем тексты в векторы TF-IDF
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        
        # Вычисляем сходство
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        return similarity
    
    except Exception as e:
        logger.error(f"Ошибка при вычислении сходства текстов: {e}")
        return 0.0
