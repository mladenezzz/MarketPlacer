from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from app.models.user import User
from app.models.token import Token
from app.models.product import Product, Warehouse
from app.models.wildberries import WBSale, WBOrder, WBIncome, WBIncomeItem, WBStock
from app.models.ozon import OzonStock, OzonSale, OzonOrder, OzonSupplyOrder, OzonSupplyItem
from app.models.sync import CollectionLog, SyncState

__all__ = [
    'db', 'User', 'Token',
    'Product', 'Warehouse',
    'WBSale', 'WBOrder', 'WBIncome', 'WBIncomeItem', 'WBStock',
    'OzonStock', 'OzonSale', 'OzonOrder', 'OzonSupplyOrder', 'OzonSupplyItem',
    'CollectionLog', 'SyncState'
]

