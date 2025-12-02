import json
import logging
import time
import requests
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
from datacollector.collectors.base import BaseCollector
from app.models import OzonStock, OzonSale, OzonOrder, OzonSupplyOrder, OzonSupplyItem

logger = logging.getLogger(__name__)


class OzonCollector(BaseCollector):
    """Collector for Ozon marketplace data"""

    def __init__(self, token_id: int, client_id: str, api_key: str, database_uri: str):
        super().__init__(database_uri)
        self.token_id = token_id
        self.client_id = client_id
        self.api_key = api_key
        self.marketplace = 'ozon'
        self.base_url = 'https://api-seller.ozon.ru'

        self.headers = {
            'Client-Id': str(client_id),
            'Api-Key': api_key,
            'Content-Type': 'application/json'
        }

    @staticmethod
    def parse_offer_id(offer_id: str) -> tuple:
        """
        Parse offer_id to extract article and size
        Format: article/size

        Examples:
        - 3031080131/S -> (3031080131, S)
        - 3031080131/65 -> (3031080131, 6,5)
        - 3031080131/685 -> (3031080131, 6-8,5)
        """
        if not offer_id or '/' not in offer_id:
            return (offer_id, '')

        parts = offer_id.split('/')
        article = parts[0]
        size_raw = parts[1] if len(parts) > 1 else ''

        # Parse numeric sizes
        if size_raw.isdigit():
            size_num = int(size_raw)

            # Special case: 685 -> "6-8,5"
            if size_num == 685:
                size = "6-8,5"
            # Standard sizes: 65->6,5, 75->7,5, etc.
            elif size_num >= 65 and size_num % 10 == 5:
                size = f"{size_num // 10},{size_num % 10}"
            else:
                size = size_raw
        else:
            # Letter sizes (S, M, L, etc.)
            size = size_raw

        return (article, size)

    def collect_all(self):
        """Collect all data for initial sync"""
        session = self.Session()
        try:
            sync_state_stocks = self.get_sync_state(session, self.token_id, 'ozon_stocks')

            if sync_state_stocks.last_successful_sync:
                logger.info(f"Token {self.token_id}: Already synced, skipping initial collection")
                session.close()
                return

            logger.info(f"Token {self.token_id}: Initial data collection for Ozon")

            # Collect in order: stocks, orders, sales, supply orders
            self.collect_stocks(session, initial=True)
            time.sleep(1)
            self.collect_orders(session, initial=True)
            time.sleep(1)
            self.collect_sales(session, initial=True)
            time.sleep(1)
            self.collect_supply_orders(session, initial=True)

        except Exception as e:
            logger.error(f"Error in initial collection for Ozon token {self.token_id}: {e}")
        finally:
            session.close()

    def collect_stocks(self, session, initial: bool = False):
        """Collect stocks/warehouse data using /v1/report/products/create (includes FBO and FBS)"""
        started_at = datetime.now(timezone.utc)
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'ozon_stocks')

            logger.info(f"Collecting Ozon stocks for token {self.token_id}")

            # Step 1: Create report
            create_url = f"{self.base_url}/v1/report/products/create"
            payload = {
                "language": "DEFAULT",
                "offer_id": [],
                "search": "",
                "sku": [],
                "visibility": "ALL"
            }

            logger.info("  Creating stocks report...")
            response = requests.post(create_url, headers=self.headers, json=payload, timeout=30)

            if response.status_code != 200:
                logger.error(f"Ozon create report API error {response.status_code}: {response.text}")
                raise Exception(f"Failed to create report: {response.status_code}")

            data = response.json()
            report_code = data.get('result', {}).get('code')

            if not report_code:
                raise Exception("No report code in response")

            logger.info(f"  Report code: {report_code}")

            # Step 2: Wait for report to be ready
            info_url = f"{self.base_url}/v1/report/info"
            max_attempts = 30
            attempt = 0
            report_file_url = None

            while attempt < max_attempts:
                attempt += 1
                time.sleep(5)

                info_payload = {"code": report_code}
                response = requests.post(info_url, headers=self.headers, json=info_payload, timeout=30)

                if response.status_code == 200:
                    info_data = response.json()
                    result = info_data.get('result', {})
                    status = result.get('status')

                    if status == "success":
                        report_file_url = result.get('file')
                        logger.info(f"  Report ready!")
                        break
                    elif status == "failed":
                        error = result.get('error')
                        raise Exception(f"Report generation failed: {error}")

            if not report_file_url:
                raise Exception("Report did not complete in time")

            # Step 3: Download report file
            logger.info("  Downloading report...")
            response = requests.get(report_file_url, timeout=30)

            if response.status_code != 200:
                raise Exception(f"Failed to download report: {response.status_code}")

            # Step 4: Parse CSV
            import csv
            from io import StringIO

            csv_content = response.content.decode('utf-8-sig')
            reader = csv.reader(StringIO(csv_content), delimiter=';')
            rows = list(reader)

            if not rows:
                raise Exception("CSV file is empty")

            headers = rows[0]
            data_rows = rows[1:]

            logger.info(f"  Downloaded report with {len(data_rows)} products")

            # Find FBO stock column (column 18: "Остаток на складе Ozon FBO, шт.")
            fbo_stock_col_idx = 17  # Column 18 (0-indexed)

            # Save to database
            saved_count = 0
            current_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

            for row in data_rows:
                if len(row) <= fbo_stock_col_idx:
                    continue

                try:
                    # Extract data from CSV
                    article = row[0] if len(row) > 0 else ''
                    sku = row[2] if len(row) > 2 else ''
                    barcode = row[3] if len(row) > 3 else ''

                    # Get FBO stock value
                    fbo_present = 0
                    if len(row) > fbo_stock_col_idx and row[fbo_stock_col_idx]:
                        try:
                            fbo_present = int(float(row[fbo_stock_col_idx]))
                        except (ValueError, IndexError):
                            pass

                    # Skip if no article
                    if not article:
                        continue

                    # Get or create product
                    product_data = {
                        'supplierArticle': article,
                        'nmId': sku,
                        'barcode': barcode,
                        'brand': None,
                        'category': None,
                        'subject': None
                    }
                    product = self.get_or_create_product(session, self.token_id, self.marketplace, product_data)

                    # Check if stock already exists for today
                    existing_stock = session.query(OzonStock).filter_by(
                        token_id=self.token_id,
                        product_id=product.id,
                        warehouse_id=None,  # Report doesn't provide warehouse info
                        date=current_date
                    ).first()

                    if existing_stock:
                        # Update existing record
                        existing_stock.fbo_present = fbo_present
                        existing_stock.fbo_reserved = 0
                        existing_stock.fbs_present = 0
                        existing_stock.fbs_reserved = 0
                    else:
                        # Create new record
                        stock = OzonStock(
                            token_id=self.token_id,
                            product_id=product.id,
                            warehouse_id=None,  # Report doesn't provide warehouse info
                            offer_id=article,
                            product_sku=sku,
                            fbo_present=fbo_present,
                            fbo_reserved=0,
                            fbs_present=0,
                            fbs_reserved=0,
                            date=current_date
                        )
                        session.add(stock)
                        saved_count += 1

                except Exception as e:
                    logger.debug(f"  Error processing row: {e}")
                    continue

            session.commit()
            self.update_sync_state(session, self.token_id, 'ozon_stocks', success=True)
            self.log_collection(session, self.token_id, self.marketplace, 'ozon_stocks', 'success', saved_count, started_at=started_at)
            logger.info(f"Saved {saved_count} Ozon stock records")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'ozon_stocks', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting Ozon stocks: {e}")

    def collect_orders(self, session, initial: bool = False):
        """Collect orders data (FBS and FBO orders) using /v3/posting/fbs/list and /v2/posting/fbo/list"""
        started_at = datetime.now(timezone.utc)
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'ozon_orders')

            # Определяем начальную дату для сбора
            if initial or not sync_state.last_successful_sync:
                # Находим дату первой поставки (из supply_orders)
                from app.models import OzonSupplyOrder
                first_supply = session.query(OzonSupplyOrder).filter_by(
                    token_id=self.token_id
                ).order_by(OzonSupplyOrder.timeslot_from.asc()).first()

                if first_supply and first_supply.timeslot_from:
                    # Сначала пробуем 180 дней, если не получится - 90 дней
                    start_date_180 = max(first_supply.timeslot_from, datetime.now(timezone.utc) - timedelta(days=180))
                    start_date_90 = max(first_supply.timeslot_from, datetime.now(timezone.utc) - timedelta(days=90))

                    logger.info(f"First supply found at {first_supply.timeslot_from.strftime('%Y-%m-%d')}, trying to collect orders from {start_date_180.strftime('%Y-%m-%d')} (180 days)")

                    # Пробуем собрать с 180 дней
                    start_date = start_date_180
                    test_saved = self._test_orders_date_range(start_date)

                    if test_saved == -1:  # API error, fallback to 90 days
                        logger.warning(f"180-day range failed, falling back to 90 days from {start_date_90.strftime('%Y-%m-%d')}")
                        start_date = start_date_90
                else:
                    # Если поставок нет, пробуем 180 дней, если не получится - 90
                    logger.info(f"No supplies found, trying 180 days")
                    start_date = datetime.now(timezone.utc) - timedelta(days=180)
                    test_saved = self._test_orders_date_range(start_date)

                    if test_saved == -1:  # API error, fallback to 90 days
                        logger.warning(f"180-day range failed, falling back to 90 days")
                        start_date = datetime.now(timezone.utc) - timedelta(days=90)
            else:
                start_date = sync_state.last_successful_sync
                # Ensure start_date has timezone info
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)

            logger.info(f"Collecting Ozon orders from {start_date.strftime('%Y-%m-%d')}")

            saved_count = 0

            # Collect FBS orders
            saved_count += self._collect_fbs_orders(session, start_date)
            time.sleep(1)

            # Collect FBO orders
            saved_count += self._collect_fbo_orders(session, start_date)

            session.commit()
            self.update_sync_state(session, self.token_id, 'ozon_orders', success=True)
            self.log_collection(session, self.token_id, self.marketplace, 'ozon_orders', 'success', saved_count, started_at=started_at)
            logger.info(f"Saved {saved_count} Ozon orders")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'ozon_orders', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting Ozon orders: {e}")

    def collect_sales(self, session, initial: bool = False):
        """Collect sales data using /v3/finance/transaction/list with OperationAgentDeliveredToCustomer"""
        started_at = datetime.now(timezone.utc)
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'ozon_sales')

            # Определяем начальную дату для сбора
            # Если первая синхронизация, собираем помесячно с даты первой поставки
            if initial or not sync_state.last_successful_sync:
                # Находим дату первой поставки (из supply_orders)
                from app.models import OzonSupplyOrder
                first_supply = session.query(OzonSupplyOrder).filter_by(
                    token_id=self.token_id
                ).order_by(OzonSupplyOrder.timeslot_from.asc()).first()

                if first_supply and first_supply.timeslot_from:
                    start_date = first_supply.timeslot_from
                    logger.info(f"First supply found at {start_date.strftime('%Y-%m-%d')}, collecting sales from that date")
                else:
                    # Если поставок нет, берем последние 12 месяцев
                    start_date = datetime.now(timezone.utc) - relativedelta(months=12)
                    logger.info(f"No supplies found, collecting sales for last 12 months")
            else:
                start_date = sync_state.last_successful_sync

            logger.info(f"Collecting Ozon sales from {start_date.strftime('%Y-%m-%d')}")

            saved_count = self._collect_finance_transactions(session, start_date)

            session.commit()
            self.update_sync_state(session, self.token_id, 'ozon_sales', success=True)
            self.log_collection(session, self.token_id, self.marketplace, 'ozon_sales', 'success', saved_count, started_at=started_at)
            logger.info(f"Saved {saved_count} Ozon sales")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'ozon_sales', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting Ozon sales: {e}")

    def _test_orders_date_range(self, start_date: datetime) -> int:
        """Test if date range is acceptable by API (returns -1 on error, 0+ on success)"""
        url = f"{self.base_url}/v3/posting/fbs/list"

        payload = {
            "dir": "ASC",
            "filter": {
                "since": start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                "to": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                "status": ""
            },
            "limit": 1,  # Only test with 1 record
            "offset": 0,
            "with": {
                "analytics_data": False,
                "financial_data": False
            }
        }

        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)

            if response.status_code == 200:
                return 0  # Success
            else:
                logger.warning(f"Date range test failed with status {response.status_code}")
                return -1  # Error
        except Exception as e:
            logger.warning(f"Date range test exception: {e}")
            return -1

    def _collect_fbs_orders(self, session, start_date: datetime) -> int:
        """Collect FBS orders with pagination"""
        url = f"{self.base_url}/v3/posting/fbs/list"
        saved_count = 0
        offset = 0
        limit = 1000

        while True:
            payload = {
                "dir": "ASC",
                "filter": {
                    "since": start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    "to": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    "status": ""
                },
                "limit": limit,
                "offset": offset,
                "with": {
                    "analytics_data": True,
                    "financial_data": True
                }
            }

            response = requests.post(url, headers=self.headers, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                result = data.get('result', {})
                postings = result.get('postings', [])

                if not postings:
                    break

                for posting in postings:
                    saved_count += self._save_posting(session, posting, 'FBS')

                logger.info(f"  FBS: loaded {len(postings)} orders at offset {offset}")

                # Check if we got less than limit (last page)
                if len(postings) < limit:
                    break

                offset += limit
                time.sleep(1)  # Rate limiting
            else:
                logger.error(f"Ozon FBS API error {response.status_code}: {response.text}")
                break

        return saved_count

    def _collect_fbo_orders(self, session, start_date: datetime) -> int:
        """Collect FBO orders with pagination"""
        url = f"{self.base_url}/v2/posting/fbo/list"
        saved_count = 0
        offset = 0
        limit = 1000

        while True:
            payload = {
                "dir": "ASC",
                "filter": {
                    "since": start_date.strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    "to": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z'),
                    "status": ""
                },
                "limit": limit,
                "offset": offset,
                "with": {
                    "analytics_data": True,
                    "financial_data": True
                }
            }

            response = requests.post(url, headers=self.headers, json=payload, timeout=30)

            if response.status_code == 200:
                data = response.json()
                result = data.get('result', [])

                if not result:
                    break

                for posting in result:
                    saved_count += self._save_posting(session, posting, 'FBO')

                logger.info(f"  FBO: loaded {len(result)} orders at offset {offset}")

                # Check if we got less than limit (last page)
                if len(result) < limit:
                    break

                offset += limit
                time.sleep(1)  # Rate limiting
            else:
                logger.error(f"Ozon FBO API error {response.status_code}: {response.text}")
                break

        return saved_count

    def _save_posting(self, session, posting: dict, delivery_schema: str) -> int:
        """Save single posting (order) to ozon_orders database"""
        posting_number = posting.get('posting_number')
        saved_count = 0
        products = posting.get('products', [])

        for product_data in products:
            offer_id = product_data.get('offer_id', '')
            article, size = self.parse_offer_id(offer_id)

            # Get or create product
            product_dict = {
                'supplierArticle': article,
                'nmId': product_data.get('sku'),
                'barcode': product_data.get('barcode', ''),
                'brand': None,
                'category': None,
                'subject': None
            }
            product = self.get_or_create_product(session, self.token_id, self.marketplace, product_dict)

            # Check if this specific product in posting already exists
            sku = product_data.get('sku')
            existing = session.query(OzonOrder).filter_by(
                posting_number=posting_number,
                sku=sku
            ).first()
            if existing:
                continue

            # Parse dates
            shipment_date = posting.get('shipment_date')
            in_process_at = posting.get('in_process_at')

            order = OzonOrder(
                token_id=self.token_id,
                product_id=product.id,
                posting_number=posting_number,
                order_id=posting.get('order_id'),
                order_number=posting.get('order_number'),
                offer_id=offer_id,
                sku=product_data.get('sku'),
                quantity=product_data.get('quantity', 1),
                shipment_date=datetime.fromisoformat(shipment_date.replace('Z', '+00:00')) if shipment_date else None,
                in_process_at=datetime.fromisoformat(in_process_at.replace('Z', '+00:00')) if in_process_at else None,
                delivery_schema=delivery_schema,
                price=product_data.get('price'),
                status=posting.get('status')
            )

            # Add financial data if available
            financial_data = posting.get('financial_data', {})
            if financial_data:
                order.commission_amount = financial_data.get('commission_amount')
                order.commission_percent = financial_data.get('commission_percent')
                order.payout = financial_data.get('payout')

            session.add(order)
            saved_count += 1

        return saved_count

    def _collect_finance_transactions(self, session, start_date: datetime) -> int:
        """Collect sales from /v3/finance/transaction/list with monthly pagination"""
        url = f"{self.base_url}/v3/finance/transaction/list"
        saved_count = 0
        today = datetime.now(timezone.utc)

        # Ensure start_date has timezone info
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)

        # Iterate through each month from start_date to today
        current_date = start_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        while current_date <= today:
            # Define start and end of current month
            month_start = current_date
            month_end = (current_date + relativedelta(months=1)) - timedelta(seconds=1)

            # If month end is after today, use today
            if month_end > today:
                month_end = today

            # Format dates for API
            date_from_str = month_start.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            date_to_str = month_end.strftime('%Y-%m-%dT%H:%M:%S.999Z')

            logger.info(f"  Collecting sales for {month_start.strftime('%B %Y')}")

            # Pagination - get all pages for current month
            page = 1
            has_next = True
            month_saved = 0

            while has_next:
                params = {
                    "filter": {
                        "date": {
                            "from": date_from_str,
                            "to": date_to_str
                        },
                        "operation_type": ["OperationAgentDeliveredToCustomer"],
                        "posting_number": "",
                        "transaction_type": "all"
                    },
                    "page": page,
                    "page_size": 1000
                }

                # Retry loop for 429 errors
                max_retries = 5
                retry_count = 0
                request_successful = False

                while retry_count < max_retries and not request_successful:
                    response = requests.post(url, headers=self.headers, json=params, timeout=30)

                    if response.status_code == 200:
                        request_successful = True
                        data = response.json()
                        result = data.get('result', {})
                        operations = result.get('operations', [])

                        # If no operations - exit loop
                        if not operations:
                            has_next = False
                            break

                        # Process operations from current page
                        for operation in operations:
                            if operation.get('operation_type') == 'OperationAgentDeliveredToCustomer':
                                if self._save_finance_transaction(session, operation):
                                    month_saved += 1

                        # Check if there are more pages
                        # If we got less than 1000 records - this is the last page
                        if len(operations) < 1000:
                            has_next = False
                        else:
                            page += 1

                    elif response.status_code == 429:
                        retry_count += 1
                        if retry_count < max_retries:
                            logger.warning(f"    Error 429 for page {page} in {month_start.strftime('%B %Y')}. Retry {retry_count}/{max_retries}. Waiting 20 seconds...")
                            time.sleep(20)
                        else:
                            logger.error(f"    Max retries exceeded for page {page} in {month_start.strftime('%B %Y')}. Skipping.")
                            has_next = False
                    else:
                        logger.error(f"    Ozon finance API error {response.status_code} for page {page}: {response.text}")
                        has_next = False
                        break

            logger.info(f"    Saved {month_saved} sales for {month_start.strftime('%B %Y')}")
            saved_count += month_saved

            # Move to next month
            current_date = current_date + relativedelta(months=1)
            time.sleep(1)  # Rate limiting between months

        return saved_count

    def _save_finance_transaction(self, session, operation: dict) -> bool:
        """Save single finance transaction (sale) to ozon_sales database"""
        try:
            posting_number = operation.get('posting', {}).get('posting_number')
            if not posting_number:
                return False

            # Get operation_id as unique identifier
            operation_id = operation.get('operation_id')
            if not operation_id:
                return False

            # Check if this transaction already exists
            existing = session.query(OzonSale).filter_by(
                token_id=self.token_id,
                posting_number=posting_number
            ).first()
            if existing:
                return False

            # Parse operation date
            operation_date_str = operation.get('operation_date')
            operation_date = datetime.fromisoformat(operation_date_str.replace('Z', '+00:00')) if operation_date_str else None

            # Extract posting info
            posting_info = operation.get('posting', {})
            delivery_schema = posting_info.get('delivery_schema', '')

            # Get product info from items (if available)
            items = operation.get('items', [])
            sku = items[0].get('sku') if items else None

            # Create sale record
            sale = OzonSale(
                token_id=self.token_id,
                product_id=None,  # Will be linked later if needed
                posting_number=posting_number,
                order_id=None,
                order_number=None,
                offer_id='',
                sku=sku,
                quantity=1,  # Finance API doesn't provide quantity directly
                shipment_date=operation_date,
                in_process_at=None,
                delivery_schema=delivery_schema,
                price=operation.get('accruals_for_sale', 0),  # Using accruals_for_sale as price
                commission_amount=None,
                commission_percent=None,
                payout=operation.get('amount', 0),
                status='delivered'  # OperationAgentDeliveredToCustomer means delivered
            )

            session.add(sale)
            return True

        except Exception as e:
            logger.debug(f"    Error saving finance transaction: {e}")
            return False

    def collect_supply_orders(self, session, initial: bool = False):
        """Collect supply orders (поставки FBO) using /v3/supply-order/list, /v3/supply-order/get, and /v1/supply-order/bundle"""
        started_at = datetime.now(timezone.utc)
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'ozon_supply_orders')

            logger.info(f"Collecting Ozon supply orders for token {self.token_id}")

            # Step 1: Get list of supply order IDs
            url_list = f"{self.base_url}/v3/supply-order/list"
            payload_order_list = {
                "filter": {
                    "states": ["COMPLETED"]
                },
                "limit": 100,
                "sort_by": 1
            }

            response_order_list = requests.post(url_list, headers=self.headers, json=payload_order_list, timeout=30)

            if response_order_list.status_code != 200:
                logger.error(f"Ozon supply-order/list API error {response_order_list.status_code}: {response_order_list.text}")
                raise Exception(f"Failed to get order list: {response_order_list.status_code}")

            orderid_list = response_order_list.json().get('order_ids', [])
            logger.info(f"API returned {len(orderid_list)} supply order IDs")

            # Step 2: Filter out orders that already exist in database
            existing_order_ids = set()
            for order_id in orderid_list:
                existing = session.query(OzonSupplyOrder).filter_by(
                    token_id=self.token_id,
                    supply_order_id=str(order_id)
                ).first()
                if existing:
                    existing_order_ids.add(order_id)

            new_order_ids = [oid for oid in orderid_list if oid not in existing_order_ids]
            logger.info(f"Found {len(new_order_ids)} NEW orders (skipping {len(existing_order_ids)} existing)")

            if not new_order_ids:
                logger.info("No new supply orders to process")
                self.update_sync_state(session, self.token_id, 'ozon_supply_orders', success=True)
                self.log_collection(session, self.token_id, self.marketplace, 'ozon_supply_orders', 'success', 0, started_at=started_at)
                return

            # Step 3: Get order details in batches of 50 (only for NEW orders)
            url_get = f"{self.base_url}/v3/supply-order/get"
            batch_size = 50
            all_orders = []

            for i in range(0, len(new_order_ids), batch_size):
                batch = new_order_ids[i:i + batch_size]
                payload_order_get = {"order_ids": batch}

                response_order_get = requests.post(url_get, headers=self.headers, json=payload_order_get, timeout=30)

                if response_order_get.status_code == 200:
                    batch_orders = response_order_get.json().get('orders', [])
                    all_orders.extend(batch_orders)
                    logger.info(f"  Loaded batch {i//batch_size + 1}: {len(batch_orders)} NEW orders")
                else:
                    logger.error(f"Failed to get batch {i//batch_size + 1}: {response_order_get.status_code}")

                time.sleep(1)

            logger.info(f"Loaded total {len(all_orders)} NEW supply orders with details")

            # Step 4: Extract bundle_ids and order info, save NEW supply orders
            bundle_data = []  # List of (bundle_id, order_number, timeslot_from, supply_order)

            for order in all_orders:
                order_id = order.get('order_id')
                order_number = order.get('order_number')
                supplies = order.get('supplies', [])

                if not supplies:
                    continue

                bundle_id = supplies[0].get('bundle_id')
                timeslot = supplies[0].get('timeslot', {})
                timeslot_from_str = timeslot.get('from') if timeslot else None
                timeslot_from = datetime.fromisoformat(timeslot_from_str.replace('Z', '+00:00')) if timeslot_from_str else None

                # Save NEW supply order to database
                warehouse_name = order.get('drop_off_warehouse', {}).get('name')
                warehouse = self.get_or_create_warehouse(session, self.marketplace, warehouse_name) if warehouse_name else None

                # All orders here are NEW (filtered earlier)
                created_at_str = order.get('created_date')
                updated_at_str = order.get('state_updated_date')

                supply_order = OzonSupplyOrder(
                    token_id=self.token_id,
                    warehouse_id=warehouse.id if warehouse else None,
                    supply_order_id=str(order_id),
                    supply_order_number=order_number,
                    bundle_id=bundle_id,
                    timeslot_from=timeslot_from,
                    created_at_api=datetime.fromisoformat(created_at_str.replace('Z', '+00:00')) if created_at_str else None,
                    updated_at_api=datetime.fromisoformat(updated_at_str.replace('Z', '+00:00')) if updated_at_str else None,
                    status=order.get('state'),
                    warehouse_name_api=warehouse_name
                )
                session.add(supply_order)
                session.flush()

                if bundle_id:
                    bundle_data.append((bundle_id, order_number, timeslot_from, supply_order))

            session.commit()
            logger.info(f"Saved {len(bundle_data)} NEW supply orders to database")

            # Step 5: Collect items for each NEW bundle SEPARATELY with pagination
            url_bundle = f"{self.base_url}/v1/supply-order/bundle"
            saved_items_count = 0
            bundle_count = 1

            for bundle_id, order_number, timeslot_from, supply_order in bundle_data:
                logger.info(f"  Processing bundle {bundle_count}/{len(bundle_data)}: {bundle_id}")

                last_id = ''
                bundle_items = []

                while True:
                    payload_order_bundle = {
                        "bundle_ids": [bundle_id],
                        "limit": 100,
                        "last_id": last_id
                    }

                    # Retry loop for 429 errors
                    retry_count = 0
                    max_retries = 10
                    while retry_count < max_retries:
                        response_order_bundle = requests.post(url_bundle, headers=self.headers, json=payload_order_bundle, timeout=30)

                        if response_order_bundle.status_code == 200:
                            break
                        else:
                            retry_count += 1
                            logger.warning(f"    Bundle {bundle_id} - Error {response_order_bundle.status_code}, retry {retry_count}/{max_retries}")
                            time.sleep(10)

                    if response_order_bundle.status_code != 200:
                        logger.error(f"Failed to get bundle {bundle_id} after {max_retries} retries")
                        break

                    bundle_response = response_order_bundle.json()
                    items = bundle_response.get('items', [])
                    bundle_items.extend(items)

                    logger.info(f"    Loaded {len(items)} items from bundle {bundle_id} (total: {len(bundle_items)})")

                    if bundle_response.get('has_next') is True:
                        last_id = bundle_response.get('last_id')
                    else:
                        time.sleep(5)
                        break

                # Save items to database
                for item_data in bundle_items:
                    offer_id = item_data.get('offer_id', '')
                    article, size = self.parse_offer_id(offer_id)

                    # Get or create product
                    product_dict = {
                        'supplierArticle': article,
                        'nmId': item_data.get('product_id'),
                        'barcode': item_data.get('barcode', ''),
                        'brand': None,
                        'category': None,
                        'subject': None
                    }
                    product = self.get_or_create_product(session, self.token_id, self.marketplace, product_dict)

                    # Check if item already exists
                    sku = item_data.get('sku')
                    existing_item = session.query(OzonSupplyItem).filter_by(
                        supply_order_id=supply_order.id,
                        sku=sku
                    ).first()

                    if not existing_item:
                        item = OzonSupplyItem(
                            supply_order_id=supply_order.id,
                            product_id=product.id,
                            sku=sku,
                            offer_id=offer_id,
                            article=article,
                            size=size,
                            quantity=item_data.get('quantity', 0),
                            barcode=item_data.get('barcode'),
                            name=item_data.get('name'),
                            bundle_id=bundle_id,
                            timeslot_from=timeslot_from
                        )
                        session.add(item)
                        saved_items_count += 1

                session.commit()
                logger.info(f"  Bundle {bundle_count}/{len(bundle_data)}: saved {len(bundle_items)} items")
                bundle_count += 1

            self.update_sync_state(session, self.token_id, 'ozon_supply_orders', success=True)
            self.log_collection(session, self.token_id, self.marketplace, 'ozon_supply_orders', 'success', saved_items_count, started_at=started_at)
            logger.info(f"Saved {saved_items_count} supply items from {len(bundle_data)} bundles")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'ozon_supply_orders', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting Ozon supply orders: {e}")

