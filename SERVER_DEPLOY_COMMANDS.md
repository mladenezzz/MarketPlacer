# Команды для развертывания на сервере

## Подключитесь к серверу и выполните команды:

```bash
# 1. Подключиться к серверу
ssh user@your-server-ip

# 2. Перейти в папку проекта
cd /path/to/MarketPlacer

# 3. Остановить datacollector
sudo systemctl stop datacollector

# 4. Обновить код из GitHub
git pull origin main

# 5. Запустить datacollector
sudo systemctl start datacollector

# 6. Проверить статус
sudo systemctl status datacollector

# 7. Проверить логи (нажмите Ctrl+C для выхода)
sudo journalctl -u datacollector -f
```

## Что должно быть в логах:

Вы должны увидеть:
- `Scheduling initial tasks...`
- `Ozon token 3 already synced, scheduling normal updates`
- `Worker X: Processing ozon_sales for token 3`
- `Worker Y: Processing ozon_orders for token 3`
- `Collecting Ozon orders from YYYY-MM-DD HH:MM:SS` (с точным временем)
- `Successfully processed ozon_sales...`
- `Saved N Ozon orders` (где N > 0, если есть новые заказы)
- `Successfully processed ozon_orders...`

## ВАЖНО:

- ✅ Миграция уже выполнена (база общая)
- ✅ Данные уже собраны
- ✅ Datacollector будет работать в инкрементальном режиме
- ✅ **ИСПРАВЛЕНИЕ**: Добавлено перекрытие в 1 час для сбора заказов Ozon, чтобы не пропускать заказы с ранним in_process_at
- ❌ НЕ запускайте migrate_ozon_sales.py на сервере
- ❌ НЕ запускайте reset_ozon_sync.py на сервере

## Последние изменения:

### Commit 5b6177a - fix: add 1-hour overlap for Ozon orders collection
**Проблема:**
- Datacollector обновлял last_successful_sync на текущее время даже когда не находил заказы
- Это создавало "слепую зону" - заказы с ранним in_process_at пропускались
- Пример: datacollector запустился в 12:04, не нашел заказов, установил last_successful_sync=12:04
- Заказы с in_process_at между 00:00 и 12:04 были пропущены навсегда

**Решение:**
- Добавлено перекрытие в 1 час при использовании last_successful_sync
- Теперь datacollector запрашивает заказы с (last_successful_sync - 1 час)
- Существующая проверка дубликатов (по posting_number + sku) предотвращает создание дублей
- Улучшено логирование - показывает точное время начала сбора

## Если что-то пошло не так:

```bash
# Проверить, что все файлы обновились:
git log -1 --stat

# Запустить datacollector вручную для отладки:
cd /path/to/MarketPlacer
source venv/bin/activate
python -m datacollector.main

# Откатить изменения (если нужно):
git checkout HEAD~1
sudo systemctl restart datacollector
```
