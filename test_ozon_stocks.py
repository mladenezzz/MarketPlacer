"""
Тестовый скрипт для получения остатков Ozon и анализа структуры CSV-отчёта
"""
import csv
import requests
import time
from io import StringIO
from datacollector.config import DataCollectorConfig
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Token


def get_ozon_token():
    """Получить активный Ozon токен из БД"""
    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    token = session.query(Token).filter_by(
        marketplace='ozon',
        is_active=True
    ).first()

    session.close()

    if not token:
        raise Exception("Активный Ozon токен не найден в БД")

    return token.client_id, token.token


def fetch_stocks_report():
    """Получить отчёт по остаткам через Ozon API"""
    client_id, api_key = get_ozon_token()

    base_url = 'https://api-seller.ozon.ru'
    headers = {
        'Client-Id': str(client_id),
        'Api-Key': api_key,
        'Content-Type': 'application/json'
    }

    # Шаг 1: Создание отчёта
    print("1. Создание отчёта...")
    create_url = f"{base_url}/v1/report/products/create"
    payload = {
        "language": "DEFAULT",
        "offer_id": [],
        "search": "",
        "sku": [],
        "visibility": "ALL"
    }

    response = requests.post(create_url, headers=headers, json=payload, timeout=30)

    if response.status_code != 200:
        print(f"Ошибка API: {response.status_code}")
        print(response.text)
        return None

    data = response.json()
    report_code = data.get('result', {}).get('code')
    print(f"   Report code: {report_code}")

    # Шаг 2: Ожидание готовности отчёта
    print("2. Ожидание готовности отчёта...")
    info_url = f"{base_url}/v1/report/info"
    max_attempts = 30
    report_file_url = None

    for attempt in range(1, max_attempts + 1):
        time.sleep(5)

        info_payload = {"code": report_code}
        response = requests.post(info_url, headers=headers, json=info_payload, timeout=30)

        if response.status_code == 200:
            info_data = response.json()
            result = info_data.get('result', {})
            status = result.get('status')

            print(f"   Попытка {attempt}: статус = {status}")

            if status == "success":
                report_file_url = result.get('file')
                print(f"   Отчёт готов!")
                break
            elif status == "failed":
                error = result.get('error')
                print(f"   Ошибка генерации отчёта: {error}")
                return None

    if not report_file_url:
        print("   Отчёт не готов после всех попыток")
        return None

    # Шаг 3: Скачивание отчёта
    print("3. Скачивание отчёта...")
    response = requests.get(report_file_url, timeout=30)

    if response.status_code != 200:
        print(f"   Ошибка скачивания: {response.status_code}")
        return None

    return response.content.decode('utf-8-sig')


def analyze_csv(csv_content):
    """Анализ структуры CSV и поиск колонок с остатками"""
    reader = csv.reader(StringIO(csv_content), delimiter=';')
    rows = list(reader)

    if not rows:
        print("CSV файл пустой!")
        return

    headers = rows[0]
    data_rows = rows[1:]

    print("\n" + "="*80)
    print("АНАЛИЗ СТРУКТУРЫ CSV-ОТЧЁТА")
    print("="*80)

    print(f"\nВсего колонок: {len(headers)}")
    print(f"Всего строк данных: {len(data_rows)}")

    print("\n--- СПИСОК ВСЕХ КОЛОНОК ---")
    for i, header in enumerate(headers):
        print(f"  [{i:2d}] {header}")

    # Поиск колонок с остатками
    print("\n--- КОЛОНКИ СВЯЗАННЫЕ С ОСТАТКАМИ (FBO/FBS/stock/остаток) ---")
    stock_columns = []
    for i, header in enumerate(headers):
        header_lower = header.lower()
        if any(keyword in header_lower for keyword in ['fbo', 'fbs', 'stock', 'остаток', 'склад', 'warehouse']):
            stock_columns.append((i, header))
            print(f"  [{i:2d}] {header}")

    # Показать первые 5 строк данных для колонок с остатками
    if stock_columns and data_rows:
        print("\n--- ПРИМЕРЫ ДАННЫХ (первые 10 товаров) ---")
        print(f"{'Артикул':<20} | " + " | ".join([f"[{idx}] {name[:25]}" for idx, name in stock_columns]))
        print("-" * 120)

        for row in data_rows[:10]:
            article = row[0] if len(row) > 0 else ''
            values = []
            for idx, _ in stock_columns:
                val = row[idx] if len(row) > idx else ''
                values.append(val[:25] if val else '(пусто)')
            print(f"{article:<20} | " + " | ".join([f"{v:<30}" for v in values]))

    # Анализ колонки 17 (текущая в коде)
    print("\n--- АНАЛИЗ КОЛОНКИ [17] (используется в коде) ---")
    if len(headers) > 17:
        print(f"  Название: {headers[17]}")
        non_empty = 0
        non_zero = 0
        for row in data_rows:
            if len(row) > 17 and row[17]:
                non_empty += 1
                try:
                    if float(row[17]) > 0:
                        non_zero += 1
                except:
                    pass
        print(f"  Непустых значений: {non_empty} из {len(data_rows)}")
        print(f"  Ненулевых значений: {non_zero} из {len(data_rows)}")
    else:
        print("  Колонка [17] отсутствует в отчёте!")

    # Найти колонки с ненулевыми числовыми значениями
    print("\n--- КОЛОНКИ С НЕНУЛЕВЫМИ ЧИСЛОВЫМИ ЗНАЧЕНИЯМИ ---")
    for i, header in enumerate(headers):
        non_zero_count = 0
        total_sum = 0
        for row in data_rows:
            if len(row) > i and row[i]:
                try:
                    val = float(row[i])
                    if val > 0:
                        non_zero_count += 1
                        total_sum += val
                except:
                    pass
        if non_zero_count > 0:
            header_lower = header.lower()
            if any(keyword in header_lower for keyword in ['fbo', 'fbs', 'остаток', 'склад', 'шт']):
                print(f"  [{i:2d}] {header}: {non_zero_count} ненулевых, сумма={total_sum:.0f}")


def main():
    print("="*80)
    print("ТЕСТ ПОЛУЧЕНИЯ ОСТАТКОВ OZON")
    print("="*80)

    csv_content = fetch_stocks_report()

    if csv_content:
        # Сохраняем CSV для ручного анализа
        with open('ozon_stocks_report.csv', 'w', encoding='utf-8-sig') as f:
            f.write(csv_content)
        print("\n   CSV сохранён в ozon_stocks_report.csv")

        analyze_csv(csv_content)
    else:
        print("\nНе удалось получить отчёт")


if __name__ == '__main__':
    main()
