"""
Тесты для управления статусами книг
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from main import (
    status_start, status_select_book, status_select_status, status_cancel
)


class TestStatusManagement:
    """Тесты для управления статусами книг"""
    
    @pytest.mark.asyncio
    async def test_status_start(self, mock_update, mock_context, mock_db_connection):
        """Тест: начало процесса изменения статуса"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        # Act
        await status_start(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "выберите книгу" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_status_start_no_books(self, mock_update, mock_context, mock_db_connection):
        """Тест: попытка изменить статус при отсутствии книг"""
        # Act
        await status_start(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "книг нет" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_status_select_book_valid(self, mock_update, mock_context, mock_db_connection):
        """Тест: выбор книги для изменения статуса"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "1"
        mock_context.user_data['books_list'] = [(1, "Война и мир")]
        
        # Act
        await status_select_book(mock_update, mock_context)
        
        # Assert
        assert mock_context.user_data['book_for_status'] == 1
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "выберите статус" in response_text.lower()
        assert "планирую" in response_text.lower()
        assert "читаю" in response_text.lower()
        assert "закончил" in response_text.lower()
        assert "отменил" in response_text.lower()
    
    @pytest.mark.asyncio
    async def test_status_select_book_invalid(self, mock_update, mock_context, mock_db_connection):
        """Тест: выбор невалидной книги для изменения статуса"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "999"
        mock_context.user_data['books_list'] = [(1, "Война и мир")]
        
        # Act
        await status_select_book(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "неверный номер" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_status_select_status_planning(self, mock_update, mock_context, mock_db_connection):
        """Тест: установка статуса 'планирую'"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "Планирую"
        mock_context.user_data['book_for_status'] = 1
        
        # Act
        result = await status_select_status(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
        mock_update.message.reply_text.assert_called()
        assert "статус установлен" in mock_update.message.reply_text.call_args[0][0].lower()
        
        # Проверяем, что статус сохранен в базе
        cursor.execute("SELECT status FROM user_books WHERE user_id = ? AND book_id = ?", (12345, 1))
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "planning"
    
    @pytest.mark.asyncio
    async def test_status_select_status_reading(self, mock_update, mock_context, mock_db_connection):
        """Тест: установка статуса 'читаю'"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "Читаю"
        mock_context.user_data['book_for_status'] = 1
        
        # Act
        result = await status_select_status(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
        
        # Проверяем, что статус сохранен в базе
        cursor.execute("SELECT status FROM user_books WHERE user_id = ? AND book_id = ?", (12345, 1))
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "reading"
    
    @pytest.mark.asyncio
    async def test_status_select_status_finished(self, mock_update, mock_context, mock_db_connection):
        """Тест: установка статуса 'закончил'"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "Закончил"
        mock_context.user_data['book_for_status'] = 1
        
        # Act
        result = await status_select_status(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
        
        # Проверяем, что статус сохранен в базе
        cursor.execute("SELECT status FROM user_books WHERE user_id = ? AND book_id = ?", (12345, 1))
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "finished"
    
    @pytest.mark.asyncio
    async def test_status_select_status_cancelled(self, mock_update, mock_context, mock_db_connection):
        """Тест: установка статуса 'отменил'"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "Отменил"
        mock_context.user_data['book_for_status'] = 1
        
        # Act
        result = await status_select_status(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
        
        # Проверяем, что статус сохранен в базе
        cursor.execute("SELECT status FROM user_books WHERE user_id = ? AND book_id = ?", (12345, 1))
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_status_select_status_invalid(self, mock_update, mock_context, mock_db_connection):
        """Тест: попытка установить невалидный статус"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "Неверный статус"
        mock_context.user_data['book_for_status'] = 1
        
        # Act
        await status_select_status(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "неверный статус" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_status_update_existing(self, mock_update, mock_context, mock_db_connection):
        """Тест: обновление существующего статуса"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        cursor.execute("INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)", (12345, 1, "planning"))
        mock_db_connection.commit()
        
        mock_update.message.text = "Читаю"
        mock_context.user_data['book_for_status'] = 1
        
        # Act
        result = await status_select_status(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
        
        # Проверяем, что статус обновлен
        cursor.execute("SELECT status FROM user_books WHERE user_id = ? AND book_id = ?", (12345, 1))
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "reading"
    
    @pytest.mark.asyncio
    async def test_status_cancel(self, mock_update, mock_context):
        """Тест: отмена изменения статуса"""
        # Act
        result = await status_cancel(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
        mock_update.message.reply_text.assert_called_once()
        assert "отменено" in mock_update.message.reply_text.call_args[0][0].lower() 