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

    # Настройки VPS для VLESS/Reality
    VPS_HOST = os.environ.get('VPS_HOST') or '185.171.80.56'
    VPS_SSH_PORT = int(os.environ.get('VPS_SSH_PORT') or 2211)
    VPS_SSH_USER = os.environ.get('VPS_SSH_USER') or 'mike'
    VPS_SSH_PASSWORD = os.environ.get('VPS_SSH_PASSWORD') or 'Lvl12311party'
    VPS_SSH_KEY = os.environ.get('VPS_SSH_KEY') or '''-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACB+iK9iY9rlWigQTMd5Y/gOIU/ZBGTw5yyHlqMEYLwbggAAAKD7A495+wOP
eQAAAAtzc2gtZWQyNTUxOQAAACB+iK9iY9rlWigQTMd5Y/gOIU/ZBGTw5yyHlqMEYLwbgg
AAAEAnjn+NxubPPUm1azQrj4KCcCXAMJPPCGlH7LFn2exc+n6Ir2Jj2uVaKBBMx3lj+A4h
T9kEZPDnLIeWowRgvBuCAAAAF212ZXJldGVsbmlrb3ZAZ21haWwuY29tAQIDBAUG
-----END OPENSSH PRIVATE KEY-----'''

    # Настройки VLESS/Reality
    VLESS_PORT = 443
    VLESS_PUBLIC_KEY = os.environ.get('VLESS_PUBLIC_KEY') or '-j0jYK4LWRb0PutTpuN9vIYwcMnofq_fpU5NKAms9AU'
    VLESS_PRIVATE_KEY = os.environ.get('VLESS_PRIVATE_KEY') or 'kAl2R_xsgBn9cb4NHyWDOaZRPUvidhkMO_KntaGvW2M'
    VLESS_SHORT_ID = os.environ.get('VLESS_SHORT_ID') or 'abcd1234'

