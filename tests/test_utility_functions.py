"""
Тесты для утилитных функций бота
"""
import pytest
import json
import tempfile
import os
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes
from main import (
    show_statistics, export_library, show_help, menu_handler,
    universal_cancel, universal_menu, add_isbn
)


class TestStatistics:
    """Тесты для функции статистики"""

    @pytest.mark.asyncio
    async def test_show_statistics_empty(self, mock_update, mock_context, mock_db_connection):
        """Тест статистики с пустой библиотекой"""
        await show_statistics(mock_update, mock_context)
        response_text = mock_update.message.reply_text.call_args[0][0].lower()
        assert "всего книг:** 0" in response_text
        assert "всего ваших книг:** 0" in response_text

    @pytest.mark.asyncio
    async def test_show_statistics_with_data(self, mock_update, mock_context, mock_db_connection):
        """Тест статистики с данными в библиотеке"""
        # Подготовка тестовых данных
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO series (name) VALUES ('Русская классика')")
        cursor.execute("INSERT INTO authors (name) VALUES ('Автор 1'), ('Автор 2')")
        cursor.execute("""
            INSERT INTO books (title, description, series_id, series_order)
            VALUES ('Книга 1', 'Описание 1', 1, 1),
                   ('Книга 2', 'Описание 2', 1, 2),
                   ('Книга 3', 'Описание 3', NULL, NULL)
        """)
        cursor.execute("""
            INSERT INTO book_authors (book_id, author_id)
            VALUES (1, 1), (2, 2), (3, 1)
        """)
        cursor.execute("""
            INSERT INTO user_books (user_id, book_id, status)
            VALUES (12345, 1, 'finished'), (12345, 2, 'reading')
        """)
        mock_db_connection.commit()

        await show_statistics(mock_update, mock_context)
        response_text = mock_update.message.reply_text.call_args[0][0].lower()
        assert "статистика библиотеки" in response_text.lower()
        assert "всего книг" in response_text.lower()
        assert "серий" in response_text.lower()
        assert "авторов" in response_text.lower()
        assert "прочитано: 1" in response_text
        assert "читаю: 1" in response_text
        assert "всего ваших книг:** 2" in response_text


class TestExportLibrary:
    """Тесты для функции экспорта библиотеки"""

    @pytest.mark.asyncio
    async def test_export_library_empty(self, mock_update, mock_context, mock_db_connection):
        """Тест экспорта пустой библиотеки"""
        await export_library(mock_update, mock_context)
        # Для пустой библиотеки должно быть сообщение, а не документ
        assert mock_update.message.reply_text.called
        response_text = mock_update.message.reply_text.call_args[0][0].lower()
        assert "библиотека пуста" in response_text

    @pytest.mark.asyncio
    async def test_export_library_with_data(self, mock_update, mock_context, mock_db_connection):
        """Тест экспорта библиотеки с данными"""
        # Подготовка тестовых данных
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO series (name) VALUES ('Русская классика')")
        cursor.execute("INSERT INTO authors (name) VALUES ('Автор 1'), ('Автор 2')")
        cursor.execute("""
            INSERT INTO books (title, description, series_id, series_order)
            VALUES ('Книга 1', 'Описание 1', 1, 1),
                   ('Книга 2', 'Описание 2', 1, 2)
        """)
        cursor.execute("""
            INSERT INTO book_authors (book_id, author_id)
            VALUES (1, 1), (2, 2)
        """)
        mock_db_connection.commit()

        await export_library(mock_update, mock_context)
        assert mock_update.message.reply_document.called
        call_args = mock_update.message.reply_document.call_args[1]
        assert 'filename' in call_args
        assert call_args['filename'].startswith('library_export_')
        assert call_args['filename'].endswith('.txt')


class TestHelpAndMenu:
    """Тесты для функций справки и меню"""

    @pytest.mark.asyncio
    async def test_show_help(self, mock_update, mock_context):
        """Тест отображения справки"""
        await show_help(mock_update, mock_context)
        response_text = mock_update.message.reply_text.call_args[0][0].lower()
        assert "справка по командам" in response_text
        assert "основные команды:" in response_text
        assert "управление книгами:" in response_text
        assert "просмотр и поиск:" in response_text

    @pytest.mark.asyncio
    async def test_menu_handler(self, mock_update, mock_context):
        """Тест обработчика меню"""
        await menu_handler(mock_update, mock_context)
        response_text = mock_update.message.reply_text.call_args[0][0].lower()
        assert "выберите действие:" in response_text

    @pytest.mark.asyncio
    async def test_universal_cancel(self, mock_update, mock_context):
        """Тест универсальной отмены"""
        await universal_cancel(mock_update, mock_context)
        response_text = mock_update.message.reply_text.call_args[0][0].lower()
        assert "операция отменена" in response_text
        assert "возвращаюсь в главное меню" in response_text

    @pytest.mark.asyncio
    async def test_universal_menu(self, mock_update, mock_context):
        """Тест универсального меню"""
        await universal_menu(mock_update, mock_context)
        response_text = mock_update.message.reply_text.call_args[0][0].lower()
        assert "возвращаюсь в главное меню" in response_text


class TestInputValidation:
    """Тесты для валидации ввода"""

    @pytest.mark.asyncio
    async def test_isbn_validation_various_formats(self, mock_update, mock_context):
        """Тест валидации ISBN в различных форматах"""
        # Подготовка контекста для add_isbn
        mock_context.user_data['new_book'] = {
            'title': 'Тестовая книга',
            'description': 'Описание',
            'image_blob': b'test_data'
        }
        
        # Тест с корректным ISBN-13
        mock_update.message.text = "978-3-16-148410-0"
        result = await add_isbn(mock_update, mock_context)
        assert result == 4  # ADD_AUTHORS (переход к следующему шагу)

        # Тест с корректным ISBN-10
        mock_update.message.text = "0-7475-3269-9"
        result = await add_isbn(mock_update, mock_context)
        assert result == 4  # ADD_AUTHORS (переход к следующему шагу)

        # Тест с некорректным ISBN
        mock_update.message.text = "123-456-789"
        result = await add_isbn(mock_update, mock_context)
        assert result == 3  # ADD_ISBN (остается в том же состоянии)

        # Тест с пустым ISBN
        mock_update.message.text = ""
        result = await add_isbn(mock_update, mock_context)
        assert result == 3  # ADD_ISBN (остается в том же состоянии)

        # Тест с отменой
        mock_update.message.text = "/cancel"
        result = await add_isbn(mock_update, mock_context)
        assert result == 3  # ADD_ISBN (остается в том же состоянии, так как /cancel обрабатывается отдельно) 