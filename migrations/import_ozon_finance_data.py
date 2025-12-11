"""
Разовый импорт всех финансовых транзакций Ozon в ozon_sales
Добавляет только недостающие записи по operation_id
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import time
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from datacollector.config import DataCollectorConfig
from app.models import Token
from app.models.ozon import OzonSale


def get_ozon_tokens(session):
    """Получить все активные токены Ozon из БД"""
    tokens = session.query(Token).filter_by(marketplace='ozon', is_active=True).all()
    return [(t.id, t.name, t.client_id, t.token) for t in tokens]


def import_finance_transactions(session, token_id: int, client_id: str, api_key: str, months_back: int = 36):
    """
    Импортирует все финансовые транзакции за указанный период
    Пропускает записи, которые уже есть в БД (по operation_id)
    """
    url = 'https://api-seller.ozon.ru/v3/finance/transaction/list'
    headers = {
        'Client-Id': str(client_id),
        'Api-Key': api_key,
        'Content-Type': 'application/json'
    }

    total_saved = 0
    total_skipped = 0
    today = datetime.now(timezone.utc)
    start_date = today - relativedelta(months=months_back)

    current_date = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    print(f"\nИмпорт данных с {current_date.strftime('%Y-%m-%d')} по {today.strftime('%Y-%m-%d')}")
    print("=" * 60)

    while current_date <= today:
        month_start = current_date
        month_end = (current_date + relativedelta(months=1)) - relativedelta(seconds=1)

        if month_end > today:
            month_end = today

        date_from_str = month_start.strftime('%Y-%m-%dT%H:%M:%S.000Z')
        date_to_str = month_end.strftime('%Y-%m-%dT%H:%M:%S.999Z')

        print(f"\n{month_start.strftime('%B %Y')}...")

        page = 1
        has_next = True
        month_saved = 0
        month_skipped = 0

        while has_next:
            params = {
                "filter": {
                    "date": {
                        "from": date_from_str,
                        "to": date_to_str
                    },
                    "posting_number": "",
                    "transaction_type": "all"
                },
                "page": page,
                "page_size": 1000
            }

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

                        for operation in operations:
                            operation_id = operation.get('operation_id')
                            if not operation_id:
                                continue

                            # Проверяем существование по operation_id
                            existing = session.query(OzonSale).filter_by(operation_id=operation_id).first()
                            if existing:
                                month_skipped += 1
                                continue

                            # Парсим даты
                            operation_date_str = operation.get('operation_date')
                            operation_date = datetime.fromisoformat(operation_date_str.replace('Z', '+00:00')) if operation_date_str else None

                            posting_info = operation.get('posting', {})
                            posting_order_date_str = posting_info.get('order_date')
                            posting_order_date = datetime.fromisoformat(posting_order_date_str.replace('Z', '+00:00')) if posting_order_date_str else None

                            items = operation.get('items', [])
                            services = operation.get('services', [])
                            first_item = items[0] if items else {}
                            sku = first_item.get('sku')

                            # Создаём запись
                            sale = OzonSale(
                                token_id=token_id,
                                product_id=None,
                                operation_id=operation_id,
                                operation_type=operation.get('operation_type', ''),
                                operation_type_name=operation.get('operation_type_name'),
                                operation_date=operation_date,
                                delivery_charge=operation.get('delivery_charge', 0),
                                return_delivery_charge=operation.get('return_delivery_charge', 0),
                                accruals_for_sale=operation.get('accruals_for_sale', 0),
                                sale_commission=operation.get('sale_commission', 0),
                                amount=operation.get('amount', 0),
                                type=operation.get('type'),
                                posting_delivery_schema=posting_info.get('delivery_schema'),
                                posting_order_date=posting_order_date,
                                posting_posting_number=posting_info.get('posting_number'),
                                posting_warehouse_id=posting_info.get('warehouse_id'),
                                items=items if items else None,
                                services=services if services else None,
                                posting_number=posting_info.get('posting_number'),
                                sku=sku,
                                shipment_date=operation_date,
                                delivery_schema=posting_info.get('delivery_schema'),
                                price=operation.get('accruals_for_sale', 0),
                                payout=operation.get('amount', 0),
                                status=operation.get('operation_type', '')
                            )

                            session.add(sale)
                            month_saved += 1

                        # Коммитим каждую страницу
                        session.commit()

                        print(f"  Страница {page}: +{month_saved - (total_saved - (total_saved - month_saved + month_skipped))} новых")

                        if len(operations) < 1000:
                            has_next = False
                        else:
                            page += 1
                            time.sleep(0.5)

                    elif response.status_code == 429:
                        retry_count += 1
                        wait_time = 20 * retry_count
                        print(f"  Ошибка 429, ожидание {wait_time} сек...")
                        time.sleep(wait_time)

                    else:
                        print(f"  Ошибка API: {response.status_code}")
                        has_next = False
                        break

                except Exception as e:
                    retry_count += 1
                    print(f"  Ошибка: {e}")
                    time.sleep(10)

            if not request_successful and retry_count >= max_retries:
                print(f"  Превышено количество попыток")
                has_next = False

        print(f"  Итого: +{month_saved} новых, {month_skipped} пропущено")
        total_saved += month_saved
        total_skipped += month_skipped

        current_date = current_date + relativedelta(months=1)
        time.sleep(1)

    return total_saved, total_skipped


def main():
    print("Подключение к БД...")
    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        tokens = get_ozon_tokens(session)
        if not tokens:
            print("Не найдено активных токенов Ozon")
            return

        print(f"Найдено {len(tokens)} токенов:")
        for token_id, name, client_id, _ in tokens:
            print(f"  - {token_id}: {name}")

        for token_id, token_name, client_id, api_key in tokens:
            print(f"\n{'='*60}")
            print(f"Импорт для токена: {token_name} (ID: {token_id})")

            saved, skipped = import_finance_transactions(
                session, token_id, client_id, api_key, months_back=36
            )

            print(f"\n{'='*60}")
            print(f"Токен {token_name}: добавлено {saved}, пропущено {skipped}")

    except Exception as e:
        print(f"Ошибка: {e}")
        session.rollback()
    finally:
        session.close()

    print("\nИмпорт завершён!")


if __name__ == '__main__':
    main()
