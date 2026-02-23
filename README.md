# Photo Processing

API для обработки изображений с поддержкой двух типов обработки:
- **White Background** - удаление фона и замена на белый
- **Interior** - обработка интерьерных изображений с AI-категоризацией

## 🚀 Возможности

- Асинхронная обработка изображений
- Фоновая обработка задач
- UUID-based аутентификация
- Административное управление пользователями
- Отслеживание прогресса обработки
- Автоматическая очистка старых задач
- Health check с проверкой БД
- Поддержка множественных воркеров

## 📋 Требования

- Python 3.13+
- PostgreSQL 12+
- Docker (опционально)

## 🛠 Установка

### Локальная установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd photo-processing
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл `.env`:
```bash
cp .env.example .env
```

5. Настройте переменные окружения в `.env`:
```env
# ============================================
# Конфигурация базы данных PostgreSQL
# ============================================
# Формат: postgresql://user:password@host:port/database
DATABASE_URL=postgresql://user:password@host:5432/database_name

# ============================================
# OpenAI API (для обработки интерьеров)
# ============================================
OPENAI_API_KEY=sk-your-openai-api-key-here
MODEL_NAME=openai-gpt-4.1-mini
IMAGE_MODEL=gemini-2.5-flash-image

# ============================================
# Pixian API (для обработки белого фона)
# ============================================
PIXIAN_API_USER=your-pixian-api-user
PIXIAN_API_KEY=your-pixian-api-key

# ============================================
# Логирование (Poradock Logging API)
# ============================================
PORADOCK_LOG_TOKEN=your-interior-log-token-uuid

# ============================================
# Опциональные настройки
# ============================================
# Включить логирование SQL запросов (true/false)
SQL_DEBUG=false
```

6. Примените миграции БД:
```bash
psql -h host -U user -d dbname -f database/migrations/001_initial_schema.sql
psql -h host -U user -d dbname -f database/migrations/002_insert_categories.sql
```

7. Запустите приложение:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker

1. Соберите образ:
```bash
docker build -t photo-processing:latest .
```

2. Запустите контейнер:
```bash
docker run -d --name photo-processing -p 8000:8000 --env-file .env photo-processing:latest
```

Или используйте `docker-compose` (если есть):
```bash
docker-compose up -d
```

## 📚 API Документация

После запуска приложения документация доступна по адресу:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔐 Аутентификация

API использует UUID-based аутентификацию. Передавайте UUID пользователя в заголовке:

```bash
curl -H "X-User-Id: your-user-uuid" http://localhost:8000/api/v1/auth/me
```

### Создание пользователя (только для админов)

```bash
curl -X POST http://localhost:8000/api/v1/admin/users \
  -H "X-User-Id: admin-uuid" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "is_admin": false,
    "rate_limit": 100
  }'
```

## 📡 Основные эндпоинты

### Аутентификация

- `GET /api/v1/auth/me` - Получить текущего пользователя

### Администрирование (только для админов)

- `POST /api/v1/admin/users` - Создать пользователя
- `GET /api/v1/admin/users` - Список всех пользователей
- `GET /api/v1/admin/users/{user_id}` - Получить пользователя
- `PUT /api/v1/admin/users/{user_id}` - Обновить пользователя
- `DELETE /api/v1/admin/users/{user_id}` - Удалить пользователя

### Обработка изображений

- `POST /api/v1/processing/parallel` - Запустить обработку

**Параметры:**
- `white_bg` (bool, по умолчанию `true`) - Тип обработки:
  - `true` - White Background: удаление фона и замена на белый через Pixian.AI
  - `false` - Interior: AI-обработка интерьерных изображений с автоматической категоризацией

**Как работает определение типа обработки:**

1. **White Background** (`white_bg=true`):
   - Удаление фона через Pixian.AI API
   - Замена на белый фон (#FFFFFF)
   - Подходит для товарных фотографий

2. **Interior** (`white_bg=false`):
   - Автоматическое определение категории товара через GPT-4 Vision:
     - Анализ изображения
     - Определение основной категории (KITCHEN, BATHROOM, LIVING_ROOM, BEDROOM, OFFICE, HOLIDAY)
     - Определение подкатегории (например, COOKWARE, TOWELS, FURNITURE)
   - Генерация промпта на основе категории
   - Обработка изображения через Gemini для создания профессионального изображения
   - Обрезка до формата 3:4

**Пример запроса:**
```bash
# White Background обработка
curl -X POST http://localhost:8000/api/v1/processing/parallel \
  -H "X-User-Id: your-uuid" \
  -F "white_bg=true" \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg"

# Interior обработка
curl -X POST http://localhost:8000/api/v1/processing/parallel \
  -H "X-User-Id: your-uuid" \
  -F "white_bg=false" \
  -F "files=@interior1.jpg"
```

### Управление задачами

- `GET /api/v1/tasks/{task_id}/status` - Статус задачи
- `GET /api/v1/tasks/{task_id}/download` - Скачать результат

### Системные

- `GET /health` - Health check

## 📊 Примеры использования

### 1. Обработка изображений с белым фоном

```python
import requests

url = "http://localhost:8000/api/v1/processing/parallel"
headers = {"X-User-Id": "your-uuid"}

with open("image.jpg", "rb") as f:
    files = {"files": f}
    data = {"white_bg": True}  # White Background обработка
    response = requests.post(url, headers=headers, files=files, data=data)
    task_id = response.json()["task_id"]
    print(f"Task ID: {task_id}")
```

### 1.1. Обработка интерьерных изображений (с автоматической категоризацией)

```python
import requests

url = "http://localhost:8000/api/v1/processing/parallel"
headers = {"X-User-Id": "your-uuid"}

with open("interior.jpg", "rb") as f:
    files = {"files": f}
    data = {"white_bg": False}  # Interior обработка
    response = requests.post(url, headers=headers, files=files, data=data)
    task_id = response.json()["task_id"]
    print(f"Task ID: {task_id}")
    # Система автоматически определит категорию товара через AI
```

### 2. Проверка статуса задачи

```python
import requests
import time

task_id = "your-task-id"
url = f"http://localhost:8000/api/v1/tasks/{task_id}/status"
headers = {"X-User-Id": "your-uuid"}

while True:
    response = requests.get(url, headers=headers)
    status = response.json()
    print(f"Status: {status['status']}, Progress: {status['progress']}%")
    
    if status["status"] == "completed":
        break
    elif status["status"] == "failed":
        print(f"Error: {status.get('error')}")
        break
    
    time.sleep(2)
```

### 3. Скачивание результата

```python
import requests

task_id = "your-task-id"
url = f"http://localhost:8000/api/v1/tasks/{task_id}/download"
headers = {"X-User-Id": "your-uuid"}

response = requests.get(url, headers=headers)
with open("result.zip", "wb") as f:
    f.write(response.content)
```

## 🏗 Архитектура

Проект использует 3-слойную архитектуру:

```
Routers → Handlers → Services → Repositories → Database
```

- **Routers** (`api/routers/`) - FastAPI роутеры для эндпоинтов
- **Handlers** (`api/handlers/`) - Обработка HTTP запросов/ответов
- **Services** (`api/services/`) - Бизнес-логика
- **Repositories** (`api/repositories/`) - Доступ к данным
- **Models** (`database/models.py`) - SQLAlchemy модели

## 📁 Структура проекта

```
photo-processing/
├── api/
│   ├── routers/          # API роутеры
│   ├── handlers/         # Обработчики запросов
│   ├── services/         # Бизнес-логика
│   ├── repositories/     # Доступ к данным
│   ├── processors/       # Обработчики изображений
│   ├── models/           # Pydantic схемы
│   ├── main.py           # Точка входа
│   ├── dependencies.py   # FastAPI зависимости
│   └── logging.py        # Логирование
├── core/
│   └── config.py         # Конфигурация
├── database/
│   ├── models.py         # SQLAlchemy модели
│   ├── db_session.py     # Сессии БД
│   └── migrations/       # SQL миграции
├── white/                # Обработка белого фона
├── interior/             # Обработка интерьеров
├── Dockerfile
├── requirements.txt
└── README.md
```

## ⚙️ Конфигурация

Все настройки через environment variables:

- `DATABASE_URL` - URL подключения к PostgreSQL
- `MAX_FILE_SIZE` - Максимальный размер файла (по умолчанию 10MB)
- `MAX_FILES_COUNT` - Максимальное количество файлов (по умолчанию 50)
- `TASK_CLEANUP_INTERVAL_HOURS` - Интервал очистки задач (по умолчанию 1 час)
- `TASK_MAX_AGE_HOURS` - Возраст задач для удаления (по умолчанию 24 часа)
- `SQL_DEBUG` - Включить SQL логирование (по умолчанию false)

## 🔍 Мониторинг

### Health Check

```bash
curl http://localhost:8000/health
```

Ответ:
```json
{
  "status": "healthy",
  "database": "connected"
}
```

### Логи

Логи доступны через Docker:
```bash
docker logs photo-processing
docker logs photo-processing --tail 100 -f
```

## 🐛 Решение проблем

### Ошибка подключения к БД

Проверьте `DATABASE_URL` в переменных окружения и доступность PostgreSQL.

### Ошибка обработки изображений

Проверьте:
- API ключи для Pixian/OpenAI
- Размер и формат файлов
- Логи контейнера

### Контейнер не запускается

Проверьте логи:
```bash
docker logs photo-processing
```
