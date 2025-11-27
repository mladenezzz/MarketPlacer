from app.models import db
from datetime import datetime


class Product(db.Model):
    """Модель товара"""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=False)
    marketplace = db.Column(db.String(50), nullable=False)
    article = db.Column(db.String(200), nullable=False)
    nm_id = db.Column(db.BigInteger, nullable=True)
    barcode = db.Column(db.String(200), nullable=True)
    name = db.Column(db.String(500), nullable=True)
    brand = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(200), nullable=True)
    subject = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    token = db.relationship('Token', backref=db.backref('products', lazy=True))

    __table_args__ = (
        db.Index('idx_products_token', 'token_id'),
        db.Index('idx_products_article', 'article', 'marketplace'),
    )

    def __repr__(self):
        return f'<Product {self.article} - {self.marketplace}>'


class Warehouse(db.Model):
    """Модель склада"""
    __tablename__ = 'warehouses'

    id = db.Column(db.Integer, primary_key=True)
    marketplace = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    warehouse_type = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_warehouses_marketplace', 'marketplace', 'name'),
    )

    def __repr__(self):
        return f'<Warehouse {self.name} - {self.marketplace}>'
