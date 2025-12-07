from app.models import db
from datetime import datetime, time


class Token(db.Model):
    """Модель токена маркетплейса (глобальные токены для всех пользователей)"""
    __tablename__ = 'tokens'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=True)  # Название токена
    description = db.Column(db.String(500), nullable=True)  # Описание токена
    marketplace = db.Column(db.String(50), nullable=False)  # 'wildberries', 'ozon' или 'telegram'
    token = db.Column(db.String(500), nullable=False)
    client_id = db.Column(db.String(200), nullable=True)  # Только для Ozon
    is_active = db.Column(db.Boolean, default=True, nullable=False)  # Активен ли токен
    stocks_sync_time = db.Column(db.Time, default=lambda: time(3, 0))  # Время синхронизации остатков (по умолчанию 3:00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def get_marketplace_display(self):
        """Получить название маркетплейса для отображения"""
        marketplaces = {
            'wildberries': 'Wildberries',
            'ozon': 'Ozon',
            'telegram': 'Telegram'
        }
        return marketplaces.get(self.marketplace, self.marketplace)

    def __repr__(self):
        return f'<Token {self.marketplace} - {self.name}>'

