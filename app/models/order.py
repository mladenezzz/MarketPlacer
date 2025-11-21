from app.models import db
from datetime import datetime
import json


class Order(db.Model):
    """Модель для хранения заказов маркетплейсов"""
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=False, index=True)
    marketplace = db.Column(db.String(50), nullable=False)  # 'wildberries', 'ozon'
    order_type = db.Column(db.String(20), nullable=True)  # 'FBS', 'FBO' для Ozon, None для Wildberries
    
    # Идентификаторы заказа
    order_id = db.Column(db.String(200), nullable=False, index=True)  # Уникальный ID заказа на маркетплейсе
    posting_number = db.Column(db.String(200), nullable=True)  # Для Ozon
    
    # Информация о товаре
    supplier_article = db.Column(db.String(200), nullable=True, index=True)  # Артикул продавца (SKU)
    
    # Даты
    order_date = db.Column(db.DateTime, nullable=False, index=True)  # Дата заказа
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Когда запись создана в БД
    
    # Финансовые данные
    price = db.Column(db.Float, nullable=False, default=0.0)  # Цена заказа
    price_with_discount = db.Column(db.Float, nullable=True)  # Цена со скидкой (для WB)
    finished_price = db.Column(db.Float, nullable=True)  # Итоговая цена (для WB)
    
    # Дополнительные данные в JSON формате
    raw_data = db.Column(db.Text, nullable=True)  # Полные данные из API в JSON
    
    # Связь с токеном
    token = db.relationship('Token', backref=db.backref('orders', lazy=True, cascade='all, delete-orphan'))
    
    # Уникальный индекс для предотвращения дубликатов
    __table_args__ = (db.UniqueConstraint('token_id', 'order_id', 'marketplace', name='uq_order_token_marketplace'),)
    
    def set_raw_data(self, data):
        """Сохранить сырые данные в JSON формате"""
        if data:
            self.raw_data = json.dumps(data, ensure_ascii=False, default=str)
    
    def get_raw_data(self):
        """Получить сырые данные из JSON формата"""
        if self.raw_data:
            try:
                return json.loads(self.raw_data)
            except:
                return None
        return None
    
    def __repr__(self):
        return f'<Order {self.order_id} for token {self.token_id}>'

