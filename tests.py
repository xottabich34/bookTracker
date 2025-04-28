import pytest
import sqlite3
from telegram import User, Chat, Update
from telegram.ext import ContextTypes
from main import (
    add_start, add_title, add_description, add_cover, add_isbn,
    add_authors, add_series, add_series_order, finalize_book,
    add_cancel, list_books, list_series, my_books, ALLOWED_IDS
)

# 🔍 Фикстуры для моков

@pytest.fixture
async def context():
    class DummyContext:
        def __init__(self):
            self.user_data = {}
            self.args = []
    return DummyContext()

@pytest.fixture
async def update():
    ALLOWED_IDS.add(12345)

    user = User(id=12345, first_name="TestUser", is_bot=False)
    chat = Chat(id=12345, type="private")

    class DummyPhoto:
        async def get_file(self):
            class DummyFile:
                async def download_as_bytearray(self):
                    return b"mock_image_data"
            return DummyFile()

    class DummyMessage:
        def __init__(self):
            self.from_user = user
            self.chat = chat
            self._text = "Тестовая книга"

        async def reply_text(self, text, reply_markup=None):
            print(f"Reply: {text}")

        @property
        def text(self):
            return self._text

        @property
        def photo(self):
            return [DummyPhoto()]

    message = DummyMessage()
    return Update(update_id=1, message=message)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    conn = sqlite3.connect("books.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM books")
    cursor.execute("DELETE FROM series")
    cursor.execute("DELETE FROM authors")
    conn.commit()
    yield
    cursor.execute("DELETE FROM books")
    cursor.execute("DELETE FROM series")
    cursor.execute("DELETE FROM authors")
    conn.commit()
    conn.close()

# 👩‍Ὅa Тесты добавления книги

@pytest.mark.asyncio
async def test_add_start(update, context):
    result = await add_start(update, context)
    assert result == 0

@pytest.mark.asyncio
async def test_add_title(update, context):
    result = await add_title(update, context)
    assert result == 1
    assert context.user_data['new_book']['title'] == "Тестовая книга"

@pytest.mark.asyncio
async def test_add_description(update, context):
    context.user_data['new_book'] = {}
    result = await add_description(update, context)
    assert result == 2

@pytest.mark.asyncio
async def test_add_cover(update, context):
    context.user_data['new_book'] = {}
    result = await add_cover(update, context)
    assert result == 3

@pytest.mark.asyncio
async def test_add_isbn_correct(update, context):
    context.user_data['new_book'] = {}
    update.message._text = "9783161484100"
    result = await add_isbn(update, context)
    assert result == 4

@pytest.mark.asyncio
async def test_add_authors(update, context):
    context.user_data['new_book'] = {}
    update.message._text = "Автор1, Автор2"
    result = await add_authors(update, context)
    assert result == 5

@pytest.mark.asyncio
async def test_add_series(update, context):
    context.user_data['new_book'] = {}
    update.message._text = "СерияТест"
    result = await add_series(update, context)
    assert result == 6 or result is None

@pytest.mark.asyncio
async def test_add_series_order(update, context):
    context.user_data['new_book'] = {
        'title': 'Книга из серии',
        'description': 'Описание книги из серии',
        'image_blob': b'test',
        'isbn': '9783161484100',
        'authors': ['Автор Серии'],
        'series_id': 1,
        'series_order': None
    }
    update.message._text = "1"
    result = await add_series_order(update, context)
    assert result == -1

@pytest.mark.asyncio
async def test_finalize_book(update, context):
    context.user_data['new_book'] = {
        'title': 'Финальная книга',
        'description': 'Описание',
        'image_blob': b'test',
        'isbn': '9783161484100',
        'authors': ['АвторТест'],
        'series_id': None,
        'series_order': None
    }
    result = await finalize_book(update, context)
    assert result == -1

# 📕 Другие команды

@pytest.mark.asyncio
async def test_add_cancel(update, context):
    result = await add_cancel(update, context)
    assert result == -1

@pytest.mark.asyncio
async def test_list_books(update, context):
    await list_books(update, context)

@pytest.mark.asyncio
async def test_list_series(update, context):
    await list_series(update, context)

@pytest.mark.asyncio
async def test_my_books(update, context):
    await my_books(update, context)
