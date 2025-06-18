"""
Тесты для управления книгами
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from main import (
    add_start, add_title, add_description, add_cover, add_isbn,
    add_authors, add_series, add_series_order, finalize_book,
    delete_book_start, delete_book_select, delete_book_confirm,
    edit_book_start, edit_book_select, edit_field_select,
    edit_value_process, ADD_TITLE, ADD_DESC, ADD_COVER, ADD_ISBN,
    ADD_AUTHORS, ADD_SERIES, ADD_SERIES_ORDER
)


class TestBookAddition:
    """Тесты добавления книг"""
    
    @pytest.mark.asyncio
    async def test_add_start(self, mock_update, mock_context):
        """Тест: начало процесса добавления книги"""
        # Act
        result = await add_start(mock_update, mock_context)
        
        # Assert
        assert result == ADD_TITLE
        mock_update.message.reply_text.assert_called_once()
        assert "название книги" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_add_title_valid(self, mock_update, mock_context):
        """Тест: добавление валидного названия книги"""
        # Arrange
        mock_update.message.text = "Война и мир"
        
        # Act
        result = await add_title(mock_update, mock_context)
        
        # Assert
        assert result == ADD_DESC
        assert mock_context.user_data['new_book']['title'] == "Война и мир"
        mock_update.message.reply_text.assert_called_once()
        assert "описание" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_add_title_empty(self, mock_update, mock_context):
        """Тест: попытка добавить пустое название"""
        # Arrange
        mock_update.message.text = "   "
        
        # Act
        result = await add_title(mock_update, mock_context)
        
        # Assert
        assert result == ADD_TITLE
        mock_update.message.reply_text.assert_called_once()
        assert "не может быть пустым" in mock_update.message.reply_text.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_add_description(self, mock_update, mock_context):
        """Тест: добавление описания книги"""
        # Arrange
        mock_update.message.text = "Роман-эпопея Льва Толстого"
        mock_context.user_data['new_book'] = {'title': 'Война и мир'}
        
        # Act
        result = await add_description(mock_update, mock_context)
        
        # Assert
        assert result == ADD_COVER
        assert mock_context.user_data['new_book']['description'] == "Роман-эпопея Льва Толстого"
        mock_update.message.reply_text.assert_called_once()
        assert "обложку" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_add_cover_valid(self, mock_update, mock_context, mock_photo):
        """Тест: добавление обложки книги"""
        # Arrange
        mock_update.message.photo = [mock_photo]
        mock_context.user_data['new_book'] = {'title': 'Война и мир', 'description': 'Описание'}
        
        # Act
        result = await add_cover(mock_update, mock_context)
        
        # Assert
        assert result == ADD_ISBN
        assert 'image_blob' in mock_context.user_data['new_book']
        mock_update.message.reply_text.assert_called_once()
        assert "isbn" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_add_cover_no_photo(self, mock_update, mock_context):
        """Тест: попытка добавить обложку без фото"""
        # Arrange
        mock_update.message.photo = []
        mock_context.user_data['new_book'] = {'title': 'Война и мир', 'description': 'Описание'}
        
        # Act
        result = await add_cover(mock_update, mock_context)
        
        # Assert
        assert result == ADD_COVER
        mock_update.message.reply_text.assert_called_once()
        assert "отправь фото" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_add_isbn_valid_13(self, mock_update, mock_context):
        """Тест: добавление валидного ISBN-13"""
        # Arrange
        mock_update.message.text = "9783161484100"
        mock_context.user_data['new_book'] = {'title': 'Война и мир', 'description': 'Описание', 'image_blob': b'test'}
        
        # Act
        result = await add_isbn(mock_update, mock_context)
        
        # Assert
        assert result == ADD_AUTHORS
        assert mock_context.user_data['new_book']['isbn'] == "9783161484100"
        mock_update.message.reply_text.assert_called_once()
        assert "авторов" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_add_isbn_valid_10(self, mock_update, mock_context):
        """Тест: добавление валидного ISBN-10"""
        # Arrange
        mock_update.message.text = "316148410X"
        mock_context.user_data['new_book'] = {'title': 'Война и мир', 'description': 'Описание', 'image_blob': b'test'}
        
        # Act
        result = await add_isbn(mock_update, mock_context)
        
        # Assert
        assert result == ADD_AUTHORS
        assert mock_context.user_data['new_book']['isbn'] == "316148410X"
    
    @pytest.mark.asyncio
    async def test_add_isbn_skip(self, mock_update, mock_context):
        """Тест: пропуск ISBN"""
        # Arrange
        mock_update.message.text = "-"
        mock_context.user_data['new_book'] = {'title': 'Война и мир', 'description': 'Описание', 'image_blob': b'test'}
        
        # Act
        result = await add_isbn(mock_update, mock_context)
        
        # Assert
        assert result == ADD_AUTHORS
        assert mock_context.user_data['new_book']['isbn'] is None
    
    @pytest.mark.asyncio
    async def test_add_isbn_invalid(self, mock_update, mock_context):
        """Тест: добавление невалидного ISBN"""
        # Arrange
        mock_update.message.text = "invalid_isbn"
        mock_context.user_data['new_book'] = {'title': 'Война и мир', 'description': 'Описание', 'image_blob': b'test'}
        
        # Act
        result = await add_isbn(mock_update, mock_context)
        
        # Assert
        assert result == ADD_ISBN
        mock_update.message.reply_text.assert_called_once()
        assert "некорректный формат" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_add_authors_valid(self, mock_update, mock_context):
        """Тест: добавление авторов"""
        # Arrange
        mock_update.message.text = "Лев Толстой, Анна Каренина"
        mock_context.user_data['new_book'] = {'title': 'Война и мир', 'description': 'Описание', 'image_blob': b'test', 'isbn': '9783161484100'}
        
        # Act
        result = await add_authors(mock_update, mock_context)
        
        # Assert
        assert result == ADD_SERIES
        assert mock_context.user_data['new_book']['authors'] == ["Лев Толстой", "Анна Каренина"]
        mock_update.message.reply_text.assert_called_once()
        assert "серию" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_add_authors_empty(self, mock_update, mock_context):
        """Тест: попытка добавить пустых авторов"""
        # Arrange
        mock_update.message.text = "   "
        mock_context.user_data['new_book'] = {'title': 'Война и мир', 'description': 'Описание', 'image_blob': b'test', 'isbn': '9783161484100'}
        
        # Act
        result = await add_authors(mock_update, mock_context)
        
        # Assert
        assert result == ADD_AUTHORS
        mock_update.message.reply_text.assert_called_once()
        assert "не может быть пустым" in mock_update.message.reply_text.call_args[0][0]
    
    @pytest.mark.asyncio
    async def test_add_series_valid(self, mock_update, mock_context):
        """Тест: добавление серии"""
        # Arrange
        mock_update.message.text = "Русская классика"
        mock_context.user_data['new_book'] = {
            'title': 'Война и мир', 
            'description': 'Описание', 
            'image_blob': b'test', 
            'isbn': '9783161484100',
            'authors': ['Лев Толстой']
        }
        
        # Act
        result = await add_series(mock_update, mock_context)
        
        # Assert
        assert result == ADD_SERIES_ORDER
        assert mock_context.user_data['new_book']['series_name'] == "Русская классика"
        mock_update.message.reply_text.assert_called_once()
        assert "номер" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_add_series_skip(self, mock_update, mock_context):
        """Тест: пропуск серии"""
        # Arrange
        mock_update.message.text = "-"
        mock_context.user_data['new_book'] = {
            'title': 'Война и мир', 
            'description': 'Описание', 
            'image_blob': b'test', 
            'isbn': '9783161484100',
            'authors': ['Лев Толстой']
        }
        
        # Act
        result = await add_series(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
        # Проверяем, что книга была сохранена
        mock_update.message.reply_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_add_series_order_valid(self, mock_update, mock_context, mock_db_connection):
        """Тест: добавление номера в серии"""
        # Arrange
        mock_update.message.text = "1"
        mock_context.user_data['new_book'] = {
            'title': 'Война и мир', 
            'description': 'Описание', 
            'image_blob': b'test', 
            'isbn': '9783161484100',
            'authors': ['Лев Толстой'],
            'series_name': 'Русская классика',
            'series_id': 1
        }
        
        # Act
        result = await add_series_order(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
        assert mock_context.user_data['new_book']['series_order'] == 1
        mock_update.message.reply_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_finalize_book_complete(self, mock_update, mock_context, mock_db_connection):
        """Тест: финализация полной книги"""
        # Arrange
        mock_context.user_data['new_book'] = {
            'title': 'Война и мир', 
            'description': 'Описание', 
            'image_blob': b'test', 
            'isbn': '9783161484100',
            'authors': ['Лев Толстой'],
            'series_id': None,
            'series_order': None
        }
        
        # Act
        result = await finalize_book(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
        mock_update.message.reply_text.assert_called()
        assert "успешно добавлена" in mock_update.message.reply_text.call_args[0][0].lower()


class TestBookDeletion:
    """Тесты удаления книг"""
    
    @pytest.mark.asyncio
    async def test_delete_book_start(self, mock_update, mock_context, mock_db_connection):
        """Тест: начало процесса удаления книги"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Тестовая книга", "Описание"))
        mock_db_connection.commit()
        
        # Act
        await delete_book_start(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "выберите книгу" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_delete_book_select(self, mock_update, mock_context, mock_db_connection):
        """Тест: выбор книги для удаления"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Тестовая книга", "Описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "1"
        mock_context.user_data['books_list'] = [(1, "Тестовая книга")]
        
        # Act
        await delete_book_select(mock_update, mock_context)
        
        # Assert
        assert mock_context.user_data['book_to_delete'] == 1
        mock_update.message.reply_text.assert_called_once()
        assert "подтвердите" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_delete_book_confirm_yes(self, mock_update, mock_context, mock_db_connection):
        """Тест: подтверждение удаления книги"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Тестовая книга", "Описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "Да"
        mock_context.user_data['book_to_delete'] = 1
        
        # Act
        result = await delete_book_confirm(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
        mock_update.message.reply_text.assert_called()
        assert "удалена" in mock_update.message.reply_text.call_args[0][0].lower()
        
        # Проверяем, что книга действительно удалена
        cursor.execute("SELECT COUNT(*) FROM books WHERE id = 1")
        count = cursor.fetchone()[0]
        assert count == 0


class TestBookEditing:
    """Тесты редактирования книг"""
    
    @pytest.mark.asyncio
    async def test_edit_book_start(self, mock_update, mock_context, mock_db_connection):
        """Тест: начало процесса редактирования книги"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Тестовая книга", "Описание"))
        mock_db_connection.commit()
        
        # Act
        await edit_book_start(mock_update, mock_context)
        
        # Assert
        mock_update.message.reply_text.assert_called_once()
        assert "выберите книгу" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_edit_book_select(self, mock_update, mock_context, mock_db_connection):
        """Тест: выбор книги для редактирования"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Тестовая книга", "Описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "1"
        mock_context.user_data['books_list'] = [(1, "Тестовая книга")]
        
        # Act
        await edit_book_select(mock_update, mock_context)
        
        # Assert
        assert mock_context.user_data['book_to_edit'] == 1
        mock_update.message.reply_text.assert_called_once()
        assert "выберите поле" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_edit_field_select_description(self, mock_update, mock_context):
        """Тест: выбор поля описания для редактирования"""
        # Arrange
        mock_update.message.text = "Описание"
        mock_context.user_data['book_to_edit'] = 1
        
        # Act
        await edit_field_select(mock_update, mock_context)
        
        # Assert
        assert mock_context.user_data['field_to_edit'] == 'description'
        mock_update.message.reply_text.assert_called_once()
        assert "новое описание" in mock_update.message.reply_text.call_args[0][0].lower()
    
    @pytest.mark.asyncio
    async def test_edit_value_process_description(self, mock_update, mock_context, mock_db_connection):
        """Тест: обработка нового значения описания"""
        # Arrange
        cursor = mock_db_connection.cursor()
        cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", ("Тестовая книга", "Старое описание"))
        mock_db_connection.commit()
        
        mock_update.message.text = "Новое описание"
        mock_context.user_data['book_to_edit'] = 1
        mock_context.user_data['field_to_edit'] = 'description'
        
        # Act
        result = await edit_value_process(mock_update, mock_context)
        
        # Assert
        assert result == -1  # ConversationHandler.END
        mock_update.message.reply_text.assert_called()
        assert "обновлено" in mock_update.message.reply_text.call_args[0][0].lower()
        
        # Проверяем, что описание действительно обновлено
        cursor.execute("SELECT description FROM books WHERE id = 1")
        description = cursor.fetchone()[0]
        assert description == "Новое описание" 