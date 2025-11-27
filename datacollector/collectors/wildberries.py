import logging
import time
from datetime import datetime
from wb_api import WBApi
from datacollector.collectors.base import BaseCollector
from app.models import WBSale, WBOrder, WBIncome, WBIncomeItem

logger = logging.getLogger(__name__)


class WildberriesCollector(BaseCollector):
    """Collector for Wildberries marketplace data"""

    def __init__(self, token_id: int, token: str, database_uri: str):
        super().__init__(database_uri)
        self.token_id = token_id
        self.api = WBApi(token)
        self.marketplace = 'wildberries'

    def collect_all(self):
        """Collect all data for initial sync"""
        session = self.Session()
        try:
            sync_state_incomes = self.get_sync_state(session, self.token_id, 'incomes')

            if sync_state_incomes.last_successful_sync:
                logger.info(f"Token {self.token_id}: Already synced, skipping initial collection")
                session.close()
                return

            logger.info(f"Token {self.token_id}: Initial data collection")

            self.collect_incomes(session, initial=True)
            self.collect_sales(session, initial=True)
            self.collect_orders(session, initial=True)

        except Exception as e:
            logger.error(f"Error in initial collection for token {self.token_id}: {e}")
        finally:
            session.close()

    def collect_incomes(self, session, initial: bool = False):
        """Collect incomes data"""
        started_at = datetime.utcnow()
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'incomes')

            if initial or not sync_state.last_successful_sync:
                start_date = datetime(2019, 1, 1)
            else:
                start_date = sync_state.last_successful_sync

            logger.info(f"Collecting incomes from {start_date.strftime('%Y-%m-%d')}")

            time.sleep(60)
            incomes_data = self.api.statistics.get_data(
                endpoint="incomes",
                date_from=start_date.strftime('%Y-%m-%d')
            )

            saved_count = 0
            for income_data in incomes_data:
                product = self.get_or_create_product(session, self.token_id, self.marketplace, income_data)
                warehouse = self.get_or_create_warehouse(session, self.marketplace, income_data.get('warehouseName'))

                income_id_val = income_data.get('incomeId')
                income = session.query(WBIncome).filter_by(
                    token_id=self.token_id,
                    income_id=income_id_val
                ).first()

                if not income:
                    income = WBIncome(
                        token_id=self.token_id,
                        warehouse_id=warehouse.id if warehouse else None,
                        income_id=income_id_val,
                        number=income_data.get('number'),
                        date=datetime.fromisoformat(income_data.get('date').replace('Z', '+00:00')),
                        last_change_date=datetime.fromisoformat(income_data.get('lastChangeDate').replace('Z', '+00:00')) if income_data.get('lastChangeDate') else None,
                        status=income_data.get('status')
                    )
                    session.add(income)
                    session.flush()

                existing_item = session.query(WBIncomeItem).filter_by(
                    income_id=income.id,
                    product_id=product.id
                ).first()

                if not existing_item:
                    item = WBIncomeItem(
                        income_id=income.id,
                        product_id=product.id,
                        quantity=income_data.get('quantity'),
                        total_price=income_data.get('totalPrice'),
                        date_close=datetime.fromisoformat(income_data.get('dateClose').replace('Z', '+00:00')) if income_data.get('dateClose') else None
                    )
                    session.add(item)
                    saved_count += 1

            session.commit()
            self.update_sync_state(session, self.token_id, 'incomes', success=True)
            self.log_collection(session, self.token_id, self.marketplace, 'incomes', 'success', saved_count, started_at=started_at)
            logger.info(f"Saved {saved_count} income items")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'incomes', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting incomes: {e}")

    def collect_sales(self, session, initial: bool = False):
        """Collect sales data"""
        started_at = datetime.utcnow()
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'sales')

            if initial or not sync_state.last_successful_sync:
                time.sleep(60)
                incomes = self.api.statistics.get_data(endpoint="incomes", date_from=datetime(2019, 1, 1).strftime('%Y-%m-%d'))
                if incomes:
                    first_income = min(datetime.fromisoformat(inc['date'].replace('Z', '+00:00')) for inc in incomes)
                    start_date = first_income.replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    start_date = datetime(2019, 1, 1)
            else:
                start_date = sync_state.last_successful_sync

            logger.info(f"Collecting sales from {start_date.strftime('%Y-%m-%d')}")

            time.sleep(60)
            sales_data = self.api.statistics.get_data(
                endpoint="sales",
                date_from=start_date.strftime('%Y-%m-%d'),
                flag=0
            )

            saved_count = 0
            for sale_data in sales_data:
                existing = session.query(WBSale).filter_by(srid=sale_data.get('srid')).first()
                if existing:
                    continue

                product = self.get_or_create_product(session, self.token_id, self.marketplace, sale_data)
                warehouse = self.get_or_create_warehouse(session, self.marketplace, sale_data.get('warehouseName'))

                sale = WBSale(
                    token_id=self.token_id,
                    product_id=product.id,
                    warehouse_id=warehouse.id if warehouse else None,
                    date=datetime.fromisoformat(sale_data.get('date').replace('Z', '+00:00')),
                    last_change_date=datetime.fromisoformat(sale_data.get('lastChangeDate').replace('Z', '+00:00')) if sale_data.get('lastChangeDate') else None,
                    sale_id=sale_data.get('saleID'),
                    g_number=sale_data.get('gNumber'),
                    srid=sale_data.get('srid'),
                    total_price=sale_data.get('totalPrice'),
                    discount_percent=sale_data.get('discountPercent'),
                    spp=sale_data.get('spp'),
                    for_pay=sale_data.get('forPay'),
                    finished_price=sale_data.get('finishedPrice'),
                    price_with_disc=sale_data.get('priceWithDisc'),
                    region_name=sale_data.get('regionName'),
                    country_name=sale_data.get('countryName'),
                    oblast_okrug_name=sale_data.get('oblastOkrugName')
                )
                session.add(sale)
                saved_count += 1

            session.commit()
            self.update_sync_state(session, self.token_id, 'sales', success=True)
            self.log_collection(session, self.token_id, self.marketplace, 'sales', 'success', saved_count, started_at=started_at)
            logger.info(f"Saved {saved_count} sales")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'sales', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting sales: {e}")

    def collect_orders(self, session, initial: bool = False):
        """Collect orders data"""
        started_at = datetime.utcnow()
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'orders')

            if initial or not sync_state.last_successful_sync:
                time.sleep(60)
                incomes = self.api.statistics.get_data(endpoint="incomes", date_from=datetime(2019, 1, 1).strftime('%Y-%m-%d'))
                if incomes:
                    first_income = min(datetime.fromisoformat(inc['date'].replace('Z', '+00:00')) for inc in incomes)
                    start_date = first_income.replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    start_date = datetime(2019, 1, 1)
            else:
                start_date = sync_state.last_successful_sync

            logger.info(f"Collecting orders from {start_date.strftime('%Y-%m-%d')}")

            time.sleep(60)
            orders_data = self.api.statistics.get_data(
                endpoint="orders",
                date_from=start_date.strftime('%Y-%m-%d'),
                flag=0
            )

            saved_count = 0
            for order_data in orders_data:
                existing = session.query(WBOrder).filter_by(srid=order_data.get('srid')).first()
                if existing:
                    continue

                product = self.get_or_create_product(session, self.token_id, self.marketplace, order_data)
                warehouse = self.get_or_create_warehouse(session, self.marketplace, order_data.get('warehouseName'))

                order = WBOrder(
                    token_id=self.token_id,
                    product_id=product.id,
                    warehouse_id=warehouse.id if warehouse else None,
                    date=datetime.fromisoformat(order_data.get('date').replace('Z', '+00:00')),
                    last_change_date=datetime.fromisoformat(order_data.get('lastChangeDate').replace('Z', '+00:00')) if order_data.get('lastChangeDate') else None,
                    g_number=order_data.get('gNumber'),
                    srid=order_data.get('srid'),
                    total_price=order_data.get('totalPrice'),
                    discount_percent=order_data.get('discountPercent'),
                    spp=order_data.get('spp'),
                    finished_price=order_data.get('finishedPrice'),
                    is_cancel=order_data.get('isCancel', False),
                    cancel_date=datetime.fromisoformat(order_data.get('cancelDate').replace('Z', '+00:00')) if order_data.get('cancelDate') else None,
                    region_name=order_data.get('regionName')
                )
                session.add(order)
                saved_count += 1

            session.commit()
            self.update_sync_state(session, self.token_id, 'orders', success=True)
            self.log_collection(session, self.token_id, self.marketplace, 'orders', 'success', saved_count, started_at=started_at)
            logger.info(f"Saved {saved_count} orders")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'orders', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting orders: {e}")

    def update_data(self):
        """Update data (called every 10 minutes)"""
        session = self.Session()
        try:
            logger.info(f"Token {self.token_id}: Updating data")

            self.collect_incomes(session)
            self.collect_sales(session)
            self.collect_orders(session)

        except Exception as e:
            logger.error(f"Error updating data for token {self.token_id}: {e}")
        finally:
            session.close()
