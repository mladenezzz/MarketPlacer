"""
Тестовый скрипт для получения всех финансовых транзакций Ozon
без фильтров и сохранения в Excel
"""
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import time
import pandas as pd
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from datacollector.config import DataCollectorConfig
from app.models import Token


def get_ozon_tokens():
    """Получить все активные токены Ozon из БД"""
    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        tokens = session.query(Token).filter_by(marketplace='ozon', is_active=True).all()
        result = [(t.id, t.name, t.client_id, t.token) for t in tokens]
        return result
    finally:
        session.close()


def flatten_dict(d, parent_key='', sep='_'):
    """Рекурсивно разворачивает вложенные словари в плоскую структуру"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # Для списков сохраняем как JSON-строку или разворачиваем первый элемент
            if v and isinstance(v[0], dict):
                # Разворачиваем первый элемент списка с префиксом
                for i, item in enumerate(v):
                    items.extend(flatten_dict(item, f"{new_key}_{i}", sep=sep).items())
            else:
                items.append((new_key, str(v)))
        else:
            items.append((new_key, v))
    return dict(items)


def collect_all_finance_transactions(client_id: str, api_key: str, months_back: int = 36):
    """
    Собирает все финансовые транзакции без фильтров за указанный период

    Args:
        client_id: Client-Id для Ozon API
        api_key: API ключ Ozon
        months_back: Сколько месяцев назад начать сбор (по умолчанию 36 = 3 года)

    Returns:
        list: Список всех операций
    """
    url = 'https://api-seller.ozon.ru/v3/finance/transaction/list'
    headers = {
        'Client-Id': str(client_id),
        'Api-Key': api_key,
        'Content-Type': 'application/json'
    }

    all_operations = []
    today = datetime.now(timezone.utc)
    start_date = today - relativedelta(months=months_back)

    # Начинаем с первого дня месяца
    current_date = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    print(f"Сбор данных с {current_date.strftime('%Y-%m-%d')} по {today.strftime('%Y-%m-%d')}")
    print("=" * 60)

    while current_date <= today:
        # Определяем начало и конец текущего месяца
        month_start = current_date
        month_end = (current_date + relativedelta(months=1)) - relativedelta(seconds=1)

        if month_end > today:
            month_end = today

        date_from_str = month_start.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        date_to_str = month_end.strftime('%Y-%m-%dT%H:%M:%S.999Z')

        print(f"\nСбор за {month_start.strftime('%B %Y')}...")

        # Пагинация - получаем все страницы за месяц
        page = 1
        has_next = True
        month_count = 0

        while has_next:
            params = {
                "filter": {
                    "date": {
                        "from": date_from_str,
                        "to": date_to_str
                    },
                    # БЕЗ фильтра operation_type - получаем ВСЕ типы операций
                    "posting_number": "",
                    "transaction_type": "all"
                },
                "page": page,
                "page_size": 1000
            }

            # Повторные попытки при ошибке 429
            max_retries = 5
            retry_count = 0
            request_successful = False

            while retry_count < max_retries and not request_successful:
                try:
                    response = requests.post(url, headers=headers, json=params, timeout=60)

                    if response.status_code == 200:
                        request_successful = True
                        data = response.json()

                        result = data.get('result', {})
                        operations = result.get('operations', [])

                        if not operations:
                            has_next = False
                            break

                        all_operations.extend(operations)
                        month_count += len(operations)

                        print(f"  Страница {page}: получено {len(operations)} операций")

                        # Если получили меньше 1000 - это последняя страница
                        if len(operations) < 1000:
                            has_next = False
                        else:
                            page += 1
                            time.sleep(0.5)  # Небольшая задержка между страницами

                    elif response.status_code == 429:
                        retry_count += 1
                        wait_time = 20 * retry_count
                        print(f"  Ошибка 429, ожидание {wait_time} сек... (попытка {retry_count}/{max_retries})")
                        time.sleep(wait_time)

                    else:
                        print(f"  Ошибка API: {response.status_code} - {response.text[:200]}")
                        has_next = False
                        break

                except Exception as e:
                    retry_count += 1
                    print(f"  Ошибка запроса: {e} (попытка {retry_count}/{max_retries})")
                    time.sleep(10)

            if not request_successful and retry_count >= max_retries:
                print(f"  Превышено количество попыток для страницы {page}")
                has_next = False

        print(f"  Итого за {month_start.strftime('%B %Y')}: {month_count} операций")

        # Переходим к следующему месяцу
        current_date = current_date + relativedelta(months=1)
        time.sleep(1)  # Задержка между месяцами

    return all_operations


def save_to_excel(operations: list, filename: str):
    """Сохраняет операции в Excel файл"""
    if not operations:
        print("Нет данных для сохранения")
        return

    # Разворачиваем все вложенные структуры
    flat_operations = [flatten_dict(op) for op in operations]

    # Создаём DataFrame
    df = pd.DataFrame(flat_operations)

    # Сортируем по дате операции
    if 'operation_date' in df.columns:
        df['operation_date'] = pd.to_datetime(df['operation_date'])
        df = df.sort_values('operation_date', ascending=False)

    # Сохраняем в Excel
    df.to_excel(filename, index=False, engine='openpyxl')
    print(f"\nСохранено {len(df)} записей в {filename}")
    print(f"Столбцы: {list(df.columns)}")


def main():
    print("Получение токенов Ozon из БД...")
    tokens = get_ozon_tokens()

    if not tokens:
        print("Не найдено активных токенов Ozon")
        return

    print(f"Найдено {len(tokens)} токенов:")
    for token_id, name, client_id, _ in tokens:
        print(f"  - {token_id}: {name} (client_id: {client_id})")

    # Используем первый токен (или можно добавить выбор)
    token_id, token_name, client_id, api_key = tokens[0]
    print(f"\nИспользуем токен: {token_name}")

    # Собираем все транзакции за 3 года
    operations = collect_all_finance_transactions(client_id, api_key, months_back=36)

    print(f"\n{'=' * 60}")
    print(f"Всего получено операций: {len(operations)}")

    # Подсчитываем типы операций
    if operations:
        operation_types = {}
        for op in operations:
            op_type = op.get('operation_type', 'unknown')
            operation_types[op_type] = operation_types.get(op_type, 0) + 1

        print("\nТипы операций:")
        for op_type, count in sorted(operation_types.items(), key=lambda x: -x[1]):
            print(f"  {op_type}: {count}")

    # Сохраняем в Excel
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"ozon_finance_transactions_{timestamp}.xlsx"
    save_to_excel(operations, filename)


if __name__ == '__main__':
    main()
