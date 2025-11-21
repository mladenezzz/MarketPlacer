from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user', nullable=False)
    is_blocked = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Установить хешированный пароль"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Проверить пароль"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Обновить время последнего входа"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def is_admin(self):
        """Проверить, является ли пользователь администратором"""
        return self.role == 'admin'
    
    def is_analyst(self):
        """Проверить, является ли пользователь аналитиком"""
        return self.role == 'analyst'
    
    def is_accountant(self):
        """Проверить, является ли пользователь бухгалтером"""
        return self.role == 'accountant'
    
    def get_role_display(self):
        """Получить название роли на русском"""
        roles = {
            'admin': 'Администратор',
            'analyst': 'Аналитик',
            'accountant': 'Бухгалтер',
            'user': 'Пользователь'
        }
        return roles.get(self.role, 'Пользователь')
    
    def is_active(self):
        """Переопределение метода для Flask-Login - активен ли пользователь"""
        return not self.is_blocked
    
    def __repr__(self):
        return f'<User {self.username}>'


class Token(db.Model):
    """Модель токена маркетплейса"""
    __tablename__ = 'tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    marketplace = db.Column(db.String(50), nullable=False)  # 'wildberries' или 'ozon'
    token = db.Column(db.String(500), nullable=False)
    client_id = db.Column(db.String(200), nullable=True)  # Только для Ozon
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связь с пользователем
    user = db.relationship('User', backref=db.backref('tokens', lazy=True, cascade='all, delete-orphan'))
    
    def get_marketplace_display(self):
        """Получить название маркетплейса для отображения"""
        marketplaces = {
            'wildberries': 'Wildberries',
            'ozon': 'Ozon'
        }
        return marketplaces.get(self.marketplace, self.marketplace)
    
    def __repr__(self):
        return f'<Token {self.marketplace} for User {self.user_id}>'
