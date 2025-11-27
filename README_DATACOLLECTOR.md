# DataCollector - Руководство по развертыванию

## Архитектура

```
Windows (разработка) → Git → Ubuntu Server (продакшн)
                              ↓
                         PostgreSQL (192.168.0.44)
```

## Разработка на Windows

1. Разрабатывайте код в `datacollector/`
2. Тестируйте локально
3. Коммитьте и пушьте в Git

```bash
git add datacollector/
git commit -m "feat: add new collector feature"
git push
```

## Развертывание на сервере Ubuntu

### Первичная установка

```bash
# Скопируйте скрипт на сервер
scp deploy_datacollector.sh user@192.168.0.44:/home/user/

# Подключитесь к серверу
ssh user@192.168.0.44

# Запустите деплой
chmod +x deploy_datacollector.sh
./deploy_datacollector.sh
```

### Обновление после изменений

```bash
# На сервере
cd /opt/marketplacer
git pull origin main
sudo systemctl restart marketplacer-datacollector
```

## Управление сервисом

```bash
# Статус
sudo systemctl status marketplacer-datacollector

# Запуск
sudo systemctl start marketplacer-datacollector

# Остановка
sudo systemctl stop marketplacer-datacollector

# Перезапуск
sudo systemctl restart marketplacer-datacollector

# Просмотр логов
sudo journalctl -u marketplacer-datacollector -f

# Логи за последний час
sudo journalctl -u marketplacer-datacollector --since "1 hour ago"
```

## Структура DataCollector

```
datacollector/
├── main.py                      # Главный файл, точка входа
├── config.py                    # Конфигурация
└── collectors/
    ├── wildberries.py          # Сборщик данных Wildberries
    └── ozon.py                 # Сборщик данных Ozon (TODO)
```

## Конфигурация

Переменные окружения (опционально):

```bash
# На сервере в /etc/environment или .env
DATABASE_URL=postgresql://user:pass@host:5432/db
LOG_LEVEL=INFO
```

## Как работает сборщик

1. Каждый час запрашивает данные из API маркетплейсов
2. Соблюдает rate limits (1 запрос в минуту для WB)
3. Сохраняет данные в PostgreSQL
4. Логирует все действия

## Мониторинг

```bash
# Проверка что сервис работает
sudo systemctl is-active marketplacer-datacollector

# Проверка ошибок
sudo journalctl -u marketplacer-datacollector -p err

# Просмотр последних 100 строк лога
sudo journalctl -u marketplacer-datacollector -n 100
```
