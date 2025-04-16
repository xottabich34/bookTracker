from logging import raiseExceptions

import logging
import sqlite3
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

IDS = {7286822228, }
# 🔧 Логи
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

# 📚 Подключение к БД
conn = sqlite3.connect("books.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    is_read BOOLEAN DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS books_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    book_id INTEGER,book
    is_read BOOLEAN DEFAULT 0
)
""")

conn.commit()
def ensure_blob_column():
    cursor.execute("PRAGMA table_info(books)")
    columns = [col[1] for col in cursor.fetchall()]
    if "image_blob" not in columns:
        cursor.execute("ALTER TABLE books ADD COLUMN image_blob BLOB")
        conn.commit()

ensure_blob_column()

# 🔹 Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info('')
    if update.effective_user.id not in IDS:
        logger.debug('wrong user %s', update.effective_user.id)
        raise Exception("wrong user")
    await update.message.reply_text(
        "Привет! Я помогу тебе вести список книг 📚\n"
        "➕ /add <название> — добавить книгу\n"
        "✅ /read <название> — отметить как прочитанную\n"
        "📋 /list — все книги\n"
        "📖 /list_read — прочитанные\n"
        "📕 /list_unread — непрочитанные\n"
        "🧹 /clear — удалить все книги"
    )

async def add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    title = " ".join(context.args).strip()
    if not title:
        await update.message.reply_text("Укажи название книги после команды /add")
        return

    cursor.execute("INSERT INTO books (user_id, title) VALUES (?, ?)", (user_id, title))
    conn.commit()
    await update.message.reply_text(f"Книга «{title}» добавлена!")

async def mark_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    title = " ".join(context.args).strip()
    if not title:
        await update.message.reply_text("Укажи название книги после команды /read")
        return

    cursor.execute("""
        UPDATE books
        SET is_read = 1
        WHERE user_id = ? AND title = ?
    """, (user_id, title))
    conn.commit()

    if cursor.rowcount == 0:
        await update.message.reply_text("Такой книги не найдено.")
    else:
        await update.message.reply_text(f"Книга «{title}» отмечена как прочитанная!")

async def list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("SELECT title, is_read FROM books WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("У тебя пока нет ни одной книги.")
        return

    msg = "📚 Твои книги:\n"
    for title, is_read in rows:
        status = "✅" if is_read else "❌"
        msg += f"{status} {title}\n"

    await update.message.reply_text(msg)

async def list_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("SELECT title FROM books WHERE user_id = ? AND is_read = 1", (user_id,))
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("Прочитанных книг пока нет.")
        return

    msg = "📖 Прочитанные книги:\n" + "\n".join(f"✅ {row[0]}" for row in rows)
    await update.message.reply_text(msg)

async def list_unread(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("SELECT title FROM books WHERE user_id = ? AND is_read = 0", (user_id,))
    rows = cursor.fetchall()

    if not rows:
        await update.message.reply_text("Все книги прочитаны 🎉")
        return

    msg = "📕 Непрочитанные книги:\n" + "\n".join(f"❌ {row[0]}" for row in rows)
    await update.message.reply_text(msg)

async def clear_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("DELETE FROM books WHERE user_id = ?", (user_id,))
    conn.commit()
    await update.message.reply_text("Список книг очищен.")

# 🚀 Запуск бота
async def main():
    app = ApplicationBuilder().token("7885426006:AAFg9OWfl4nw_dJ4IJRZV-bKGH9UQf3aTnc").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_book))
    app.add_handler(CommandHandler("read", mark_read))
    app.add_handler(CommandHandler("list", list_books))
    app.add_handler(CommandHandler("list_read", list_read))
    app.add_handler(CommandHandler("list_unread", list_unread))
    app.add_handler(CommandHandler("clear", clear_books))

    logger.info("Бот запущен.")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановка бота...")

    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    logger.info("Бот корректно остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "event loop is closed" in str(e):
            logger.warning("Цикл событий уже закрыт.")
        else:
            raise
