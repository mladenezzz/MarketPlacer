"""
Скрипт для очистки таблицы wb_stocks
"""
from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Проверяем количество записей до удаления
    result = conn.execute(text("SELECT COUNT(*) FROM wb_stocks"))
    count_before = result.fetchone()[0]
    print(f"Записей до удаления: {count_before}")

    # Удаляем все записи
    conn.execute(text("DELETE FROM wb_stocks"))
    conn.commit()

    # Проверяем количество записей после удаления
    result = conn.execute(text("SELECT COUNT(*) FROM wb_stocks"))
    count_after = result.fetchone()[0]
    print(f"Записей после удаления: {count_after}")

print("\nГотово!")
