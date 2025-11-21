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

