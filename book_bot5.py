import logging
import os
import re
import sqlite3

import dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

dotenv.load_dotenv('.env')
IDS =set(int(x) for x in os.getenv('IDS').split(','))

TOKEN = os.getenv('TOKEN')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- DB SETUP ---
conn = sqlite3.connect("books.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
""")

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS authors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS book_authors (
    book_id INTEGER,
    author_id INTEGER,
    PRIMARY KEY (book_id, author_id),
    FOREIGN KEY (book_id) REFERENCES books(id),
    FOREIGN KEY (author_id) REFERENCES authors(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS user_books (
    user_id INTEGER,
    book_id INTEGER,
    status TEXT CHECK(status IN ('planning', 'reading', 'finished')),
    PRIMARY KEY (user_id, book_id),
    FOREIGN KEY (book_id) REFERENCES books(id)
)
""")
conn.commit()

# --- ADD BOOK WIZARD ---
ADD_TITLE, ADD_DESC, ADD_COVER, ADD_ISBN, ADD_AUTHORS = range(5)

menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        ["➕ Добавить книгу", "📋 Все книги"],
        ["📖 Мои книги", "🔍 Поиск"],
        ["🏷 Статусы", "📚 Серии"],
        ["📷 Обложки", "ℹ️ О книге"]
    ],
    resize_keyboard=True
)

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи название книги:", reply_markup=ReplyKeyboardRemove())
    return ADD_TITLE


async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_book'] = {'title': update.message.text.strip()}
    await update.message.reply_text("Теперь введи описание книги:")
    return ADD_DESC

async def add_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['new_book']['description'] = update.message.text.strip()
    await update.message.reply_text("Теперь отправь обложку книги (как изображение):")
    return ADD_COVER

async def add_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправь фото")
        return ADD_COVER
    file = await update.message.photo[-1].get_file()
    byte_data = await file.download_as_bytearray()
    context.user_data['new_book']['image_blob'] = byte_data
    await update.message.reply_text("Введите ISBN книги (или пропусти, отправив '-'):")
    return ADD_ISBN

async def add_isbn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    isbn = update.message.text.strip()
    isbn_clean = isbn.replace("-", "").replace(" ", "")
    if isbn != '-' and not re.match(r'^\d{9}[\dXx]$|^\d{13}$', isbn_clean):
        await update.message.reply_text("Некорректный формат ISBN. Введи 10 или 13 цифр (последняя может быть X для ISBN-10). Попробуй ещё раз или введи '-' чтобы пропустить:")
        return ADD_ISBN
    context.user_data['new_book']['isbn'] = None if isbn == '-' else isbn
    await update.message.reply_text("Введи авторов книги через запятую:")
    return ADD_AUTHORS

async def add_authors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data['new_book']
    author_names = [a.strip() for a in update.message.text.split(',') if a.strip()]

    cursor.execute("""
        INSERT OR IGNORE INTO books (title, description, image_blob, isbn)
        VALUES (?, ?, ?, ?)
    """, (data['title'], data['description'], data['image_blob'], data['isbn']))
    conn.commit()
    cursor.execute("SELECT id FROM books WHERE title = ?", (data['title'],))
    book_id = cursor.fetchone()[0]

    for name in author_names:
        cursor.execute("INSERT OR IGNORE INTO authors (name) VALUES (?)", (name,))
        cursor.execute("SELECT id FROM authors WHERE name = ?", (name,))
        author_id = cursor.fetchone()[0]
        cursor.execute("INSERT OR IGNORE INTO book_authors (book_id, author_id) VALUES (?, ?)", (book_id, author_id))
    conn.commit()

    await update.message.reply_text(f"Книга «{data['title']}» добавлена ✅", reply_markup=menu_keyboard)
    return ConversationHandler.END

async def add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добавление книги отменено", reply_markup=menu_keyboard)
    return ConversationHandler.END

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите действие:", reply_markup=menu_keyboard)

# --- PLACEHOLDER FUNCTIONS ---
async def list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Список всех книг пока не реализован")

async def show_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Показ конкретной книги пока не реализован")

async def your_books_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ваши книги пока не реализованы")

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Поиск пока не реализован")

async def update_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Изменение статуса пока не реализовано")

async def series_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Работа с сериями пока не реализована")

async def covers_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Работа с обложками пока не реализована")

# --- BOT LAUNCH ---
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_start), MessageHandler(filters.Regex("^➕ Добавить книгу$"), add_start)],
        states={
            ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
            ADD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_description)],
            ADD_COVER: [MessageHandler(filters.PHOTO, add_cover)],
            ADD_ISBN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_isbn)],
            ADD_AUTHORS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_authors)]
        },
        fallbacks=[CommandHandler("cancel", add_cancel)]
    )

    app.add_handler(CommandHandler("start", menu_handler))
    app.add_handler(CommandHandler("menu", menu_handler))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("list", list_books))
    app.add_handler(CommandHandler("book", show_book))

    app.add_handler(MessageHandler(filters.Regex("^📋 Все книги$"), list_books))
    app.add_handler(MessageHandler(filters.Regex("^📖 Мои книги$"), your_books_handler))
    app.add_handler(MessageHandler(filters.Regex("^🔍 Поиск$"), search_handler))
    app.add_handler(MessageHandler(filters.Regex("^🏷 Статусы$"), update_status_handler))
    app.add_handler(MessageHandler(filters.Regex("^📚 Серии$"), series_handler))
    app.add_handler(MessageHandler(filters.Regex("^📷 Обложки$"), covers_handler))
    app.add_handler(MessageHandler(filters.Regex("^ℹ️ О книге$"), show_book))

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