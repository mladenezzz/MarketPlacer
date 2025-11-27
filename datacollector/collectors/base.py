import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Product, Warehouse, SyncState, CollectionLog

logger = logging.getLogger(__name__)


class BaseCollector:
    """Base class for marketplace collectors"""

    def __init__(self, database_uri: str):
        self.engine = create_engine(database_uri)
        self.Session = sessionmaker(bind=self.engine)

    def get_or_create_product(self, session, token_id: int, marketplace: str, data: dict) -> Product:
        """Get existing product or create new one"""
        article = data.get('supplierArticle')
        nm_id = data.get('nmId')

        product = session.query(Product).filter_by(
            token_id=token_id,
            marketplace=marketplace,
            article=article
        ).first()

        if not product:
            product = Product(
                token_id=token_id,
                marketplace=marketplace,
                article=article,
                nm_id=nm_id,
                barcode=data.get('barcode'),
                brand=data.get('brand'),
                category=data.get('category'),
                subject=data.get('subject')
            )
            session.add(product)
            session.flush()

        return product

    def get_or_create_warehouse(self, session, marketplace: str, warehouse_name: str) -> Warehouse:
        """Get existing warehouse or create new one"""
        if not warehouse_name:
            return None

        warehouse = session.query(Warehouse).filter_by(
            marketplace=marketplace,
            name=warehouse_name
        ).first()

        if not warehouse:
            warehouse = Warehouse(
                marketplace=marketplace,
                name=warehouse_name
            )
            session.add(warehouse)
            session.flush()

        return warehouse

    def get_sync_state(self, session, token_id: int, endpoint: str) -> SyncState:
        """Get sync state for token and endpoint"""
        sync_state = session.query(SyncState).filter_by(
            token_id=token_id,
            endpoint=endpoint
        ).first()

        if not sync_state:
            sync_state = SyncState(
                token_id=token_id,
                endpoint=endpoint
            )
            session.add(sync_state)
            session.flush()

        return sync_state

    def update_sync_state(self, session, token_id: int, endpoint: str, success: bool = True):
        """Update sync state after collection"""
        sync_state = self.get_sync_state(session, token_id, endpoint)
        sync_state.last_sync_date = datetime.utcnow()
        if success:
            sync_state.last_successful_sync = datetime.utcnow()
        sync_state.next_sync_date = datetime.utcnow() + timedelta(minutes=10)
        session.commit()

    def log_collection(self, session, token_id: int, marketplace: str, endpoint: str,
                      status: str, records_count: int = 0, error_message: str = None,
                      started_at: datetime = None):
        """Log collection attempt"""
        log = CollectionLog(
            token_id=token_id,
            marketplace=marketplace,
            endpoint=endpoint,
            status=status,
            records_count=records_count,
            error_message=error_message,
            started_at=started_at or datetime.utcnow(),
            finished_at=datetime.utcnow()
        )
        session.add(log)
        session.commit()
