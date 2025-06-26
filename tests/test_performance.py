"""
Тесты производительности для больших объемов данных
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from main import (
    list_books, my_books, search_books, search_start, search_process,
    list_series, show_statistics, export_library
)

@pytest.fixture(autouse=True)
def patch_main_db(mock_db_connection, mock_context):
    mock_context.cursor = mock_db_connection.cursor()
    mock_context.conn = mock_db_connection
    yield

class TestPerformanceWithLargeData:
    """Тесты производительности с большими объемами данных"""
    
    @pytest.mark.asyncio
    async def test_list_books_performance(self, mock_update, mock_context, mock_db_connection):
        """Тест: производительность отображения большого списка книг"""
        # Arrange - Добавляем много книг
        cursor = mock_db_connection.cursor()
        for i in range(100):
            cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", 
                          (f"Книга {i}", f"Описание {i}"))
        mock_db_connection.commit()
        
        # Act
        start_time = time.time()
        await list_books(mock_update, mock_context)
        end_time = time.time()
        
        # Assert
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Должно выполняться менее чем за 1 секунду
        
        # Проверяем, что все книги отображаются
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Книга 0" in response_text
        assert "Книга 99" in response_text
    
    @pytest.mark.asyncio
    async def test_search_performance(self, mock_update, mock_context, mock_db_connection):
        """Тест: производительность поиска в большом объеме данных"""
        # Arrange - Добавляем много книг с разными названиями
        cursor = mock_db_connection.cursor()
        for i in range(1000):
            cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", 
                          (f"Книга {i}", f"Описание {i}"))
        mock_db_connection.commit()
        
        # Act
        await search_start(mock_update, mock_context)
        start_time = time.time()
        mock_update.message.text = "книга 500"
        await search_process(mock_update, mock_context)
        end_time = time.time()
        
        # Assert
        execution_time = end_time - start_time
        assert execution_time < 0.5  # Должно выполняться менее чем за 0.5 секунды
        
        # Проверяем результат поиска
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Книга 500" in response_text
    
    @pytest.mark.asyncio
    async def test_my_books_performance(self, mock_update, mock_context, mock_db_connection):
        """Тест: производительность отображения моих книг с большим количеством статусов"""
        # Arrange - Добавляем много книг и статусов
        cursor = mock_db_connection.cursor()
        for i in range(500):
            cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", 
                          (f"Книга {i}", f"Описание {i}"))
            cursor.execute("INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)", 
                          (12345, i+1, "reading" if i % 2 == 0 else "finished"))
        mock_db_connection.commit()
        
        # Act
        start_time = time.time()
        await my_books(mock_update, mock_context)
        end_time = time.time()
        
        # Assert
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Должно выполняться менее чем за 1 секунду
        
        # Проверяем, что статусы отображаются корректно
        response_text = mock_update.message.reply_text.call_args[0][0].lower()
        if "нет отмеченных книг" in response_text:
            assert "нет отмеченных книг" in response_text
        else:
            assert "читаю" in response_text
            assert "прочитано" in response_text
    
    @pytest.mark.asyncio
    async def test_series_performance(self, mock_update, mock_context, mock_db_connection):
        """Тест: производительность отображения серий с большим количеством книг"""
        # Arrange - Добавляем много серий и книг
        cursor = mock_db_connection.cursor()
        for i in range(50):
            cursor.execute("INSERT INTO series (name) VALUES (?)", (f"Серия {i}",))
            for j in range(20):
                cursor.execute("INSERT INTO books (title, description, series_id, series_order) VALUES (?, ?, ?, ?)", 
                              (f"Книга {i}-{j}", f"Описание {i}-{j}", i+1, j+1))
        mock_db_connection.commit()
        
        # Act
        start_time = time.time()
        await list_series(mock_update, mock_context)
        end_time = time.time()
        
        # Assert
        execution_time = end_time - start_time
        assert execution_time < 1.0  # Должно выполняться менее чем за 1 секунду
        
        # Проверяем, что серии отображаются
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "Серия 0" in response_text
        assert "Серия 49" in response_text
    
    @pytest.mark.asyncio
    async def test_statistics_performance(self, mock_update, mock_context, mock_db_connection):
        """Тест: производительность расчета статистики"""
        # Arrange - Добавляем много данных
        cursor = mock_db_connection.cursor()
        
        # Добавляем серии
        for i in range(20):
            cursor.execute("INSERT INTO series (name) VALUES (?)", (f"Серия {i}",))
        
        # Добавляем авторов
        for i in range(100):
            cursor.execute("INSERT INTO authors (name) VALUES (?)", (f"Автор {i}",))
        
        # Добавляем книги
        for i in range(1000):
            series_id = (i % 20) + 1
            cursor.execute("INSERT INTO books (title, description, series_id, series_order) VALUES (?, ?, ?, ?)", 
                          (f"Книга {i}", f"Описание {i}", series_id, (i % 10) + 1))
            
            # Добавляем связи с авторами
            author_id = (i % 100) + 1
            cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (i+1, author_id))
            
            # Добавляем статусы
            status = "reading" if i % 3 == 0 else "finished" if i % 3 == 1 else "planning"
            cursor.execute("INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)", 
                          (12345, i+1, status))
        
        mock_db_connection.commit()
        
        # Act
        start_time = time.time()
        await show_statistics(mock_update, mock_context)
        end_time = time.time()
        
        # Assert
        execution_time = end_time - start_time
        assert execution_time < 2.0  # Должно выполняться менее чем за 2 секунды
        
        # Проверяем статистику
        response_text = mock_update.message.reply_text.call_args[0][0]
        assert "1000" in response_text  # Общее количество книг
        assert "20" in response_text    # Количество серий
        assert "100" in response_text   # Количество авторов
    
    @pytest.mark.asyncio
    async def test_export_performance(self, mock_update, mock_context, mock_db_connection):
        """Тест: производительность экспорта большого объема данных"""
        # Arrange - Добавляем много данных
        cursor = mock_db_connection.cursor()
        
        # Добавляем серии
        for i in range(10):
            cursor.execute("INSERT INTO series (name) VALUES (?)", (f"Серия {i}",))
        
        # Добавляем авторов
        for i in range(50):
            cursor.execute("INSERT INTO authors (name) VALUES (?)", (f"Автор {i}",))
        
        # Добавляем книги с обложками
        for i in range(500):
            series_id = (i % 10) + 1
            image_blob = f"image_data_{i}".encode()
            cursor.execute("INSERT INTO books (title, description, image_blob, series_id, series_order, isbn) VALUES (?, ?, ?, ?, ?, ?)", 
                          (f"Книга {i}", f"Описание {i}", image_blob, series_id, (i % 10) + 1, f"9783161484{i:03d}"))
            
            # Добавляем связи с авторами
            author_id = (i % 50) + 1
            cursor.execute("INSERT INTO book_authors (book_id, author_id) VALUES (?, ?)", (i+1, author_id))
            
            # Добавляем статусы
            status = "reading" if i % 3 == 0 else "finished" if i % 3 == 1 else "planning"
            cursor.execute("INSERT INTO user_books (user_id, book_id, status) VALUES (?, ?, ?)", 
                          (12345, i+1, status))
        
        mock_db_connection.commit()
        
        # Act
        start_time = time.time()
        await export_library(mock_update, mock_context)
        end_time = time.time()
        
        # Assert
        execution_time = end_time - start_time
        assert execution_time < 5.0  # Должно выполняться менее чем за 5 секунд
        
        # Проверяем, что экспорт выполнен
        mock_update.message.reply_document.assert_called_once()
        call_args = mock_update.message.reply_document.call_args
        filename = call_args[1]['filename']
        assert filename.startswith('library_export')
        assert filename.endswith('.txt') or filename.endswith('.json')


class TestMemoryUsage:
    """Тесты использования памяти"""
    
    @pytest.mark.asyncio
    async def test_memory_efficient_search(self, mock_update, mock_context, mock_db_connection):
        """Тест: эффективное использование памяти при поиске"""
        import psutil
        import os
        
        # Arrange - Добавляем много книг
        cursor = mock_db_connection.cursor()
        for i in range(10000):
            cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", 
                          (f"Книга {i}", f"Описание {i}"))
        mock_db_connection.commit()
        
        # Act
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        await search_start(mock_update, mock_context)
        mock_update.message.text = "книга 5000"
        await search_process(mock_update, mock_context)
        
        memory_after = process.memory_info().rss
        
        # Assert
        memory_increase = memory_after - memory_before
        # Увеличение памяти не должно превышать 50MB
        assert memory_increase < 50 * 1024 * 1024
    
    @pytest.mark.asyncio
    async def test_memory_efficient_list(self, mock_update, mock_context, mock_db_connection):
        """Тест: эффективное использование памяти при отображении списков"""
        import psutil
        import os
        
        # Arrange - Добавляем много книг
        cursor = mock_db_connection.cursor()
        for i in range(5000):
            cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", 
                          (f"Книга {i}", f"Описание {i}"))
        mock_db_connection.commit()
        
        # Act
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss
        
        await list_books(mock_update, mock_context)
        
        memory_after = process.memory_info().rss
        
        # Assert
        memory_increase = memory_after - memory_before
        # Увеличение памяти не должно превышать 30MB
        assert memory_increase < 30 * 1024 * 1024


class TestConcurrentOperations:
    """Тесты конкурентных операций"""
    
    @pytest.mark.asyncio
    async def test_concurrent_book_additions(self, mock_db_connection):
        """Тест: конкурентное добавление книг"""
        import asyncio
        
        # Arrange
        async def add_book_simulation(book_id):
            cursor = mock_db_connection.cursor()
            cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", 
                          (f"Книга {book_id}", f"Описание {book_id}"))
            mock_db_connection.commit()
        
        # Act
        tasks = [add_book_simulation(i) for i in range(100)]
        start_time = time.time()
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Assert
        execution_time = end_time - start_time
        assert execution_time < 2.0  # Должно выполняться менее чем за 2 секунды
        
        # Проверяем, что все книги добавлены
        cursor = mock_db_connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM books")
        count = cursor.fetchone()[0]
        assert count == 100
    
    @pytest.mark.asyncio
    async def test_concurrent_searches(self, mock_update, mock_context, mock_db_connection):
        """Тест: конкурентные поиски"""
        import asyncio
        
        # Arrange - Добавляем много книг
        cursor = mock_db_connection.cursor()
        for i in range(1000):
            cursor.execute("INSERT INTO books (title, description) VALUES (?, ?)", 
                          (f"Книга {i}", f"Описание {i}"))
        mock_db_connection.commit()
        
        # Act
        async def search_simulation(search_term):
            await search_start(mock_update, mock_context)
            mock_update.message.text = search_term
            await search_process(mock_update, mock_context)
        
        search_terms = [f"книга {i}" for i in range(50)]
        tasks = [search_simulation(term) for term in search_terms]
        
        start_time = time.time()
        await asyncio.gather(*tasks)
        end_time = time.time()
        
        # Assert
        execution_time = end_time - start_time
        assert execution_time < 5.0  # Должно выполняться менее чем за 5 секунд 