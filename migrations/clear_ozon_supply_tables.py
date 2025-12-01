"""Clear ozon_supply_orders and ozon_supply_items tables"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Clearing ozon_supply_items table...")
    try:
        db.session.execute(text("TRUNCATE TABLE ozon_supply_items CASCADE"))
        db.session.commit()
        print("✓ Cleared ozon_supply_items")
    except Exception as e:
        db.session.rollback()
        print(f"Error clearing ozon_supply_items: {e}")

    print("Clearing ozon_supply_orders table...")
    try:
        db.session.execute(text("TRUNCATE TABLE ozon_supply_orders CASCADE"))
        db.session.commit()
        print("✓ Cleared ozon_supply_orders")
    except Exception as e:
        db.session.rollback()
        print(f"Error clearing ozon_supply_orders: {e}")

    print("\nTables cleared successfully!")
