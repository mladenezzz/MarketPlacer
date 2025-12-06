from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Проверяем форматы размеров в wb_goods для артикула 2005090018
    print("=== WB goods (tech_size) ===")
    result = conn.execute(text("""
        SELECT DISTINCT tech_size, vendor_code
        FROM wb_goods
        WHERE vendor_code = '2005090018'
        ORDER BY tech_size
    """))
    for row in result.fetchall():
        size = row[0]
        print(f"  '{size}' (repr: {repr(size)})")

    # Проверяем форматы в ozon_stocks
    print("\n=== Ozon stocks (offer_id) ===")
    result = conn.execute(text("""
        SELECT DISTINCT offer_id
        FROM ozon_stocks
        WHERE offer_id LIKE '2005090018/%'
        ORDER BY offer_id
    """))
    for row in result.fetchall():
        offer_id = row[0]
        print(f"  '{offer_id}'")
