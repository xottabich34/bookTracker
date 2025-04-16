import logging
import sqlite3
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

# 🔧 Настройка логов
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 📚 База данных
conn = sqlite3.connect("books.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS books (
    user_id INTEGER,
    title TEXT
)
""")
conn.commit()

# 📌 Команды бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу тебе сохранять прочитанные книги.\n"
        "Добавь книгу через /add <название> и покажи список через /list."
    )

async def add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    title = " ".join(context.args)
    if title:
        cursor.execute("INSERT INTO books (user_id, title) VALUES (?, ?)", (user_id, title))
        conn.commit()
        await update.message.reply_text(f"Книга «{title}» добавлена!")
    else:
        await update.message.reply_text("Укажи название книги после /add")

async def list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("SELECT title FROM books WHERE user_id = ?", (user_id,))
    books = cursor.fetchall()
    if books:
        text = "\n".join(f"- {title[0]}" for title in books)
        await update.message.reply_text("Твои книги:\n" + text)
    else:
        await update.message.reply_text("Ты ещё не добавил ни одной книги.")

async def clear_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("DELETE FROM books WHERE user_id = ?", (user_id,))
    conn.commit()
    await update.message.reply_text("Список книг очищен.")

# 🚀 Запуск бота с возможностью корректной остановки
async def main():
    app = ApplicationBuilder().token("7885426006:AAFg9OWfl4nw_dJ4IJRZV-bKGH9UQf3aTnc").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_book))
    app.add_handler(CommandHandler("list", list_books))
    app.add_handler(CommandHandler("clear", clear_books))

    logger.info("Бот запущен и готов к работе.")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # Ждём завершения (например, по Ctrl+C или Stop)
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Получен сигнал остановки")

    logger.info("Останавливаем бота...")
    await app.updater.stop()
    await app.stop()
    await app.shutdown()
    logger.info("Бот корректно остановлен.")

# 🔁 Безопасный запуск в PyCharm
if __name__ == "__main__":
    import asyncio

    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "event loop is closed" in str(e):
            # Бывает при повторном запуске в некоторых IDE
            logger.warning("Цикл событий был закрыт, перезапускаем...")
            import sys
            sys.exit(0)
        else:
            raise
