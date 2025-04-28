# Book Tracker Bot 📚🤖

Telegram-бот для хранения и отслеживания списка прочитанных книг.

## Возможности

- Добавление книг с обложкой, описанием и ISBN
- Отметка книг как прочитанных
- Работа с сериями книг
- Список всех книг, только прочитанных или непрочитанных
- Полная поддержка нескольких пользователей

## Структура проекта

bookTracker/ 
├── booktracker/ # Исходный код бота 
│ └── main.py 
├── tests/ # Тесты проекта 
│ └── test_main.py 
├── books.db # Локальная база данных SQLite 
├── htmlcov/ # Отчёты покрытия кода (генерируются автоматически) 
├── pytest.ini # Настройки pytest 
├── requirements.txt # Зависимости проекта 
└── README.md # Этот файл


## Установка

```bash
git clone https://github.com/yourusername/bookTracker.git
cd bookTracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Запуск бота

Создайте файл .env в корне проекта и добавьте туда:

```BOT_TOKEN=ваш_токен_бота
ALLOWED_IDS=123456789
```

Запустите:

`python -m booktracker.main`

Запуск тестов

`pytest`

Или с отчётом покрытия:

`pytest -v --cov=booktracker --cov-report=term-missing --cov-report=html`

После этого откройте файл htmlcov/index.html в браузере для просмотра покрытия кода.
Лицензия

Проект распространяется под лицензией MIT.
