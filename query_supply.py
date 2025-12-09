from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote_plus

password = quote_plus('MarketPlacer2024!Secure')
engine = create_engine(f'postgresql://marketplacer_user:{password}@192.168.0.44:5432/marketplacer')
Session = sessionmaker(bind=engine)
session = Session()

result = session.execute(text('''
    SELECT so.created_at_api, so.timeslot_from, si.timeslot_from as item_timeslot, so.supply_order_number, si.size, si.quantity
    FROM ozon_supply_items si
    JOIN ozon_supply_orders so ON si.supply_order_id = so.id
    WHERE si.article = '3007090014'
    ORDER BY so.created_at_api, si.size
'''))

for row in result:
    created = row[0].strftime('%Y-%m-%d') if row[0] else 'N/A'
    order_timeslot = row[1].strftime('%Y-%m-%d') if row[1] else 'N/A'
    item_timeslot = row[2].strftime('%Y-%m-%d') if row[2] else 'N/A'
    order_num = row[3] or 'N/A'
    size = row[4]
    qty = row[5]
    print(f'Created: {created} | OrderSlot: {order_timeslot} | ItemSlot: {item_timeslot} | Order: {order_num} | {size} | {qty}')

session.close()
