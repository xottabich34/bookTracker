import logging
import os
import re
import sqlite3

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# Загрузка переменных окружения из файла .env
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")  # Токен бота, полученный от BotFather
ALLOWED_IDS = set(map(int, os.getenv("ALLOWED_IDS", "").split(",")))  # Список ID пользователей, которым разрешён доступ

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Уровень логирования — DEBUG
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # Формат логов
    datefmt="%Y-%m-%d %H:%M:%S"  # Формат даты и времени
)
logger = logging.getLogger(__name__)  # Создание логгера для текущего модуля

# --- НАСТРОЙКА БАЗЫ ДАННЫХ ---
# Подключение к базе данных SQLite (или создание, если её нет)
conn = sqlite3.connect("books.db", check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы для серий книг, если она ещё не существует
cursor.execute("""
CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
""")

# Создание таблицы для книг, если она ещё не существует
cursor.execute("""
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT UNIQUE,
    description TEXT,
    image_blob BLOB,
    series_id INTEGER,
    series_order INTEGER,
    isbn TEXT,
    FOREIGN KEY (series_id) REFERENCES series(id)
)
""")

# Создание таблицы для авторов, если она ещё не существует
cursor.execute("""
CREATE TABLE IF NOT EXISTS authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
""")

# Создание таблицы для связи книг и авторов, если она ещё не существует
cursor.execute("""
CREATE TABLE IF NOT EXISTS book_authors (
    book_id INTEGER,
    author_id INTEGER,
    PRIMARY KEY (book_id, author_id),
    FOREIGN KEY (book_id) REFERENCES books(id),
    FOREIGN KEY (author_id) REFERENCES authors(id)
)
""")

# Создание таблицы для связи пользователей и книг, если она ещё не существует
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_books (
    user_id INTEGER,
    book_id INTEGER,
    status TEXT CHECK(status IN ('planning', 'reading', 'finished')),
    PRIMARY KEY (user_id, book_id),
    FOREIGN KEY (book_id) REFERENCES books(id)
)
""")
conn.commit()  # Сохранение изменений в базе данных


# --- ДЕКОРАТОР ДЛЯ КОНТРОЛЯ ДОСТУПА ---
def owner_only(func):
    # Декоратор, который проверяет, есть ли ID пользователя в списке разрешённых
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if False:  # user_id not in ALLOWED_IDS:
            await update.message.reply_text("Извините, доступ запрещён.")
            return
        return await func(update, context)

    return wrapper


# --- МАСТЕР ДОБАВЛЕНИЯ КНИГИ ---
# Константы для состояний ConversationHandler
ADD_TITLE, ADD_DESC, ADD_COVER, ADD_ISBN, ADD_AUTHORS, ADD_SERIES, ADD_SERIES_ORDER = range(7)

# Клавиатура с основными командами
menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Добавить книгу", "📋 Список книг"],
        ["📖 Мои книги", "🔍 Поиск"],
        ["🏷 Статусы", "📚 Серии"],
        ["📷 Обложки", "ℹ️ О книге"]
    ],
    resize_keyboard=True  # Автоматическое изменение размера клавиатуры
)


# Начало процесса добавления книги
@owner_only
async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи название книги:", reply_markup=ReplyKeyboardRemove())
    return ADD_TITLE  # Переход к состоянию ADD_TITLE


# Обработка ввода названия книги
@owner_only
async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.strip():
        await update.message.reply_text("Название книги не может быть пустым. Введите снова:")
        return ADD_TITLE
    context.user_data['new_book'] = {'title': update.message.text.strip()}  # Сохранение названия
    await update.message.reply_text("Теперь введи описание книги:")
    return ADD_DESC  # Переход к состоянию ADD_DESC


# Обработка ввода описания книги
@owner_only
async def add_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_book']['description'] = update.message.text.strip()  # Сохранение описания
    await update.message.reply_text("Теперь отправь обложку книги (как изображение):")
    return ADD_COVER  # Переход к состоянию ADD_COVER


# Обработка загрузки обложки книги
@owner_only
async def add_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:  # Проверка, что сообщение содержит фото
        await update.message.reply_text("Пожалуйста, отправь фото")
        return ADD_COVER
    file = await update.message.photo[-1].get_file()  # Получение файла изображения
    byte_data = await file.download_as_bytearray()  # Преобразование изображения в байты
    context.user_data['new_book']['image_blob'] = byte_data  # Сохранение обложки
    await update.message.reply_text("Введите ISBN книги (или пропусти, отправив '-'):")
    return ADD_ISBN  # Переход к состоянию ADD_ISBN


# Обработка ввода ISBN
@owner_only
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
@owner_only
async def add_authors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.strip():
        await update.message.reply_text("Список авторов не может быть пустым. Введите хотя бы одного автора:")
        return ADD_AUTHORS
    author_names = [a.strip() for a in update.message.text.split(',') if a.strip()]  # Разделение авторов
    context.user_data['new_book']['authors'] = author_names  # Сохранение авторов
    await update.message.reply_text("Введите название серии (или '-' если без серии):")
    return ADD_SERIES  # Переход к состоянию ADD_SERIES


# Обработка ввода серии
@owner_only
async def add_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    series_name = update.message.text.strip()
    if series_name != "-":  # Если серия указана
        cursor.execute("INSERT OR IGNORE INTO series (name) VALUES (?)", (series_name,))  # Добавление серии
        cursor.execute("SELECT id FROM series WHERE name = ?", (series_name,))  # Получение ID серии
        series_id = cursor.fetchone()[0]
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
    data = context.user_data['new_book']
    cursor.execute("""
        INSERT OR IGNORE INTO books (title, description, image_blob, isbn, series_id, series_order)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (data['title'], data['description'], data['image_blob'], data['isbn'], data.get('series_id'),
          data.get('series_order')))
    conn.commit()
    cursor.execute("SELECT id FROM books WHERE title = ?", (data['title'],))
    book_id = cursor.fetchone()[0]
    for name in data['authors']:
        cursor.execute("INSERT OR IGNORE INTO authors (name) VALUES (?)", (name,))
        cursor.execute("SELECT id FROM authors WHERE name = ?", (name,))
        author_id = cursor.fetchone()[0]
        cursor.execute("INSERT OR IGNORE INTO book_authors (book_id, author_id) VALUES (?, ?)",
                       (book_id, author_id))
    conn.commit()
    await update.message.reply_text(f"Книга «{data['title']}» добавлена ✅", reply_markup=menu_keyboard)
    return ConversationHandler.END


@owner_only
async def add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добавление книги отменено", reply_markup=menu_keyboard)
    return ConversationHandler.END


@owner_only
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите действие:", reply_markup=menu_keyboard)


@owner_only
async def list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT title FROM books")
    rows = cursor.fetchall()
    if rows:
        text = "\n".join([row[0] for row in rows])
        await update.message.reply_text("📚 Список книг:\n" + text)
    else:
        await update.message.reply_text("Библиотека пуста")


@owner_only
async def my_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("""
        SELECT b.title, ub.status FROM books b
        JOIN user_books ub ON b.id = ub.book_id
        WHERE ub.user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    if rows:
        lines = [f"{title} — {status}" for title, status in rows]
        await update.message.reply_text("📖 Ваши книги:\n" + "\n".join(lines))
    else:
        await update.message.reply_text("У вас нет отмеченных книг")


@owner_only
async def list_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT id, name FROM series")
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("Серии не найдены")
        return
    result = []
    for series_id, name in rows:
        cursor.execute("SELECT title FROM books WHERE series_id = ? ORDER BY series_order", (series_id,))
        books = [row[0] for row in cursor.fetchall()]
        result.append(f"📚 {name}:\n  " + "\n  ".join(books))
    await update.message.reply_text("\n\n".join(result))


# --- BOT LAUNCH ---
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
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
        fallbacks=[CommandHandler("cancel", add_cancel)]
    )

    app.add_handler(CommandHandler("start", menu_handler))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("list", list_books))
    app.add_handler(CommandHandler("series", list_series))
    app.add_handler(CommandHandler("my", my_books))
    app.add_handler(MessageHandler(filters.Regex("^📋 Список книг$"), list_books))
    app.add_handler(MessageHandler(filters.Regex("^📖 Мои книги$"), my_books))
    app.add_handler(MessageHandler(filters.Regex("^📚 Серии$"), list_series))

    try:
        app.run_polling()
    except RuntimeError:
        import nest_asyncio
        nest_asyncio.apply()
        app.run_polling()


if __name__ == "__main__":
    import asyncio

    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        import nest_asyncio

        nest_asyncio.apply()
        asyncio.get_event_loop().run_until_complete(main())
