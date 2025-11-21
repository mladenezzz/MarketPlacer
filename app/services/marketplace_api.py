"""Сервис для работы с API маркетплейсов"""
from typing import Dict, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
import time

try:
    import requests
except ImportError:
    requests = None  # type: ignore

if TYPE_CHECKING:
    from app.models.token import Token


class MarketplaceAPI:
    """Класс для работы с API различных маркетплейсов"""
    
    # Минимальная задержка между запросами (в секундах) для rate limiting
    MIN_REQUEST_DELAY = 0.5
    # Максимальное количество попыток при ошибке 429
    MAX_RETRIES = 3
    # Базовая задержка для экспоненциального backoff (в секундах)
    BASE_RETRY_DELAY = 2
    
    @staticmethod
    def _make_request_with_retry(url: str, headers: Dict, params: Optional[Dict] = None, 
                                  method: str = 'GET', json_data: Optional[Dict] = None,
                                  timeout: int = 10) -> requests.Response:
        """
        Выполнить HTTP запрос с обработкой ошибки 429 и retry логикой
        
        Args:
            url: URL для запроса
            headers: Заголовки запроса
            params: Параметры запроса (для GET)
            method: HTTP метод ('GET' или 'POST')
            json_data: JSON данные для POST запроса
            timeout: Таймаут запроса в секундах
            
        Returns:
            Response объект requests
            
        Raises:
            requests.RequestException: При превышении количества попыток
        """
        last_request_time = [0]  # Используем список для изменения в замыкании
        
        def _wait_for_rate_limit():
            """Ожидание для соблюдения rate limit"""
            current_time = time.time()
            time_since_last_request = current_time - last_request_time[0]
            if time_since_last_request < MarketplaceAPI.MIN_REQUEST_DELAY:
                sleep_time = MarketplaceAPI.MIN_REQUEST_DELAY - time_since_last_request
                time.sleep(sleep_time)
            last_request_time[0] = time.time()
        
        response = None
        for attempt in range(MarketplaceAPI.MAX_RETRIES + 1):
            # Соблюдаем rate limiting
            _wait_for_rate_limit()
            
            try:
                if method.upper() == 'GET':
                    response = requests.get(url, headers=headers, params=params, timeout=timeout)
                elif method.upper() == 'POST':
                    response = requests.post(url, headers=headers, json=json_data, timeout=timeout)
                else:
                    raise ValueError(f"Неподдерживаемый HTTP метод: {method}")
                
                # Если успешный ответ или ошибка не 429, возвращаем сразу
                if response.status_code != 429:
                    return response
                
                # Обработка ошибки 429 (Too Many Requests)
                if attempt < MarketplaceAPI.MAX_RETRIES:
                    # Пытаемся получить Retry-After из заголовков
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            wait_time = int(retry_after)
                        except ValueError:
                            # Если Retry-After не число, используем экспоненциальный backoff
                            wait_time = MarketplaceAPI.BASE_RETRY_DELAY * (2 ** attempt)
                    else:
                        # Экспоненциальный backoff: 2, 4, 8 секунд
                        wait_time = MarketplaceAPI.BASE_RETRY_DELAY * (2 ** attempt)
                    
                    # Ждем перед следующей попыткой
                    time.sleep(wait_time)
                    continue
                else:
                    # Превышено количество попыток
                    return response
                    
            except requests.Timeout:
                if attempt < MarketplaceAPI.MAX_RETRIES:
                    # При таймауте также используем экспоненциальный backoff
                    wait_time = MarketplaceAPI.BASE_RETRY_DELAY * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        
        # Если дошли сюда, значит все попытки исчерпаны
        # Возвращаем последний response (должен быть 429) или создаем фиктивный
        if response is None:
            # Создаем фиктивный response объект для случая, когда все попытки провалились
            class FakeResponse:
                status_code = 429
                headers = {}
            response = FakeResponse()
        return response
    
    @staticmethod
    def get_today_orders_total(token: 'Token') -> Dict:
        """
        Получить сумму заказов на сегодня для токена
        
        Args:
            token: объект токена из базы данных
            
        Returns:
            Dict с информацией о заказах:
            {
                'success': bool,
                'total': float,  # сумма заказов
                'count': int,    # количество заказов
                'error': str     # сообщение об ошибке (если success=False)
            }
        """
        if token.marketplace == 'wildberries':
            return MarketplaceAPI._get_wildberries_orders(token)
        elif token.marketplace == 'ozon':
            return MarketplaceAPI._get_ozon_orders(token)
        elif token.marketplace == 'telegram':
            return {
                'success': True,
                'total': 0.0,
                'count': 0,
                'error': 'Telegram не поддерживает получение заказов'
            }
        else:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': 'Неизвестный маркетплейс'
            }
    
    @staticmethod
    def _get_wildberries_orders(token: 'Token') -> Dict:
        """
        Получить заказы Wildberries на сегодня
        
        API документация: https://openapi.wildberries.ru/
        Endpoint: GET /api/v1/supplier/orders
        
        Ограничения API:
        - Параметр dateTo не поддерживается - API возвращает все данные от dateFrom до текущего момента
        - Данные доступны до 6 месяцев назад от текущей даты
        - Рекомендуется не запрашивать данные старше 6 месяцев
        - При запросе за большой период API может вернуть очень большой объем данных
        """
        try:
            # Получаем начало и конец сегодняшнего дня
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Форматируем даты для API WB (RFC3339)
            date_from = today_start.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            date_to = today_end.strftime('%Y-%m-%dT%H:%M:%S.999Z')
            
            headers = {
                'Authorization': token.token,
                'Content-Type': 'application/json'
            }
            
            # API endpoint для получения заказов
            url = 'https://statistics-api.wildberries.ru/api/v1/supplier/orders'
            params = {
                'dateFrom': date_from,
                'flag': 0  # 0 - все заказы
            }
            
            response = MarketplaceAPI._make_request_with_retry(
                url, headers, params=params, method='GET', timeout=10
            )
            
            if response.status_code == 200:
                orders = response.json()
                
                # Фильтруем заказы по дате (только сегодняшние)
                today_orders = []
                for order in orders:
                    order_date_str = order.get('date', '')
                    if order_date_str:
                        try:
                            # Парсим дату заказа (может быть без таймзоны)
                            if 'Z' in order_date_str:
                                order_date = datetime.fromisoformat(order_date_str.replace('Z', '+00:00'))
                            else:
                                order_date = datetime.fromisoformat(order_date_str)
                            
                            # Сравниваем только дату, без времени
                            if order_date.date() == today_start.date():
                                today_orders.append(order)
                        except:
                            continue
                
                # Подсчитываем сумму по priceWithDisc (цена для покупателя со скидкой)
                # Это реальная сумма заказов, которую платят покупатели
                total = sum(float(order.get('priceWithDisc', 0)) for order in today_orders)
                
                return {
                    'success': True,
                    'total': total,
                    'count': len(today_orders),
                    'error': None
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': 'Неверный токен авторизации'
                }
            elif response.status_code == 429:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': 'Превышен лимит запросов к API. Попробуйте позже.'
                }
            else:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': f'Ошибка API: {response.status_code}'
                }
                
        except requests.Timeout:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': 'Превышено время ожидания ответа'
            }
        except requests.RequestException as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка соединения: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Непредвиденная ошибка: {str(e)}'
            }
    
    @staticmethod
    def _get_ozon_orders(token: 'Token') -> Dict:
        """
        Получить заказы Ozon на сегодня
        
        API документация: https://docs.ozon.ru/api/seller/
        Получает заказы из FBS (продавец отправляет) и FBO (Ozon отправляет)
        
        Ограничения API:
        - Максимальный период в одном запросе: до 30 дней
        - Данные доступны до 3-6 месяцев назад (зависит от типа данных)
        - Для периодов больше 30 дней нужно делать несколько запросов
        - Максимум 1000 записей в одном ответе (требуется пагинация для больших периодов)
        """
        try:
            if not token.client_id:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': 'Не указан Client-Id для Ozon'
                }
            
            # Получаем начало и конец сегодняшнего дня
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Форматируем даты для API Ozon (ISO 8601)
            date_from = today_start.isoformat() + 'Z'
            date_to = today_end.isoformat() + 'Z'
            
            headers = {
                'Client-Id': token.client_id,
                'Api-Key': token.token,
                'Content-Type': 'application/json'
            }
            
            total_sum = 0.0
            total_count = 0
            errors = []
            
            # Получаем заказы из обоих типов: FBS и FBO
            endpoints = [
                ('https://api-seller.ozon.ru/v3/posting/fbs/list', 'FBS'),
                ('https://api-seller.ozon.ru/v2/posting/fbo/list', 'FBO')
            ]
            
            for url, scheme_type in endpoints:
                payload = {
                    "dir": "ASC",
                    "filter": {
                        "since": date_from,
                        "to": date_to,
                        "status": ""
                    },
                    "limit": 1000,
                    "offset": 0,
                    "with": {
                        "analytics_data": True,
                        "financial_data": True
                    }
                }
                
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get('result', {})
                        
                        # FBO v2 может возвращать result как список, а FBS v3 как dict с postings
                        if isinstance(result, list):
                            postings = result
                        elif isinstance(result, dict):
                            postings = result.get('postings', [])
                        else:
                            postings = []
                        
                        # Подсчитываем сумму
                        for posting in postings:
                            # Получаем финансовые данные
                            financial_data = posting.get('financial_data', {})
                            products = financial_data.get('products', [])
                            
                            # Суммируем стоимость всех товаров в заказе
                            # В Ozon API price уже в рублях (не в копейках)
                            for product in products:
                                # Используем price - стоимость товара для покупателя
                                price = float(product.get('price', 0))
                                total_sum += price
                        
                        total_count += len(postings)
                    elif response.status_code == 401:
                        errors.append(f'{scheme_type}: Неверный API ключ или Client-Id')
                    else:
                        errors.append(f'{scheme_type}: Ошибка API {response.status_code}')
                except Exception as e:
                    errors.append(f'{scheme_type}: {str(e)}')
            
            # Если есть данные, считаем успешным
            if total_count > 0 or not errors:
                return {
                    'success': True,
                    'total': total_sum,
                    'count': total_count,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': '; '.join(errors) if errors else 'Нет данных'
                }
                
        except requests.Timeout:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': 'Превышено время ожидания ответа'
            }
        except requests.RequestException as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка соединения: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Непредвиденная ошибка: {str(e)}'
            }
    
    @staticmethod
    def get_today_sales_total(token: 'Token') -> Dict:
        """
        Получить сумму продаж на сегодня для токена
        
        Args:
            token: объект токена из базы данных
            
        Returns:
            Dict с информацией о продажах:
            {
                'success': bool,
                'total': float,  # сумма продаж
                'count': int,    # количество продаж
                'error': str     # сообщение об ошибке (если success=False)
            }
        """
        if token.marketplace == 'wildberries':
            return MarketplaceAPI._get_wildberries_sales(token)
        elif token.marketplace == 'ozon':
            return MarketplaceAPI._get_ozon_sales(token)
        elif token.marketplace == 'telegram':
            return {
                'success': True,
                'total': 0.0,
                'count': 0,
                'error': 'Telegram не поддерживает получение продаж'
            }
        else:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': 'Неизвестный маркетплейс'
            }
    
    @staticmethod
    def _get_wildberries_sales(token: 'Token') -> Dict:
        """
        Получить продажи Wildberries на сегодня
        
        API документация: https://openapi.wildberries.ru/
        Endpoint: GET /api/v1/supplier/sales
        
        Ограничения API:
        - Параметр dateTo не поддерживается - API возвращает все данные от dateFrom до текущего момента
        - Данные доступны до 6 месяцев назад от текущей даты
        - Рекомендуется не запрашивать данные старше 6 месяцев
        - При запросе за большой период API может вернуть очень большой объем данных
        """
        try:
            # Получаем начало и конец сегодняшнего дня
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Форматируем даты для API WB (RFC3339)
            date_from = today_start.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            headers = {
                'Authorization': token.token,
                'Content-Type': 'application/json'
            }
            
            # API endpoint для получения продаж
            url = 'https://statistics-api.wildberries.ru/api/v1/supplier/sales'
            params = {
                'dateFrom': date_from,
                'flag': 0  # 0 - все продажи
            }
            
            response = MarketplaceAPI._make_request_with_retry(
                url, headers, params=params, method='GET', timeout=10
            )
            
            if response.status_code == 200:
                sales = response.json()
                
                # Фильтруем продажи по дате (только сегодняшние)
                today_sales = []
                for sale in sales:
                    sale_date_str = sale.get('date', '')
                    if sale_date_str:
                        try:
                            # Парсим дату продажи
                            if 'Z' in sale_date_str:
                                sale_date = datetime.fromisoformat(sale_date_str.replace('Z', '+00:00'))
                            else:
                                sale_date = datetime.fromisoformat(sale_date_str)
                            
                            # Сравниваем только дату, без времени
                            if sale_date.date() == today_start.date():
                                today_sales.append(sale)
                        except:
                            continue
                
                # Подсчитываем сумму по finishedPrice (итоговая цена продажи для продавца)
                total = sum(float(sale.get('finishedPrice', 0)) for sale in today_sales)
                
                return {
                    'success': True,
                    'total': total,
                    'count': len(today_sales),
                    'error': None
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': 'Неверный токен авторизации'
                }
            elif response.status_code == 429:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': 'Превышен лимит запросов к API. Попробуйте позже.'
                }
            else:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': f'Ошибка API: {response.status_code}'
                }
                
        except requests.Timeout:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': 'Превышено время ожидания ответа'
            }
        except requests.RequestException as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка соединения: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Непредвиденная ошибка: {str(e)}'
            }
    
    @staticmethod
    def _get_ozon_sales(token: 'Token') -> Dict:
        """
        Получить продажи (реализацию) Ozon на сегодня
        
        API документация: https://docs.ozon.ru/api/seller/
        Использует те же данные что и для заказов - отправленные сегодня заказы = продажи
        
        Ограничения API:
        - Максимальный период в одном запросе: до 30 дней
        - Данные доступны до 3-6 месяцев назад (зависит от типа данных)
        - Для периодов больше 30 дней нужно делать несколько запросов
        - Максимум 1000 записей в одном ответе (требуется пагинация для больших периодов)
        """
        try:
            if not token.client_id:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': 'Не указан Client-Id для Ozon'
                }
            
            # Получаем начало и конец сегодняшнего дня
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = datetime.now().replace(hour=23, minute=59, second=59, microsecond=999999)
            
            # Форматируем даты для API Ozon (ISO 8601)
            date_from = today_start.isoformat() + 'Z'
            date_to = today_end.isoformat() + 'Z'
            
            headers = {
                'Client-Id': token.client_id,
                'Api-Key': token.token,
                'Content-Type': 'application/json'
            }
            
            total_sum = 0.0
            total_count = 0
            errors = []
            
            # Получаем отправленные заказы (продажи) из обоих типов: FBS и FBO
            # Используем статус "delivering" - товар в пути к покупателю = продажа состоялась
            endpoints = [
                ('https://api-seller.ozon.ru/v3/posting/fbs/list', 'FBS'),
                ('https://api-seller.ozon.ru/v2/posting/fbo/list', 'FBO')
            ]
            
            for url, scheme_type in endpoints:
                payload = {
                    "dir": "ASC",
                    "filter": {
                        "since": date_from,
                        "to": date_to,
                        "status": ""
                    },
                    "limit": 1000,
                    "offset": 0,
                    "with": {
                        "analytics_data": True,
                        "financial_data": True
                    }
                }
                
                try:
                    response = requests.post(url, headers=headers, json=payload, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        result = data.get('result', {})
                        
                        # FBO v2 может возвращать result как список, а FBS v3 как dict с postings
                        if isinstance(result, list):
                            postings = result
                        elif isinstance(result, dict):
                            postings = result.get('postings', [])
                        else:
                            postings = []
                        
                        # Подсчитываем сумму продаж
                        # Считаем продажами: delivering (в доставке) и delivered (доставлен)
                        for posting in postings:
                            status = posting.get('status', '')
                            
                            # Пропускаем заказы в обработке, отмененные и т.д.
                            if status not in ['delivering', 'delivered', 'sent']:
                                continue
                            
                            # Получаем финансовые данные
                            financial_data = posting.get('financial_data', {})
                            products = financial_data.get('products', [])
                            
                            if products:
                                for product in products:
                                    try:
                                        price = float(product.get('price', 0))
                                        if price > 0:
                                            total_sum += price
                                    except (ValueError, TypeError):
                                        pass
                            else:
                                # Если нет financial_data, берем из products
                                products = posting.get('products', [])
                                for product in products:
                                    try:
                                        price = float(product.get('price', 0))
                                        quantity = int(product.get('quantity', 1))
                                        if price > 0:
                                            total_sum += price * quantity
                                    except (ValueError, TypeError):
                                        pass
                        
                        # Считаем количество постингов со статусами продаж
                        total_count += len([p for p in postings if p.get('status', '') in ['delivering', 'delivered', 'sent']])
                        
                    elif response.status_code == 401:
                        errors.append(f'{scheme_type}: Неверный API ключ или Client-Id')
                    else:
                        errors.append(f'{scheme_type}: Ошибка API {response.status_code}')
                except Exception as e:
                    errors.append(f'{scheme_type}: {str(e)}')
            
            # Если есть хоть какие-то данные или нет ошибок, считаем успешным
            if total_count > 0 or total_sum > 0 or not errors:
                return {
                    'success': True,
                    'total': total_sum,
                    'count': total_count,
                    'error': None
                }
            else:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': '; '.join(errors) if errors else 'Нет данных'
                }
                
        except requests.Timeout:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': 'Превышено время ожидания ответа'
            }
        except requests.RequestException as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка соединения: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Непредвиденная ошибка: {str(e)}'
            }

