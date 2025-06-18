"""
Интеграционные тесты для полных сценариев работы бота
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from main import (
    add_start, add_title, add_description, add_cover, add_isbn,
    add_authors, add_series, add_series_order, finalize_book,
    list_books, my_books, search_books, search_process,
    status_start, status_select_book, status_select_status,
    delete_book_start, delete_book_select, delete_book_confirm,
    edit_book_start, edit_book_select, edit_field_select, edit_value_process
)


class TestCompleteBookWorkflow:
    """Тесты полного рабочего процесса с книгой"""
    
    @pytest.mark.asyncio
    async def test_complete_book_addition_workflow(self, mock_update, mock_context, mock_db_connection, mock_photo):
        """Тест: полный процесс добавления книги"""
        # Arrange
        mock_update.message.photo = [mock_photo]
        
        # Act & Assert - Шаг 1: Начало добавления
        result = await add_start(mock_update, mock_context)
        assert result == 0  # ADD_TITLE
        
        # Шаг 2: Добавление названия
        mock_update.message.text = "Война и мир"
        result = await add_title(mock_update, mock_context)
        assert result == 1  # ADD_DESC
        assert mock_context.user_data['new_book']['title'] == "Война и мир"
        
        # Шаг 3: Добавление описания
        mock_update.message.text = "Роман-эпопея Льва Толстого"
        result = await add_description(mock_update, mock_context)
        assert result == 2  # ADD_COVER
        assert mock_context.user_data['new_book']['description'] == "Роман-эпопея Льва Толстого"
        
        # Шаг 4: Добавление обложки
        result = await add_cover(mock_update, mock_context)
        assert result == 3  # ADD_ISBN
        assert 'image_blob' in mock_context.user_data['new_book']
        
        # Шаг 5: Добавление ISBN
        mock_update.message.text = "9783161484100"
        result = await add_isbn(mock_update, mock_context)
        assert result == 4  # ADD_AUTHORS
        assert mock_context.user_data['new_book']['isbn'] == "9783161484100"
        
        # Шаг 6: Добавление авторов
        mock_update.message.text = "Лев Толстой"
        result = await add_authors(mock_update, mock_context)
        assert result == 5  # ADD_SERIES
        assert mock_context.user_data['new_book']['authors'] == ["Лев Толстой"]
        
        # Шаг 7: Добавление серии
        mock_update.message.text = "Русская классика"
        result = await add_series(mock_update, mock_context)
        assert result == 6  # ADD_SERIES_ORDER
        assert mock_context.user_data['new_book']['series_name'] == "Русская классика"
        
        # Шаг 8: Добавление номера в серии
        mock_update.message.text = "1"
        result = await add_series_order(mock_update, mock_context)
        assert result == -1  # ConversationHandler.END
        
        # Проверяем, что книга сохранена в базе
        cursor = mock_db_connection.cursor()
        cursor.execute("SELECT title, description, isbn FROM books WHERE title = ?", ("Война и мир",))
        book = cursor.fetchone()
        assert book is not None
        assert book[0] == "Война и мир"
        assert book[1] == "Роман-эпопея Льва Толстого"
        assert book[2] == "9783161484100"
        
        # Проверяем авторов
        cursor.execute("""
            SELECT a.name FROM authors a 
            JOIN book_authors ba ON a.id = ba.author_id 
            JOIN books b ON ba.book_id = b.id 
            WHERE b.title = ?
        """, ("Война и мир",))
        authors = [row[0] for row in cursor.fetchall()]
        assert "Лев Толстой" in authors
        
        # Проверяем серию
        cursor.execute("""
            SELECT s.name, b.series_order FROM series s 
            JOIN books b ON s.id = b.series_id 
            WHERE b.title = ?
        """, ("Война и мир",))
        series_info = cursor.fetchone()
        assert series_info is not None
        assert series_info[0] == "Русская классика"
        assert series_info[1] == 1
    
    @pytest.mark.asyncio
    async def test_complete_book_without_series_workflow(self, mock_update, mock_context, mock_db_connection, mock_photo):
        """Тест: полный процесс добавления книги без серии"""
        # Arrange
        mock_update.message.photo = [mock_photo]
        
        # Act & Assert - Шаг 1-6: Аналогично предыдущему тесту
        await add_start(mock_update, mock_context)
        
        mock_update.message.text = "Анна Каренина"
        await add_title(mock_update, mock_context)
        
        mock_update.message.text = "Роман Льва Толстого"
        await add_description(mock_update, mock_context)
        
        await add_cover(mock_update, mock_context)
        
        mock_update.message.text = "9783161484101"
        await add_isbn(mock_update, mock_context)
        
        mock_update.message.text = "Лев Толстой"
        await add_authors(mock_update, mock_context)
        
        # Шаг 7: Пропуск серии
        mock_update.message.text = "-"
        result = await add_series(mock_update, mock_context)
        assert result == -1  # ConversationHandler.END
        
        # Проверяем, что книга сохранена без серии
        cursor = mock_db_connection.cursor()
        cursor.execute("SELECT title, series_id FROM books WHERE title = ?", ("Анна Каренина",))
        book = cursor.fetchone()
        assert book is not None
        assert book[1] is None  # series_id должен быть None


class TestCompleteStatusWorkflow:
    """Тесты полного рабочего процесса со статусами"""
    
    @pytest.mark.asyncio
    async def test_complete_status_workflow(self, mock_update, mock_context, mock_db_connection):
        """Тест: полный процесс изменения статуса книги"""
        # Arrange - Добавляем книгу
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        mock_db_connection.commit()
        
        # Act & Assert - Шаг 1: Начало изменения статуса
        await status_start(mock_update, mock_context)
        
        # Шаг 2: Выбор книги
        mock_update.message.text = "1"
        mock_context.user_data['books_list'] = [(1, "Война и мир")]
        await status_select_book(mock_update, mock_context)
        assert mock_context.user_data['book_for_status'] == 1
        
        # Шаг 3: Установка статуса "читаю"
        mock_update.message.text = "Читаю"
        result = await status_select_status(mock_update, mock_context)
        assert result == -1  # ConversationHandler.END
        
        # Проверяем, что статус сохранен
        cursor.execute("SELECT status FROM user_books WHERE user_id = ? AND book_id = ?", (12345, 1))
        status = cursor.fetchone()
        assert status is not None
        assert status[0] == "reading"
        
        # Шаг 4: Изменение статуса на "закончил"
        await status_start(mock_update, mock_context)
        mock_update.message.text = "1"
        await status_select_book(mock_update, mock_context)
        mock_update.message.text = "Закончил"
        await status_select_status(mock_update, mock_context)
        
        # Проверяем, что статус обновлен
        cursor.execute("SELECT status FROM user_books WHERE user_id = ? AND book_id = ?", (12345, 1))
        status = cursor.fetchone()
        assert status is not None
        assert status[0] == "finished"


class TestCompleteSearchWorkflow:
    """Тесты полного рабочего процесса поиска"""
    
    @pytest.mark.asyncio
    async def test_complete_search_workflow(self, mock_update, mock_context, mock_db_connection):
        """Тест: полный процесс поиска книг"""
        # Arrange - Добавляем книги и авторов
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Анна Каренина", "Описание"))
        cursor.execute("INSERT INTO authors (name) VALUES (?)", ("Лев Толстой",))
        cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (1, 1))
        cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (2, 1))
        mock_db_connection.commit()
        
        # Act & Assert - Поиск по названию
        await search_start(mock_update, mock_context)
        mock_update.message.text = "война"
        result = await search_process(mock_update, mock_context)
        assert result == -1  # ConversationHandler.END
        
        # Проверяем результат поиска
        mock_update.message.reply_text.assert_called_once()
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Война и мир" in response_text
        assert "Анна Каренина" not in response_text
        
        # Поиск по автору
        mock_update.message.reply_text.reset_mock()
        await search_start(mock_update, mock_context)
        mock_update.message.text = "толстой"
        await search_process(mock_update, mock_context)
        
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Война и мир" in response_text
        assert "Анна Каренина" in response_text
        assert "Лев Толстой" in response_text


class TestCompleteDeleteWorkflow:
    """Тесты полного рабочего процесса удаления"""
    
    @pytest.mark.asyncio
    async def test_complete_delete_workflow(self, mock_update, mock_context, mock_db_connection):
        """Тест: полный процесс удаления книги"""
        # Arrange - Добавляем книгу
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        cursor.execute("INSERT INTO authors (name) VALUES (?)", ("Лев Толстой",))
        cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (1, 1))
        cursor.execute("INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)", (12345, 1, "reading"))
        mock_db_connection.commit()
        
        # Act & Assert - Шаг 1: Начало удаления
        await delete_book_start(mock_update, mock_context)
        
        # Шаг 2: Выбор книги
        mock_update.message.text = "1"
        mock_context.user_data['books_list'] = [(1, "Война и мир")]
        await delete_book_select(mock_update, mock_context)
        assert mock_context.user_data['book_to_delete'] == 1
        
        # Шаг 3: Подтверждение удаления
        mock_update.message.text = "Да"
        result = await delete_book_confirm(mock_update, mock_context)
        assert result == -1  # ConversationHandler.END
        
        # Проверяем, что книга удалена
        cursor.execute("SELECT COUNT(*) FROM books WHERE id = 1")
        count = cursor.fetchone()[0]
        assert count == 0
        
        # Проверяем, что связанные записи тоже удалены
        cursor.execute("SELECT COUNT(*) FROM book_authors WHERE book_id = 1")
        count = cursor.fetchone()[0]
        assert count == 0
        
        cursor.execute("SELECT COUNT(*) FROM user_books WHERE book_id = 1")
        count = cursor.fetchone()[0]
        assert count == 0


class TestCompleteEditWorkflow:
    """Тесты полного рабочего процесса редактирования"""
    
    @pytest.mark.asyncio
    async def test_complete_edit_workflow(self, mock_update, mock_context, mock_db_connection):
        """Тест: полный процесс редактирования книги"""
        # Arrange - Добавляем книгу
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description, isbn) VALUES (?, ?, ?)", 
                      ("Война и мир", "Старое описание", "9783161484100"))
        mock_db_connection.commit()
        
        # Act & Assert - Шаг 1: Начало редактирования
        await edit_book_start(mock_update, mock_context)
        
        # Шаг 2: Выбор книги
        mock_update.message.text = "1"
        mock_context.user_data['books_list'] = [(1, "Война и мир")]
        await edit_book_select(mock_update, mock_context)
        assert mock_context.user_data['book_to_edit'] == 1
        
        # Шаг 3: Выбор поля для редактирования
        mock_update.message.text = "Описание"
        await edit_field_select(mock_update, mock_context)
        assert mock_context.user_data['field_to_edit'] == 'description'
        
        # Шаг 4: Ввод нового значения
        mock_update.message.text = "Новое описание"
        result = await edit_value_process(mock_update, mock_context)
        assert result == -1  # ConversationHandler.END
        
        # Проверяем, что описание обновлено
        cursor.execute("SELECT description FROM books WHERE id = 1")
        description = cursor.fetchone()[0]
        assert description == "Новое описание"
        
        # Редактирование ISBN
        await edit_book_start(mock_update, mock_context)
        mock_update.message.text = "1"
        await edit_book_select(mock_update, mock_context)
        mock_update.message.text = "ISBN"
        await edit_field_select(mock_update, mock_context)
        mock_update.message.text = "9783161484101"
        await edit_value_process(mock_update, mock_context)
        
        # Проверяем, что ISBN обновлен
        cursor.execute("SELECT isbn FROM books WHERE id = 1")
        isbn = cursor.fetchone()[0]
        assert isbn == "9783161484101"


class TestCrossFunctionality:
    """Тесты кросс-функциональности"""
    
    @pytest.mark.asyncio
    async def test_book_appears_in_all_lists(self, mock_update, mock_context, mock_db_connection, mock_photo):
        """Тест: книга появляется во всех списках после добавления"""
        # Arrange - Добавляем книгу
        mock_update.message.photo = [mock_photo]
        
        await add_start(mock_update, mock_context)
        mock_update.message.text = "Война и мир"
        await add_title(mock_update, mock_context)
        mock_update.message.text = "Описание"
        await add_description(mock_update, mock_context)
        await add_cover(mock_update, mock_context)
        mock_update.message.text = "9783161484100"
        await add_isbn(mock_update, mock_context)
        mock_update.message.text = "Лев Толстой"
        await add_authors(mock_update, mock_context)
        mock_update.message.text = "-"
        await add_series(mock_update, mock_context)
        
        # Act & Assert - Проверяем, что книга есть в общем списке
        mock_update.message.reply_text.reset_mock()
        await list_books(mock_update, mock_context)
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Война и мир" in response_text
        
        # Проверяем, что книга есть в поиске
        mock_update.message.reply_text.reset_mock()
        await search_start(mock_update, mock_context)
        mock_update.message.text = "война"
        await search_process(mock_update, mock_context)
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Война и мир" in response_text
    
    @pytest.mark.asyncio
    async def test_status_affects_my_books(self, mock_update, mock_context, mock_db_connection):
        """Тест: статус влияет на отображение в 'Мои книги'"""
        # Arrange - Добавляем книгу и устанавливаем статус
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        cursor.execute("INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)", (12345, 1, "reading"))
        mock_db_connection.commit()
        
        # Act
        await my_books(mock_update, mock_context)
        
        # Assert
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Война и мир" in response_text
        assert "читаю" in response_text.lower()
        
        # Изменяем статус
        await status_start(mock_update, mock_context)
        mock_update.message.text = "1"
        mock_context.user_data['books_list'] = [(1, "Война и мир")]
        await status_select_book(mock_update, mock_context)
        mock_update.message.text = "Закончил"
        await status_select_status(mock_update, mock_context)
        
        # Проверяем обновленный статус
        mock_update.message.reply_text.reset_mock()
        await my_books(mock_update, mock_context)
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "закончил" in response_text.lower() 