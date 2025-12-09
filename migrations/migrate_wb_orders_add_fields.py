"""
Миграция: добавление новых полей в таблицу wb_orders
"""
import sys
sys.path.insert(0, 'z:/')

from sqlalchemy import create_engine, text
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

migration_sql = """
-- Добавляем новые поля в таблицу wb_orders

-- Информация о товаре
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS supplier_article VARCHAR(200);
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS nm_id BIGINT;
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS barcode VARCHAR(200);
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS category VARCHAR(200);
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS subject VARCHAR(200);
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS brand VARCHAR(200);
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS tech_size VARCHAR(50);

-- Склад
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS warehouse_name VARCHAR(200);
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS warehouse_type VARCHAR(100);

-- География
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS country_name VARCHAR(200);
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS oblast_okrug_name VARCHAR(200);

-- Цены
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS price_with_disc NUMERIC(10, 2);

-- Поставка
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS income_id BIGINT;
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS is_supply BOOLEAN;
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS is_realization BOOLEAN;

-- Стикер
ALTER TABLE wb_orders ADD COLUMN IF NOT EXISTS sticker VARCHAR(200);
"""

def run_migration():
    with engine.connect() as conn:
        for statement in migration_sql.strip().split(';'):
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    conn.execute(text(statement))
                    print(f"OK: {statement[:60]}...")
                except Exception as e:
                    print(f"SKIP: {statement[:60]}... ({e})")
        conn.commit()
    print("\nМиграция завершена!")

if __name__ == '__main__':
    run_migration()
