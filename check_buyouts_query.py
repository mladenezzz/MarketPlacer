from sqlalchemy import create_engine, text
from datetime import date

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'
engine = create_engine(DATABASE_URL)

today = date.today()
print(f"Сегодня: {today}")

with engine.connect() as conn:
    # Проверяем записи в wb_stocks для product_id=6200
    print("\n=== Записи в wb_stocks для product_id=6200 ===")
    result = conn.execute(text('''
        SELECT id, token_id, product_id, quantity, date
        FROM wb_stocks
        WHERE product_id = 6200
    '''))
    for row in result.fetchall():
        print(f"id={row[0]}, token_id={row[1]}, product_id={row[2]}, quantity={row[3]}, date={row[4]}")

    # Проверяем как работает фильтр по дате
    print("\n=== Проверка фильтра по дате ===")
    result = conn.execute(text('''
        SELECT id, token_id, product_id, quantity, date, date::date as date_only
        FROM wb_stocks
        WHERE product_id = 6200 AND date::date = :today
    '''), {"today": today})
    rows = result.fetchall()
    print(f"Найдено записей с датой {today}: {len(rows)}")
    for row in rows:
        print(f"id={row[0]}, token_id={row[1]}, quantity={row[3]}, date={row[4]}, date_only={row[5]}")

    # Проверяем полный JOIN запрос
    print("\n=== Полный JOIN запрос (как в buyouts) ===")
    result = conn.execute(text('''
        SELECT
            g.vendor_code,
            g.tech_size,
            SUM(s.quantity) as total_quantity
        FROM wb_goods g
        JOIN wb_stocks s ON s.product_id = g.id
        WHERE s.token_id = 1
        AND s.date::date = :today
        AND g.id = 6200
        GROUP BY g.vendor_code, g.tech_size
        HAVING SUM(s.quantity) > 0
    '''), {"today": today})
    rows = result.fetchall()
    print(f"Результат: {len(rows)} строк")
    for row in rows:
        print(f"vendor_code={row[0]}, tech_size={row[1]}, total_quantity={row[2]}")
