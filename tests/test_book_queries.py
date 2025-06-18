"""
Тесты для запросов книг
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from main import (
    list_books, my_books, search_books, search_start, search_process,
    book_info_start, book_info_select, list_series
)


class TestBookListing:
    """Тесты для отображения списков книг"""
    
    @pytest.mark.asyncio
    async def test_list_books_empty(self, mock_update, mock_context, mock_db_connection):
        """Тест: отображение пустого списка книг"""
        # Act
        await list_books(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "книг нет" in mock_update.message.reply_text.call_args[0][0].lower()
    
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
        assert "у вас нет книг" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_my_books_with_statuses(self, mock_update, mock_context, mock_db_connection):
        """Тест: отображение моих книг со статусами"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Книга 1", "Описание 1"))
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Книга 2", "Описание 2"))
        cursor.execute("INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)", (12345, 1, "reading"))
        cursor.execute("INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)", (12345, 2, "finished"))
        mock_db_connection.commit()
        
        # Act
        await my_books(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Книга 1" in response_text
        assert "Книга 2" in response_text
        assert "читаю" in response_text.lower()
        assert "закончил" in response_text.lower()


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
        mock_db_connection.commit()
        
        mock_update.message.text = "война"
        
        # Act
        result = await search_process(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
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
        cursor.execute("INSERT INTO authors (name) VALUES (?)", ("Лев Толстой",))
        cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (1, 1))
        mock_db_connection.commit()
        
        mock_update.message.text = "толстой"
        
        # Act
        result = await search_process(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
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
        assert result == -1  # ConversationHandler.END
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
        assert "введите поисковый запрос" in mock_update.message.reply_text.call_args[0][0].lower()


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
        mock_context.user_data['books_list'] = [(1, "Война и мир")]
        
        # Act
        await book_info_select(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_photo.assert_called_once()
        mock_update.message.reply_text.assert_called()
        response_text = mock_update.message.reply_text.call_args[0][0]
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
        mock_context.user_data['books_list'] = [(1, "Война и мир")]
        
        # Act
        await book_info_select(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_photo.assert_not_called()
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Война и мир" in response_text
        assert "Описание" in response_text
        assert "обложка отсутствует" in response_text.lower()


class TestSeriesListing:
    """Тесты для отображения серий"""
    
    @pytest.mark.asyncio
    async def test_list_series_empty(self, mock_update, mock_context, mock_db_connection):
        """Тест: отображение пустого списка серий"""
        # Act
        await list_series(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "серий нет" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_list_series_with_books(self, mock_update, mock_context, mock_db_connection):
        """Тест: отображение серий с книгами"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO series (name) VALUES (?)", ("Русская классика",))
        cursor.execute("INSERT INTO books (title, description, series_id, series_order) VALUES (?, ?, ?, ?)", 
                      ("Книга 1", "Описание 1", 1, 1))
        cursor.execute("INSERT INTO books (title, description, series_id, series_order) VALUES (?, ?, ?, ?)", 
                      ("Книга 2", "Описание 2", 1, 2))
        mock_db_connection.commit()
        
        # Act
        await list_series(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Русская классика" in response_text
        assert "Книга 1" in response_text
        assert "Книга 2" in response_text 