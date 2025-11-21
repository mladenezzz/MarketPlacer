from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from app.models.user import User
from app.models.token import Token
from app.models.order import Order
from app.models.sale import Sale

__all__ = ['db', 'User', 'Token', 'Order', 'Sale']

