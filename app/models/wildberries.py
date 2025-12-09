from app.models import db
from datetime import datetime


class WBSale(db.Model):
    """Модель продаж Wildberries"""
    __tablename__ = 'wb_sales'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)

    date = db.Column(db.DateTime, nullable=False)
    last_change_date = db.Column(db.DateTime, nullable=True)
    sale_id = db.Column(db.String(200), nullable=True)
    g_number = db.Column(db.String(200), nullable=True)
    srid = db.Column(db.String(200), nullable=False, unique=True)

    total_price = db.Column(db.Numeric(10, 2), nullable=True)
    discount_percent = db.Column(db.Integer, nullable=True)
    spp = db.Column(db.Numeric(10, 2), nullable=True)
    for_pay = db.Column(db.Numeric(10, 2), nullable=True)
    finished_price = db.Column(db.Numeric(10, 2), nullable=True)
    price_with_disc = db.Column(db.Numeric(10, 2), nullable=True)

    region_name = db.Column(db.String(200), nullable=True)
    country_name = db.Column(db.String(200), nullable=True)
    oblast_okrug_name = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    token = db.relationship('Token', backref=db.backref('wb_sales', lazy=True))
    product = db.relationship('Product', backref=db.backref('wb_sales', lazy=True))
    warehouse = db.relationship('Warehouse', backref=db.backref('wb_sales', lazy=True))

    __table_args__ = (
        db.Index('idx_wb_sales_token_date', 'token_id', 'date'),
        db.Index('idx_wb_sales_product', 'product_id'),
        db.Index('idx_wb_sales_srid', 'srid'),
    )

    def __repr__(self):
        return f'<WBSale {self.srid}>'


class WBOrder(db.Model):
    """Модель заказов Wildberries"""
    __tablename__ = 'wb_orders'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)

    # Основные идентификаторы
    srid = db.Column(db.String(200), nullable=False, unique=True)
    g_number = db.Column(db.String(200), nullable=True)

    # Даты
    date = db.Column(db.DateTime, nullable=False)
    last_change_date = db.Column(db.DateTime, nullable=True)

    # Информация о товаре (из API)
    supplier_article = db.Column(db.String(200), nullable=True)
    nm_id = db.Column(db.BigInteger, nullable=True)
    barcode = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(200), nullable=True)
    subject = db.Column(db.String(200), nullable=True)
    brand = db.Column(db.String(200), nullable=True)
    tech_size = db.Column(db.String(50), nullable=True)

    # Склад
    warehouse_name = db.Column(db.String(200), nullable=True)
    warehouse_type = db.Column(db.String(100), nullable=True)

    # География
    country_name = db.Column(db.String(200), nullable=True)
    oblast_okrug_name = db.Column(db.String(200), nullable=True)
    region_name = db.Column(db.String(200), nullable=True)

    # Цены
    total_price = db.Column(db.Numeric(10, 2), nullable=True)
    discount_percent = db.Column(db.Integer, nullable=True)
    spp = db.Column(db.Numeric(10, 2), nullable=True)
    finished_price = db.Column(db.Numeric(10, 2), nullable=True)
    price_with_disc = db.Column(db.Numeric(10, 2), nullable=True)

    # Поставка
    income_id = db.Column(db.BigInteger, nullable=True)
    is_supply = db.Column(db.Boolean, nullable=True)
    is_realization = db.Column(db.Boolean, nullable=True)

    # Отмена
    is_cancel = db.Column(db.Boolean, default=False)
    cancel_date = db.Column(db.DateTime, nullable=True)

    # Стикер
    sticker = db.Column(db.String(200), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    token = db.relationship('Token', backref=db.backref('wb_orders', lazy=True))
    product = db.relationship('Product', backref=db.backref('wb_orders', lazy=True))
    warehouse = db.relationship('Warehouse', backref=db.backref('wb_orders', lazy=True))

    __table_args__ = (
        db.Index('idx_wb_orders_token_date', 'token_id', 'date'),
        db.Index('idx_wb_orders_product', 'product_id'),
        db.Index('idx_wb_orders_srid', 'srid'),
    )

    def __repr__(self):
        return f'<WBOrder {self.srid}>'


class WBIncome(db.Model):
    """Модель поставок Wildberries"""
    __tablename__ = 'wb_incomes'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)

    income_id = db.Column(db.BigInteger, nullable=False)
    number = db.Column(db.String(200), nullable=True)
    date = db.Column(db.DateTime, nullable=False)
    last_change_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(100), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    token = db.relationship('Token', backref=db.backref('wb_incomes', lazy=True))
    warehouse = db.relationship('Warehouse', backref=db.backref('wb_incomes', lazy=True))

    __table_args__ = (
        db.Index('idx_wb_incomes_token', 'token_id'),
        db.Index('idx_wb_incomes_income_id', 'income_id'),
    )

    def __repr__(self):
        return f'<WBIncome {self.income_id}>'


class WBIncomeItem(db.Model):
    """Модель позиций в поставках Wildberries"""
    __tablename__ = 'wb_income_items'

    id = db.Column(db.Integer, primary_key=True)
    income_id = db.Column(db.Integer, db.ForeignKey('wb_incomes.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)

    quantity = db.Column(db.Integer, nullable=True)
    total_price = db.Column(db.Numeric(10, 2), nullable=True)
    date_close = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    income = db.relationship('WBIncome', backref=db.backref('items', lazy=True))
    product = db.relationship('Product', backref=db.backref('wb_income_items', lazy=True))

    def __repr__(self):
        return f'<WBIncomeItem {self.id}>'


class WBStock(db.Model):
    """Модель остатков Wildberries"""
    __tablename__ = 'wb_stocks'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('wb_goods.id'), nullable=True)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouses.id'), nullable=True)

    quantity = db.Column(db.Integer, nullable=True)
    quantity_full = db.Column(db.Integer, nullable=True)
    in_way_to_client = db.Column(db.Integer, nullable=True)
    in_way_from_client = db.Column(db.Integer, nullable=True)

    date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    token = db.relationship('Token', backref=db.backref('wb_stocks', lazy=True))
    product = db.relationship('WBGood', backref=db.backref('wb_stocks', lazy=True))
    warehouse = db.relationship('Warehouse', backref=db.backref('wb_stocks', lazy=True))

    __table_args__ = (
        db.Index('idx_wb_stocks_token_date', 'token_id', 'date'),
        db.Index('idx_wb_stocks_product', 'product_id'),
    )

    def __repr__(self):
        return f'<WBStock {self.id}>'


class WBGood(db.Model):
    """Модель карточки товара Wildberries"""
    __tablename__ = 'wb_goods'

    id = db.Column(db.Integer, primary_key=True)

    # Информация о товаре
    vendor_code = db.Column(db.String(200), nullable=True)  # Артикул поставщика
    brand = db.Column(db.String(200), nullable=True)
    title = db.Column(db.String(500), nullable=True)  # Название
    description = db.Column(db.Text, nullable=True)  # Описание

    # Размер
    tech_size = db.Column(db.String(50), nullable=True)  # Технический размер
    wb_size = db.Column(db.String(50), nullable=True)  # Размер на WB
    barcode = db.Column(db.String(200), nullable=False, unique=True)  # Штрихкод
    gtin = db.Column(db.String(20), nullable=True)  # GTIN (Global Trade Item Number)

    # Фото (все ссылки через запятую)
    photos = db.Column(db.Text, nullable=True)

    # Даты из API
    card_created_at = db.Column(db.DateTime, nullable=True)  # Дата создания карточки
    card_updated_at = db.Column(db.DateTime, nullable=True)  # Дата обновления карточки

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_wb_goods_vendor_code', 'vendor_code'),
    )

    def __repr__(self):
        return f'<WBGood {self.vendor_code} - {self.tech_size}>'
