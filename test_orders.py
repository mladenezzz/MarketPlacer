from app import create_app, db
from app.models.ozon import OzonOrder
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    two_weeks_ago = today - timedelta(days=14)

    # Предыдущая неделя (от 14 до 7 дней назад)
    total = OzonOrder.query.filter(
        db.func.date(OzonOrder.in_process_at) >= two_weeks_ago,
        db.func.date(OzonOrder.in_process_at) < week_ago
    ).count()

    delivered = OzonOrder.query.filter(
        db.func.date(OzonOrder.in_process_at) >= two_weeks_ago,
        db.func.date(OzonOrder.in_process_at) < week_ago,
        OzonOrder.status == 'delivered'
    ).count()

    cancelled = OzonOrder.query.filter(
        db.func.date(OzonOrder.in_process_at) >= two_weeks_ago,
        db.func.date(OzonOrder.in_process_at) < week_ago,
        OzonOrder.status == 'cancelled'
    ).count()

    print(f"Previous week ({two_weeks_ago} - {week_ago}):")
    print(f"  Total: {total}")
    print(f"  Delivered: {delivered}")
    print(f"  Cancelled: {cancelled}")
