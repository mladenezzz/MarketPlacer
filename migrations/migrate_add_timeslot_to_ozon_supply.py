"""Add timeslot_from field to ozon_supply_orders and ozon_supply_items tables"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("Adding timeslot_from field to ozon_supply_orders...")

    # Add timeslot_from to ozon_supply_orders
    try:
        db.session.execute(text("""
            ALTER TABLE ozon_supply_orders
            ADD COLUMN timeslot_from TIMESTAMP
        """))
        db.session.commit()
        print("✓ Added timeslot_from to ozon_supply_orders")
    except Exception as e:
        db.session.rollback()
        print(f"Column timeslot_from may already exist in ozon_supply_orders: {e}")

    # Add timeslot_from to ozon_supply_items
    try:
        db.session.execute(text("""
            ALTER TABLE ozon_supply_items
            ADD COLUMN timeslot_from TIMESTAMP
        """))
        db.session.commit()
        print("✓ Added timeslot_from to ozon_supply_items")
    except Exception as e:
        db.session.rollback()
        print(f"Column timeslot_from may already exist in ozon_supply_items: {e}")

    # Add bundle_id to ozon_supply_items
    try:
        db.session.execute(text("""
            ALTER TABLE ozon_supply_items
            ADD COLUMN bundle_id VARCHAR(200)
        """))
        db.session.commit()
        print("✓ Added bundle_id to ozon_supply_items")
    except Exception as e:
        db.session.rollback()
        print(f"Column bundle_id may already exist in ozon_supply_items: {e}")

    # Add index on bundle_id
    try:
        db.session.execute(text("""
            CREATE INDEX idx_ozon_supply_items_bundle_id ON ozon_supply_items(bundle_id)
        """))
        db.session.commit()
        print("✓ Created index on ozon_supply_items.bundle_id")
    except Exception as e:
        db.session.rollback()
        print(f"Index may already exist: {e}")

    print("\nMigration completed!")
