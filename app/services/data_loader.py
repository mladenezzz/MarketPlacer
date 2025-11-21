"""Сервис для фоновой загрузки исторических данных"""
import threading
from datetime import datetime, timedelta
from typing import Dict, List
from app import create_app
from app.models import db, Token, Order, Sale
from app.services.marketplace_api import MarketplaceAPI


class DataLoader:
    """Класс для загрузки исторических данных в фоновом режиме"""
    
    # Максимальный период для загрузки (в месяцах)
    MAX_MONTHS_WILDBERRIES = 6
    MAX_MONTHS_OZON = 6
    
    # Размер периода для Ozon (в днях) - максимум 30 дней за один запрос
    OZON_PERIOD_DAYS = 30
    
    @staticmethod
    def start_background_loading(token_id: int):
        """
        Запустить фоновую загрузку данных для токена
        
        Args:
            token_id: ID токена для загрузки данных
        """
        thread = threading.Thread(
            target=DataLoader._load_historical_data,
            args=(token_id,),
            daemon=True
        )
        thread.start()
    
    @staticmethod
    def _load_historical_data(token_id: int):
        """
        Загрузить исторические данные для токена
        
        Args:
            token_id: ID токена
        """
        app = create_app()
        with app.app_context():
            try:
                token = Token.query.get(token_id)
                if not token:
                    return
                
                # Обновляем статус на "загрузка"
                token.data_loading_status = 'loading'
                token.data_loading_started_at = datetime.utcnow()
                token.data_loading_progress = 0
                token.data_loading_loaded_periods = 0
                db.session.commit()
                
                # Определяем максимальный период для загрузки
                if token.marketplace == 'wildberries':
                    DataLoader._load_wildberries_data(token)
                elif token.marketplace == 'ozon':
                    DataLoader._load_ozon_data(token)
                else:
                    # Для других маркетплейсов просто помечаем как завершенное
                    token.data_loading_status = 'completed'
                    token.data_loading_progress = 100
                    token.data_loading_completed_at = datetime.utcnow()
                    db.session.commit()
                    
            except Exception as e:
                # В случае ошибки обновляем статус
                try:
                    token = Token.query.get(token_id)
                    if token:
                        token.data_loading_status = 'error'
                        token.data_loading_error = str(e)
                        token.data_loading_completed_at = datetime.utcnow()
                        db.session.commit()
                except:
                    pass
    
    @staticmethod
    def _load_wildberries_data(token: Token):
        """
        Загрузить исторические данные для Wildberries
        
        Args:
            token: Объект токена
        """
        try:
            # Для Wildberries загружаем данные за последние 6 месяцев
            # Разбиваем на месяцы для отслеживания прогресса
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=DataLoader.MAX_MONTHS_WILDBERRIES * 30)
            
            # Разбиваем на месяцы
            periods = []
            current_date = start_date
            while current_date < end_date:
                period_end = min(current_date + timedelta(days=30), end_date)
                periods.append((current_date, period_end))
                current_date = period_end
            
            token.data_loading_total_periods = len(periods) * 2  # Заказы и продажи
            db.session.commit()
            
            loaded = 0
            
            # Загружаем заказы
            for period_start, period_end in periods:
                try:
                    # Для Wildberries используем dateFrom на начало периода
                    # API вернет все данные от этой даты, фильтруем на стороне
                    date_from = period_start.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                    
                    headers = {
                        'Authorization': token.token,
                        'Content-Type': 'application/json'
                    }
                    
                    url = 'https://statistics-api.wildberries.ru/api/v1/supplier/orders'
                    params = {'dateFrom': date_from, 'flag': 0}
                    
                    response = MarketplaceAPI._make_request_with_retry(
                        url, headers, params=params, method='GET', timeout=30
                    )
                    
                    if response.status_code == 200:
                        orders_data = response.json()
                        if orders_data:
                            DataLoader._save_wildberries_orders(token, orders_data, period_start, period_end)
                    
                    loaded += 1
                    token.data_loading_loaded_periods = loaded
                    token.data_loading_progress = int((loaded / token.data_loading_total_periods) * 100)
                    db.session.commit()
                    
                except Exception as e:
                    # Продолжаем загрузку даже при ошибках в отдельных периодах
                    loaded += 1
                    token.data_loading_loaded_periods = loaded
                    token.data_loading_progress = int((loaded / token.data_loading_total_periods) * 100)
                    db.session.commit()
            
            # Загружаем продажи
            for period_start, period_end in periods:
                try:
                    date_from = period_start.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                    
                    headers = {
                        'Authorization': token.token,
                        'Content-Type': 'application/json'
                    }
                    
                    url = 'https://statistics-api.wildberries.ru/api/v1/supplier/sales'
                    params = {'dateFrom': date_from, 'flag': 0}
                    
                    response = MarketplaceAPI._make_request_with_retry(
                        url, headers, params=params, method='GET', timeout=30
                    )
                    
                    if response.status_code == 200:
                        sales_data = response.json()
                        if sales_data:
                            DataLoader._save_wildberries_sales(token, sales_data, period_start, period_end)
                    
                    loaded += 1
                    token.data_loading_loaded_periods = loaded
                    token.data_loading_progress = int((loaded / token.data_loading_total_periods) * 100)
                    db.session.commit()
                    
                except Exception as e:
                    loaded += 1
                    token.data_loading_loaded_periods = loaded
                    token.data_loading_progress = int((loaded / token.data_loading_total_periods) * 100)
                    db.session.commit()
            
            # Завершаем загрузку
            token.data_loading_status = 'completed'
            token.data_loading_progress = 100
            token.data_loading_completed_at = datetime.utcnow()
            db.session.commit()
            
        except Exception as e:
            token.data_loading_status = 'error'
            token.data_loading_error = str(e)
            token.data_loading_completed_at = datetime.utcnow()
            db.session.commit()
    
    @staticmethod
    def _load_ozon_data(token: Token):
        """
        Загрузить исторические данные для Ozon
        
        Args:
            token: Объект токена
        """
        try:
            if not token.client_id:
                token.data_loading_status = 'error'
                token.data_loading_error = 'Не указан Client ID для Ozon'
                token.data_loading_completed_at = datetime.utcnow()
                db.session.commit()
                return
            
            # Для Ozon загружаем данные за последние 6 месяцев
            # Разбиваем на периоды по 30 дней
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=DataLoader.MAX_MONTHS_OZON * 30)
            
            # Разбиваем на периоды по 30 дней
            periods = []
            current_date = start_date
            while current_date < end_date:
                period_end = min(current_date + timedelta(days=DataLoader.OZON_PERIOD_DAYS), end_date)
                periods.append((current_date, period_end))
                current_date = period_end
            
            token.data_loading_total_periods = len(periods) * 4  # FBS заказы, FBS продажи, FBO заказы, FBO продажи
            db.session.commit()
            
            loaded = 0
            headers = {
                'Client-Id': token.client_id,
                'Api-Key': token.token,
                'Content-Type': 'application/json'
            }
            
            # Загружаем FBS заказы
            for period_start, period_end in periods:
                try:
                    date_from = period_start.isoformat() + 'Z'
                    date_to = period_end.isoformat() + 'Z'
                    
                    url = 'https://api-seller.ozon.ru/v3/posting/fbs/list'
                    payload = {
                        "dir": "ASC",
                        "filter": {"since": date_from, "to": date_to, "status": ""},
                        "limit": 1000,
                        "offset": 0
                    }
                    
                    response = MarketplaceAPI._make_request_with_retry(
                        url, headers, json_data=payload, method='POST', timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get('result', {})
                        if isinstance(result, list):
                            postings = result
                        elif isinstance(result, dict):
                            postings = result.get('postings', [])
                        else:
                            postings = []
                        
                        if postings:
                            DataLoader._save_ozon_orders(token, postings, 'FBS', period_start, period_end)
                    
                    loaded += 1
                    token.data_loading_loaded_periods = loaded
                    token.data_loading_progress = int((loaded / token.data_loading_total_periods) * 100)
                    db.session.commit()
                
                except Exception as e:
                    loaded += 1
                    token.data_loading_loaded_periods = loaded
                    token.data_loading_progress = int((loaded / token.data_loading_total_periods) * 100)
                    db.session.commit()
            
            # Загружаем FBO заказы
            for period_start, period_end in periods:
                try:
                    date_from = period_start.isoformat() + 'Z'
                    date_to = period_end.isoformat() + 'Z'
                    
                    url = 'https://api-seller.ozon.ru/v2/posting/fbo/list'
                    payload = {
                        "dir": "ASC",
                        "filter": {"since": date_from, "to": date_to, "status": ""},
                        "limit": 1000,
                        "offset": 0
                    }
                    
                    response = MarketplaceAPI._make_request_with_retry(
                        url, headers, json_data=payload, method='POST', timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get('result', {})
                        if isinstance(result, list):
                            postings = result
                        elif isinstance(result, dict):
                            postings = result.get('postings', [])
                        else:
                            postings = []
                        
                        if postings:
                            DataLoader._save_ozon_orders(token, postings, 'FBO', period_start, period_end)
                    
                    loaded += 1
                    token.data_loading_loaded_periods = loaded
                    token.data_loading_progress = int((loaded / token.data_loading_total_periods) * 100)
                    db.session.commit()
                
                except Exception as e:
                    loaded += 1
                    token.data_loading_loaded_periods = loaded
                    token.data_loading_progress = int((loaded / token.data_loading_total_periods) * 100)
                    db.session.commit()
            
            # Загружаем FBS продажи (те же данные что и заказы, но с фильтром по статусу)
            for period_start, period_end in periods:
                try:
                    date_from = period_start.isoformat() + 'Z'
                    date_to = period_end.isoformat() + 'Z'
                    
                    url = 'https://api-seller.ozon.ru/v3/posting/fbs/list'
                    payload = {
                        "dir": "ASC",
                        "filter": {"since": date_from, "to": date_to, "status": ""},
                        "limit": 1000,
                        "offset": 0
                    }
                    
                    response = MarketplaceAPI._make_request_with_retry(
                        url, headers, json_data=payload, method='POST', timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get('result', {})
                        if isinstance(result, list):
                            postings = result
                        elif isinstance(result, dict):
                            postings = result.get('postings', [])
                        else:
                            postings = []
                        
                        if postings:
                            DataLoader._save_ozon_sales(token, postings, 'FBS', period_start, period_end)
                    
                    loaded += 1
                    token.data_loading_loaded_periods = loaded
                    token.data_loading_progress = int((loaded / token.data_loading_total_periods) * 100)
                    db.session.commit()
                
                except Exception as e:
                    loaded += 1
                    token.data_loading_loaded_periods = loaded
                    token.data_loading_progress = int((loaded / token.data_loading_total_periods) * 100)
                    db.session.commit()
            
            # Загружаем FBO продажи
            for period_start, period_end in periods:
                try:
                    date_from = period_start.isoformat() + 'Z'
                    date_to = period_end.isoformat() + 'Z'
                    
                    url = 'https://api-seller.ozon.ru/v2/posting/fbo/list'
                    payload = {
                        "dir": "ASC",
                        "filter": {"since": date_from, "to": date_to, "status": ""},
                        "limit": 1000,
                        "offset": 0
                    }
                    
                    response = MarketplaceAPI._make_request_with_retry(
                        url, headers, json_data=payload, method='POST', timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get('result', {})
                        if isinstance(result, list):
                            postings = result
                        elif isinstance(result, dict):
                            postings = result.get('postings', [])
                        else:
                            postings = []
                        
                        if postings:
                            DataLoader._save_ozon_sales(token, postings, 'FBO', period_start, period_end)
                    
                    loaded += 1
                    token.data_loading_loaded_periods = loaded
                    token.data_loading_progress = int((loaded / token.data_loading_total_periods) * 100)
                    db.session.commit()
                
                except Exception as e:
                    loaded += 1
                    token.data_loading_loaded_periods = loaded
                    token.data_loading_progress = int((loaded / token.data_loading_total_periods) * 100)
                    db.session.commit()
            
            # Завершаем загрузку
            token.data_loading_status = 'completed'
            token.data_loading_progress = 100
            token.data_loading_completed_at = datetime.utcnow()
            db.session.commit()
            
        except Exception as e:
            token.data_loading_status = 'error'
            token.data_loading_error = str(e)
            token.data_loading_completed_at = datetime.utcnow()
            db.session.commit()
    
    @staticmethod
    def _save_wildberries_orders(token: Token, orders_data: List[Dict], period_start: datetime, period_end: datetime):
        """Сохранить заказы Wildberries в базу данных"""
        saved_count = 0
        for order_data in orders_data:
            try:
                order_date_str = order_data.get('date', '')
                if not order_date_str:
                    continue
                try:
                    if 'Z' in order_date_str:
                        order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00'))
                    else:
                        order_date = datetime.fromisoformat(order_date_str)
                    # Преобразуем в naive datetime для сравнения
                    if order_date.tzinfo is not None:
                        order_date = order_date.replace(tzinfo=None)
                except:
                    continue
                if order_date < period_start or order_date > period_end:
                    continue
                order_id = str(order_data.get('gNumber', '')) or str(order_data.get('srid', ''))
                if not order_id:
                    continue
                existing = Order.query.filter_by(token_id=token.id, order_id=order_id, marketplace='wildberries').first()
                if existing:
                    continue
                price = float(order_data.get('priceWithDisc', 0) or order_data.get('price', 0))
                price_with_discount = float(order_data.get('priceWithDisc', 0)) if order_data.get('priceWithDisc') else None
                finished_price = float(order_data.get('finishedPrice', 0)) if order_data.get('finishedPrice') else None
                order = Order(token_id=token.id, marketplace='wildberries', order_type=None, order_id=order_id, order_date=order_date, price=price, price_with_discount=price_with_discount, finished_price=finished_price)
                order.set_raw_data(order_data)
                db.session.add(order)
                saved_count += 1
                if saved_count % 100 == 0:
                    db.session.commit()
            except Exception:
                continue
        if saved_count % 100 != 0:
            db.session.commit()
    
    @staticmethod
    def _save_wildberries_sales(token: Token, sales_data: List[Dict], period_start: datetime, period_end: datetime):
        """Сохранить продажи Wildberries в базу данных"""
        saved_count = 0
        for sale_data in sales_data:
            try:
                sale_date_str = sale_data.get('date', '')
                if not sale_date_str:
                    continue
                try:
                    if 'Z' in sale_date_str:
                        sale_date = datetime.fromisoformat(sale_date_str.replace('Z', '+00:00'))
                    else:
                        sale_date = datetime.fromisoformat(sale_date_str)
                    # Преобразуем в naive datetime для сравнения
                    if sale_date.tzinfo is not None:
                        sale_date = sale_date.replace(tzinfo=None)
                except:
                    continue
                if sale_date < period_start or sale_date > period_end:
                    continue
                sale_id = str(sale_data.get('gNumber', '')) or str(sale_data.get('srid', ''))
                if not sale_id:
                    continue
                existing = Sale.query.filter_by(token_id=token.id, sale_id=sale_id, marketplace='wildberries').first()
                if existing:
                    continue
                price = float(sale_data.get('finishedPrice', 0) or sale_data.get('priceWithDisc', 0) or sale_data.get('price', 0))
                finished_price = float(sale_data.get('finishedPrice', 0)) if sale_data.get('finishedPrice') else None
                sale = Sale(token_id=token.id, marketplace='wildberries', sale_type=None, sale_id=sale_id, sale_date=sale_date, price=price, finished_price=finished_price)
                sale.set_raw_data(sale_data)
                db.session.add(sale)
                saved_count += 1
                if saved_count % 100 == 0:
                    db.session.commit()
            except Exception:
                continue
        if saved_count % 100 != 0:
            db.session.commit()
    
    @staticmethod
    def _save_ozon_orders(token: Token, postings: List[Dict], order_type: str, period_start: datetime, period_end: datetime):
        """Сохранить заказы Ozon в базу данных"""
        saved_count = 0
        for posting in postings:
            try:
                order_date_str = posting.get('in_process_at', '') or posting.get('created_at', '')
                if not order_date_str:
                    continue
                try:
                    if 'Z' in order_date_str:
                        order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00'))
                    else:
                        order_date = datetime.fromisoformat(order_date_str)
                    # Преобразуем в naive datetime для сравнения
                    if order_date.tzinfo is not None:
                        order_date = order_date.replace(tzinfo=None)
                except:
                    continue
                if order_date < period_start or order_date > period_end:
                    continue
                posting_number = posting.get('posting_number', '')
                order_id = posting.get('order_id', posting_number)
                if not order_id:
                    continue
                existing = Order.query.filter_by(token_id=token.id, order_id=str(order_id), marketplace='ozon', order_type=order_type).first()
                if existing:
                    continue
                financial_data = posting.get('financial_data', {})
                products = financial_data.get('products', [])
                total_price = 0.0
                for product in products:
                    total_price += float(product.get('price', 0))
                if total_price == 0:
                    products_direct = posting.get('products', [])
                    for product in products_direct:
                        price = float(product.get('price', 0))
                        quantity = int(product.get('quantity', 1))
                        total_price += price * quantity
                order = Order(token_id=token.id, marketplace='ozon', order_type=order_type, order_id=str(order_id), posting_number=posting_number, order_date=order_date, price=total_price)
                order.set_raw_data(posting)
                db.session.add(order)
                saved_count += 1
                if saved_count % 100 == 0:
                    db.session.commit()
            except Exception:
                continue
        if saved_count % 100 != 0:
            db.session.commit()
    
    @staticmethod
    def _save_ozon_sales(token: Token, postings: List[Dict], sale_type: str, period_start: datetime, period_end: datetime):
        """Сохранить продажи Ozon в базу данных"""
        saved_count = 0
        for posting in postings:
            try:
                status = posting.get('status', '')
                if status not in ['delivering', 'delivered', 'sent']:
                    continue
                sale_date_str = posting.get('in_process_at', '') or posting.get('created_at', '')
                if not sale_date_str:
                    continue
                try:
                    if 'Z' in sale_date_str:
                        sale_date = datetime.fromisoformat(sale_date_str.replace('Z', '+00:00'))
                    else:
                        sale_date = datetime.fromisoformat(sale_date_str)
                    # Преобразуем в naive datetime для сравнения
                    if sale_date.tzinfo is not None:
                        sale_date = sale_date.replace(tzinfo=None)
                except:
                    continue
                if sale_date < period_start or sale_date > period_end:
                    continue
                posting_number = posting.get('posting_number', '')
                sale_id = posting.get('order_id', posting_number)
                if not sale_id:
                    continue
                existing = Sale.query.filter_by(token_id=token.id, sale_id=str(sale_id), marketplace='ozon', sale_type=sale_type).first()
                if existing:
                    continue
                financial_data = posting.get('financial_data', {})
                products = financial_data.get('products', [])
                total_price = 0.0
                for product in products:
                    total_price += float(product.get('price', 0))
                if total_price == 0:
                    products_direct = posting.get('products', [])
                    for product in products_direct:
                        price = float(product.get('price', 0))
                        quantity = int(product.get('quantity', 1))
                        total_price += price * quantity
                sale = Sale(token_id=token.id, marketplace='ozon', sale_type=sale_type, sale_id=str(sale_id), posting_number=posting_number, sale_date=sale_date, price=total_price)
                sale.set_raw_data(posting)
                db.session.add(sale)
                saved_count += 1
                if saved_count % 100 == 0:
                    db.session.commit()
            except Exception:
                continue
        if saved_count % 100 != 0:
            db.session.commit()
