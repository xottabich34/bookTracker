# --- ПЛАН РЕФАКТОРИНГА main.py ---
# 1. booktracker/db.py         — работа с базой данных (инициализация, функции)
# 2. booktracker/handlers.py   — все обработчики команд и состояний
# 3. booktracker/keyboards.py  — все клавиатуры ReplyKeyboardMarkup
# 4. booktracker/utils.py      — декораторы, вспомогательные функции
# 5. main.py                   — только точка входа, запуск приложения
#
# По мере переноса кода, этот план будет обновляться.
# ------------------------------
# mypy: disable-error-code="union-attr,index"
import logging
import os
import re
import sqlite3
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

from booktracker.db import conn, cursor
from booktracker.utils import owner_only
from booktracker.keyboards import menu_keyboard, cancel_keyboard, status_keyboard
from booktracker.handlers import universal_cancel, add_cancel, status_cancel, search_cancel, book_info_cancel, delete_book_cancel, edit_book_cancel

# Загрузка переменных окружения из файла .env
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")  # Токен бота, полученный от BotFather
ALLOWED_IDS = set(map(int, os.getenv("ALLOWED_IDS", "").split(",")))  # Список ID пользователей, которым разрешён доступ

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Уровень логирования — DEBUG
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Формат логов ignore
    datefmt="%Y-%m-%d %H:%M:%S"  # Формат даты и времени
)
logger = logging.getLogger(__name__)  # Создание логгера для текущего модуля

# --- НАСТРОЙКА БАЗЫ ДАННЫХ ---
# Подключение к базе данных SQLite (или создание, если её нет)
# conn = sqlite3.connect("books.db", check_same_thread=False)
# cursor = conn.cursor()
# Создание таблицы для серий книг, если она ещё не существует
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS series (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT UNIQUE COLLATE NOCASE
# )
# """)

# Создание таблицы для книг, если она ещё не существует
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS books (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     title TEXT UNIQUE,
#     description TEXT,
#     image_blob BLOB,
#     series_id INTEGER,
#     series_order INTEGER,
#     isbn TEXT,
#     FOREIGN KEY (series_id) REFERENCES series(id)
# )
# """)

# Создание таблицы для авторов, если она ещё не существует
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS authors (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     name TEXT UNIQUE
# )
# """)

# Создание таблицы для связи книг и авторов, если она ещё не существует
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS book_authors (
#     book_id INTEGER,
#     author_id INTEGER,
#     PRIMARY KEY (book_id, author_id),
#     FOREIGN KEY (book_id) REFERENCES books(id),
#     FOREIGN KEY (author_id) REFERENCES authors(id)
# )
# """)

# Создание таблицы для связи пользователей и книг, если она ещё не существует
# cursor.execute("""
# CREATE TABLE IF NOT EXISTS user_books (
#     user_id INTEGER,
#     book_id INTEGER,
#     status TEXT CHECK(status IN ('planning', 'reading', 'finished', 'cancelled')),
#     PRIMARY KEY (user_id, book_id),
#     FOREIGN KEY (book_id) REFERENCES books(id)
# )
# """)
# conn.commit()  # Сохранение изменений в базе данных


# --- ДЕКОРАТОР ДЛЯ КОНТРОЛЯ ДОСТУПА ---
# def owner_only(func): ...


# --- МАСТЕР ДОБАВЛЕНИЯ КНИГИ ---
# Константы для состояний ConversationHandler
ADD_TITLE, ADD_DESC, ADD_COVER, ADD_ISBN, ADD_AUTHORS, ADD_SERIES, ADD_SERIES_ORDER, SEARCH_QUERY = range(8)


# Клавиатура с основными командами
# menu_keyboard = ...

# Универсальная клавиатура с кнопкой отмены
# cancel_keyboard = ...


# Начало процесса добавления книги
# @owner_only
async def add_start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введи название книги:",
        reply_markup=cancel_keyboard
    )
    return ADD_TITLE  # Переход к состоянию ADD_TITLE


# Обработка ввода названия книги
# @owner_only
async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.strip():
        await update.message.reply_text("Название книги не может быть пустым. Введите снова:")
        return ADD_TITLE
    context.user_data['new_book'] = {'title': update.message.text.strip()}  # Сохранение названия
    await update.message.reply_text("Теперь введи описание книги:")
    return ADD_DESC  # Переход к состоянию ADD_DESC


# Обработка ввода описания книги
# @owner_only
async def add_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_book']['description'] = update.message.text.strip()  # Сохранение описания
    await update.message.reply_text("Теперь отправь обложку книги (как изображение):")
    return ADD_COVER  # Переход к состоянию ADD_COVER


# Обработка загрузки обложки книги
# @owner_only
async def add_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:  # Проверка, что сообщение содержит фото
        await update.message.reply_text("Пожалуйста, отправь фото")
        return ADD_COVER

    try:
        file = await update.message.photo[-1].get_file()  # Получение файла изображения
        byte_data = await file.download_as_bytearray()  # Преобразование изображения в байты
        context.user_data['new_book']['image_blob'] = byte_data  # Сохранение обложки
        await update.message.reply_text("Введите ISBN книги (или пропусти, отправив '-'):")
        return ADD_ISBN  # Переход к состоянию ADD_ISBN
    except Exception as e:
        logger.error(f"Ошибка при загрузке изображения: {e}")
        await update.message.reply_text("Ошибка при загрузке изображения. Попробуйте еще раз:")
        return ADD_COVER


# Обработка ввода ISBN
# @owner_only
async def add_isbn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    isbn = update.message.text.strip()
    isbn_clean = isbn.replace("-", "").replace(" ", "")  # Очистка ISBN от лишних символов
    if isbn != '-' and not re.match(r'^\d{9}[\dXx]$|^\d{13}$', isbn_clean):  # Проверка формата ISBN
        await update.message.reply_text(
            "Некорректный формат ISBN. Введи 10 или 13 цифр (последняя может быть X для ISBN-10). Попробуй ещё раз или введи '-' чтобы пропустить:")
        return ADD_ISBN
    context.user_data['new_book']['isbn'] = None if isbn == '-' else isbn  # Сохранение ISBN
    await update.message.reply_text("Введи авторов книги через запятую:")
    return ADD_AUTHORS  # Переход к состоянию ADD_AUTHORS


# Обработка ввода авторов
# @owner_only
async def add_authors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.strip():
        await update.message.reply_text("Список авторов не может быть пустым. Введите хотя бы одного автора:")
        return ADD_AUTHORS
    author_names = [a.strip() for a in update.message.text.split(',') if a.strip()]  # Разделение авторов
    context.user_data['new_book']['authors'] = author_names  # Сохранение авторов
    await update.message.reply_text("Введите название серии (или '-' если без серии):")
    return ADD_SERIES  # Переход к состоянию ADD_SERIES


# Обработка ввода серии
# @owner_only
async def add_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    series_name = update.message.text.strip()
    if series_name != "-":  # Если серия указана
        cursor.execute("SELECT id FROM series WHERE name = ? COLLATE NOCASE", (series_name,))
        result = cursor.fetchone()

        if result:
            series_id = result[0]
        else:
            cursor.execute("INSERT INTO series (name) VALUES (?)", (series_name,))
            series_id = cursor.lastrowid
        context.user_data['new_book']['series_id'] = series_id  # Сохранение ID серии
        await update.message.reply_text("Введите номер книги в серии:")
        return ADD_SERIES_ORDER  # Переход к состоянию ADD_SERIES_ORDER
    else:  # Если серия не указана
        context.user_data['new_book']['series_id'] = None
        context.user_data['new_book']['series_order'] = None
        return await finalize_book(update, context)  # Завершение добавления книги


@owner_only
async def add_series_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        order = int(update.message.text.strip())
        context.user_data['new_book']['series_order'] = order
    except ValueError:
        await update.message.reply_text("Введите числовой порядковый номер:")
        return ADD_SERIES_ORDER
    return await finalize_book(update, context)


async def finalize_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = context.user_data['new_book']

        # Проверяем, не существует ли уже книга с таким названием
        cursor.execute("SELECT id FROM books WHERE title = ?", (data['title'],))
        existing_book = cursor.fetchone()
        if existing_book:
            await update.message.reply_text(f"Книга «{data['title']}» уже существует в базе данных.", reply_markup=menu_keyboard)
            return ConversationHandler.END

        # Добавляем книгу
        cursor.execute("""
            INSERT INTO books (title, description, image_blob, isbn, series_id, series_order)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (data['title'], data['description'], data['image_blob'], data['isbn'], data.get('series_id'),
              data.get('series_order')))

        book_id = cursor.lastrowid

        # Добавляем авторов
        for name in data['authors']:
            cursor.execute("INSERT OR IGNORE INTO authors (name) VALUES (?)", (name,))
            cursor.execute("SELECT id FROM authors WHERE name = ?", (name,))
            author_id = cursor.fetchone()[0]
            cursor.execute("INSERT OR IGNORE INTO book_authors (book_id, author_id) VALUES (?, ?)",
                           (book_id, author_id))

        conn.commit()
        await update.message.reply_text(f"Книга «{data['title']}» добавлена ✅", reply_markup=menu_keyboard)
        return ConversationHandler.END

    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при добавлении книги: {e}")
        await update.message.reply_text("Произошла ошибка при добавлении книги. Попробуйте еще раз.", reply_markup=menu_keyboard)
        return ConversationHandler.END


@owner_only
async def add_cancel(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добавление книги отменено", reply_markup=menu_keyboard)
    return ConversationHandler.END


@owner_only
async def menu_handler(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите действие:", reply_markup=menu_keyboard)


@owner_only
async def list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur = getattr(context, 'cursor', cursor)
    cur.execute("SELECT title FROM books")
    rows = cur.fetchall()
    if rows:
        text = "\n".join([row[0] for row in rows])
        await update.message.reply_text("📚 Список книг:\n" + text)
    else:
        await update.message.reply_text("Библиотека пуста")


@owner_only
async def my_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur = getattr(context, 'cursor', cursor)
    user_id = update.effective_user.id
    cur.execute("""
        SELECT b.title, ub.status FROM books b
        JOIN user_books ub ON b.id = ub.book_id
        WHERE ub.user_id = ?
        ORDER BY b.title
    """, (user_id,))
    rows = cur.fetchall()

    if rows:
        status_emoji = {
            'planning': '📋',
            'reading': '📖',
            'finished': '✅',
            'cancelled': '❌'
        }

        lines = []
        for title, status in rows:
            emoji = status_emoji.get(status, '❓')
            status_text = {
                'planning': 'Запланировано',
                'reading': 'Читаю',
                'finished': 'Прочитано',
                'cancelled': 'Отменено'
            }.get(status, status)
            lines.append(f"{emoji} {title} — {status_text}")

        await update.message.reply_text("📖 Ваши книги:\n\n" + "\n".join(lines))
    else:
        await update.message.reply_text("У вас нет отмеченных книг. Используйте кнопку «🏷 Статусы» чтобы добавить книги в свой список.")


@owner_only
async def list_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cur = getattr(context, 'cursor', cursor)
    cur.execute("SELECT id, name FROM series")
    rows = cur.fetchall()
    if not rows:
        await update.message.reply_text("Серии не найдены")
        return
    result = []
    for series_id, name in rows:
        cur.execute("SELECT title FROM books WHERE series_id = ? ORDER BY series_order", (series_id,))
        books = [row[0] for row in cur.fetchall()]
        result.append(f"📚 {name}:\n  " + "\n  ".join(books))
    await update.message.reply_text("\n\n".join(result))


# Константы для состояний управления статусами
STATUS_SELECT_BOOK, STATUS_SELECT_STATUS = range(7, 9)

# Клавиатура для выбора статуса
# status_keyboard = ...

# Универсальная клавиатура с кнопкой отмены
# cancel_keyboard = ...


@owner_only
async def status_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса изменения статуса книги"""
    cursor.execute("SELECT title FROM books ORDER BY title")
    books = cursor.fetchall()
    if not books:
        await update.message.reply_text("В библиотеке нет книг для изменения статуса.")
        return ConversationHandler.END

    book_list = "\n".join([f"{i+1}. {book[0]}" for i, book in enumerate(books)])
    context.user_data['available_books'] = [book[0] for book in books]

    await update.message.reply_text(
        f"Выберите книгу для изменения статуса (введите номер):\n\n{book_list}",
        reply_markup=cancel_keyboard
    )
    return STATUS_SELECT_BOOK


@owner_only
async def status_select_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора книги"""
    try:
        book_index = int(update.message.text.strip()) - 1
        available_books = context.user_data.get('available_books', [])

        if book_index < 0 or book_index >= len(available_books):
            await update.message.reply_text("Неверный номер книги. Попробуйте еще раз:")
            return STATUS_SELECT_BOOK

        selected_book = available_books[book_index]
        context.user_data['selected_book'] = selected_book

        # Получаем текущий статус книги
        user_id = update.effective_user.id
        cursor.execute("""
            SELECT ub.status FROM user_books ub
            JOIN books b ON ub.book_id = b.id
            WHERE b.title = ? AND ub.user_id = ?
        """, (selected_book, user_id))
        current_status = cursor.fetchone()

        status_text = f"Текущий статус: {current_status[0] if current_status else 'Не установлен'}"
        await update.message.reply_text(
            f"Книга: {selected_book}\n{status_text}\n\nВыберите новый статус:",
            reply_markup=status_keyboard
        )
        return STATUS_SELECT_STATUS

    except ValueError:
        await update.message.reply_text("Пожалуйста, введите числовой номер книги:")
        return STATUS_SELECT_BOOK


@owner_only
async def status_select_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора статуса"""
    status_mapping = {
        "📖 Читаю": "reading",
        "✅ Прочитано": "finished",
        "📋 Запланировано": "planning",
        "❌ Отменено": "cancelled"
    }

    status_text = update.message.text.strip()
    if status_text not in status_mapping:
        await update.message.reply_text("Неверный статус. Выберите из предложенных вариантов:")
        return STATUS_SELECT_STATUS

    selected_book = context.user_data['selected_book']
    status = status_mapping[status_text]
    user_id = update.effective_user.id

    try:
        # Получаем ID книги
        cursor.execute("SELECT id FROM books WHERE title = ?", (selected_book,))
        book_id = cursor.fetchone()[0]

        # Обновляем или добавляем статус
        cursor.execute("""
            INSERT OR REPLACE INTO user_books (user_id, book_id, status)
            VALUES (?, ?, ?)
        """, (user_id, book_id, status))

        conn.commit()
        await update.message.reply_text(
            f"Статус книги «{selected_book}» изменен на: {status_text}",
            reply_markup=menu_keyboard
        )
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Ошибка при изменении статуса: {e}")
        await update.message.reply_text(
            "Произошла ошибка при изменении статуса. Попробуйте еще раз.",
            reply_markup=menu_keyboard
        )
        return ConversationHandler.END


@owner_only
async def status_cancel(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Отмена изменения статуса"""
    await update.message.reply_text("Изменение статуса отменено", reply_markup=menu_keyboard)
    return ConversationHandler.END


@owner_only
async def search_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Поиск книг по названию или автору"""
    if not context.args:
        await update.message.reply_text("Использование: /search <поисковый запрос>\nИли нажмите кнопку «🔍 Поиск» и введите запрос.")
        return

    query = ' '.join(context.args)
    search_term = f"%{query}%"
    print("SEARCH_TERM:", search_term)

    cursor.execute("""
        SELECT DISTINCT b.title, GROUP_CONCAT(a.name, ', ') as authors
        FROM books b
        LEFT JOIN book_authors ba ON b.id = ba.book_id
        LEFT JOIN authors a ON ba.author_id = a.id
        WHERE b.title LIKE ? OR a.name LIKE ?
        GROUP BY b.id, b.title
        ORDER BY b.title
    """, (search_term, search_term))

    results = cursor.fetchall()
    print("SEARCH_RESULTS:", results)

    if results:
        lines = []
        for title, authors in results:
            author_text = f" ({authors})" if authors else ""
            lines.append(f"📚 {title}{author_text}")

        await update.message.reply_text(f"🔍 Результаты поиска по запросу «{query}»:\n\n" + "\n".join(lines))
    else:
        await update.message.reply_text(f"По запросу «{query}» ничего не найдено.")


# Константы для состояний поиска
SEARCH_QUERY = 9

# Константы для состояний просмотра информации о книге
BOOK_INFO_SELECT = 10

# Константы для состояний удаления книги
DELETE_SELECT_BOOK, DELETE_CONFIRM = range(11, 13)

# Константы для состояний редактирования книги
EDIT_SELECT_BOOK, EDIT_SELECT_FIELD, EDIT_VALUE = range(13, 16)


@owner_only
async def search_start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Начало поиска через кнопку"""
    await update.message.reply_text("Введите поисковый запрос:", reply_markup=cancel_keyboard)
    return SEARCH_QUERY


@owner_only
async def search_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка поискового запроса"""
    cur = getattr(context, 'cursor', cursor)
    query = update.message.text.strip()
    if not query:
        await update.message.reply_text("Поисковый запрос не может быть пустым. Попробуйте еще раз:")
        return SEARCH_QUERY

    search_term = f"%{query}%"
    print("SEARCH_TERM:", search_term)

    cur.execute("""
        SELECT DISTINCT b.title, GROUP_CONCAT(a.name, ', ') as authors
        FROM books b
        LEFT JOIN book_authors ba ON b.id = ba.book_id
        LEFT JOIN authors a ON ba.author_id = a.id
        WHERE b.title LIKE ? OR a.name LIKE ?
        GROUP BY b.id, b.title
        ORDER BY b.title
    """, (search_term, search_term))
    results = cur.fetchall()
    print("SEARCH_RESULTS:", results)

    if results:
        lines = []
        for title, authors in results:
            author_text = f" ({authors})" if authors else ""
            lines.append(f"📚 {title}{author_text}")

        await update.message.reply_text(
            f"🔍 Результаты поиска по запросу «{query}»:\n\n" + "\n".join(lines),
            reply_markup=menu_keyboard
        )
    else:
        await update.message.reply_text(
            f"По запросу «{query}» ничего не найдено.",
            reply_markup=menu_keyboard
        )

    return ConversationHandler.END


@owner_only
async def search_cancel(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Отмена поиска"""
    await update.message.reply_text("Поиск отменен", reply_markup=menu_keyboard)
    return ConversationHandler.END


@owner_only
async def book_info_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса просмотра информации о книге"""
    cursor.execute("SELECT title FROM books ORDER BY title")
    books = cursor.fetchall()
    if not books:
        await update.message.reply_text("В библиотеке нет книг.")
        return ConversationHandler.END

    book_list = "\n".join([f"{i+1}. {book[0]}" for i, book in enumerate(books)])
    context.user_data['available_books'] = [book[0] for book in books]

    await update.message.reply_text(
        f"Выберите книгу для просмотра информации (введите номер):\n\n{book_list}",
        reply_markup=cancel_keyboard
    )
    return BOOK_INFO_SELECT


@owner_only
async def book_info_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора книги для просмотра информации"""
    try:
        book_index = int(update.message.text.strip()) - 1
        available_books = context.user_data.get('available_books', [])

        if book_index < 0 or book_index >= len(available_books):
            await update.message.reply_text("Неверный номер книги. Попробуйте еще раз:")
            return BOOK_INFO_SELECT

        selected_book = available_books[book_index]

        # Получаем подробную информацию о книге
        cursor.execute("""
            SELECT b.title, b.description, b.isbn, b.series_order, b.image_blob,
                   s.name as series_name,
                   GROUP_CONCAT(a.name, ', ') as authors
            FROM books b
            LEFT JOIN series s ON b.series_id = s.id
            LEFT JOIN book_authors ba ON b.id = ba.book_id
            LEFT JOIN authors a ON ba.author_id = a.id
            WHERE b.title = ?
            GROUP BY b.id, b.title, b.description, b.isbn, b.series_order, b.image_blob, s.name
        """, (selected_book,))

        book_info = cursor.fetchone()
        if not book_info:
            await update.message.reply_text("Книга не найдена.", reply_markup=menu_keyboard)
            return ConversationHandler.END

        title, description, isbn, series_order, image_blob, series_name, authors = book_info

        # Формируем текст с информацией
        info_text = f"📚 **{title}**\n\n"

        if authors:
            info_text += f"👤 **Авторы:** {authors}\n\n"

        if description:
            info_text += f"📝 **Описание:** {description}\n\n"

        if series_name:
            series_text = f"📚 **Серия:** {series_name}"
            if series_order:
                series_text += f" (книга {series_order})"
            info_text += series_text + "\n\n"

        if isbn:
            info_text += f"🔢 **ISBN:** {isbn}\n\n"

        # Отправляем обложку, если есть
        if image_blob:
            try:
                await update.message.reply_photo(
                    photo=image_blob,
                    caption=info_text,
                    parse_mode='Markdown',
                    reply_markup=menu_keyboard
                )
            except Exception as e:
                logger.error(f"Ошибка при отправке изображения: {e}")
                await update.message.reply_text(
                    info_text,
                    parse_mode='Markdown',
                    reply_markup=menu_keyboard
                )
        else:
            await update.message.reply_text(
                info_text,
                parse_mode='Markdown',
                reply_markup=menu_keyboard
            )

        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("Пожалуйста, введите числовой номер книги:")
        return BOOK_INFO_SELECT


@owner_only
async def book_info_cancel(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Отмена просмотра информации о книге"""
    await update.message.reply_text("Просмотр информации отменен", reply_markup=menu_keyboard)
    return ConversationHandler.END


@owner_only
async def delete_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса удаления книги"""
    cursor.execute("SELECT title FROM books ORDER BY title")
    books = cursor.fetchall()
    if not books:
        await update.message.reply_text("В библиотеке нет книг для удаления.")
        return ConversationHandler.END

    book_list = "\n".join([f"{i+1}. {book[0]}" for i, book in enumerate(books)])
    context.user_data['available_books'] = [book[0] for book in books]

    await update.message.reply_text(
        f"⚠️ **ВНИМАНИЕ:** Удаление книги необратимо!\n\n"
        f"Выберите книгу для удаления (введите номер):\n\n{book_list}",
        reply_markup=cancel_keyboard,
        parse_mode='Markdown'
    )
    return DELETE_SELECT_BOOK


@owner_only
async def delete_book_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора книги для удаления"""
    try:
        book_index = int(update.message.text.strip()) - 1
        available_books = context.user_data.get('available_books', [])

        if book_index < 0 or book_index >= len(available_books):
            await update.message.reply_text("Неверный номер книги. Попробуйте еще раз:")
            return DELETE_SELECT_BOOK

        selected_book = available_books[book_index]
        
        # Получаем ID книги по названию
        cur = getattr(context, 'cursor', cursor)
        cur.execute("SELECT id FROM books WHERE title = ?", (selected_book,))
        book_id_result = cur.fetchone()
        
        if not book_id_result:
            await update.message.reply_text("Книга не найдена. Попробуйте еще раз:")
            return DELETE_SELECT_BOOK
            
        book_id = book_id_result[0]
        context.user_data['book_to_delete'] = book_id

        # Создаем клавиатуру подтверждения
        confirm_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                ["✅ Да, удалить", "❌ Нет, отменить"]
            ],
            resize_keyboard=True
        )

        await update.message.reply_text(
            f"Вы действительно хотите удалить книгу «{selected_book}»?\n\n"
            f"Это действие нельзя отменить!",
            reply_markup=confirm_keyboard
        )
        return DELETE_CONFIRM

    except ValueError:
        await update.message.reply_text("Пожалуйста, введите числовой номер книги:")
        return DELETE_SELECT_BOOK


@owner_only
async def delete_book_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления книги"""
    response = update.message.text.strip()

    if response == "✅ Да, удалить":
        book_id = context.user_data.get('book_to_delete')

        try:
            # Получаем название книги по ID
            cur = getattr(context, 'cursor', cursor)
            cur.execute("SELECT title FROM books WHERE id = ?", (book_id,))
            book_title_result = cur.fetchone()

            if not book_title_result:
                await update.message.reply_text("Книга не найдена.", reply_markup=menu_keyboard)
                return ConversationHandler.END

            book_title = book_title_result[0]

            # Удаляем связанные записи
            cur.execute("DELETE FROM user_books WHERE book_id = ?", (book_id,))
            cur.execute("DELETE FROM book_authors WHERE book_id = ?", (book_id,))

            # Удаляем саму книгу
            cur.execute("DELETE FROM books WHERE id = ?", (book_id,))

            db_conn = getattr(context, 'conn', conn)
            db_conn.commit()

            await update.message.reply_text(
                f"Книга «{book_title}» успешно удалена из библиотеки.",
                reply_markup=menu_keyboard
            )

        except Exception as e:
            db_conn = getattr(context, 'conn', conn)
            db_conn.rollback()
            logger.error(f"Ошибка при удалении книги: {e}")
            await update.message.reply_text(
                "Произошла ошибка при удалении книги. Попробуйте еще раз.",
                reply_markup=menu_keyboard
            )

        return ConversationHandler.END

    elif response == "❌ Нет, отменить":
        await update.message.reply_text("Удаление отменено.", reply_markup=menu_keyboard)
        return ConversationHandler.END

    else:
        await update.message.reply_text("Пожалуйста, выберите «✅ Да, удалить» или «❌ Нет, отменить»:")
        return DELETE_CONFIRM


@owner_only
async def delete_book_cancel(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Отмена удаления книги"""
    await update.message.reply_text("Удаление книги отменено", reply_markup=menu_keyboard)
    return ConversationHandler.END


@owner_only
async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику библиотеки и чтения"""
    cur = getattr(context, 'cursor', cursor)
    user_id = update.effective_user.id

    try:
        # Общая статистика библиотеки
        cur.execute("SELECT COUNT(*) FROM books")
        total_books = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM series")
        total_series = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM authors")
        total_authors = cur.fetchone()[0]

        # Статистика пользователя
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM user_books
            WHERE user_id = ?
            GROUP BY status
        """, (user_id,))
        user_stats = dict(cur.fetchall())

        # Статистика по авторам
        cur.execute("""
            SELECT a.name, COUNT(ba.book_id) as book_count
            FROM authors a
            JOIN book_authors ba ON a.id = ba.author_id
            GROUP BY a.id, a.name
            ORDER BY book_count DESC
            LIMIT 5
        """)
        top_authors = cur.fetchall()

        # Статистика по сериям
        cur.execute("""
            SELECT s.name, COUNT(b.id) as book_count
            FROM series s
            JOIN books b ON s.id = b.series_id
            GROUP BY s.id, s.name
            ORDER BY book_count DESC
            LIMIT 5
        """)
        top_series = cur.fetchall()

        # Формируем отчет
        stats_text = "📊 **Статистика библиотеки**\n\n"

        # Общая статистика
        stats_text += f"📚 **Всего книг:** {total_books}\n"
        stats_text += f"📚 **Серий:** {total_series}\n"
        stats_text += f"👤 **Авторов:** {total_authors}\n\n"

        # Статистика пользователя
        stats_text += "📖 **Ваши книги:**\n"
        status_names = {
            'planning': 'Запланировано',
            'reading': 'Читаю',
            'finished': 'Прочитано',
            'cancelled': 'Отменено'
        }

        total_user_books = 0
        for status, count in user_stats.items():
            status_name = status_names.get(status, status)
            stats_text += f"  • {status_name}: {count}\n"
            total_user_books += count

        if total_user_books == 0:
            stats_text += "  • У вас пока нет отмеченных книг\n"

        stats_text += f"\n**Всего ваших книг:** {total_user_books}\n\n"

        # Топ авторов
        if top_authors:
            stats_text += "👑 **Топ авторов:**\n"
            for author, count in top_authors:
                stats_text += f"  • {author}: {count} книг\n"
            stats_text += "\n"

        # Топ серий
        if top_series:
            stats_text += "📚 **Топ серий:**\n"
            for series, count in top_series:
                stats_text += f"  • {series}: {count} книг\n"

        await update.message.reply_text(stats_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await update.message.reply_text("Произошла ошибка при получении статистики.")


@owner_only
async def export_library(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт библиотеки в текстовый файл"""
    cur = getattr(context, 'cursor', cursor)
    db_conn = getattr(context, 'conn', conn)
    try:
        # Получаем все книги с полной информацией
        cur.execute("""
            SELECT b.title, b.description, b.isbn, b.series_order,
                   s.name as series_name,
                   GROUP_CONCAT(a.name, ', ') as authors
            FROM books b
            LEFT JOIN series s ON b.series_id = s.id
            LEFT JOIN book_authors ba ON b.id = ba.book_id
            LEFT JOIN authors a ON ba.author_id = a.id
            GROUP BY b.id, b.title, b.description, b.isbn, b.series_order, s.name
            ORDER BY b.title
        """)

        books = cur.fetchall()

        if not books:
            await update.message.reply_text("Библиотека пуста.")
            return

        # Формируем содержимое файла
        export_content = "📚 МОЯ БИБЛИОТЕКА\n"
        export_content += "=" * 50 + "\n\n"

        for i, book in enumerate(books, 1):
            title, description, isbn, series_order, series_name, authors = book

            export_content += f"{i}. {title}\n"

            if authors:
                export_content += f"   Авторы: {authors}\n"

            if series_name:
                series_text = f"   Серия: {series_name}"
                if series_order:
                    series_text += f" (книга {series_order})"
                export_content += series_text + "\n"

            if isbn:
                export_content += f"   ISBN: {isbn}\n"

            if description:
                # Обрезаем длинное описание
                desc = description[:200] + "..." if len(description) > 200 else description
                export_content += f"   Описание: {desc}\n"

            export_content += "\n"

        # Добавляем статистику
        cur.execute("SELECT COUNT(*) FROM books")
        total_books = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM series")
        total_series = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM authors")
        total_authors = cur.fetchone()[0]

        export_content += "=" * 50 + "\n"
        export_content += f"📊 СТАТИСТИКА\n"
        export_content += f"Всего книг: {total_books}\n"
        export_content += f"Серий: {total_series}\n"
        export_content += f"Авторов: {total_authors}\n"
        export_content += f"Дата экспорта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

        # Создаем временный файл
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write(export_content)
            temp_file_path = f.name

        # Отправляем файл
        with open(temp_file_path, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f"library_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                caption="📚 Экспорт вашей библиотеки"
            )

        # Удаляем временный файл
        os.unlink(temp_file_path)

    except Exception as e:
        logger.error(f"Ошибка при экспорте библиотеки: {e}")
        await update.message.reply_text("Произошла ошибка при экспорте библиотеки.")


@owner_only
async def edit_book_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса редактирования книги"""
    cursor.execute("SELECT title FROM books ORDER BY title")
    books = cursor.fetchall()
    if not books:
        await update.message.reply_text("В библиотеке нет книг для редактирования.")
        return ConversationHandler.END

    book_list = "\n".join([f"{i+1}. {book[0]}" for i, book in enumerate(books)])
    context.user_data['available_books'] = [book[0] for book in books]

    await update.message.reply_text(
        f"Выберите книгу для редактирования (введите номер):\n\n{book_list}",
        reply_markup=cancel_keyboard
    )
    return EDIT_SELECT_BOOK


@owner_only
async def edit_book_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора книги для редактирования"""
    try:
        book_index = int(update.message.text.strip()) - 1
        available_books = context.user_data.get('available_books', [])

        if book_index < 0 or book_index >= len(available_books):
            await update.message.reply_text("Неверный номер книги. Попробуйте еще раз:")
            return EDIT_SELECT_BOOK

        selected_book = available_books[book_index]
        
        # Получаем ID книги по названию
        cur = getattr(context, 'cursor', cursor)
        cur.execute("SELECT id FROM books WHERE title = ?", (selected_book,))
        book_id_result = cur.fetchone()
        
        if not book_id_result:
            await update.message.reply_text("Книга не найдена. Попробуйте еще раз:")
            return EDIT_SELECT_BOOK
            
        book_id = book_id_result[0]
        context.user_data['book_to_edit'] = book_id
        context.user_data['book_title'] = selected_book  # Сохраняем название для отображения

        # Создаем клавиатуру для выбора поля
        field_keyboard = ReplyKeyboardMarkup(
            keyboard=[
                ["📝 Описание", "🔢 ISBN"],
                ["👤 Авторы", "📚 Серия"],
                ["❌ Отмена"]
            ],
            resize_keyboard=True
        )

        await update.message.reply_text(
            f"Выберите, что хотите отредактировать в книге «{selected_book}»:",
            reply_markup=field_keyboard
        )
        return EDIT_SELECT_FIELD

    except ValueError:
        await update.message.reply_text("Пожалуйста, введите числовой номер книги:")
        return EDIT_SELECT_BOOK


@owner_only
async def edit_field_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора поля для редактирования"""
    field = update.message.text.strip()

    if field == "❌ Отмена":
        await update.message.reply_text("Редактирование отменено", reply_markup=menu_keyboard)
        return ConversationHandler.END

    field_mapping = {
        "📝 Описание": "description",
        "🔢 ISBN": "isbn",
        "👤 Авторы": "authors",
        "📚 Серия": "series"
    }

    if field not in field_mapping:
        await update.message.reply_text("Неверный выбор. Выберите поле из списка:")
        return EDIT_SELECT_FIELD

    context.user_data['edit_field'] = field_mapping[field]

    # Получаем текущее значение
    book_id = context.user_data['book_to_edit']
    book_title = context.user_data['book_title']
    field_name = field_mapping[field]

    if field_name == "description" or field_name == "isbn":
        cur = getattr(context, 'cursor', cursor)
        cur.execute(f"SELECT {field_name} FROM books WHERE id = ?", (book_id,))
        current_value = cur.fetchone()[0] or "Не задано"
        await update.message.reply_text(
            f"Текущее значение: {current_value}\n\nВведите новое значение:",
            reply_markup=ReplyKeyboardRemove()
        )
    elif field_name == "authors":
        cur = getattr(context, 'cursor', cursor)
        cur.execute("""
            SELECT GROUP_CONCAT(a.name, ', ') as authors
            FROM books b
            JOIN book_authors ba ON b.id = ba.book_id
            JOIN authors a ON ba.author_id = a.id
            WHERE b.id = ?
            GROUP BY b.id
        """, (book_id,))
        result = cur.fetchone()
        current_value = result[0] if result else "Не задано"
        await update.message.reply_text(
            f"Текущие авторы: {current_value}\n\nВведите новых авторов через запятую:",
            reply_markup=ReplyKeyboardRemove()
        )
    elif field_name == "series":
        cur = getattr(context, 'cursor', cursor)
        cur.execute("""
            SELECT s.name, b.series_order
            FROM books b
            LEFT JOIN series s ON b.series_id = s.id
            WHERE b.id = ?
        """, (book_id,))
        result = cur.fetchone()
        if result and result[0]:
            current_value = f"{result[0]} (книга {result[1]})" if result[1] else result[0]
        else:
            current_value = "Не задано"
        await update.message.reply_text(
            f"Текущая серия: {current_value}\n\nВведите новое название серии (или '-' для удаления):",
            reply_markup=ReplyKeyboardRemove()
        )

    return EDIT_VALUE


@owner_only
async def edit_value_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нового значения поля"""
    if update.message is None or update.message.text is None:
        return ConversationHandler.END

    new_value = update.message.text.strip()
    book_id = context.user_data['book_to_edit']
    book_title = context.user_data['book_title']
    field_name = context.user_data['edit_field']

    try:
        cur = getattr(context, 'cursor', cursor)
        db_conn = getattr(context, 'conn', conn)
        
        if field_name == "description":
            cur.execute("UPDATE books SET description = ? WHERE id = ?", (new_value, book_id))
            db_conn.commit()
            await update.message.reply_text(
                f"Описание книги «{book_title}» обновлено!",
                reply_markup=menu_keyboard
            )

        elif field_name == "isbn":
            # Проверяем формат ISBN
            isbn_clean = new_value.replace("-", "").replace(" ", "")
            if new_value != '-' and not re.match(r'^\d{9}[\dXx]$|^\d{13}$', isbn_clean):
                await update.message.reply_text(
                    "Некорректный формат ISBN. Введите 10 или 13 цифр (последняя может быть X для ISBN-10) или '-' для удаления:"
                )
                return EDIT_VALUE

            isbn_value = None if new_value == '-' else new_value
            cur.execute("UPDATE books SET isbn = ? WHERE id = ?", (isbn_value, book_id))
            db_conn.commit()
            await update.message.reply_text(
                f"ISBN книги «{book_title}» обновлен!",
                reply_markup=menu_keyboard
            )

        elif field_name == "authors":
            # Удаляем старых авторов
            cur.execute("DELETE FROM book_authors WHERE book_id = ?", (book_id,))

            # Добавляем новых авторов
            if new_value and new_value != '-':
                author_names = [a.strip() for a in new_value.split(',') if a.strip()]

                for name in author_names:
                    cur.execute("INSERT OR IGNORE INTO authors (name) VALUES (?)", (name,))
                    cur.execute("SELECT id FROM authors WHERE name = ?", (name,))
                    author_id = cur.fetchone()[0]
                    cur.execute("INSERT OR IGNORE INTO book_authors (book_id, author_id) VALUES (?, ?)",
                               (book_id, author_id))

            db_conn.commit()
            await update.message.reply_text(
                f"Авторы книги «{book_title}» обновлены!",
                reply_markup=menu_keyboard
            )

        elif field_name == "series":
            if new_value == '-':
                # Удаляем серию
                cur.execute("UPDATE books SET series_id = NULL, series_order = NULL WHERE id = ?", (book_id,))
            else:
                # Добавляем или обновляем серию
                cur.execute("SELECT id FROM series WHERE name = ? COLLATE NOCASE", (new_value,))
                result = cur.fetchone()

                if result:
                    series_id = result[0]
                else:
                    cur.execute("INSERT INTO series (name) VALUES (?)", (new_value,))
                    series_id = cur.lastrowid
                cur.execute("UPDATE books SET series_id = ? WHERE id = ?", (series_id, book_id))

            db_conn.commit()
            await update.message.reply_text(
                f"Серия книги «{book_title}» обновлена!",
                reply_markup=menu_keyboard
            )

        return ConversationHandler.END

    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при редактировании книги: {e}")
        if update.message is not None:
            await update.message.reply_text(
                "Произошла ошибка при редактировании. Попробуйте еще раз.",
                reply_markup=menu_keyboard
            )
        return ConversationHandler.END


@owner_only
async def edit_book_cancel(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Отмена редактирования книги"""
    if update.message is not None:
        await update.message.reply_text("Редактирование отменено", reply_markup=menu_keyboard)
    return ConversationHandler.END


@owner_only
async def show_help(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Показать справку по командам"""
    help_text = """
📚 **СПРАВКА ПО КОМАНДАМ**

**Основные команды:**
/start, /menu - Главное меню
/help - Эта справка

**Управление книгами:**
/add - Добавить новую книгу
/edit - Редактировать существующую книгу
/delete - Удалить книгу из библиотеки
/book_info - Просмотр информации о книге

**Просмотр и поиск:**
/list - Список всех книг
/search <запрос> - Поиск книг по названию или автору
/series - Просмотр серий книг
/my - Мои книги с статусами

**Управление статусами:**
/status - Изменить статус книги (читаю/прочитано/запланировано)

**Статистика и экспорт:**
/statistics - Статистика библиотеки
/export_library - Экспорт библиотеки в файл

**Отмена операций:**
/cancel - Отменить текущую операцию и вернуться в меню
/menu - Вернуться в главное меню из любой операции
🔙 Отмена - кнопка отмены в диалогах
🏠 Главное меню - кнопка возврата в меню

**Статусы книг:**
📖 Читаю - книга в процессе чтения
✅ Прочитано - книга прочитана
📋 Запланировано - планирую прочитать
❌ Отменено - отменил чтение

**💡 Полезные советы:**
• В любой момент можно нажать /cancel или /menu для возврата в главное меню
• Используйте кнопки 🔙 Отмена и 🏠 Главное меню в диалогах
• Команды работают даже во время длительных операций

**Примеры использования:**
/search Гарри Поттер
/statistics
/export_library
"""

    if update.message is not None:
        await update.message.reply_text(help_text, parse_mode='Markdown')


@owner_only
async def universal_cancel(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Универсальная отмена - возврат в главное меню"""
    if update.message is not None:
        await update.message.reply_text(
            "Операция отменена. Возвращаюсь в главное меню.",
            reply_markup=menu_keyboard
        )
    return ConversationHandler.END


@owner_only
async def universal_menu(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Универсальный возврат в главное меню"""
    if update.message is not None:
        await update.message.reply_text(
            "Возвращаюсь в главное меню.",
            reply_markup=menu_keyboard
        )
    return ConversationHandler.END


@owner_only
async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start - приветствие и восстановление клавиатуры"""
    welcome_text = """
🎉 **Добро пожаловать в BookTracker!** 📚

Этот бот поможет вам:
• 📖 Отслеживать прочитанные книги
• 📚 Ведсти свою библиотеку
• 🏷 Управлять статусами чтения
• 🔍 Искать книги по названию и автору
• 📊 Анализировать статистику чтения

Выберите действие:
"""
    await update.message.reply_text(
        welcome_text,
        reply_markup=menu_keyboard,
        parse_mode='Markdown'
    )


@owner_only
async def show_covers(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Показать обложки книг"""
    cursor.execute("SELECT title FROM books WHERE image_blob IS NOT NULL")
    books_with_covers = cursor.fetchall()

    if books_with_covers:
        text = "📷 **Книги с обложками:**\n\n"
        for i, (title,) in enumerate(books_with_covers, 1):
            text += f"{i}. {title}\n"
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text("В библиотеке пока нет книг с обложками.")


# --- BOT LAUNCH ---
def build_application():
    app = ApplicationBuilder().token(TOKEN).build()

    # Универсальные обработчики для кнопок отмены и возврата в меню (работают всегда)
    app.add_handler(MessageHandler(filters.Regex("^🔙 Отмена$"), universal_cancel), group=0)
    app.add_handler(MessageHandler(filters.Regex("^🏠 Главное меню$"), universal_menu), group=0)

    # Conversation handler для добавления книг
    add_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_start),
                      MessageHandler(filters.Regex("^➕ Добавить книгу$"), add_start)],
        states={
            ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
            ADD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_description)],
            ADD_COVER: [MessageHandler(filters.PHOTO, add_cover)],
            ADD_ISBN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_isbn)],
            ADD_AUTHORS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_authors)],
            ADD_SERIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_series)],
            ADD_SERIES_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_series_order)],
        },
        fallbacks=[
            CommandHandler("cancel", universal_cancel),
            CommandHandler("menu", universal_menu),
            MessageHandler(filters.Regex("^❌ Отмена$"), universal_cancel),
            MessageHandler(filters.Regex("^🔙 Отмена$"), universal_cancel),
            MessageHandler(filters.Regex("^🏠 Главное меню$"), universal_menu)
        ]
    )

    # Conversation handler для управления статусами
    status_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("status", status_start),
                      MessageHandler(filters.Regex("^🏷 Статусы$"), status_start)],
        states={
            STATUS_SELECT_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, status_select_book)],
            STATUS_SELECT_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, status_select_status)],
        },
        fallbacks=[
            CommandHandler("cancel", universal_cancel),
            CommandHandler("menu", universal_menu),
            MessageHandler(filters.Regex("^❌ Отмена$"), universal_cancel),
            MessageHandler(filters.Regex("^🔙 Отмена$"), universal_cancel),
            MessageHandler(filters.Regex("^🏠 Главное меню$"), universal_menu)
        ]
    )

    # Conversation handler для поиска
    search_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔍 Поиск$"), search_start)],
        states={
            SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_process)],
        },
        fallbacks=[
            CommandHandler("cancel", universal_cancel),
            CommandHandler("menu", universal_menu),
            MessageHandler(filters.Regex("^❌ Отмена$"), universal_cancel),
            MessageHandler(filters.Regex("^🔙 Отмена$"), universal_cancel),
            MessageHandler(filters.Regex("^🏠 Главное меню$"), universal_menu)
        ]
    )

    # Conversation handler для просмотра информации о книге
    book_info_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^ℹ️ О книге$"), book_info_start)],
        states={
            BOOK_INFO_SELECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, book_info_select)],
        },
        fallbacks=[
            CommandHandler("cancel", universal_cancel),
            CommandHandler("menu", universal_menu),
            MessageHandler(filters.Regex("^❌ Отмена$"), universal_cancel),
            MessageHandler(filters.Regex("^🔙 Отмена$"), universal_cancel),
            MessageHandler(filters.Regex("^🏠 Главное меню$"), universal_menu)
        ]
    )

    # Conversation handler для удаления книги
    delete_book_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("delete", delete_book_start)],
        states={
            DELETE_SELECT_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_book_select)],
            DELETE_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_book_confirm)],
        },
        fallbacks=[
            CommandHandler("cancel", universal_cancel),
            CommandHandler("menu", universal_menu),
            MessageHandler(filters.Regex("^❌ Отмена$"), universal_cancel),
            MessageHandler(filters.Regex("^🔙 Отмена$"), universal_cancel),
            MessageHandler(filters.Regex("^🏠 Главное меню$"), universal_menu)
        ]
    )

    # Conversation handler для редактирования книги
    edit_book_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("edit", edit_book_start)],
        states={
            EDIT_SELECT_BOOK: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_book_select)],
            EDIT_SELECT_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field_select)],
            EDIT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value_process)],
        },
        fallbacks=[
            CommandHandler("cancel", universal_cancel),
            CommandHandler("menu", universal_menu),
            MessageHandler(filters.Regex("^❌ Отмена$"), universal_cancel),
            MessageHandler(filters.Regex("^🔙 Отмена$"), universal_cancel),
            MessageHandler(filters.Regex("^🏠 Главное меню$"), universal_menu)
        ]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(CommandHandler("help", show_help))
    app.add_handler(CommandHandler("cancel", universal_cancel))
    app.add_handler(add_conv_handler)
    app.add_handler(status_conv_handler)
    app.add_handler(search_conv_handler)
    app.add_handler(book_info_conv_handler)
    app.add_handler(delete_book_conv_handler)
    app.add_handler(edit_book_conv_handler)
    app.add_handler(CommandHandler("list", list_books))
    app.add_handler(CommandHandler("series", list_series))
    app.add_handler(CommandHandler("my", my_books))
    app.add_handler(CommandHandler("search", search_books))
    app.add_handler(CommandHandler("book_info", book_info_start))
    app.add_handler(CommandHandler("delete_book", delete_book_start))
    app.add_handler(CommandHandler("edit", edit_book_start))
    app.add_handler(CommandHandler("statistics", show_statistics))
    app.add_handler(CommandHandler("export_library", export_library))
    app.add_handler(MessageHandler(filters.Regex("^📋 Список книг$"), list_books))
    app.add_handler(MessageHandler(filters.Regex("^📖 Мои книги$"), my_books))
    app.add_handler(MessageHandler(filters.Regex("^📚 Серии$"), list_series))
    app.add_handler(MessageHandler(filters.Regex("^📷 Обложки$"), show_covers))

    return app

# Удаляю дублирующее определение main и оставляю только одну функцию main
async def main():
    app = build_application()
    try:
        app.run_polling()
    except RuntimeError:
        import nest_asyncio  # type: ignore
        nest_asyncio.apply()
        app.run_polling()


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        import nest_asyncio  # type: ignore

        nest_asyncio.apply()
        asyncio.get_event_loop().run_until_complete(main())
