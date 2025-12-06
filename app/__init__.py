from flask import Flask
from flask_login import LoginManager
from app.models import db, User
from config import Config
import os


def create_app(config_class=Config):
    """Фабрика приложения Flask"""
    # Указываем пути к шаблонам и статическим файлам
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    app.config.from_object(config_class)
    
    # Инициализация расширений
    db.init_app(app)
    
    # Настройка Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Регистрация blueprints
    from app.routes import main_bp, auth_bp, admin_bp, tokens_bp, vpn_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(tokens_bp)
    app.register_blueprint(vpn_bp)
    
    # Создание таблиц базы данных
    with app.app_context():
        db.create_all()
    
    return app

