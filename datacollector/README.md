# DataCollector Architecture

## Обзор

DataCollector - автоматическая система сбора данных с маркетплейсов с поддержкой приоритизации задач, многопоточной обработки и механизма повторных попыток.

## Ключевые компоненты

### 1. Task Queue System (`queue_manager.py`)

**TaskPriority:**
- `HIGH = 1` - Высокий приоритет (initial sync, stocks)
- `NORMAL = 2` - Обычный приоритет (regular updates)
- `LOW = 3` - Низкий приоритет

**Task:**
- Хранит информацию о задаче (token_id, endpoint, priority)
- Поддерживает retry с exponential backoff
- Максимум 5 попыток выполнения
- Backoff: min(60 * 2^attempts, 3600) секунд

**TaskQueue:**
- Priority queue для упорядочивания задач
- Retry queue для неудачных задач
- Thread-safe операции

### 2. Worker Pool (`worker.py`)

**Worker:**
- Обрабатывает задачи из очереди
- Соблюдает rate limits (60 сек между запросами для WB)
- Обрабатывает 429 ошибки с retry
- Логирует результаты выполнения

**WorkerPool:**
- Управляет пулом из 3 воркеров
- Graceful shutdown
- Параллельная обработка задач

### 3. Main Service (`main.py`)

**Функции при запуске:**
1. Инициализация коллекторов для всех токенов
2. Проверка наличия остатков за сегодня
3. Планирование initial/regular tasks
4. Запуск worker pool
5. Запуск background threads:
   - Retry queue processor (каждую минуту)
   - Stocks scheduler (проверка каждые 5 минут)

**Regular updates:**
- Каждые 10 минут добавление задач для всех endpoints
- Обработка через priority queue

**Stocks collection:**
- Ежедневно в 3:00 UTC (configurable per token)
- Автоматическая загрузка при отсутствии данных за сегодня
- Обновление существующих записей вместо дубликатов

### 4. Collectors (`collectors/wildberries.py`)

**Endpoints:**
- `incomes` - Поступления товаров
- `sales` - Продажи
- `orders` - Заказы
- `stocks` - Остатки (новое)

**Особенности:**
- Initial sync: загрузка всех данных с 2019-01-01
- Incremental sync: загрузка с последней успешной синхронизации
- Обработка 429 ошибок с retry
- Rate limiting: 60 секунд между запросами

## Конфигурация

### Database
- PostgreSQL на 192.168.0.44:5432
- Автоматическое создание/обновление записей

### Rate Limits
- Wildberries: 60 секунд между запросами
- Retry backoff: 60, 120, 240, 480, 960 секунд (max 3600)

### Intervals
- Regular updates: 10 минут
- Retry queue check: 1 минута
- Stocks scheduler check: 5 минут

## Запуск

```bash
python -m datacollector.main
```

## Graceful Shutdown

- SIGINT (Ctrl+C) или SIGTERM
- Остановка worker pool
- Завершение текущих задач
- Закрытие соединений с БД

## Логирование

- Уровень: INFO
- Формат: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Вывод: stdout
- Будущее: файл `/var/log/marketplacer/datacollector.log`

## Масштабирование

Для увеличения производительности можно:
1. Увеличить количество воркеров в `WorkerPool`
2. Настроить rate limits в `config.py`
3. Изменить интервалы обновления

## Мониторинг

Проверка статуса в таблицах:
- `sync_states` - последние синхронизации
- `collection_logs` - история сбора данных
