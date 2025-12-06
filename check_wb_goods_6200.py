from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text('SELECT id, vendor_code, tech_size, title FROM wb_goods WHERE id = 6200'))
    row = result.fetchone()
    if row:
        print(f'ID: {row[0]}')
        print(f'vendor_code: {row[1]}')
        print(f'tech_size: {row[2]}')
        print(f'title: {row[3]}')
    else:
        print('Запись с id=6200 НЕ НАЙДЕНА в wb_goods')
