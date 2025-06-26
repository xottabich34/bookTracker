"""
Общие фикстуры для тестов Telegram бота
"""
import pytest
import sqlite3
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock
from telegram import User, Chat, Message, Update, PhotoSize
from telegram.ext import ContextTypes
from typing import Dict, Any


@pytest.fixture(scope="session")
def test_db_path():
    """Создает временную базу данных для тестов"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    yield db_path
    
    # Очистка после всех тестов
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture(scope="function")
def db_connection(test_db_path):
    """Создает подключение к тестовой базе данных"""
    conn = sqlite3.connect(test_db_path, check_same_thread=False)
    
    # Создание таблиц
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS series (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT UNIQUE,
        description TEXT,
        image_blob BLOB,
        series_id INTEGER,
        series_order INTEGER,
        isbn TEXT,
        FOREIGN KEY (series_id) REFERENCES series(id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS authors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS book_authors (
        book_id INTEGER,
        author_id INTEGER,
        PRIMARY KEY (book_id, author_id),
        FOREIGN KEY (book_id) REFERENCES books(id),
        FOREIGN KEY (author_id) REFERENCES authors(id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_books (
        user_id INTEGER,
        book_id INTEGER,
        status TEXT CHECK(status IN ('planning', 'reading', 'finished', 'cancelled')),
        PRIMARY KEY (user_id, book_id),
        FOREIGN KEY (book_id) REFERENCES books(id)
    )
    """)
    conn.commit()
    
    yield conn
    
    # Очистка данных после каждого теста
    cursor.execute("DELETE FROM user_books")
    cursor.execute("DELETE FROM book_authors")
    cursor.execute("DELETE FROM books")
    cursor.execute("DELETE FROM authors")
    cursor.execute("DELETE FROM series")
    conn.commit()
    conn.close()


@pytest.fixture
def mock_user():
    """Создает мок пользователя"""
    user = MagicMock(spec=User)
    user.id = 12345
    user.first_name = "TestUser"
    user.last_name = "TestLastName"
    user.username = "testuser"
    user.is_bot = False
    return user


@pytest.fixture
def mock_chat():
    """Создает мок чата"""
    chat = MagicMock(spec=Chat)
    chat.id = 12345
    chat.type = "private"
    return chat


@pytest.fixture
def mock_photo():
    """Создает мок фотографии"""
    photo = MagicMock(spec=PhotoSize)
    photo.file_id = "test_file_id"
    photo.file_unique_id = "test_unique_id"
    photo.width = 100
    photo.height = 100
    photo.file_size = 1024
    
    # Мок для get_file
    mock_file = AsyncMock()
    mock_file.download_as_bytearray.return_value = b"mock_image_data"
    photo.get_file = AsyncMock(return_value=mock_file)
    
    return photo


@pytest.fixture
def mock_message(mock_user, mock_chat):
    """Создает мок сообщения"""
    message = MagicMock(spec=Message)
    message.message_id = 1
    message.from_user = mock_user
    message.chat = mock_chat
    message.date = None
    message.text = "Test message"
    message.photo = []
    message.reply_text = AsyncMock()
    message.reply_photo = AsyncMock()
    message.reply_document = AsyncMock()
    
    return message


@pytest.fixture
def mock_update(mock_message):
    """Создает мок обновления"""
    update = MagicMock(spec=Update)
    update.update_id = 1
    update.message = mock_message
    update.effective_user = mock_message.from_user
    update.effective_chat = mock_message.chat
    
    return update


@pytest.fixture
def mock_context(mock_db_connection):
    """Создает мок контекста"""
    context = MagicMock()
    context.user_data = {}
    context.args = []
    context.cursor = mock_db_connection.cursor()
    context.conn = mock_db_connection
    return context


@pytest.fixture
def sample_book_data():
    """Возвращает тестовые данные книги"""
    return {
        'title': 'Тестовая книга',
        'description': 'Описание тестовой книги',
        'image_blob': b'test_image_data',
        'isbn': '9783161484100',
        'authors': ['Тестовый Автор 1', 'Тестовый Автор 2'],
        'series_id': None,
        'series_order': None
    }


@pytest.fixture
def sample_series_data():
    """Возвращает тестовые данные серии"""
    return {
        'name': 'Тестовая серия'
    }


@pytest.fixture
def allowed_user_id():
    """ID разрешенного пользователя для тестов"""
    return 12345


@pytest.fixture
def blocked_user_id():
    """ID заблокированного пользователя для тестов"""
    return 99999


@pytest.fixture(autouse=True)
def setup_allowed_ids(allowed_user_id):
    """Настраивает список разрешенных ID для тестов"""
    from main import ALLOWED_IDS
    original_ids = ALLOWED_IDS.copy()
    ALLOWED_IDS.clear()
    ALLOWED_IDS.add(allowed_user_id)
    
    yield
    
    # Восстановление оригинального списка
    ALLOWED_IDS.clear()
    ALLOWED_IDS.update(original_ids)


@pytest.fixture
def mock_db_connection(monkeypatch, db_connection):
    """Мокает подключение к базе данных"""
    monkeypatch.setattr('main.conn', db_connection)
    monkeypatch.setattr('main.cursor', db_connection.cursor())
    return db_connection 