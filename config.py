import os
from datetime import timedelta

class Config:
    """Конфигурация приложения"""
    
    # Секретный ключ для сессий и CSRF защиты
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Конфигурация базы данных
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Настройки сессии
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = False  # Установите True при использовании HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

