"""
Миграция: добавление поля imt_id в таблицу wb_goods
"""
import sys
sys.path.insert(0, 'z:/')

from sqlalchemy import create_engine, text
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

migration_sql = """
-- Добавляем поле imt_id в таблицу wb_goods
ALTER TABLE wb_goods ADD COLUMN IF NOT EXISTS imt_id BIGINT;

-- Добавляем индекс для быстрого поиска по imt_id
CREATE INDEX IF NOT EXISTS idx_wb_goods_imt_id ON wb_goods(imt_id);
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
