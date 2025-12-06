"""
Скрипт для удаления колонок nm_id и imt_id из таблицы wb_goods
"""
from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Удаляем колонку nm_id
    print("Удаление колонки nm_id...")
    try:
        conn.execute(text("ALTER TABLE wb_goods DROP COLUMN IF EXISTS nm_id"))
        conn.commit()
        print("Колонка nm_id удалена")
    except Exception as e:
        print(f"Ошибка при удалении nm_id: {e}")

    # Удаляем колонку imt_id
    print("\nУдаление колонки imt_id...")
    try:
        conn.execute(text("ALTER TABLE wb_goods DROP COLUMN IF EXISTS imt_id"))
        conn.commit()
        print("Колонка imt_id удалена")
    except Exception as e:
        print(f"Ошибка при удалении imt_id: {e}")

    # Проверяем структуру таблицы
    print("\nТекущая структура таблицы wb_goods:")
    result = conn.execute(text("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'wb_goods'
        ORDER BY ordinal_position
    """))
    for row in result.fetchall():
        print(f"  {row[0]}: {row[1]}")

print("\nГотово!")
