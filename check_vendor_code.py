from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT id, vendor_code, tech_size, barcode
        FROM wb_goods
        WHERE id = 6200
    """))
    row = result.fetchone()
    print(f"id={row[0]}")
    print(f"vendor_code='{row[1]}' (len={len(row[1]) if row[1] else 0}, bool={bool(row[1])})")
    print(f"tech_size='{row[2]}'")
    print(f"barcode='{row[3]}'")
