# -*- coding: utf-8 -*-
import sqlite3
import json
from config import DATABASE_NAME

def init_db():
    """Инициализация базы данных и создание необходимых таблиц"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    # Таблица пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Таблица каналов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS channels (
        channel_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        channel_name TEXT,
        channel_url TEXT,
        last_checked_message_id INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    # Таблица сообщений
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        message_id INTEGER PRIMARY KEY,
        channel_id INTEGER,
        message_text TEXT,
        message_date TIMESTAMP,
        processed BOOLEAN DEFAULT FALSE,
        vector_representation TEXT,  -- Сохраняем векторное представление как JSON
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (channel_id) REFERENCES channels (channel_id)
    )
    ''')
    
    # Таблица медиафайлов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS media (
        media_id INTEGER PRIMARY KEY,
        message_id INTEGER,
        media_type TEXT,  -- photo, video, etc.
        media_url TEXT,
        local_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (message_id) REFERENCES messages (message_id)
    )
    ''')
    
    # Таблица суммаризаций
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS summaries (
        summary_id INTEGER PRIMARY KEY,
        user_id INTEGER,
        summary_text TEXT,
        source_messages TEXT,  -- JSON массив ID сообщений
        media_files TEXT,  -- JSON массив ID медиафайлов
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Функции для работы с пользователями
def add_user(user_id, username=None, first_name=None, last_name=None):
    """Добавление нового пользователя или обновление существующего"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
    VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name))
    
    conn.commit()
    conn.close()

def get_user(user_id):
    """Получение информации о пользователе"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user:
        return {
            'user_id': user[0],
            'username': user[1],
            'first_name': user[2],
            'last_name': user[3],
            'created_at': user[4]
        }
    return None

# Функции для работы с каналами
def add_channel(user_id, channel_name, channel_url):
    """Добавление нового канала для отслеживания"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO channels (user_id, channel_name, channel_url)
    VALUES (?, ?, ?)
    ''', (user_id, channel_name, channel_url))
    
    channel_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return channel_id

def get_channels(user_id):
    """Получение списка каналов пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    if user_id is None:
        cursor.execute('SELECT * FROM channels')
    else:
        cursor.execute('SELECT * FROM channels WHERE user_id = ?', (user_id,))
    channels = cursor.fetchall()
    
    conn.close()
    
    result = []
    for channel in channels:
        result.append({
            'channel_id': channel[0],
            'user_id': channel[1],
            'channel_name': channel[2],
            'channel_url': channel[3],
            'last_checked_message_id': channel[4],
            'created_at': channel[5]
        })
    
    return result

def remove_channel(channel_id):
    """Удаление канала из отслеживаемых"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
    
    conn.commit()
    conn.close()

def update_last_checked_message_id(channel_id, message_id):
    """Обновление ID последнего проверенного сообщения"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    UPDATE channels SET last_checked_message_id = ?
    WHERE channel_id = ?
    ''', (message_id, channel_id))
    
    conn.commit()
    conn.close()

# Функции для работы с сообщениями

def get_messages_last_hour():
    """Получение сообщений за последний час"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM messages
    WHERE message_date >= datetime('now', '-1 hour')
    ORDER BY message_date ASC
    ''')
    
    messages = cursor.fetchall()
    conn.close()
    
    result = []
    for message in messages:
        vector = None
        if message[5]:  # vector_representation
            try:
                vector = json.loads(message[5])
            except:
                pass
                
        result.append({
            'message_id': message[0],
            'channel_id': message[1],
            'message_text': message[2],
            'message_date': message[3],
            'processed': bool(message[4]),
            'vector_representation': vector,
            'created_at': message[6]
        })
    
    return result
def add_message(channel_id, message_text, message_date, vector_representation=None):
    """Добавление нового сообщения из канала"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    vector_json = None
    if vector_representation is not None:
        vector_json = json.dumps(vector_representation.tolist() if hasattr(vector_representation, 'tolist') else vector_representation)
    
    cursor.execute('''
    INSERT INTO messages (channel_id, message_text, message_date, vector_representation)
    VALUES (?, ?, ?, ?)
    ''', (channel_id, message_text, message_date, vector_json))
    
    message_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return message_id

def get_unprocessed_messages(limit=100):
    """Получение необработанных сообщений для суммаризации"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM messages 
    WHERE processed = FALSE
    ORDER BY message_date ASC
    LIMIT ?
    ''', (limit,))
    
    messages = cursor.fetchall()
    
    conn.close()
    
    result = []
    for message in messages:
        vector = None
        if message[5]:  # vector_representation
            try:
                vector = json.loads(message[5])
            except:
                pass
                
        result.append({
            'message_id': message[0],
            'channel_id': message[1],
            'message_text': message[2],
            'message_date': message[3],
            'processed': bool(message[4]),
            'vector_representation': vector,
            'created_at': message[6]
        })
    
    return result

def mark_messages_as_processed(message_ids):
    """Отметка сообщений как обработанных"""
    if not message_ids:
        return
        
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    placeholders = ', '.join(['?'] * len(message_ids))
    cursor.execute(f'''
    UPDATE messages SET processed = TRUE
    WHERE message_id IN ({placeholders})
    ''', message_ids)
    
    conn.commit()
    conn.close()

# Функции для работы с медиафайлами
def add_media(message_id, media_type, media_url, local_path=None):
    """Добавление медиафайла, связанного с сообщением"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    INSERT INTO media (message_id, media_type, media_url, local_path)
    VALUES (?, ?, ?, ?)
    ''', (message_id, media_type, media_url, local_path))
    
    media_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return media_id

def get_media_for_message(message_id):
    """Получение медиафайлов для сообщения"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM media WHERE message_id = ?', (message_id,))
    media_files = cursor.fetchall()
    
    conn.close()
    
    result = []
    for media in media_files:
        result.append({
            'media_id': media[0],
            'message_id': media[1],
            'media_type': media[2],
            'media_url': media[3],
            'local_path': media[4],
            'created_at': media[5]
        })
    
    return result

# Функции для работы с суммаризациями
def add_summary(user_id, summary_text, source_messages, media_files=None):
    """Добавление новой суммаризации"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    source_messages_json = json.dumps(source_messages)
    media_files_json = json.dumps(media_files) if media_files else None
    
    cursor.execute('''
    INSERT INTO summaries (user_id, summary_text, source_messages, media_files)
    VALUES (?, ?, ?, ?)
    ''', (user_id, summary_text, source_messages_json, media_files_json))
    
    summary_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    return summary_id

def get_recent_summaries(user_id, limit=10):
    """Получение последних суммаризаций для пользователя"""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT * FROM summaries 
    WHERE user_id = ?
    ORDER BY created_at DESC
    LIMIT ?
    ''', (user_id, limit))
    
    summaries = cursor.fetchall()
    
    conn.close()
    
    result = []
    for summary in summaries:
        source_messages = json.loads(summary[3]) if summary[3] else []
        media_files = json.loads(summary[4]) if summary[4] else []
        
        result.append({
            'summary_id': summary[0],
            'user_id': summary[1],
            'summary_text': summary[2],
            'source_messages': source_messages,
            'media_files': media_files,
            'created_at': summary[5]
        })
    
    return result

# Инициализация базы данных при импорте модуля
if __name__ == "__main__":
    init_db()
    print(f"База данных {DATABASE_NAME} успешно инициализирована.")
