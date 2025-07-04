"""
Интеграционные тесты для полных сценариев работы бота
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from main import (
    add_start, add_title, add_description, add_cover, add_isbn,
    add_authors, add_series, add_series_order, finalize_book,
    list_books, my_books, search_books, search_start, search_process,
    status_start, status_select_book, status_select_status,
    delete_book_start, delete_book_select, delete_book_confirm,
    edit_book_start, edit_book_select, edit_field_select, edit_value_process
)

@pytest.fixture(autouse=True)
def patch_main_db(mock_db_connection):
    with patch("main.cursor", mock_db_connection.cursor()), patch("main.conn", mock_db_connection):
        yield

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
        book_id = cursor.lastrowid
        mock_db_connection.commit()
        
        # Act & Assert - Шаг 1: Начало изменения статуса
        await status_start(mock_update, mock_context)
        
        # Шаг 2: Выбор книги
        mock_update.message.text = "1"
        mock_context.user_data['books_list'] = [(1, "Война и мир")]
        mock_update.effective_user.id = 12345
        await status_select_book(mock_update, mock_context)
        assert mock_context.user_data['selected_book'] == "Война и мир"
        
        # Шаг 3: Установка статуса "читаю"
        mock_update.effective_user.id = 12345
        mock_update.message.text = "📖 Читаю"
        result = await status_select_status(mock_update, mock_context)
        assert result == -1  # ConversationHandler.END
        
        # Проверяем, что статус сохранен
        cursor.execute("SELECT status FROM user_books WHERE user_id = ? AND book_id = ?", (12345, book_id))
        status = cursor.fetchone()
        assert status is not None
        assert status[0] == "reading"
        
        # Шаг 4: Изменение статуса на "прочитано"
        await status_start(mock_update, mock_context)
        mock_update.message.text = "1"
        mock_update.effective_user.id = 12345
        await status_select_book(mock_update, mock_context)
        mock_update.effective_user.id = 12345
        mock_update.message.text = "✅ Прочитано"
        await status_select_status(mock_update, mock_context)
        
        # Проверяем, что статус обновлен
        cursor.execute("SELECT status FROM user_books WHERE user_id = ? AND book_id = ?", (12345, book_id))
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
        book1_id = cursor.lastrowid
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Анна Каренина", "Описание"))
        book2_id = cursor.lastrowid
        cursor.execute("INSERT INTO authors (name) VALUES (?)", ("Лев Толстой",))
        author_id = cursor.lastrowid
        cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (book1_id, author_id))
        cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (book2_id, author_id))
        mock_db_connection.commit()
        
        # ВАЖНО: добавить cursor и conn в mock_context
        mock_context.cursor = cursor
        mock_context.conn = mock_db_connection
        
        # Диагностика: выводим содержимое таблиц
        print("BOOKS:", list(cursor.execute("SELECT id, title FROM books")))
        print("AUTHORS:", list(cursor.execute("SELECT id, name FROM authors")))
        print("BOOK_AUTHORS:", list(cursor.execute("SELECT book_id, author_id FROM book_authors")))
        
        # Act & Assert - Поиск по названию
        await search_start(mock_update, mock_context)
        mock_update.message.text = "Война"
        result = await search_process(mock_update, mock_context)
        # Диагностика: выводим результаты поиска
        # (print удалён, так как теперь используется LOWER())
        assert result == -1  # ConversationHandler.END
        
        # Проверяем результат поиска
        assert mock_update.message.reply_text.call_count == 2
        response_text = mock_update.message.reply_text.call_args_list[1][0][0]
        assert "Война и мир" in response_text
        assert "Анна Каренина" not in response_text
        
        # Поиск по автору
        mock_update.message.reply_text.reset_mock()
        await search_start(mock_update, mock_context)
        mock_update.message.text = "Толстой"
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
        book_id = cursor.lastrowid
        cursor.execute("INSERT INTO authors (name) VALUES (?)", ("Лев Толстой",))
        author_id = cursor.lastrowid
        cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (book_id, author_id))
        cursor.execute("INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)", (12345, book_id, "reading"))
        mock_db_connection.commit()
        
        # Act & Assert - Шаг 1: Начало удаления
        await delete_book_start(mock_update, mock_context)
        
        # Шаг 2: Выбор книги
        mock_update.message.text = "1"
        mock_context.user_data['available_books'] = ["Война и мир"]
        await delete_book_select(mock_update, mock_context)
        assert mock_context.user_data['book_to_delete'] == book_id
        
        # Шаг 3: Подтверждение удаления
        mock_update.message.text = "✅ Да, удалить"
        result = await delete_book_confirm(mock_update, mock_context)
        assert result == -1  # ConversationHandler.END
        
        # Проверяем, что книга удалена
        cursor.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        assert cursor.fetchone() is None
        cursor.execute("SELECT * FROM book_authors WHERE book_id = ?", (book_id,))
        assert cursor.fetchone() is None
        cursor.execute("SELECT * FROM user_books WHERE book_id = ?", (book_id,))
        assert cursor.fetchone() is None


class TestCompleteEditWorkflow:
    """Тесты полного рабочего процесса редактирования"""
    
    @pytest.mark.asyncio
    async def test_complete_edit_workflow(self, mock_update, mock_context, mock_db_connection):
        """Тест: полный процесс редактирования книги"""
        # Arrange - Добавляем книгу
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Старая книга", "Старое описание"))
        book_id = cursor.lastrowid
        mock_db_connection.commit()
        
        # Act & Assert - Шаг 1: Начало редактирования
        await edit_book_start(mock_update, mock_context)
        
        # Шаг 2: Выбор книги
        mock_update.message.text = "1"
        mock_context.user_data['available_books'] = ["Старая книга"]
        await edit_book_select(mock_update, mock_context)
        assert mock_context.user_data['book_to_edit'] == book_id
        
        # Шаг 3: Выбор поля для редактирования
        mock_update.message.text = "📝 Описание"
        result = await edit_field_select(mock_update, mock_context)
        assert result == 15  # EDIT_VALUE
        assert mock_context.user_data['edit_field'] == 'description'
        
        # Шаг 4: Ввод нового значения
        mock_update.message.text = "Новое описание"
        result = await edit_value_process(mock_update, mock_context)
        assert result == -1  # ConversationHandler.END
        
        # Проверяем, что описание обновлено
        cursor.execute("SELECT description FROM books WHERE id = ?", (book_id,))
        assert cursor.fetchone()[0] == "Новое описание"


class TestCrossFunctionality:
    """Тесты сквозной функциональности"""
    
    @pytest.mark.asyncio
    async def test_book_appears_in_all_lists(self, mock_update, mock_context, mock_db_connection, mock_photo):
        """Тест: книга появляется во всех списках после добавления"""
        # Arrange - Полностью добавляем книгу
        cursor = mock_db_connection.cursor()
        mock_context.cursor = cursor
        mock_context.conn = mock_db_connection
        mock_update.effective_user.id = 12345
        mock_context.effective_user = mock_update.effective_user

        mock_update.message.photo = [mock_photo]
        await add_start(mock_update, mock_context)
        mock_update.message.text = "Война и мир"
        await add_title(mock_update, mock_context)
        mock_update.message.text = "Роман-эпопея"
        await add_description(mock_update, mock_context)
        await add_cover(mock_update, mock_context)
        mock_update.message.text = "9783161484100"
        await add_isbn(mock_update, mock_context)
        mock_update.message.text = "Лев Толстой"
        await add_authors(mock_update, mock_context)
        mock_update.message.text = "-"
        await add_series(mock_update, mock_context)
        
        # Act & Assert - Проверка в общем списке
        mock_update.message.reply_text.reset_mock()
        await list_books(mock_update, mock_context)
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Война и мир" in response_text
        
        # Проверка в поиске
        mock_update.message.reply_text.reset_mock()
        await search_start(mock_update, mock_context)
        mock_update.message.text = "Война"
        await search_process(mock_update, mock_context)
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Война и мир" in response_text

    @pytest.mark.asyncio
    async def test_status_affects_my_books(self, mock_update, mock_context, mock_db_connection):
        """Тест: статус влияет на отображение в 'Мои книги'"""
        # Arrange - Добавляем книгу и устанавливаем статус
        cursor = mock_db_connection.cursor()
        mock_context.cursor = cursor
        mock_context.conn = mock_db_connection
        mock_update.effective_user.id = 12345
        mock_context.effective_user = mock_update.effective_user

        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Война и мир", "Описание"))
        book_id = cursor.lastrowid
        cursor.execute("INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)", (12345, book_id, "reading"))
        mock_db_connection.commit()
        
        # Act
        await my_books(mock_update, mock_context)
        
        # Assert
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Война и мир" in response_text
        assert "читаю" in response_text.lower()
        
        # Изменяем статус
        mock_update.message.reply_text.reset_mock()
        await status_start(mock_update, mock_context)
        mock_update.message.text = "1"
        mock_context.user_data['available_books'] = ["Война и мир"]
        await status_select_book(mock_update, mock_context)
        mock_update.message.text = "✅ Прочитано"
        await status_select_status(mock_update, mock_context)
        
        # Проверяем обновленный статус
        mock_update.message.reply_text.reset_mock()
        await my_books(mock_update, mock_context)
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "прочитано" in response_text.lower() 