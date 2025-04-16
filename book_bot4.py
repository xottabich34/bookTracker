import logging
import sqlite3
import asyncio
from io import BytesIO
import re
from telegram import Update, InputFile, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

IDS = {7286822228, 833243761}
TOKEN = "7885426006:AAFg9OWfl4nw_dJ4IJRZV-bKGH9UQf3aTnc"
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

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введи название книги:")
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

    await update.message.reply_text(f"Книга «{data['title']}» добавлена ✅", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добавление книги отменено", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для учёта книг 📚\n"
        "/add — добавить книгу (по шагам)\n"
        "/status <название> <статус> — установить статус\n"
        "/list — список книг\n"
        "/series_add <название> — создать серию\n"
        "/add_to_series <книга> | <серия> | <номер>\n"
        "/series <название> — показать книги серии\n"
        "/cover <название> (ответом на фото) — установить обложку\n"
        "/show <название> — показать обложку\n"
        "/search_series <фрагмент> — найти серии по названию\n"
        "/search_author <имя> — найти книги по автору\n"
        "/search_isbn <isbn> — найти книгу по ISBN\n"
        "/filter_status <статус> — отфильтровать книги по статусу"
    )

async def set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        _, title, status = update.message.text.split(maxsplit=2)
        cursor.execute("SELECT id FROM books WHERE title = ?", (title,))
        row = cursor.fetchone()
        if not row:
            await update.message.reply_text("Книга не найдена")
            return
        book_id = row[0]
        cursor.execute("""
            INSERT INTO user_books (user_id, book_id, status)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, book_id) DO UPDATE SET status = excluded.status
        """, (user_id, book_id, status))
        conn.commit()
        await update.message.reply_text(f"Статус книги «{title}» установлен как {status} ✅")
    except Exception as e:
        await update.message.reply_text("Ошибка. Формат: /status <название> <статус>")

# --- BOT LAUNCH ---
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
            ADD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_description)],
            ADD_COVER: [MessageHandler(filters.PHOTO, add_cover)],
            ADD_ISBN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_isbn)],
            ADD_AUTHORS: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_authors)]
        },
        fallbacks=[CommandHandler("cancel", add_cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("status", set_status))

    try:
        await app.run_polling()
    except RuntimeError:
        import nest_asyncio
        nest_asyncio.apply()
        await app.run_polling()

if __name__ == "__main__":
    import asyncio
    try:
        asyncio.get_event_loop().run_until_complete(main())
    except RuntimeError:
        import nest_asyncio
        nest_asyncio.apply()
        asyncio.get_event_loop().run_until_complete(main())
