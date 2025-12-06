"""
Скрипт для получения остатков Ozon по токену ИП Веретельников
и экспорта в Excel файл
"""
import csv
import time
import requests
import pandas as pd
from io import StringIO
from datetime import datetime
from sqlalchemy import create_engine, text

# Подключение к БД
DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'


def get_ozon_token_by_name(token_name: str) -> tuple:
    """Получить токен Ozon из БД по имени"""
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, client_id, token
                FROM tokens
                WHERE marketplace = 'ozon'
                AND name LIKE :name
                LIMIT 1
            """),
            {"name": f"%{token_name}%"}
        )
        row = result.fetchone()
        if row:
            return row[0], row[1], row[2]
        return None, None, None


def get_ozon_stocks(client_id: str, api_key: str) -> list:
    """Получить остатки с Ozon через API (генерация отчета)"""
    base_url = 'https://api-seller.ozon.ru'
    headers = {
        'Client-Id': str(client_id),
        'Api-Key': api_key,
        'Content-Type': 'application/json'
    }

    # Шаг 1: Создаем отчет
    create_url = f"{base_url}/v1/report/products/create"
    payload = {
        "language": "DEFAULT",
        "offer_id": [],
        "search": "",
        "sku": [],
        "visibility": "ALL"
    }

    print("  Создание отчета...")
    response = requests.post(create_url, headers=headers, json=payload, timeout=30)

    if response.status_code != 200:
        print(f"Ошибка API: {response.status_code} - {response.text}")
        return []

    data = response.json()
    report_code = data.get('result', {}).get('code')

    if not report_code:
        print("Не получен код отчета")
        return []

    print(f"  Код отчета: {report_code}")

    # Шаг 2: Ждем готовности отчета
    info_url = f"{base_url}/v1/report/info"
    max_attempts = 30
    attempt = 0
    report_file_url = None

    print("  Ожидание готовности отчета...")
    while attempt < max_attempts:
        attempt += 1
        time.sleep(5)

        info_payload = {"code": report_code}
        response = requests.post(info_url, headers=headers, json=info_payload, timeout=30)

        if response.status_code == 200:
            info_data = response.json()
            result = info_data.get('result', {})
            status = result.get('status')

            if status == "success":
                report_file_url = result.get('file')
                print("  Отчет готов!")
                break
            elif status == "failed":
                error = result.get('error')
                print(f"  Ошибка генерации отчета: {error}")
                return []

        print(f"  Попытка {attempt}/{max_attempts}...")

    if not report_file_url:
        print("Отчет не готов за отведенное время")
        return []

    # Шаг 3: Скачиваем отчет
    print("  Скачивание отчета...")
    response = requests.get(report_file_url, timeout=30)

    if response.status_code != 200:
        print(f"Ошибка скачивания: {response.status_code}")
        return []

    # Шаг 4: Парсим CSV
    csv_content = response.content.decode('utf-8-sig')
    reader = csv.reader(StringIO(csv_content), delimiter=';')
    rows = list(reader)

    if not rows:
        print("CSV файл пуст")
        return []

    headers_row = rows[0]
    data_rows = rows[1:]

    print(f"  Получено {len(data_rows)} товаров")

    # Парсим данные
    stocks = []
    for row in data_rows:
        if len(row) < 18:
            continue

        try:
            # Извлекаем данные из CSV
            # Колонки: 0-Артикул, 2-SKU, 3-Баркод, 5-Название, 17-Остаток FBO
            article = row[0] if len(row) > 0 else ''
            sku = row[2] if len(row) > 2 else ''
            barcode = row[3] if len(row) > 3 else ''
            name = row[5] if len(row) > 5 else ''

            # FBO остаток в колонке 17 (индекс 17)
            fbo_stock = 0
            if len(row) > 17 and row[17]:
                try:
                    fbo_stock = int(float(row[17]))
                except ValueError:
                    pass

            # FBS остаток в колонке 22 (если есть)
            fbs_stock = 0
            if len(row) > 22 and row[22]:
                try:
                    fbs_stock = int(float(row[22]))
                except ValueError:
                    pass

            if not article:
                continue

            stocks.append({
                'offer_id': article,
                'sku': sku,
                'barcode': barcode,
                'name': name,
                'fbo_stock': fbo_stock,
                'fbs_stock': fbs_stock,
                'total_stock': fbo_stock + fbs_stock
            })

        except Exception as e:
            continue

    return stocks


def parse_offer_id(offer_id: str) -> tuple:
    """Парсинг offer_id для извлечения артикула и размера"""
    if not offer_id:
        return '', ''

    # Убираем лишние символы в начале
    offer_id = offer_id.lstrip("'\"")

    if '/' in offer_id:
        parts = offer_id.split('/')
        article = parts[0]
        size = parts[1] if len(parts) > 1 else ''
    else:
        article = offer_id
        size = ''

    return article, size


def main():
    token_name = "Веретельников"
    print(f"Поиск токена Ozon для: {token_name}")

    token_id, client_id, api_key = get_ozon_token_by_name(token_name)
    if not api_key:
        print(f"Токен для '{token_name}' не найден!")
        return

    print(f"Токен найден (ID: {token_id}, Client-ID: {client_id})")

    # Получаем остатки
    print("\nЗапрос остатков с Ozon API...")
    stocks = get_ozon_stocks(client_id, api_key)
    print(f"Получено {len(stocks)} записей остатков")

    if not stocks:
        print("Остатки не найдены")
        return

    # Формируем данные для Excel
    rows = []
    for stock in stocks:
        # Парсим offer_id
        article, size = parse_offer_id(stock['offer_id'])

        # Пропускаем нулевые FBO остатки
        if stock['fbo_stock'] == 0:
            continue

        rows.append({
            'Offer ID': stock['offer_id'],
            'Артикул': article,
            'Размер': size,
            'SKU': stock['sku'],
            'Баркод': stock['barcode'],
            'Название': stock['name'],
            'Остаток FBO': stock['fbo_stock'],
            'Остаток FBS': stock['fbs_stock'],
            'Общий остаток': stock['total_stock']
        })

    # Создаем DataFrame
    df = pd.DataFrame(rows)

    # Сортируем по артикулу и размеру
    df = df.sort_values(['Артикул', 'Размер'])

    # Сохраняем в Excel
    now = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = f"ozon_stocks_{now}.xlsx"

    print(f"\nСохранение в файл: {filename}")
    df.to_excel(filename, index=False, engine='openpyxl')

    print(f"\nГотово! Сохранено {len(df)} строк в файл {filename}")
    print(f"Уникальных артикулов: {df['Артикул'].nunique()}")
    print(f"Общий остаток FBO: {df['Остаток FBO'].sum()}")
    print(f"Общий остаток FBS: {df['Остаток FBS'].sum()}")
    print(f"Общий остаток: {df['Общий остаток'].sum()}")


if __name__ == "__main__":
    main()
