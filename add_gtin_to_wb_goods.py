"""
Скрипт для добавления столбца GTIN в таблицу wb_goods и заполнения его из файла gtins.json
"""
import json
from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'


def main():
    # Путь к файлу с GTIN
    gtins_file = r'C:\Users\Mike01\PycharmProjects\MarketPlaceApp\data\gtins.json'

    # Загружаем GTIN из файла
    with open(gtins_file, 'r', encoding='utf-8') as f:
        gtins_data = json.load(f)

    # Создаем словарь для быстрого поиска: (article, size) -> gtin
    gtin_lookup = {}
    for item in gtins_data:
        article = item['article']
        for size, gtin in item['gtins'].items():
            gtin_lookup[(article, size)] = str(gtin)

    print(f"Загружено {len(gtin_lookup)} GTIN из файла")

    # Подключаемся к базе данных
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Проверяем, существует ли столбец gtin
        result = conn.execute(text("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'wb_goods' AND column_name = 'gtin'
        """))
        column_exists = result.fetchone() is not None

        if not column_exists:
            print("Добавляем столбец gtin в таблицу wb_goods...")
            conn.execute(text("ALTER TABLE wb_goods ADD COLUMN gtin VARCHAR(20)"))
            conn.commit()
            print("Столбец gtin добавлен")
        else:
            print("Столбец gtin уже существует")

        # Получаем все записи из wb_goods
        result = conn.execute(text("SELECT id, vendor_code, tech_size FROM wb_goods"))
        rows = result.fetchall()

        print(f"Найдено {len(rows)} записей в таблице wb_goods")

        # Обновляем GTIN для каждой записи
        updated_count = 0
        not_found_count = 0

        for row_id, vendor_code, tech_size in rows:
            if vendor_code and tech_size:
                key = (vendor_code, tech_size)
                gtin = gtin_lookup.get(key)

                if gtin:
                    conn.execute(
                        text("UPDATE wb_goods SET gtin = :gtin WHERE id = :id"),
                        {"gtin": gtin, "id": row_id}
                    )
                    updated_count += 1
                else:
                    not_found_count += 1

        conn.commit()

    print(f"\nРезультат:")
    print(f"  Обновлено записей: {updated_count}")
    print(f"  Не найден GTIN: {not_found_count}")


if __name__ == '__main__':
    main()
