"""Add new fields to ozon_sales table for full finance API data"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Adding new fields to ozon_sales table...")

    # Добавляем новые колонки
    columns_to_add = [
        ("operation_id", "BIGINT"),
        ("operation_type", "VARCHAR(100)"),
        ("operation_type_name", "VARCHAR(200)"),
        ("operation_date", "TIMESTAMP"),
        ("delivery_charge", "NUMERIC(12, 2)"),
        ("return_delivery_charge", "NUMERIC(12, 2)"),
        ("accruals_for_sale", "NUMERIC(12, 2)"),
        ("sale_commission", "NUMERIC(12, 2)"),
        ("amount", "NUMERIC(12, 2)"),
        ("type", "VARCHAR(50)"),
        ("posting_delivery_schema", "VARCHAR(50)"),
        ("posting_order_date", "TIMESTAMP"),
        ("posting_posting_number", "VARCHAR(200)"),
        ("posting_warehouse_id", "BIGINT"),
        ("items", "JSONB"),
        ("services", "JSONB"),
    ]

    for col_name, col_type in columns_to_add:
        try:
            db.session.execute(text(f"""
                ALTER TABLE ozon_sales ADD COLUMN IF NOT EXISTS {col_name} {col_type};
            """))
            print(f"  + Added column {col_name}")
        except Exception as e:
            print(f"  - Column {col_name} already exists or error: {e}")

    # Изменяем тип существующих колонок price и payout на NUMERIC(12,2)
    try:
        db.session.execute(text("""
            ALTER TABLE ozon_sales
            ALTER COLUMN price TYPE NUMERIC(12, 2),
            ALTER COLUMN payout TYPE NUMERIC(12, 2);
        """))
        print("  + Updated price and payout column types")
    except Exception as e:
        print(f"  - Error updating column types: {e}")

    # Делаем offer_id nullable
    try:
        db.session.execute(text("""
            ALTER TABLE ozon_sales ALTER COLUMN offer_id DROP NOT NULL;
        """))
        print("  + Made offer_id nullable")
    except Exception as e:
        print(f"  - offer_id already nullable or error: {e}")

    # Делаем quantity nullable
    try:
        db.session.execute(text("""
            ALTER TABLE ozon_sales ALTER COLUMN quantity DROP NOT NULL;
        """))
        print("  + Made quantity nullable")
    except Exception as e:
        print(f"  - quantity already nullable or error: {e}")

    # Удаляем старый unique constraint на posting_number
    try:
        db.session.execute(text("""
            ALTER TABLE ozon_sales DROP CONSTRAINT IF EXISTS ozon_sales_posting_number_key;
        """))
        db.session.execute(text("""
            DROP INDEX IF EXISTS ozon_sales_posting_number_sku_key;
        """))
        print("  + Removed old unique constraints")
    except Exception as e:
        print(f"  - Error removing old constraints: {e}")

    # Создаём unique constraint на operation_id
    try:
        db.session.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ozon_sales_operation_id_key ON ozon_sales (operation_id);
        """))
        print("  + Added unique index on operation_id")
    except Exception as e:
        print(f"  - Error adding unique index: {e}")

    # Создаём индексы
    try:
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ozon_sales_operation_type ON ozon_sales (operation_type);
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ozon_sales_operation_date ON ozon_sales (operation_date);
        """))
        db.session.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_ozon_sales_posting_posting_number ON ozon_sales (posting_posting_number);
        """))
        print("  + Added new indexes")
    except Exception as e:
        print(f"  - Error adding indexes: {e}")

    db.session.commit()
    print("OK: Migration completed successfully")
