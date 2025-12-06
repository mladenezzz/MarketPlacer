"""
Скрипт для получения остатков с WB по токену ИП Веретельникова
и вывода в Excel с артикулами и размерами вместо баркодов
"""
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime
from wb_api import WBApi

# Подключение к БД
DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'


def get_wb_token_by_name(token_name: str) -> tuple:
    """Получить токен WB из БД по имени"""
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, token
                FROM tokens
                WHERE marketplace = 'wildberries'
                AND name LIKE :name
                LIMIT 1
            """),
            {"name": f"%{token_name}%"}
        )
        row = result.fetchone()
        if row:
            return row[0], row[1]
        return None, None


def get_barcode_mapping() -> dict:
    """Получить маппинг barcode -> (vendor_code, tech_size, wb_size, title) из wb_goods"""
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT barcode, vendor_code, tech_size, wb_size, title, brand
                FROM wb_goods
            """)
        )
        mapping = {}
        for row in result.fetchall():
            mapping[row[0]] = {
                'vendor_code': row[1],
                'tech_size': row[2],
                'wb_size': row[3],
                'title': row[4],
                'brand': row[5]
            }
        return mapping


def get_wb_stocks(api_key: str) -> list:
    """Получить остатки с WB через API"""
    api = WBApi(api_key)
    stocks = api.statistics.get_stocks(date_from="2019-01-01")
    return stocks


def main():
    token_name = "Веретельникова"
    print(f"Поиск токена для: {token_name}")

    token_id, api_key = get_wb_token_by_name(token_name)
    if not api_key:
        print(f"Токен для '{token_name}' не найден!")
        return

    print(f"Токен найден (ID: {token_id})")

    # Получаем маппинг баркодов
    print("\nЗагрузка маппинга баркодов из wb_goods...")
    barcode_mapping = get_barcode_mapping()
    print(f"Загружено {len(barcode_mapping)} баркодов")

    # Получаем остатки
    print("\nЗапрос остатков с WB API...")
    stocks = get_wb_stocks(api_key)
    print(f"Получено {len(stocks)} записей остатков")

    if not stocks:
        print("Остатки не найдены")
        return

    # Формируем данные для Excel
    rows = []
    for stock in stocks:
        barcode = stock.barcode

        # Получаем данные из wb_goods или используем данные из API
        if barcode in barcode_mapping:
            goods_data = barcode_mapping[barcode]
            vendor_code = goods_data['vendor_code'] or stock.supplier_article
            tech_size = goods_data['tech_size'] or stock.tech_size
            wb_size = goods_data['wb_size'] or ''
            title = goods_data['title'] or ''
            brand = goods_data['brand'] or stock.brand
        else:
            vendor_code = stock.supplier_article
            tech_size = stock.tech_size
            wb_size = ''
            title = ''
            brand = stock.brand

        # Пропускаем нулевые остатки
        if stock.quantity == 0:
            continue

        rows.append({
            'Артикул': vendor_code,
            'Размер': tech_size,
            'Размер WB': wb_size,
            'Баркод': barcode,
            'Название': title,
            'Бренд': brand,
            'Склад': stock.warehouse_name,
            'Категория': stock.category,
            'Предмет': stock.subject,
            'Остаток': stock.quantity,
            'Цена': stock.price,
            'Скидка %': stock.discount,
            'Дата обновления': stock.last_change_date
        })

    # Создаем DataFrame
    df = pd.DataFrame(rows)

    # Сортируем по артикулу и размеру
    df = df.sort_values(['Артикул', 'Размер'])

    # Сохраняем в Excel
    now = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    filename = f"wb_stocks_{now}.xlsx"

    print(f"\nСохранение в файл: {filename}")
    df.to_excel(filename, index=False, engine='openpyxl')

    print(f"\nГотово! Сохранено {len(df)} строк в файл {filename}")
    print(f"Уникальных артикулов: {df['Артикул'].nunique()}")
    print(f"Общий остаток: {df['Остаток'].sum()}")


if __name__ == "__main__":
    main()
