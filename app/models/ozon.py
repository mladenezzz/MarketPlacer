from app.models import db
from datetime import datetime


class OzonStock(db.Model):
    """Модель остатков Ozon"""
    __tablename__ = 'ozon_stocks'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)

    # Ozon specific fields
    offer_id = db.Column(db.String(200), nullable=False)
    product_sku = db.Column(db.BigInteger, nullable=True)
    fbo_present = db.Column(db.Integer, default=0)
    fbo_reserved = db.Column(db.Integer, default=0)
    fbs_present = db.Column(db.Integer, default=0)
    fbs_reserved = db.Column(db.Integer, default=0)

    date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    token = db.relationship('Token', backref=db.backref('ozon_stocks', lazy=True))
    product = db.relationship('Product', backref=db.backref('ozon_stocks', lazy=True))
    warehouse = db.relationship('Warehouse', backref=db.backref('ozon_stocks', lazy=True))

    __table_args__ = (
        db.Index('idx_ozon_stocks_token_date', 'token_id', 'date'),
        db.Index('idx_ozon_stocks_product', 'product_id'),
        db.Index('idx_ozon_stocks_offer_id', 'offer_id'),
    )

    def __repr__(self):
        return f'<OzonStock {self.offer_id}>'


class OzonSale(db.Model):
    """Модель продаж Ozon (FBS и FBO)"""
    __tablename__ = 'ozon_sales'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)

    # Unique identifier (posting can have multiple products, so unique by posting+sku)
    posting_number = db.Column(db.String(200), nullable=False)
    order_id = db.Column(db.BigInteger, nullable=True)
    order_number = db.Column(db.String(200), nullable=True)

    # Product info
    offer_id = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.BigInteger, nullable=True)
    quantity = db.Column(db.Integer, nullable=False)

    # Dates
    shipment_date = db.Column(db.DateTime, nullable=True)
    in_process_at = db.Column(db.DateTime, nullable=True)

    # Delivery type
    delivery_schema = db.Column(db.String(50), nullable=True)  # FBS or FBO

    # Financial
    price = db.Column(db.Numeric(10, 2), nullable=True)
    commission_amount = db.Column(db.Numeric(10, 2), nullable=True)
    commission_percent = db.Column(db.Integer, nullable=True)
    payout = db.Column(db.Numeric(10, 2), nullable=True)

    # Status
    status = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    token = db.relationship('Token', backref=db.backref('ozon_sales', lazy=True))
    product = db.relationship('Product', backref=db.backref('ozon_sales', lazy=True))
    warehouse = db.relationship('Warehouse', backref=db.backref('ozon_sales', lazy=True))

    __table_args__ = (
        db.Index('idx_ozon_sales_token_date', 'token_id', 'shipment_date'),
        db.Index('idx_ozon_sales_product', 'product_id'),
        db.Index('idx_ozon_sales_posting', 'posting_number'),
    )

    def __repr__(self):
        return f'<OzonSale {self.posting_number}>'


class OzonSupplyOrder(db.Model):
    """Модель заявок на поставку Ozon FBO"""
    __tablename__ = 'ozon_supply_orders'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)

    # Supply order info
    supply_order_id = db.Column(db.String(200), nullable=False)
    supply_order_number = db.Column(db.String(200), nullable=True)
    bundle_id = db.Column(db.String(200), nullable=True)

    # Dates
    created_at_api = db.Column(db.DateTime, nullable=True)  # When created in Ozon
    updated_at_api = db.Column(db.DateTime, nullable=True)  # When updated in Ozon
    timeslot_from = db.Column(db.DateTime, nullable=True)  # Timeslot from

    # Status
    status = db.Column(db.String(100), nullable=True)

    # Warehouse info
    warehouse_name_api = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    token = db.relationship('Token', backref=db.backref('ozon_supply_orders', lazy=True))
    warehouse = db.relationship('Warehouse', backref=db.backref('ozon_supply_orders', lazy=True))

    __table_args__ = (
        db.Index('idx_ozon_supply_token', 'token_id'),
        db.Index('idx_ozon_supply_order_id', 'supply_order_id'),
        db.Index('idx_ozon_supply_bundle_id', 'bundle_id'),
    )

    def __repr__(self):
        return f'<OzonSupplyOrder {self.supply_order_number}>'


class OzonSupplyItem(db.Model):
    """Модель позиций в заявках на поставку Ozon FBO"""
    __tablename__ = 'ozon_supply_items'

    id = db.Column(db.Integer, primary_key=True)
    supply_order_id = db.Column(db.Integer, db.ForeignKey('ozon_supply_orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)

    # Product info
    sku = db.Column(db.BigInteger, nullable=False)
    offer_id = db.Column(db.String(200), nullable=False)
    article = db.Column(db.String(200), nullable=False)  # Parsed from offer_id
    size = db.Column(db.String(50), nullable=True)  # Parsed from offer_id

    # Item details
    quantity = db.Column(db.Integer, nullable=False)
    barcode = db.Column(db.String(200), nullable=True)
    name = db.Column(db.String(500), nullable=True)
    bundle_id = db.Column(db.String(200), nullable=True)
    timeslot_from = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    supply_order = db.relationship('OzonSupplyOrder', backref=db.backref('items', lazy=True))
    product = db.relationship('Product', backref=db.backref('ozon_supply_items', lazy=True))

    __table_args__ = (
        db.Index('idx_ozon_supply_items_supply', 'supply_order_id'),
        db.Index('idx_ozon_supply_items_product', 'product_id'),
        db.Index('idx_ozon_supply_items_sku', 'sku'),
    )

    def __repr__(self):
        return f'<OzonSupplyItem {self.article}/{self.size}>'
