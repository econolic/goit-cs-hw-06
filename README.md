# Вебзастосунок з сокетами та MongoDB

Цей проект реалізує простий вебзастосунок, який взаємодіє з сервером за допомогою сокетів та зберігає інформацію в базі даних MongoDB.

## Особливості

- HTTP-сервер на Python без використання веб-фреймворків (порт 3000 в контейнері, 8000 зовні)
- Socket-сервер для обробки повідомлень (порт 5000 в контейнері, 8001 зовні, TCP)
- Збереження даних у MongoDB з connection pooling для кращої продуктивності
- ThreadPoolExecutor для ефективної обробки concurrent з'єднань
- Обробка сигналів для елегантного закриття застосунку
- Професійна система конфігурації з підтримкою різних оточень
- Валідація конфігурації та змінних середовища
- Docker контейнеризація
- Обробка статичних ресурсів (CSS, PNG)
- Форма для відправки повідомлень

## Структура проекту

```
├── main.py                 # Основний файл з HTTP та Socket серверами
├── config.py               # Система конфігурації з підтримкою різних оточень
├── .env.example            # Приклад змінних середовища
├── requirements.txt        # Python залежності
├── Dockerfile              # Docker образ
├── docker-compose.yaml     # Docker Compose конфігурація
├── .dockerignore           # Виключення для Docker
├── .gitignore              # Git виключення
└── front-init/             # Статичні файли
    ├── index.html          # Головна сторінка
    ├── message.html        # Сторінка з формою
    ├── error.html          # Сторінка помилки 404
    ├── style.css           # Стилі
    ├── logo.png            # Логотип
    └── storage/            # Директорія зберігання (legacy)
        └── data.json       # JSON файл (не використовується)
```

## Конфігурація

Застосунок підтримує професійну систему конфігурації з різними оточеннями:

### Оточення

- **Development** (за замовчуванням): 
  - Детальне логування (`LOG_LEVEL=DEBUG`)
  - Стандартні параметри connection pool (5-50 з'єднань)
  - 10 робочих потоків ThreadPoolExecutor
  - Оптимізоване для розробки та налагодження

- **Production**: 
  - Мінімальне логування (`LOG_LEVEL=WARNING`)
  - Збільшений connection pool до 100 з'єднань для високого навантаження
  - 20 робочих потоків для кращої продуктивності
  - Оптимізоване для продуктивної роботи

- **Testing**: 
  - Детальне логування (`LOG_LEVEL=DEBUG`)
  - Окрема тестова база даних (`test_messages_db`)
  - Зменшений connection pool до 10 з'єднань
  - Ізольоване середовище для тестування

### Змінні середовища

Скопіюйте `.env.example` у `.env` та налаштуйте:

```bash
# Режим роботи (development, production, testing)
ENVIRONMENT=development

# HTTP сервер
HTTP_HOST=0.0.0.0
HTTP_PORT=3000

# Socket сервер  
SOCKET_HOST=0.0.0.0
SOCKET_PORT=5000

# MongoDB
MONGO_URI=mongodb://mongodb:27017/
DB_NAME=messages_db
COLLECTION_NAME=messages

# MongoDB Connection Pool
MONGO_MAX_POOL_SIZE=50
MONGO_MIN_POOL_SIZE=5
MONGO_MAX_IDLE_TIME_MS=30000
MONGO_WAIT_QUEUE_TIMEOUT_MS=5000

# ThreadPoolExecutor
THREAD_POOL_MAX_WORKERS=10
THREAD_NAME_PREFIX=SocketWorker

# Socket налаштування
SOCKET_TIMEOUT=30.0
SOCKET_BACKLOG=10
SOCKET_BUFFER_SIZE=1024

# Logging
LOG_LEVEL=INFO
```

### Валідація конфігурації

Система автоматично валідує:
- Коректність значень портів (1-65535)
- Існування директорії front-init  
- Правильність MongoDB connection pool налаштувань (max >= min pool size)
- Інші конфігураційні параметри при запуску застосунку

## Технічний опис

### HTTP Сервер
- Обробляє маршрути: `/`, `/index.html`, `/message.html`
- Відправляє статичні файли: `style.css`, `logo.png`
- Обробляє POST запити з форми на `/message`
- Повертає сторінку помилки 404 для неіснуючих маршрутів

### Socket Сервер
- Працює по TCP протоколу
- Отримує дані від HTTP сервера
- Зберігає повідомлення в MongoDB з часовою відміткою

### MongoDB
- База даних: `messages_db`
- Колекція: `messages`
- Формат документа:
```json
{
  "date": "2025-08-04 14:30:25.123456",
  "username": "користувач",
  "message": "текст повідомлення"
}
```

## Запуск

### Використання Docker Compose (рекомендовано)

1. Склонуйте репозиторій:
```bash
git clone <repository-url>
cd goit-cs-hw-06
```

2. Запустіть контейнери:
```bash
docker-compose up --build
```

3. Відкрийте браузер та перейдіть на `http://localhost:8000`

### Локальний запуск

1. Встановіть залежності:
```bash
pip install -r requirements.txt
```

2. Переконайтеся, що MongoDB запущена на `mongodb://localhost:27017/` (для локального запуску встановіть `MONGO_URI=mongodb://localhost:27017/`)

3. Запустіть застосунок:
```bash
python main.py
```

**Примітка:** При запуску через Docker Compose застосунок доступний за адресою `http://localhost:8000`, оскільки порт 3000 може бути зайнятий системою. Локально застосунок працює на порту 3000.

## Використання

1. Відкрийте `http://localhost:8000` для перегляду головної сторінки
2. Перейдіть на "Send message" для відправки повідомлення
3. Заповніть форму з ім'ям користувача та повідомленням
4. Повідомлення буде збережене в базі даних MongoDB

## Тестування

### Перевірка роботи системи:

```bash
# Перевірка статусу контейнерів
docker-compose ps

# Перевірка логів веб-додатку
docker-compose logs web

# Тестування через curl
curl -X POST -d "username=Test&message=Hello World!" http://localhost:8000/message

# Перевірка збережених повідомлень в MongoDB
# Для development/production оточення:
docker exec mongodb mongosh messages_db --eval "db.messages.find().toArray()"

# Для testing оточення:
docker exec mongodb mongosh test_messages_db --eval "db.messages.find().toArray()"

# Або перевірити всі бази даних:
docker exec mongodb mongosh --eval "show dbs"
```

## Архітектура

Застосунок використовує багатопроцесну архітектуру:

### Процеси
- **HTTP сервер процес**: Обробляє веб-запити та статичні файли
- **Socket сервер процес**: Обробляє повідомлення та зберігає в MongoDB

### Concurrent Programming
- **ThreadPoolExecutor**: Управління пулом потоків для Socket клієнтів (10 робочих потоків)
- **Connection Pooling**: MongoDB пул з'єднань (5-50 з'єднань) для ефективного використання ресурсів
- **Signal Handling**: Елегантне закриття з обробкою SIGTERM/SIGINT сигналів

### Надійність
- **Timeout handling**: 30-секундний timeout для Socket операцій
- **Error handling**: Детальна обробка JSON, Socket та MongoDB помилок  
- **Resource cleanup**: Автоматичне закриття з'єднань та очищення ресурсів
- **Graceful shutdown**: Коректне завершення всіх процесів та потоків

## Технічні вимоги

- Python 3.11+
- Docker та Docker Compose
- MongoDB (автоматично через Docker)

## Troubleshooting

### Поширені проблеми:

1. **Помилка з'єднання MongoDB**: Переконайтеся, що `MONGO_URI` правильно налаштовано для вашого середовища
2. **Порт зайнятий**: Змініть порти в `docker-compose.yaml` якщо 8000/8001/27017 зайняті
3. **Конфігурація не працює**: Перевірте валідацію конфігурації в логах застосунку
4. **Контейнер не запускається**: Перевірте `docker-compose logs` для деталей помилки

### Корисні команди:

```bash
# Повний перезапуск з очищенням (УВАГА: видалить всі дані MongoDB!)
docker-compose down -v
docker-compose up --build

# Перезапуск без втрати даних
docker-compose down
docker-compose up --build

# Моніторинг логів у реальному часі
docker-compose logs -f web

# Перевірка мережевого підключення
docker exec goit-cs-hw-06-web-1 ping mongodb
```
