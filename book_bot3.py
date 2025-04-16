import logging
import sqlite3
import asyncio
from io import BytesIO
from telegram import Update, InputFile, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
IDS = {7286822228, 833243761}
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
    FOREIGN KEY (series_id) REFERENCES series(id)
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
ADD_TITLE, ADD_DESC, ADD_COVER = range(3)

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
    data = context.user_data['new_book']
    cursor.execute("INSERT OR IGNORE INTO books (title, description, image_blob) VALUES (?, ?, ?)",
                   (data['title'], data['description'], byte_data))
    conn.commit()
    await update.message.reply_text(f"Книга «{data['title']}» добавлена ✅", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def add_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Добавление книги отменено", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# --- COMMANDS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_sender.id in IDS:
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
            "/search_series <фрагмент> — найти серии по названию"
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

async def list_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT title FROM books")
    books = cursor.fetchall()
    if books:
        await update.message.reply_text("Список книг:\n" + "\n".join([b[0] for b in books]))
    else:
        await update.message.reply_text("Книг пока нет")

async def series_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args)
    cursor.execute("INSERT OR IGNORE INTO series (name) VALUES (?)", (name,))
    conn.commit()
    await update.message.reply_text(f"Серия «{name}» добавлена ✅")

async def add_to_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = update.message.text.split(" ", 1)[1].split("|")
        title = parts[0].strip()
        series = parts[1].strip()
        order = int(parts[2].strip())
        cursor.execute("SELECT id FROM series WHERE name = ?", (series,))
        series_id = cursor.fetchone()
        if not series_id:
            await update.message.reply_text("Серия не найдена")
            return
        cursor.execute("UPDATE books SET series_id = ?, series_order = ? WHERE title = ?",
                       (series_id[0], order, title))
        conn.commit()
        await update.message.reply_text(f"Книга «{title}» добавлена в серию «{series}» под номером {order} ✅")
    except:
        await update.message.reply_text("Формат: /add_to_series <книга> | <серия> | <номер>")

async def series_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = " ".join(context.args)
    cursor.execute("SELECT id FROM series WHERE name = ?", (name,))
    series_id = cursor.fetchone()
    if not series_id:
        await update.message.reply_text("Серия не найдена")
        return
    cursor.execute("SELECT title, series_order FROM books WHERE series_id = ? ORDER BY series_order", (series_id[0],))
    books = cursor.fetchall()
    if books:
        lines = [f"{b[1]}. {b[0]}" for b in books if b[1] is not None]
        await update.message.reply_text(f"Книги в серии «{name}»:\n" + "\n".join(lines))
    else:
        await update.message.reply_text("Книг в серии нет")

async def upload_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.message.reply_text("Ответь на команду /cover <название> фото-картинкой")
        return
    title = " ".join(context.args)
    if not update.message.photo:
        await update.message.reply_text("Пожалуйста, отправь фото")
        return
    file = await update.message.photo[-1].get_file()
    byte_data = await file.download_as_bytearray()
    cursor.execute("UPDATE books SET image_blob = ? WHERE title = ?", (byte_data, title))
    conn.commit()
    await update.message.reply_text("Обложка обновлена ✅")

async def show_cover(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = " ".join(context.args)
    cursor.execute("SELECT image_blob FROM books WHERE title = ?", (title,))
    row = cursor.fetchone()
    if not row or not row[0]:
        await update.message.reply_text("Обложка не найдена")
        return
    await update.message.reply_photo(photo=BytesIO(row[0]), caption=title)

async def search_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = " ".join(context.args)
    cursor.execute("SELECT name FROM series WHERE name LIKE ?", (f"%{query}%",))
    results = cursor.fetchall()
    if results:
        await update.message.reply_text("Найденные серии:\n" + "\n".join([r[0] for r in results]))
    else:
        await update.message.reply_text("Серии не найдены")

# --- BOT LAUNCH ---
async def main():
    app = ApplicationBuilder().token("7885426006:AAFg9OWfl4nw_dJ4IJRZV-bKGH9UQf3aTnc").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
            ADD_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_description)],
            ADD_COVER: [MessageHandler(filters.PHOTO, add_cover)]
        },
        fallbacks=[CommandHandler("cancel", add_cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("status", set_status))
    app.add_handler(CommandHandler("list", list_books))
    app.add_handler(CommandHandler("series_add", series_add))
    app.add_handler(CommandHandler("add_to_series", add_to_series))
    app.add_handler(CommandHandler("series", series_view))
    app.add_handler(CommandHandler("cover", upload_cover))
    app.add_handler(CommandHandler("show", show_cover))
    app.add_handler(CommandHandler("search_series", search_series))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())