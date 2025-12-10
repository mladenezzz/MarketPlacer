"""Сервис для получения данных о продажах и заказах из базы данных"""
from typing import Dict
from datetime import datetime
from sqlalchemy import func
from app.models import db, WBSale, WBOrder, OzonSale, OzonOrder, Token


class SalesService:
    """Класс для работы с данными о продажах из базы данных"""

    @staticmethod
    def get_today_sales_by_token(token_id: int) -> Dict:
        """
        Получить данные о продажах на сегодня для конкретного токена из базы данных

        Args:
            token_id: ID токена

        Returns:
            Dict с информацией о продажах:
            {
                'success': bool,
                'total': float,  # сумма продаж
                'count': int,    # количество продаж
                'error': str     # сообщение об ошибке (если success=False)
            }
        """
        try:
            # Получаем токен
            token = Token.query.get(token_id)
            if not token:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': 'Токен не найден'
                }

            # Получаем начало сегодняшнего дня
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if token.marketplace == 'wildberries':
                return SalesService._get_wb_sales_today(token_id, today_start)
            elif token.marketplace == 'ozon':
                return SalesService._get_ozon_sales_today(token_id, today_start)
            else:
                return {
                    'success': True,
                    'total': 0.0,
                    'count': 0,
                    'error': f'{token.marketplace} не поддерживается'
                }

        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка при получении данных: {str(e)}'
            }

    @staticmethod
    def _get_wb_sales_today(token_id: int, today_start: datetime) -> Dict:
        """Получить продажи Wildberries на сегодня из базы данных"""
        try:
            # Запрос к таблице wb_sales
            # Используем finished_price - цена с учетом всех скидок (финальная цена для покупателя)
            sales_query = db.session.query(
                func.count(WBSale.id).label('count'),
                func.sum(WBSale.finished_price).label('total')
            ).filter(
                WBSale.token_id == token_id,
                WBSale.date >= today_start
            ).first()

            count = sales_query.count or 0
            total = float(sales_query.total or 0.0)

            return {
                'success': True,
                'total': total,
                'count': count,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка БД Wildberries: {str(e)}'
            }

    @staticmethod
    def _get_ozon_sales_today(token_id: int, today_start: datetime) -> Dict:
        """Получить продажи Ozon на сегодня из базы данных (из таблицы ozon_sales с данными finance API)"""
        try:
            # Количество продаж - только OperationAgentDeliveredToCustomer
            count_query = db.session.query(
                func.count(OzonSale.id).label('count')
            ).filter(
                OzonSale.token_id == token_id,
                OzonSale.operation_date >= today_start,
                OzonSale.operation_type == 'OperationAgentDeliveredToCustomer'
            ).first()

            # Сумма - по всем операциям (amount с учётом знака)
            total_query = db.session.query(
                func.sum(OzonSale.amount).label('total')
            ).filter(
                OzonSale.token_id == token_id,
                OzonSale.operation_date >= today_start
            ).first()

            count = count_query.count or 0
            total = float(total_query.total or 0.0)

            return {
                'success': True,
                'total': total,
                'count': count,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка БД Ozon: {str(e)}'
            }

    @staticmethod
    def get_all_sales_today() -> Dict:
        """
        Получить агрегированные данные о продажах на сегодня для всех активных токенов

        Returns:
            Dict с агрегированной информацией:
            {
                'success': bool,
                'total_sum': float,
                'total_count': int,
                'tokens': [
                    {
                        'token_id': int,
                        'token_name': str,
                        'marketplace': str,
                        'total': float,
                        'count': int
                    },
                    ...
                ],
                'error': str
            }
        """
        try:
            # Получаем все активные токены
            tokens = Token.query.filter_by(is_active=True).all()

            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            tokens_data = []
            total_sum = 0.0
            total_count = 0

            for token in tokens:
                if token.marketplace not in ['wildberries', 'ozon']:
                    continue

                # Получаем данные для каждого токена
                token_sales = SalesService.get_today_sales_by_token(token.id)

                if token_sales['success']:
                    total_sum += token_sales['total']
                    total_count += token_sales['count']

                    tokens_data.append({
                        'token_id': token.id,
                        'token_name': token.name or token.get_marketplace_display(),
                        'marketplace': token.get_marketplace_display(),
                        'total': token_sales['total'],
                        'count': token_sales['count']
                    })

            return {
                'success': True,
                'total_sum': total_sum,
                'total_count': total_count,
                'tokens': tokens_data,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'total_sum': 0.0,
                'total_count': 0,
                'tokens': [],
                'error': f'Ошибка при получении данных: {str(e)}'
            }

    @staticmethod
    def get_today_orders_by_token(token_id: int) -> Dict:
        """
        Получить данные о заказах на сегодня для конкретного токена из базы данных

        Args:
            token_id: ID токена

        Returns:
            Dict с информацией о заказах:
            {
                'success': bool,
                'total': float,  # сумма заказов
                'count': int,    # количество заказов
                'error': str     # сообщение об ошибке (если success=False)
            }
        """
        try:
            # Получаем токен
            token = Token.query.get(token_id)
            if not token:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': 'Токен не найден'
                }

            # Получаем начало сегодняшнего дня
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            if token.marketplace == 'wildberries':
                return SalesService._get_wb_orders_today(token_id, today_start)
            elif token.marketplace == 'ozon':
                return SalesService._get_ozon_orders_today(token_id, today_start)
            else:
                return {
                    'success': True,
                    'total': 0.0,
                    'count': 0,
                    'error': f'{token.marketplace} не поддерживается'
                }

        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка при получении данных: {str(e)}'
            }

    @staticmethod
    def _get_ozon_orders_today(token_id: int, today_start: datetime) -> Dict:
        """Получить заказы Ozon на сегодня из таблицы ozon_orders"""
        try:
            # Запрос к таблице ozon_orders (постинги FBS/FBO)
            # Используем in_process_at - дата оформления заказа
            orders_query = db.session.query(
                func.count(OzonOrder.id).label('count'),
                func.sum(OzonOrder.price).label('total')
            ).filter(
                OzonOrder.token_id == token_id,
                OzonOrder.in_process_at >= today_start
            ).first()

            count = orders_query.count or 0
            total = float(orders_query.total or 0.0)

            return {
                'success': True,
                'total': total,
                'count': count,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка БД Ozon: {str(e)}'
            }

    @staticmethod
    def _get_wb_orders_today(token_id: int, today_start: datetime) -> Dict:
        """Получить заказы Wildberries на сегодня из таблицы wb_orders"""
        try:
            # Запрос к таблице wb_orders
            # Используем price_with_disc - цена со скидкой WB (до вычета СПП)
            orders_query = db.session.query(
                func.count(WBOrder.id).label('count'),
                func.sum(WBOrder.price_with_disc).label('total')
            ).filter(
                WBOrder.token_id == token_id,
                WBOrder.date >= today_start
            ).first()

            count = orders_query.count or 0
            total = float(orders_query.total or 0.0)

            return {
                'success': True,
                'total': total,
                'count': count,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка БД Wildberries: {str(e)}'
            }

    @staticmethod
    def get_orders_by_date_range(token_id: int, date_from: datetime, date_to: datetime) -> Dict:
        """
        Получить данные о заказах за период для конкретного токена

        Args:
            token_id: ID токена
            date_from: Начальная дата (включительно)
            date_to: Конечная дата (включительно)

        Returns:
            Dict с информацией о заказах за период
        """
        try:
            token = Token.query.get(token_id)
            if not token:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': 'Токен не найден'
                }

            # Устанавливаем время для дат
            date_from_start = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
            date_to_end = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)

            if token.marketplace == 'wildberries':
                return SalesService._get_wb_orders_by_range(token_id, date_from_start, date_to_end)
            elif token.marketplace == 'ozon':
                return SalesService._get_ozon_orders_by_range(token_id, date_from_start, date_to_end)
            else:
                return {
                    'success': True,
                    'total': 0.0,
                    'count': 0,
                    'error': f'{token.marketplace} не поддерживается'
                }

        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка при получении данных: {str(e)}'
            }

    @staticmethod
    def get_sales_by_date_range(token_id: int, date_from: datetime, date_to: datetime) -> Dict:
        """
        Получить данные о продажах за период для конкретного токена

        Args:
            token_id: ID токена
            date_from: Начальная дата (включительно)
            date_to: Конечная дата (включительно)

        Returns:
            Dict с информацией о продажах за период
        """
        try:
            token = Token.query.get(token_id)
            if not token:
                return {
                    'success': False,
                    'total': 0.0,
                    'count': 0,
                    'error': 'Токен не найден'
                }

            # Устанавливаем время для дат
            date_from_start = date_from.replace(hour=0, minute=0, second=0, microsecond=0)
            date_to_end = date_to.replace(hour=23, minute=59, second=59, microsecond=999999)

            if token.marketplace == 'wildberries':
                return SalesService._get_wb_sales_by_range(token_id, date_from_start, date_to_end)
            elif token.marketplace == 'ozon':
                return SalesService._get_ozon_sales_by_range(token_id, date_from_start, date_to_end)
            else:
                return {
                    'success': True,
                    'total': 0.0,
                    'count': 0,
                    'error': f'{token.marketplace} не поддерживается'
                }

        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка при получении данных: {str(e)}'
            }

    @staticmethod
    def _get_wb_orders_by_range(token_id: int, date_from: datetime, date_to: datetime) -> Dict:
        """Получить заказы Wildberries за период из таблицы wb_orders"""
        try:
            orders_query = db.session.query(
                func.count(WBOrder.id).label('count'),
                func.sum(WBOrder.price_with_disc).label('total')
            ).filter(
                WBOrder.token_id == token_id,
                WBOrder.date >= date_from,
                WBOrder.date <= date_to
            ).first()

            count = orders_query.count or 0
            total = float(orders_query.total or 0.0)

            return {
                'success': True,
                'total': total,
                'count': count,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка БД Wildberries: {str(e)}'
            }

    @staticmethod
    def _get_wb_sales_by_range(token_id: int, date_from: datetime, date_to: datetime) -> Dict:
        """Получить продажи Wildberries за период из таблицы wb_sales"""
        try:
            sales_query = db.session.query(
                func.count(WBSale.id).label('count'),
                func.sum(WBSale.finished_price).label('total')
            ).filter(
                WBSale.token_id == token_id,
                WBSale.date >= date_from,
                WBSale.date <= date_to
            ).first()

            count = sales_query.count or 0
            total = float(sales_query.total or 0.0)

            return {
                'success': True,
                'total': total,
                'count': count,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка БД Wildberries: {str(e)}'
            }

    @staticmethod
    def _get_ozon_orders_by_range(token_id: int, date_from: datetime, date_to: datetime) -> Dict:
        """Получить заказы Ozon за период из таблицы ozon_orders"""
        try:
            orders_query = db.session.query(
                func.count(OzonOrder.id).label('count'),
                func.sum(OzonOrder.price).label('total')
            ).filter(
                OzonOrder.token_id == token_id,
                OzonOrder.in_process_at >= date_from,
                OzonOrder.in_process_at <= date_to
            ).first()

            count = orders_query.count or 0
            total = float(orders_query.total or 0.0)

            return {
                'success': True,
                'total': total,
                'count': count,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка БД Ozon: {str(e)}'
            }

    @staticmethod
    def _get_ozon_sales_by_range(token_id: int, date_from: datetime, date_to: datetime) -> Dict:
        """Получить продажи Ozon за период из таблицы ozon_sales (finance API)"""
        try:
            # Количество продаж - только OperationAgentDeliveredToCustomer
            count_query = db.session.query(
                func.count(OzonSale.id).label('count')
            ).filter(
                OzonSale.token_id == token_id,
                OzonSale.operation_date >= date_from,
                OzonSale.operation_date <= date_to,
                OzonSale.operation_type == 'OperationAgentDeliveredToCustomer'
            ).first()

            # Сумма - по всем операциям (amount с учётом знака)
            total_query = db.session.query(
                func.sum(OzonSale.amount).label('total')
            ).filter(
                OzonSale.token_id == token_id,
                OzonSale.operation_date >= date_from,
                OzonSale.operation_date <= date_to
            ).first()

            count = count_query.count or 0
            total = float(total_query.total or 0.0)

            return {
                'success': True,
                'total': total,
                'count': count,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'total': 0.0,
                'count': 0,
                'error': f'Ошибка БД Ozon: {str(e)}'
            }

    @staticmethod
    def get_events_feed(limit: int = 50) -> Dict:
        """
        Получить ленту событий (заказы и продажи) со всех маркетплейсов за сегодня.
        События отсортированы по дате (новые сверху).

        Args:
            limit: Максимальное количество событий

        Returns:
            Dict с событиями
        """
        from app.models.wildberries import WBOrder, WBSale

        try:
            # Получаем начало сегодняшнего дня
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # Получаем все активные токены WB и Ozon
            tokens = Token.query.filter(
                Token.is_active == True,
                Token.marketplace.in_(['wildberries', 'ozon'])
            ).all()

            if not tokens:
                return {
                    'success': True,
                    'events': [],
                    'error': None
                }

            # Создаём словарь токенов для быстрого доступа
            tokens_map = {t.id: {'name': t.name or t.get_marketplace_display(), 'marketplace': t.marketplace} for t in tokens}
            token_ids = list(tokens_map.keys())

            events = []

            # Получаем заказы WB за сегодня
            wb_orders = db.session.query(
                WBOrder.id,
                WBOrder.date,
                WBOrder.price_with_disc,
                WBOrder.supplier_article,
                WBOrder.tech_size,
                WBOrder.token_id
            ).filter(
                WBOrder.token_id.in_(token_ids),
                WBOrder.date >= today_start
            ).order_by(WBOrder.date.desc()).limit(limit).all()

            for order in wb_orders:
                token_info = tokens_map.get(order.token_id, {})
                events.append({
                    'id': f'wb_order_{order.id}',
                    'type': 'order',
                    'marketplace': 'wildberries',
                    'token_name': token_info.get('name', 'Неизвестно'),
                    'date': order.date.isoformat() if order.date else None,
                    'price': float(order.price_with_disc or 0),
                    'article': order.supplier_article or '',
                    'size': order.tech_size or ''
                })

            # Получаем продажи WB за сегодня (с джойном на Product для получения артикула)
            from app.models.product import Product
            from app.models.wildberries import WBGood

            wb_sales = db.session.query(
                WBSale.id,
                WBSale.date,
                WBSale.finished_price,
                WBSale.token_id,
                Product.article,
                WBGood.tech_size
            ).outerjoin(
                Product, WBSale.product_id == Product.id
            ).outerjoin(
                WBGood, Product.barcode == WBGood.barcode
            ).filter(
                WBSale.token_id.in_(token_ids),
                WBSale.date >= today_start
            ).order_by(WBSale.date.desc()).limit(limit).all()

            for sale in wb_sales:
                token_info = tokens_map.get(sale.token_id, {})
                events.append({
                    'id': f'wb_sale_{sale.id}',
                    'type': 'sale',
                    'marketplace': 'wildberries',
                    'token_name': token_info.get('name', 'Неизвестно'),
                    'date': sale.date.isoformat() if sale.date else None,
                    'price': float(sale.finished_price or 0),
                    'article': sale.article or '',
                    'size': sale.tech_size or ''
                })

            # Получаем заказы Ozon за сегодня
            ozon_orders = db.session.query(
                OzonOrder.id,
                OzonOrder.in_process_at,
                OzonOrder.price,
                OzonOrder.offer_id,
                OzonOrder.token_id
            ).filter(
                OzonOrder.token_id.in_(token_ids),
                OzonOrder.in_process_at >= today_start
            ).order_by(OzonOrder.in_process_at.desc()).limit(limit).all()

            for order in ozon_orders:
                token_info = tokens_map.get(order.token_id, {})
                # Парсим offer_id для получения артикула и размера (формат: артикул/размер)
                article, size = '', ''
                if order.offer_id:
                    parts = order.offer_id.split('/')
                    article = parts[0] if parts else ''
                    size = parts[1] if len(parts) > 1 else ''
                events.append({
                    'id': f'ozon_order_{order.id}',
                    'type': 'order',
                    'marketplace': 'ozon',
                    'token_name': token_info.get('name', 'Неизвестно'),
                    'date': order.in_process_at.isoformat() if order.in_process_at else None,
                    'price': float(order.price or 0),
                    'article': article,
                    'size': size
                })

            # Получаем продажи Ozon за сегодня (только OperationAgentDeliveredToCustomer)
            ozon_sales = db.session.query(
                OzonSale.id,
                OzonSale.operation_date,
                OzonSale.accruals_for_sale,
                OzonSale.offer_id,
                OzonSale.token_id
            ).filter(
                OzonSale.token_id.in_(token_ids),
                OzonSale.operation_type == 'OperationAgentDeliveredToCustomer',
                OzonSale.operation_date >= today_start
            ).order_by(OzonSale.operation_date.desc()).limit(limit).all()

            for sale in ozon_sales:
                token_info = tokens_map.get(sale.token_id, {})
                # Парсим offer_id для получения артикула и размера (формат: артикул/размер)
                article, size = '', ''
                if sale.offer_id:
                    parts = sale.offer_id.split('/')
                    article = parts[0] if parts else ''
                    size = parts[1] if len(parts) > 1 else ''
                events.append({
                    'id': f'ozon_sale_{sale.id}',
                    'type': 'sale',
                    'marketplace': 'ozon',
                    'token_name': token_info.get('name', 'Неизвестно'),
                    'date': sale.operation_date.isoformat() if sale.operation_date else None,
                    'price': float(sale.accruals_for_sale or 0),
                    'article': article,
                    'size': size
                })

            # Сортируем все события по дате (новые сверху)
            events.sort(key=lambda x: x['date'] if x['date'] else '', reverse=True)

            # Ограничиваем количество событий
            events = events[:limit]

            return {
                'success': True,
                'events': events,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'events': [],
                'error': f'Ошибка при получении ленты событий: {str(e)}'
            }
