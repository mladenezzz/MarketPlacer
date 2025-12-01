"""
Migration script to create Ozon tables in the database

This script creates the following tables:
- ozon_stocks: Ozon warehouse stocks
- ozon_sales: Ozon sales (FBS and FBO orders)
- ozon_supply_orders: Ozon supply orders (заявки на поставку FBO)
- ozon_supply_items: Items in supply orders

Run this script ONCE to add Ozon tables to the database.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from config import Config
from app.models.ozon import OzonStock, OzonSale, OzonSupplyOrder, OzonSupplyItem
from app.models import db

def migrate():
    """Create Ozon tables"""
    print("=" * 70)
    print("Creating Ozon tables...")
    print("=" * 70)

    try:
        # Create engine
        engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

        # Create all Ozon tables
        db.metadata.create_all(
            engine,
            tables=[
                OzonStock.__table__,
                OzonSale.__table__,
                OzonSupplyOrder.__table__,
                OzonSupplyItem.__table__
            ]
        )

        print("\n[OK] Successfully created Ozon tables:")
        print("  - ozon_stocks")
        print("  - ozon_sales")
        print("  - ozon_supply_orders")
        print("  - ozon_supply_items")
        print("\n" + "=" * 70)
        print("Migration completed successfully!")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Migration failed: {e}")
        print("=" * 70)
        raise

if __name__ == '__main__':
    migrate()
