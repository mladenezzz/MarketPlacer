from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Проверяем ozon_orders для артикула 2005090018
    print("=== Ozon orders для 2005090018 ===")
    result = conn.execute(text("""
        SELECT DISTINCT offer_id
        FROM ozon_orders
        WHERE offer_id LIKE '2005090018%'
        ORDER BY offer_id
    """))
    rows = result.fetchall()
    if rows:
        for row in rows:
            print(f"  '{row[0]}'")
    else:
        print("  Нет заказов")

    # Проверяем parse_offer_id логику
    print("\n=== Примеры offer_id из ozon ===")
    result = conn.execute(text("""
        SELECT DISTINCT offer_id
        FROM ozon_orders
        WHERE offer_id LIKE '%/%'
        LIMIT 10
    """))
    for row in result.fetchall():
        offer_id = row[0]
        # Эмулируем parse_offer_id
        if '/' in offer_id:
            parts = offer_id.split('/')
            article = parts[0]
            size = parts[1] if len(parts) > 1 else ''
        else:
            article = offer_id
            size = ''
        print(f"  '{offer_id}' -> article='{article}', size='{size}'")
