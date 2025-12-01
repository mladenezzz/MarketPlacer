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
            # Запрос к таблице ozon_sales (финансовые транзакции)
            # Используем shipment_date - дата операции из finance API
            # price - это accruals_for_sale (начисления за продажу)
            sales_query = db.session.query(
                func.count(OzonSale.id).label('count'),
                func.sum(OzonSale.price).label('total')
            ).filter(
                OzonSale.token_id == token_id,
                OzonSale.shipment_date >= today_start
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
                'error': f'Ошибка БД Ozon: {str(e)}'
            }

    @staticmethod
    def get_all_sales_today_by_user(user_id: int) -> Dict:
        """
        Получить агрегированные данные о продажах на сегодня для всех токенов пользователя

        Args:
            user_id: ID пользователя

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
            # Получаем все токены пользователя
            tokens = Token.query.filter_by(user_id=user_id).all()

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
            # Используем finished_price - цена с учетом всех скидок (то что платит покупатель)
            orders_query = db.session.query(
                func.count(WBOrder.id).label('count'),
                func.sum(WBOrder.finished_price).label('total')
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
                func.sum(WBOrder.finished_price).label('total')
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
            sales_query = db.session.query(
                func.count(OzonSale.id).label('count'),
                func.sum(OzonSale.price).label('total')
            ).filter(
                OzonSale.token_id == token_id,
                OzonSale.shipment_date >= date_from,
                OzonSale.shipment_date <= date_to
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
                'error': f'Ошибка БД Ozon: {str(e)}'
            }
