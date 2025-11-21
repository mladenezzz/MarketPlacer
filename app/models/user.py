from app.models import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


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

