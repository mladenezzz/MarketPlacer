"""Сервис для работы с API маркетплейсов"""
from typing import Dict, Optional, TYPE_CHECKING
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    requests = None  # type: ignore

if TYPE_CHECKING:
    from app.models.token import Token


class MarketplaceAPI:
    """Класс для работы с API различных маркетплейсов"""
    
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
        Endpoint: GET /api/v3/orders
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
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
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
                # Значение в копейках, поэтому делим на 100
                total = sum(float(order.get('priceWithDisc', 0))  for order in today_orders)
                
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

