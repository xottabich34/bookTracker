import sqlite3
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, Updater
)

# Создаём и подключаем БД
conn = sqlite3.connect("books.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS books (
    user_id INTEGER,
    title TEXT
)
""")
conn.commit()

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу тебе сохранять прочитанные книги.\n"
        "Используй команду /add <название книги>, чтобы добавить её в список."
    )

async def add_book(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    title = " ".join(context.args)
    if title:
        cursor.execute("INSERT INTO books (user_id, title) VALUES (?, ?)", (user_id, title))
        conn.commit()
        await update.message.reply_text(f"Книга «{title}» добавлена!")
    else:
        await update.message.reply_text("Пожалуйста, укажи название книги после команды /add.")

async def list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("SELECT title FROM books WHERE user_id = ?", (user_id,))
    rows = cursor.fetchall()
    if rows:
        books = "\n".join(f"- {row[0]}" for row in rows)
        await update.message.reply_text("Вот твои книги:\n" + books)
    else:
        await update.message.reply_text("Ты ещё не добавил ни одной книги.")

async def clear_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    cursor.execute("DELETE FROM books WHERE user_id = ?", (user_id,))
    conn.commit()
    await update.message.reply_text("Список книг очищен.")

# Основной запуск
async def main():
    app = ApplicationBuilder().token("7885426006:AAFg9OWfl4nw_dJ4IJRZV-bKGH9UQf3aTnc").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_book))
    app.add_handler(CommandHandler("list", list_books))
    app.add_handler(CommandHandler("clear", clear_books))

    print("Бот запущен...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    # asyncio.run(main())
    # asyncio.get_event_loop().run_until_complete(main())
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Бот остановлен вручную.")