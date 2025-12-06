"""
Скрипт для обновления таблицы wb_goods:
1. Удаление дублей
2. Удаление столбца token_id
3. Добавление столбца photos
"""
from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # 1. Удаляем дубли, оставляя только одну запись для каждого nm_id + barcode
    print("Удаление дублей...")
    conn.execute(text("""
        DELETE FROM wb_goods a
        USING wb_goods b
        WHERE a.id > b.id
        AND a.nm_id = b.nm_id
        AND a.barcode = b.barcode
    """))
    conn.commit()

    # Проверяем сколько осталось
    result = conn.execute(text("SELECT COUNT(*) FROM wb_goods"))
    print(f"Записей после удаления дублей: {result.fetchone()[0]}")

    # 2. Удаляем столбец token_id (сначала удаляем constraint и индекс)
    print("\nУдаление столбца token_id...")
    try:
        conn.execute(text("ALTER TABLE wb_goods DROP CONSTRAINT IF EXISTS wb_goods_token_id_fkey"))
        conn.commit()
    except:
        pass

    try:
        conn.execute(text("DROP INDEX IF EXISTS idx_wb_goods_token"))
        conn.commit()
    except:
        pass

    try:
        conn.execute(text("ALTER TABLE wb_goods DROP COLUMN IF EXISTS token_id"))
        conn.commit()
        print("Столбец token_id удален")
    except Exception as e:
        print(f"Ошибка при удалении token_id: {e}")

    # 3. Добавляем столбец photos
    print("\nДобавление столбца photos...")
    try:
        conn.execute(text("ALTER TABLE wb_goods ADD COLUMN IF NOT EXISTS photos TEXT"))
        conn.commit()
        print("Столбец photos добавлен")
    except Exception as e:
        print(f"Ошибка при добавлении photos: {e}")

    # 4. Обновляем unique constraint (теперь только по nm_id + barcode)
    print("\nОбновление unique constraint...")
    try:
        conn.execute(text("ALTER TABLE wb_goods DROP CONSTRAINT IF EXISTS uq_wb_goods_nm_barcode"))
        conn.commit()
    except:
        pass

    try:
        conn.execute(text("ALTER TABLE wb_goods ADD CONSTRAINT uq_wb_goods_nm_barcode UNIQUE (nm_id, barcode)"))
        conn.commit()
        print("Unique constraint обновлен")
    except Exception as e:
        print(f"Constraint уже существует или ошибка: {e}")

print("\nГотово!")
