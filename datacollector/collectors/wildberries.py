import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict
from wb_api import WBApi
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)


class WildberriesCollector:
    """Collector for Wildberries marketplace data"""

    def __init__(self, token: str, database_uri: str):
        self.api = WBApi(token)
        self.engine = create_engine(database_uri)
        self.Session = sessionmaker(bind=self.engine)

    def collect_sales(self, days: int = 1) -> List[Dict]:
        """Collect sales data for the last N days"""
        try:
            start_date = datetime.now() - timedelta(days=days)

            time.sleep(60)

            sales_data = self.api.statistics.get_data(
                endpoint="sales",
                date_from=start_date.strftime('%Y-%m-%d'),
                flag=0
            )

            logger.info(f"Collected {len(sales_data)} sales records from Wildberries")
            return sales_data

        except Exception as e:
            logger.error(f"Error collecting Wildberries sales: {e}")
            return []

    def collect_orders(self, days: int = 1) -> List[Dict]:
        """Collect orders data for the last N days"""
        try:
            start_date = datetime.now() - timedelta(days=days)

            time.sleep(60)

            orders_data = self.api.statistics.get_data(
                endpoint="orders",
                date_from=start_date.strftime('%Y-%m-%d'),
                flag=0
            )

            logger.info(f"Collected {len(orders_data)} orders from Wildberries")
            return orders_data

        except Exception as e:
            logger.error(f"Error collecting Wildberries orders: {e}")
            return []

    def save_to_database(self, data: List[Dict], table_name: str):
        """Save collected data to PostgreSQL"""
        session = self.Session()
        try:
            # TODO: Implement saving to database
            logger.info(f"Saved {len(data)} records to {table_name}")
            session.commit()
        except Exception as e:
            logger.error(f"Error saving to database: {e}")
            session.rollback()
        finally:
            session.close()
