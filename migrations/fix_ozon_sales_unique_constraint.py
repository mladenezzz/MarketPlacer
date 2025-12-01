"""Fix Ozon sales unique constraint to allow multiple products per posting"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Fixing Ozon sales unique constraint...")

    # Drop old unique constraint on posting_number
    db.session.execute(text("""
        ALTER TABLE ozon_sales DROP CONSTRAINT IF EXISTS ozon_sales_posting_number_key;
    """))

    # Create new unique constraint on (posting_number, sku)
    db.session.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS ozon_sales_posting_number_sku_key
        ON ozon_sales (posting_number, sku);
    """))

    db.session.commit()
    print("OK: Fixed Ozon sales unique constraint to (posting_number, sku)")
