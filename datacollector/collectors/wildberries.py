import logging
import time
from datetime import datetime, UTC, timedelta
from wb_api import WBApi
from datacollector.collectors.base import BaseCollector
from app.models import WBSale, WBOrder, WBIncome, WBIncomeItem, WBStock

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
        """Collect incomes data - only NEW incomes that don't exist in database"""
        started_at = datetime.now(UTC)
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'incomes')

            if initial or not sync_state.last_successful_sync:
                start_date = datetime(2019, 1, 1, tzinfo=UTC)
            else:
                start_date = sync_state.last_successful_sync
                # Ensure timezone awareness
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=UTC)

            logger.info(f"Collecting incomes from {start_date.strftime('%Y-%m-%d')}")

            # Step 1: Fetch all incomes from API
            time.sleep(60)
            all_incomes_data = self.api.statistics.get_data(
                endpoint="incomes",
                date_from=start_date.strftime('%Y-%m-%d'),
                flag=0  # Get all data from start_date
            )

            if not all_incomes_data:
                logger.info("No incomes data received from API")
                self.update_sync_state(session, self.token_id, 'incomes', success=True)
                self.log_collection(session, self.token_id, self.marketplace, 'incomes', 'success', 0, started_at=started_at)
                return

            logger.info(f"Received {len(all_incomes_data)} total incomes from API")

            # Step 2: Filter out incomes that already exist in database
            existing_income_ids = set()
            for income_data in all_incomes_data:
                income_id_val = income_data.get('incomeId')
                existing = session.query(WBIncome).filter_by(
                    token_id=self.token_id,
                    income_id=income_id_val
                ).first()
                if existing:
                    existing_income_ids.add(income_id_val)

            new_incomes_data = [inc for inc in all_incomes_data if inc.get('incomeId') not in existing_income_ids]
            logger.info(f"Found {len(new_incomes_data)} NEW incomes (skipping {len(existing_income_ids)} existing)")

            if not new_incomes_data:
                logger.info("No new incomes to process")
                self.update_sync_state(session, self.token_id, 'incomes', success=True)
                self.log_collection(session, self.token_id, self.marketplace, 'incomes', 'success', 0, started_at=started_at)
                return

            # Step 3: Process only NEW incomes
            saved_count = 0
            for income_data in new_incomes_data:
                product = self.get_or_create_product(session, self.token_id, self.marketplace, income_data)
                warehouse = self.get_or_create_warehouse(session, self.marketplace, income_data.get('warehouseName'))

                income_id_val = income_data.get('incomeId')
                last_change_str = income_data.get('lastChangeDate')
                last_change = None
                if last_change_str:
                    last_change = datetime.fromisoformat(last_change_str.replace('Z', '+00:00'))

                # Create new income (guaranteed to be new after filtering)
                income = WBIncome(
                    token_id=self.token_id,
                    warehouse_id=warehouse.id if warehouse else None,
                    income_id=income_id_val,
                    number=income_data.get('number'),
                    date=datetime.fromisoformat(income_data.get('date').replace('Z', '+00:00')),
                    last_change_date=last_change,
                    status=income_data.get('status')
                )
                session.add(income)
                session.flush()

                # Add income item
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
            logger.info(f"Saved {saved_count} NEW income items")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'incomes', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting incomes: {e}")

    def collect_sales(self, session, initial: bool = False):
        """Collect sales data with pagination using flag=1 (daily iteration)"""
        started_at = datetime.now(UTC)
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'sales')

            if initial or not sync_state.last_successful_sync:
                time.sleep(60)
                incomes = self.api.statistics.get_data(endpoint="incomes", date_from=datetime(2019, 1, 1, tzinfo=UTC).strftime('%Y-%m-%d'))
                if incomes:
                    first_income = min(datetime.fromisoformat(inc['date'].replace('Z', '+00:00')) for inc in incomes)
                    start_date = first_income.replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    start_date = datetime(2019, 1, 1, tzinfo=UTC)
            else:
                start_date = sync_state.last_successful_sync
                # Ensure timezone awareness
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=UTC)

            logger.info(f"Collecting sales from {start_date.strftime('%Y-%m-%d')}")

            # Use flag=1 to get all data for each date
            saved_count = 0
            current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

            while current_date <= end_date:
                logger.info(f"  Fetching sales for date: {current_date.strftime('%Y-%m-%d')}")
                time.sleep(60)

                sales_data = self.api.statistics.get_data(
                    endpoint="sales",
                    date_from=current_date.strftime('%Y-%m-%d'),
                    flag=1  # Get all data for this specific date
                )

                if sales_data:
                    logger.info(f"  Received {len(sales_data)} sales for {current_date.strftime('%Y-%m-%d')}")

                    for sale_data in sales_data:
                        existing = session.query(WBSale).filter_by(srid=sale_data.get('srid')).first()
                        if existing:
                            continue

                        last_change_str = sale_data.get('lastChangeDate')
                        last_change = None
                        if last_change_str:
                            last_change = datetime.fromisoformat(last_change_str.replace('Z', '+00:00'))

                        product = self.get_or_create_product(session, self.token_id, self.marketplace, sale_data)
                        warehouse = self.get_or_create_warehouse(session, self.marketplace, sale_data.get('warehouseName'))

                        sale = WBSale(
                            token_id=self.token_id,
                            product_id=product.id,
                            warehouse_id=warehouse.id if warehouse else None,
                            date=datetime.fromisoformat(sale_data.get('date').replace('Z', '+00:00')),
                            last_change_date=last_change,
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
                else:
                    logger.info(f"  No sales for {current_date.strftime('%Y-%m-%d')}")

                # Move to next day
                current_date += timedelta(days=1)

            session.commit()
            self.update_sync_state(session, self.token_id, 'sales', success=True)
            self.log_collection(session, self.token_id, self.marketplace, 'sales', 'success', saved_count, started_at=started_at)
            logger.info(f"Saved {saved_count} sales")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'sales', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting sales: {e}")

    def collect_orders(self, session, initial: bool = False):
        """Collect orders data with pagination using flag=1 (daily iteration)"""
        started_at = datetime.now(UTC)
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'orders')

            if initial or not sync_state.last_successful_sync:
                time.sleep(60)
                incomes = self.api.statistics.get_data(endpoint="incomes", date_from=datetime(2019, 1, 1, tzinfo=UTC).strftime('%Y-%m-%d'))
                if incomes:
                    first_income = min(datetime.fromisoformat(inc['date'].replace('Z', '+00:00')) for inc in incomes)
                    start_date = first_income.replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    start_date = datetime(2019, 1, 1, tzinfo=UTC)
            else:
                start_date = sync_state.last_successful_sync
                # Ensure timezone awareness
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=UTC)

            logger.info(f"Collecting orders from {start_date.strftime('%Y-%m-%d')}")

            # Use flag=1 to get all data for each date
            saved_count = 0
            current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

            while current_date <= end_date:
                logger.info(f"  Fetching orders for date: {current_date.strftime('%Y-%m-%d')}")
                time.sleep(60)

                orders_data = self.api.statistics.get_data(
                    endpoint="orders",
                    date_from=current_date.strftime('%Y-%m-%d'),
                    flag=1  # Get all data for this specific date
                )

                if orders_data:
                    logger.info(f"  Received {len(orders_data)} orders for {current_date.strftime('%Y-%m-%d')}")

                    for order_data in orders_data:
                        existing = session.query(WBOrder).filter_by(srid=order_data.get('srid')).first()
                        if existing:
                            continue

                        last_change_str = order_data.get('lastChangeDate')
                        last_change = None
                        if last_change_str:
                            last_change = datetime.fromisoformat(last_change_str.replace('Z', '+00:00'))

                        product = self.get_or_create_product(session, self.token_id, self.marketplace, order_data)
                        warehouse = self.get_or_create_warehouse(session, self.marketplace, order_data.get('warehouseName'))

                        order = WBOrder(
                            token_id=self.token_id,
                            product_id=product.id,
                            warehouse_id=warehouse.id if warehouse else None,
                            date=datetime.fromisoformat(order_data.get('date').replace('Z', '+00:00')),
                            last_change_date=last_change,
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
                else:
                    logger.info(f"  No orders for {current_date.strftime('%Y-%m-%d')}")

                # Move to next day
                current_date += timedelta(days=1)

            session.commit()
            self.update_sync_state(session, self.token_id, 'orders', success=True)
            self.log_collection(session, self.token_id, self.marketplace, 'orders', 'success', saved_count, started_at=started_at)
            logger.info(f"Saved {saved_count} orders")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'orders', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting orders: {e}")

    def collect_stocks(self, session):
        """Collect stocks data"""
        started_at = datetime.now(UTC)
        try:
            logger.info(f"Collecting stocks for token {self.token_id}")

            time.sleep(60)
            stocks_data = self.api.statistics.get_stocks(date_from="2019-01-01")

            today = datetime.now(UTC).date()
            saved_count = 0

            for stock_obj in stocks_data:
                # Convert Stock object to dict for compatibility
                stock_data = {
                    'nmId': stock_obj.nm_id,
                    'supplierArticle': stock_obj.supplier_article,
                    'warehouseName': stock_obj.warehouse_name,
                    'barcode': stock_obj.barcode,
                    'quantity': stock_obj.quantity,
                    'quantityFull': stock_obj.quantity_full,
                    'inWayToClient': stock_obj.in_way_to_client,
                    'inWayFromClient': stock_obj.in_way_from_client
                }

                product = self.get_or_create_product(session, self.token_id, self.marketplace, stock_data)
                warehouse = self.get_or_create_warehouse(session, self.marketplace, stock_data.get('warehouseName'))

                # Check if stock for today already exists
                existing = session.query(WBStock).filter_by(
                    token_id=self.token_id,
                    product_id=product.id,
                    warehouse_id=warehouse.id if warehouse else None,
                    date=today
                ).first()

                if existing:
                    # Update existing stock
                    existing.quantity = stock_data.get('quantity', 0)
                    existing.quantity_full = stock_data.get('quantityFull', 0)
                    existing.in_way_to_client = stock_data.get('inWayToClient', 0)
                    existing.in_way_from_client = stock_data.get('inWayFromClient', 0)
                else:
                    # Create new stock record
                    stock = WBStock(
                        token_id=self.token_id,
                        product_id=product.id,
                        warehouse_id=warehouse.id if warehouse else None,
                        date=today,
                        quantity=stock_data.get('quantity', 0),
                        quantity_full=stock_data.get('quantityFull', 0),
                        in_way_to_client=stock_data.get('inWayToClient', 0),
                        in_way_from_client=stock_data.get('inWayFromClient', 0)
                    )
                    session.add(stock)
                    saved_count += 1

            session.commit()
            self.update_sync_state(session, self.token_id, 'stocks', success=True)
            self.log_collection(session, self.token_id, self.marketplace, 'stocks', 'success', saved_count, started_at=started_at)
            logger.info(f"Saved {saved_count} stock records")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'stocks', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting stocks: {e}")
            raise

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
