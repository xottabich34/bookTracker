"""
Тесты для запросов книг
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram.ext import ConversationHandler
from main import (
    list_books, my_books, search_books, search_start, search_process,
    book_info_start, book_info_select, list_series
)

@pytest.fixture(autouse=True)
def patch_main_db(mock_db_connection, mock_context):
    mock_context.cursor = mock_db_connection.cursor()
    mock_context.conn = mock_db_connection
    yield

class TestBookListing:
    """Тесты для отображения списков книг"""
    
    @pytest.mark.asyncio
    async def test_list_books_empty(self, mock_update, mock_context, mock_db_connection):
        """Тест: отображение пустого списка книг"""
        # Act
        await list_books(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "библиотека пуста" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_list_books_with_books(self, mock_update, mock_context, mock_db_connection):
        """Тест: отображение списка книг"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Книга 1", "Описание 1"))
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Книга 2", "Описание 2"))
        mock_db_connection.commit()
        
        # Act
        await list_books(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Книга 1" in response_text
        assert "Книга 2" in response_text
    
    @pytest.mark.asyncio
    async def test_my_books_empty(self, mock_update, mock_context, mock_db_connection):
        """Тест: отображение пустого списка моих книг"""
        # Act
        await my_books(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "у вас нет отмеченных книг" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_my_books_with_statuses(self, mock_update, mock_context, mock_db_connection):
        """Тест: отображение моих книг со статусами"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Книга 1", "Описание 1"))
        book1_id = cursor.lastrowid
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Книга 2", "Описание 2"))
        book2_id = cursor.lastrowid
        cursor.execute("INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)", (12345, book1_id, "reading"))
        cursor.execute("INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)", (12345, book2_id, "finished"))
        mock_db_connection.commit()
        mock_update.effective_user.id = 12345
        mock_context.effective_user = mock_update.effective_user
        
        # Act
        await my_books(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Книга 1" in response_text
        assert "Книга 2" in response_text
        assert "читаю" in response_text.lower()
        assert "прочитано" in response_text.lower()


class TestBookSearch:
    """Тесты для поиска книг"""
    
    @pytest.mark.asyncio
    async def test_search_start(self, mock_update, mock_context):
        """Тест: начало поиска"""
        # Act
        await search_start(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "введите поисковый запрос" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_search_process_by_title(self, mock_update, mock_context, mock_db_connection):
        """Тест: поиск по названию"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Анна Каренина", "Описание"))
        cursor.execute("INSERT INTO authors (name) VALUES (?)", ("Лев Толстой",))
        cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (1, 1))
        cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (2, 1))
        mock_db_connection.commit()
        
        mock_update.message.text = "Война"

        # Act
        result = await search_process(mock_update, mock_context)
        
        # Assert
        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Война и мир" in response_text
        assert "Анна Каренина" not in response_text
    
    @pytest.mark.asyncio
    async def test_search_process_by_author(self, mock_update, mock_context, mock_db_connection):
        """Тест: поиск по автору"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        book1_id = cursor.lastrowid
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Анна Каренина", "Описание"))
        book2_id = cursor.lastrowid
        cursor.execute("INSERT INTO authors (name) VALUES (?)", ("Лев Толстой",))
        author_id = cursor.lastrowid
        cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (book1_id, author_id))
        cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (book2_id, author_id))
        mock_db_connection.commit()
        
        mock_update.message.text = "Лев"
        
        # Act
        result = await search_process(mock_update, mock_context)
        
        # Assert
        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Война и мир" in response_text
        assert "Лев Толстой" in response_text
    
    @pytest.mark.asyncio
    async def test_search_process_no_results(self, mock_update, mock_context, mock_db_connection):
        """Тест: поиск без результатов"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "несуществующая книга"
        
        # Act
        result = await search_process(mock_update, mock_context)
        
        # Assert
        assert result == ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "не найдено" in response_text.lower()
    
    @pytest.mark.asyncio
    async def test_search_books_direct(self, mock_update, mock_context, mock_db_connection):
        """Тест: прямой поиск книг"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        # Act
        await search_books(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        response = mock_update.message.reply_text.call_args[0][0].lower()
        assert "использование" in response
        assert "поиск" in response


class TestBookInfo:
    """Тесты для отображения информации о книге"""
    
    @pytest.mark.asyncio
    async def test_book_info_start(self, mock_update, mock_context, mock_db_connection):
        """Тест: начало просмотра информации о книге"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        # Act
        await book_info_start(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "выберите книгу" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_book_info_select_with_cover(self, mock_update, mock_context, mock_db_connection):
        """Тест: выбор книги для просмотра информации с обложкой"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description, image_blob) VALUES (?, ?, ?)", 
                      ("Война и мир", "Описание", b"test_image_data"))
        mock_db_connection.commit()
        
        mock_update.message.text = "1"
        mock_context.user_data['available_books'] = ["Война и мир"]
        
        # Act
        await book_info_select(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_photo.assert_called_once()
        response_text = mock_update.message.reply_photo.call_args[1]['caption']
        assert "Война и мир" in response_text
        assert "Описание" in response_text
    
    @pytest.mark.asyncio
    async def test_book_info_select_without_cover(self, mock_update, mock_context, mock_db_connection):
        """Тест: выбор книги для просмотра информации без обложки"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "1"
        mock_context.user_data['available_books'] = ["Война и мир"]
        
        # Act
        await book_info_select(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_photo.assert_not_called()
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Война и мир" in response_text
        assert "Описание" in response_text


class TestSeriesListing:
    """Тесты для отображения серий"""
    
    @pytest.mark.asyncio
    async def test_list_series_empty(self, mock_update, mock_context, mock_db_connection):
        """Тест: отображение пустого списка серий"""
        # Act
        await list_series(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "серии не найдены" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_list_series_with_books(self, mock_update, mock_context, mock_db_connection):
        """Тест: отображение серий с книгами"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO series (name) VALUES (?)", ("Русская классика",))
        series_id = cursor.lastrowid
        cursor.execute("INSERT INTO books (title, description, series_id, series_order) VALUES (?, ?, ?, ?)", 
                      ("Книга 1", "Описание 1", series_id, 1))
        cursor.execute("INSERT INTO books (title, description, series_id, series_order) VALUES (?, ?, ?, ?)", 
                      ("Книга 2", "Описание 2", series_id, 2))
        mock_db_connection.commit()
        
        # Act
        await list_series(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Русская классика" in response_text
        assert "Книга 1" in response_text
        assert "Книга 2" in response_text 