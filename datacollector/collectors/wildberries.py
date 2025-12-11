import logging
import time
from datetime import datetime, timezone, timedelta
from wb_api import WBApi
from datacollector.collectors.base import BaseCollector
from app.models import WBSale, WBOrder, WBIncome, WBIncomeItem, WBStock, WBGood

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

            self.collect_goods(session)
            self.collect_incomes(session, initial=True)
            self.collect_sales(session, initial=True)
            self.collect_orders(session, initial=True)

        except Exception as e:
            logger.error(f"Error in initial collection for token {self.token_id}: {e}")
        finally:
            session.close()

    def collect_incomes(self, session, initial: bool = False):
        """Collect incomes data - only NEW incomes that don't exist in database"""
        started_at = datetime.now(timezone.utc)
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'incomes')

            if initial or not sync_state.last_successful_sync:
                start_date = datetime(2019, 1, 1, tzinfo=timezone.utc)
            else:
                start_date = sync_state.last_successful_sync
                # Ensure timezone awareness
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)

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
        started_at = datetime.now(timezone.utc)
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'sales')

            if initial or not sync_state.last_successful_sync:
                time.sleep(60)
                incomes = self.api.statistics.get_data(endpoint="incomes", date_from=datetime(2019, 1, 1, tzinfo=timezone.utc).strftime('%Y-%m-%d'))
                if incomes:
                    first_income = min(datetime.fromisoformat(inc['date'].replace('Z', '+00:00')) for inc in incomes)
                    start_date = first_income.replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    start_date = datetime(2019, 1, 1, tzinfo=timezone.utc)
            else:
                start_date = sync_state.last_successful_sync
                # Ensure timezone awareness
                if start_date.tzinfo is None:
                    start_date = start_date.replace(tzinfo=timezone.utc)

            logger.info(f"Collecting sales from {start_date.strftime('%Y-%m-%d')}")

            # Use flag=1 to get all data for each date
            saved_count = 0
            current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

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
        """Collect orders data using flag=0 (all data from date)"""
        started_at = datetime.now(timezone.utc)
        try:
            sync_state = self.get_sync_state(session, self.token_id, 'orders')

            if initial or not sync_state.last_successful_sync:
                time.sleep(60)
                incomes = self.api.statistics.get_data(endpoint="incomes", date_from=datetime(2019, 1, 1, tzinfo=timezone.utc).strftime('%Y-%m-%d'))
                if incomes:
                    first_income = min(datetime.fromisoformat(inc['date'].replace('Z', '+00:00')) for inc in incomes)
                    start_date = first_income.replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    start_date = datetime(2019, 1, 1, tzinfo=timezone.utc)
            else:
                # Берём данные за последние 3 недели для обновления отмен
                start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(weeks=3)

            logger.info(f"Collecting orders from {start_date.strftime('%Y-%m-%d')}")

            time.sleep(60)

            # Используем flag=0 для получения всех данных от даты
            orders_data = self.api.statistics.get_data(
                endpoint="orders",
                date_from=start_date.strftime('%Y-%m-%dT%H:%M:%S'),
                flag=0  # Все данные от указанной даты
            )

            saved_count = 0
            updated_count = 0

            if orders_data:
                logger.info(f"Received {len(orders_data)} orders from API")

                for order_data in orders_data:
                    srid = order_data.get('srid')
                    existing = session.query(WBOrder).filter_by(srid=srid).first()

                    # Парсим даты
                    last_change_str = order_data.get('lastChangeDate')
                    last_change = None
                    if last_change_str:
                        last_change = datetime.fromisoformat(last_change_str.replace('Z', '+00:00'))

                    cancel_date = None
                    if order_data.get('cancelDate'):
                        cancel_date = datetime.fromisoformat(order_data.get('cancelDate').replace('Z', '+00:00'))

                    if existing:
                        # Обновляем существующую запись (статус отмены и другие поля)
                        existing.is_cancel = order_data.get('isCancel', False)
                        existing.cancel_date = cancel_date
                        existing.last_change_date = last_change
                        # Обновляем цены на случай изменений
                        existing.total_price = order_data.get('totalPrice')
                        existing.discount_percent = order_data.get('discountPercent')
                        existing.spp = order_data.get('spp')
                        existing.finished_price = order_data.get('finishedPrice')
                        existing.price_with_disc = order_data.get('priceWithDisc')
                        updated_count += 1
                    else:
                        # Создаём новую запись
                        product = self.get_or_create_product(session, self.token_id, self.marketplace, order_data)
                        warehouse = self.get_or_create_warehouse(session, self.marketplace, order_data.get('warehouseName'))

                        order = WBOrder(
                            token_id=self.token_id,
                            product_id=product.id,
                            warehouse_id=warehouse.id if warehouse else None,
                            # Основные идентификаторы
                            srid=srid,
                            g_number=order_data.get('gNumber'),
                            # Даты
                            date=datetime.fromisoformat(order_data.get('date').replace('Z', '+00:00')),
                            last_change_date=last_change,
                            # Информация о товаре
                            supplier_article=order_data.get('supplierArticle'),
                            nm_id=order_data.get('nmId'),
                            barcode=order_data.get('barcode'),
                            category=order_data.get('category'),
                            subject=order_data.get('subject'),
                            brand=order_data.get('brand'),
                            tech_size=order_data.get('techSize'),
                            # Склад
                            warehouse_name=order_data.get('warehouseName'),
                            warehouse_type=order_data.get('warehouseType'),
                            # География
                            country_name=order_data.get('countryName'),
                            oblast_okrug_name=order_data.get('oblastOkrugName'),
                            region_name=order_data.get('regionName'),
                            # Цены
                            total_price=order_data.get('totalPrice'),
                            discount_percent=order_data.get('discountPercent'),
                            spp=order_data.get('spp'),
                            finished_price=order_data.get('finishedPrice'),
                            price_with_disc=order_data.get('priceWithDisc'),
                            # Поставка
                            income_id=order_data.get('incomeID'),
                            is_supply=order_data.get('isSupply'),
                            is_realization=order_data.get('isRealization'),
                            # Отмена
                            is_cancel=order_data.get('isCancel', False),
                            cancel_date=cancel_date,
                            # Стикер
                            sticker=order_data.get('sticker'),
                        )
                        session.add(order)
                        saved_count += 1
            else:
                logger.info("No orders from API")

            session.commit()
            self.update_sync_state(session, self.token_id, 'orders', success=True)
            self.log_collection(session, self.token_id, self.marketplace, 'orders', 'success', saved_count, started_at=started_at)
            logger.info(f"Orders: saved {saved_count}, updated {updated_count}")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'orders', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting orders: {e}")

    def collect_stocks(self, session):
        """Collect stocks data - only quantity (available for sale)"""
        started_at = datetime.now(timezone.utc)
        try:
            logger.info(f"Collecting stocks for token {self.token_id}")

            time.sleep(60)
            stocks_data = self.api.statistics.get_stocks(date_from="2019-01-01")

            today = datetime.now(timezone.utc).date()
            saved_count = 0
            updated_count = 0

            for stock_obj in stocks_data:
                # Остаток = только quantity (доступно к продаже)
                quantity = stock_obj.quantity

                # Пропускаем нулевые остатки
                if quantity == 0:
                    continue

                barcode = stock_obj.barcode
                warehouse_name = stock_obj.warehouse_name

                # Получаем wb_good по баркоду
                wb_good = session.query(WBGood).filter_by(barcode=barcode).first()

                # Получаем или создаем склад
                warehouse = self.get_or_create_warehouse(session, self.marketplace, warehouse_name)

                # Проверяем существующую запись на сегодня по barcode + warehouse + token
                existing = session.query(WBStock).filter_by(
                    token_id=self.token_id,
                    warehouse_id=warehouse.id if warehouse else None,
                    date=today
                ).filter(
                    WBStock.product_id == (wb_good.id if wb_good else None)
                ).first()

                if existing:
                    # Обновляем существующую запись
                    existing.quantity = quantity
                    updated_count += 1
                else:
                    # Создаем новую запись
                    stock = WBStock(
                        token_id=self.token_id,
                        product_id=wb_good.id if wb_good else None,
                        warehouse_id=warehouse.id if warehouse else None,
                        date=today,
                        quantity=quantity,
                        quantity_full=stock_obj.quantity_full,
                        in_way_to_client=stock_obj.in_way_to_client,
                        in_way_from_client=stock_obj.in_way_from_client
                    )
                    session.add(stock)
                    saved_count += 1

            session.commit()
            self.update_sync_state(session, self.token_id, 'stocks', success=True)
            self.log_collection(session, self.token_id, self.marketplace, 'stocks', 'success', saved_count, started_at=started_at)
            logger.info(f"Saved {saved_count} new stock records, updated {updated_count}")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'stocks', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting stocks: {e}")
            raise

    def collect_goods(self, session):
        """Collect goods (product cards) from WB Content API"""
        import requests

        started_at = datetime.now(timezone.utc)
        try:
            logger.info(f"Collecting goods for token {self.token_id}")

            url = "https://content-api.wildberries.ru/content/v2/get/cards/list"
            headers = {
                "Authorization": self.api.api_key,
                "Content-Type": "application/json"
            }

            all_cards = []
            cursor = {"limit": 100}

            while True:
                payload = {
                    "settings": {
                        "cursor": cursor,
                        "filter": {"withPhoto": -1}
                    }
                }

                # Retry logic for 429 errors
                max_retries = 5
                retry_count = 0
                response = None

                while retry_count < max_retries:
                    try:
                        response = requests.post(url, headers=headers, json=payload, timeout=30)
                        if response.status_code == 429:
                            retry_count += 1
                            logger.warning(f"Rate limit 429, retry {retry_count}/{max_retries}, waiting 15s")
                            time.sleep(15)
                            continue
                        break
                    except requests.exceptions.Timeout:
                        retry_count += 1
                        logger.warning(f"Request timeout, retry {retry_count}/{max_retries}")
                        time.sleep(5)
                    except requests.exceptions.RequestException as e:
                        logger.error(f"Request error: {e}")
                        break

                if response is None or retry_count >= max_retries:
                    logger.error("Max retries exceeded")
                    break

                if response.status_code != 200:
                    logger.error(f"API error: {response.status_code}")
                    break

                data = response.json()
                cards = data.get("cards", [])
                cursor_data = data.get("cursor", {})

                if not cards:
                    break

                all_cards.extend(cards)

                if len(cards) < 100:
                    break

                if not cursor_data.get("updatedAt") and not cursor_data.get("nmID"):
                    break

                cursor = {
                    "limit": 100,
                    "updatedAt": cursor_data.get("updatedAt"),
                    "nmID": cursor_data.get("nmID")
                }

            logger.info(f"Received {len(all_cards)} cards from API")

            # Save cards to wb_goods
            inserted = 0
            updated = 0

            for card in all_cards:
                vendor_code = card.get("vendorCode", "")
                brand = card.get("brand", "")
                title = card.get("title", "")
                description = card.get("description", "")
                imt_id = card.get("imtID")  # ID объединения карточек

                # Parse dates
                created_at_str = card.get("createdAt")
                updated_at_str = card.get("updatedAt")
                card_created_at = None
                card_updated_at = None
                if created_at_str:
                    try:
                        card_created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    except ValueError:
                        pass
                if updated_at_str:
                    try:
                        card_updated_at = datetime.fromisoformat(updated_at_str.replace('Z', '+00:00'))
                    except ValueError:
                        pass

                # Get photos
                photos = card.get("photos", [])
                photo_urls = []
                for photo in photos:
                    photo_url = photo.get("big") or photo.get("c246x328") or photo.get("c516x688") or ""
                    if photo_url:
                        photo_urls.append(photo_url)
                photos_str = ",".join(photo_urls)

                sizes = card.get("sizes", [])
                for size in sizes:
                    tech_size = size.get("techSize", "")
                    wb_size = size.get("wbSize", "")
                    skus = size.get("skus", [])
                    barcode = skus[0] if skus else ""

                    if not barcode:
                        continue

                    # Check if exists
                    existing = session.query(WBGood).filter_by(barcode=barcode).first()

                    if existing:
                        # Update imt_id if changed
                        needs_update = False
                        if existing.imt_id != imt_id:
                            existing.imt_id = imt_id
                            needs_update = True
                        # Update if photos are empty
                        if not existing.photos and photos_str:
                            existing.photos = photos_str
                            needs_update = True
                        if needs_update:
                            updated += 1
                    else:
                        # Insert new
                        good = WBGood(
                            vendor_code=vendor_code,
                            brand=brand,
                            title=title,
                            description=description,
                            tech_size=tech_size,
                            wb_size=wb_size,
                            barcode=barcode,
                            imt_id=imt_id,
                            photos=photos_str,
                            card_created_at=card_created_at,
                            card_updated_at=card_updated_at
                        )
                        session.add(good)
                        inserted += 1

            session.commit()
            self.log_collection(session, self.token_id, self.marketplace, 'goods', 'success', inserted, started_at=started_at)
            logger.info(f"Goods: inserted {inserted}, updated photos {updated}")

        except Exception as e:
            session.rollback()
            self.log_collection(session, self.token_id, self.marketplace, 'goods', 'error', 0, str(e), started_at)
            logger.error(f"Error collecting goods: {e}")
            raise

    def update_data(self):
        """Update data (called every 10 minutes)"""
        session = self.Session()
        try:
            logger.info(f"Token {self.token_id}: Updating data")

            self.collect_goods(session)
            self.collect_incomes(session)
            self.collect_sales(session)
            self.collect_orders(session)

        except Exception as e:
            logger.error(f"Error updating data for token {self.token_id}: {e}")
        finally:
            session.close()
