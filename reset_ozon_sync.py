"""
Reset Ozon sync state to trigger initial collection of sales and orders
"""
from app import create_app, db
from app.models import SyncState

app = create_app()
app.app_context().push()

print("=" * 80)
print("RESET OZON SYNC STATE")
print("=" * 80)
print()

try:
    # Delete sync state for ozon_sales
    deleted_sales = SyncState.query.filter_by(endpoint='ozon_sales').delete()
    print(f"Deleted {deleted_sales} ozon_sales sync state records")

    # Delete sync state for ozon_orders (if exists)
    deleted_orders = SyncState.query.filter_by(endpoint='ozon_orders').delete()
    print(f"Deleted {deleted_orders} ozon_orders sync state records")

    db.session.commit()
    print()
    print("Sync state reset complete!")
    print("Datacollector will now perform initial sync for Ozon sales and orders")

except Exception as e:
    db.session.rollback()
    print(f"Error resetting sync state: {e}")
