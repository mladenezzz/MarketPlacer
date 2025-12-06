from app.routes.main import main_bp
from app.routes.auth import auth_bp
from app.routes.admin import admin_bp
from app.routes.tokens import tokens_bp
from app.routes.vpn import vpn_bp
from app.routes.marking import marking_bp

__all__ = ['main_bp', 'auth_bp', 'admin_bp', 'tokens_bp', 'vpn_bp', 'marking_bp']

