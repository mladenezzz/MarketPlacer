from app.models import db
from datetime import datetime, time


class Token(db.Model):
    """Модель токена маркетплейса"""
    __tablename__ = 'tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=True)  # Название токена
    marketplace = db.Column(db.String(50), nullable=False)  # 'wildberries', 'ozon' или 'telegram'
    token = db.Column(db.String(500), nullable=False)
    client_id = db.Column(db.String(200), nullable=True)  # Только для Ozon
    stocks_sync_time = db.Column(db.Time, default=lambda: time(3, 0))  # Время синхронизации остатков (по умолчанию 3:00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связь с пользователем
    user = db.relationship('User', backref=db.backref('tokens', lazy=True, cascade='all, delete-orphan'))
    
    def get_marketplace_display(self):
        """Получить название маркетплейса для отображения"""
        marketplaces = {
            'wildberries': 'Wildberries',
            'ozon': 'Ozon',
            'telegram': 'Telegram'
        }
        return marketplaces.get(self.marketplace, self.marketplace)
    
    def __repr__(self):
        return f'<Token {self.marketplace} for User {self.user_id}>'

