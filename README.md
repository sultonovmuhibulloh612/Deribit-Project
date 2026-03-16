# Deribit Price Tracker

Сервис для сбора и хранения индексных цен BTC/ETH с криптобиржи Deribit.

## Стек технологий

- **FastAPI** — REST API
- **Celery + Redis** — периодический сбор цен (каждую минуту)
- **PostgreSQL** — хранение данных
- **SQLAlchemy (async)** — ORM
- **aiohttp** — HTTP клиент для Deribit API
- **Docker / Docker Compose** — контейнеризация

## Структура проекта

```
deribit_project/
├── app/
│   ├── api/
│   │   └── routes/
│   │       └── prices.py       # FastAPI роуты
│   ├── client/
│   │   └── deribit_client.py   # Async HTTP клиент Deribit
│   ├── repositories/
│   │   └── price_repository.py # Слой доступа к БД
│   ├── services/
│   │   └── price_service.py    # Бизнес логика
│   ├── config.py               # Настройки через pydantic-settings
│   ├── database.py             # SQLAlchemy async engine
│   ├── models.py               # ORM модели
│   ├── schemas.py              # Pydantic схемы
│   └── main.py                 # FastAPI entrypoint
├── worker/
│   ├── celery_app.py           # Конфигурация Celery
│   └── tasks.py                # Celery таски
├── scripts/
│   └── init_db.py              # Создание таблиц
├── tests/
│   └── test_main.py            # Unit тесты
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## Разворачивание

### Требования

- Docker
- Docker Compose

### 1. Клонировать репозиторий

```bash
git clone <repository_url>
cd deribit_project
```

### 2. Запустить контейнеры

```bash
docker-compose up --build
```

После запуска:
- **API** доступно на `http://localhost:8000`
- **Swagger документация** на `http://localhost:8000/docs`
- Celery worker начнёт собирать цены каждую минуту автоматически

### 3. Запуск тестов

```bash
docker-compose exec api pytest
```

Или локально:

```bash
pip install -r requirements.txt
pytest
```

## API

Все методы принимают обязательный query-параметр `ticker` (например `btc_usd`, `eth_usd`).

### GET /api/v1/prices/all

Получить все сохранённые цены по тикеру.

```bash
curl "http://localhost:8000/api/v1/prices/all?ticker=btc_usd"
```

Ответ:
```json
[
  {
    "id": 1,
    "ticker": "btc_usd",
    "price": 65000.0,
    "timestamp": 1700000000
  }
]
```

### GET /api/v1/prices/latest

Получить последнюю цену по тикеру.

```bash
curl "http://localhost:8000/api/v1/prices/latest?ticker=btc_usd"
```

Ответ:
```json
{
  "ticker": "btc_usd",
  "price": 65000.0,
  "timestamp": 1700000000
}
```

### GET /api/v1/prices/range

Получить цены за период (UNIX timestamp в секундах).

```bash
curl "http://localhost:8000/api/v1/prices/range?ticker=btc_usd&from_timestamp=1700000000&to_timestamp=1700003600"
```

Ответ:
```json
[
  {
    "id": 2,
    "ticker": "btc_usd",
    "price": 65100.0,
    "timestamp": 1700003600
  }
]
```

## Design Decisions

### HTTP вместо WebSocket для Deribit клиента

Deribit рекомендует WebSocket для real-time подписок и активной торговли.
Задача — получать цену раз в минуту, что является классическим one-off data retrieval.
Документация Deribit прямо указывает HTTP как подходящий транспорт для таких случаев.
Держать постоянное WebSocket соединение ради одного запроса каждые 60 секунд — излишняя сложность.

### Celery вместо FastAPI BackgroundTasks

FastAPI мог бы делать периодические запросы самостоятельно, но Celery даёт:
- **Надёжность** — задачи в очереди Redis не теряются при падении сервиса
- **Retry логику** — автоматический повтор при ошибке
- **Независимость** — worker и API — отдельные процессы
- **Масштабируемость** — можно запустить несколько воркеров

### Разделение путей записи и чтения

- **Запись (Celery worker)** — создаёт свой async engine внутри `asyncio.run()`, потому что каждый вызов таски создаёт новый event loop. Использование глобального engine привело бы к ошибке `attached to a different loop`.
- **Чтение (FastAPI)** — использует `AsyncSessionFactory` из `database.py` через dependency injection. FastAPI имеет один постоянный event loop — конфликтов нет.

### Один коммит на таску

Все цены (btc_usd, eth_usd) сохраняются в одной транзакции. Если одна запись упадёт — ни одна не сохранится. Это лучше чем частично сохранённые данные за один момент времени.

### Репозиторий без commit

Метод `save` в репозитории только добавляет запись в сессию (`session.add`), не коммитит. Управление транзакцией — ответственность вызывающего кода. Это позволяет батчить несколько операций в одну транзакцию.
