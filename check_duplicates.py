from sqlalchemy import create_engine, text
from datetime import date

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'
engine = create_engine(DATABASE_URL)
today = date.today()

with engine.connect() as conn:
    # Проверяем запрос который используется в buyouts
    print("=== Результат запроса WB stocks (как в buyouts) ===")
    result = conn.execute(text("""
        SELECT
            g.vendor_code,
            g.tech_size,
            SUM(s.quantity) as total_quantity,
            COUNT(*) as row_count
        FROM wb_goods g
        JOIN wb_stocks s ON s.product_id = g.id
        WHERE s.token_id = 1
        AND s.date::date = :today
        AND g.vendor_code = '2005090018'
        GROUP BY g.vendor_code, g.tech_size
        HAVING SUM(s.quantity) > 0
        ORDER BY g.tech_size
    """), {"today": today})

    for row in result.fetchall():
        print(f"  vendor_code='{row[0]}', tech_size='{row[1]}', qty={row[2]}, rows={row[3]}")

    # Проверяем есть ли дубли в wb_goods
    print("\n=== Дубликаты в wb_goods ===")
    result = conn.execute(text("""
        SELECT vendor_code, tech_size, COUNT(*) as cnt
        FROM wb_goods
        WHERE vendor_code = '2005090018'
        GROUP BY vendor_code, tech_size
        HAVING COUNT(*) > 1
    """))
    rows = result.fetchall()
    if rows:
        for row in rows:
            print(f"  ДУБЛЬ: {row[0]} / {row[1]} - {row[2]} записей")
    else:
        print("  Дубликатов нет")
