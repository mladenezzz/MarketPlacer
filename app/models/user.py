from app.models import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import enum


class UserRole(enum.Enum):
    """Роли пользователей с доступом к разделам"""
    ADMIN = 'admin'           # Полный доступ ко всему
    MANAGER = 'manager'       # Главная, статистика, маркировка
    WAREHOUSE = 'warehouse'   # Статистика, маркировка (склад)


# Определение доступа к разделам по ролям
ROLE_SECTIONS = {
    UserRole.ADMIN: ['dashboard', 'statistics', 'marking', 'settings', 'tokens', 'users', 'server'],
    UserRole.MANAGER: ['dashboard', 'statistics', 'marking'],
    UserRole.WAREHOUSE: ['statistics', 'marking'],
}

# Названия ролей на русском
ROLE_NAMES = {
    'admin': 'Администратор',
    'manager': 'Менеджер',
    'warehouse': 'Склад',
}


class User(UserMixin, db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='viewer', nullable=False)
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

    def is_manager(self):
        """Проверить, является ли пользователь менеджером"""
        return self.role == 'manager'

    def is_warehouse(self):
        """Проверить, является ли пользователь складом"""
        return self.role == 'warehouse'

    def has_access_to(self, section):
        """Проверить доступ пользователя к разделу"""
        try:
            user_role = UserRole(self.role)
            allowed_sections = ROLE_SECTIONS.get(user_role, [])
            return section in allowed_sections
        except ValueError:
            # Для совместимости со старыми ролями - даём минимальный доступ
            if self.role == 'admin':
                return True
            return False

    def get_role_display(self):
        """Получить название роли на русском"""
        return ROLE_NAMES.get(self.role, 'Пользователь')

    @staticmethod
    def get_available_roles():
        """Получить список доступных ролей для назначения"""
        return [
            ('admin', 'Администратор'),
            ('manager', 'Менеджер'),
            ('warehouse', 'Склад'),
        ]

    def is_active(self):
        """Переопределение метода для Flask-Login - активен ли пользователь"""
        return not self.is_blocked

    def __repr__(self):
        return f'<User {self.username}>'

