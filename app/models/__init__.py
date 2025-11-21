from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from app.models.user import User
from app.models.token import Token

__all__ = ['db', 'User', 'Token']

