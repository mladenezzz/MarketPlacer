from sqlalchemy import create_engine, text
from datetime import date

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'
engine = create_engine(DATABASE_URL)

today = date.today()
token_id = 1

with engine.connect() as conn:
    # Выполняем тот же запрос что и в buyouts
    result = conn.execute(text("""
        SELECT
            g.vendor_code,
            g.tech_size,
            SUM(s.quantity) as total_quantity
        FROM wb_goods g
        JOIN wb_stocks s ON s.product_id = g.id
        WHERE s.token_id = :token_id
        AND s.date::date = :today
        GROUP BY g.vendor_code, g.tech_size
        HAVING SUM(s.quantity) > 0
        ORDER BY g.vendor_code, g.tech_size
    """), {"token_id": token_id, "today": today})

    rows = result.fetchall()
    print(f"Всего записей: {len(rows)}")

    # Ищем нашу запись
    found = False
    for row in rows:
        if row[0] == '2090090018-1':
            print(f"\nНАЙДЕНА: vendor_code='{row[0]}', tech_size='{row[1]}', quantity={row[2]}")
            found = True

    if not found:
        print("\nЗапись 2090090018-1 НЕ НАЙДЕНА в результатах запроса!")

    # Проверим первые 10 записей
    print("\nПервые 10 записей:")
    for i, row in enumerate(rows[:10]):
        print(f"  {row[0]} | {row[1]} | {row[2]}")
