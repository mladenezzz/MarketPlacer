"""
Скрипт для изменения unique constraint в таблице wb_goods:
Уникальным должен быть только barcode
"""
from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # 1. Удаляем дубли по barcode (оставляем первую запись)
    print("Удаление дублей по barcode...")
    conn.execute(text("""
        DELETE FROM wb_goods a
        USING wb_goods b
        WHERE a.id > b.id
        AND a.barcode = b.barcode
        AND a.barcode IS NOT NULL
        AND a.barcode != ''
    """))
    conn.commit()

    # Проверяем сколько осталось
    result = conn.execute(text("SELECT COUNT(*) FROM wb_goods"))
    print(f"Записей после удаления дублей: {result.fetchone()[0]}")

    # 2. Удаляем старый constraint
    print("\nУдаление старого constraint...")
    try:
        conn.execute(text("ALTER TABLE wb_goods DROP CONSTRAINT IF EXISTS uq_wb_goods_nm_barcode"))
        conn.commit()
    except:
        pass

    # 3. Создаем новый constraint только по barcode
    print("Создание нового constraint (barcode)...")
    try:
        conn.execute(text("""
            ALTER TABLE wb_goods
            ADD CONSTRAINT uq_wb_goods_barcode UNIQUE (barcode)
        """))
        conn.commit()
        print("Constraint создан")
    except Exception as e:
        print(f"Ошибка: {e}")

print("\nГотово!")
