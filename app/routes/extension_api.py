"""API endpoints для Chrome расширения OZON и WB"""
from flask import Blueprint, jsonify, request
from datetime import datetime, timezone
from app.models import db, Token, OzonOrder, OzonStock
from app.models.wildberries import WBGood, WBOrder, WBSale, WBStock
from sqlalchemy import func, distinct

extension_api_bp = Blueprint('extension_api', __name__, url_prefix='/api/extension')


def normalize_size(size: str) -> str:
    """Нормализация размера (65 -> 6.5, 75 -> 7.5 и т.д.)"""
    if not size:
        return size

    if size.isdigit() and len(size) in [2, 3]:
        try:
            num = int(size)
            # Размеры вида 65, 75, 85, 95 -> 6.5, 7.5, 8.5, 9.5
            if len(size) == 2 and num % 10 == 5 and num >= 65 and num <= 95:
                return f"{num // 10}.5"
            # Размеры вида 105, 115 -> 10.5, 11.5
            elif len(size) == 3 and num % 10 == 5 and num >= 105 and num <= 115:
                return f"{num // 10}.5"
        except ValueError:
            pass

    return size


def get_size_variants(size: str) -> list:
    """Получить все варианты размера для поиска в БД"""
    if not size:
        return ['']

    variants = [size]  # оригинал

    # Нормализуем размер
    normalized = normalize_size(size)
    if normalized != size:
        variants.append(normalized)  # с точкой (6.5)
        variants.append(normalized.replace('.', ','))  # с запятой (6,5)

    # Если размер уже с точкой, добавляем вариант с запятой
    if '.' in size:
        variants.append(size.replace('.', ','))
    elif ',' in size:
        variants.append(size.replace(',', '.'))

    return list(set(variants))  # убираем дубли


@extension_api_bp.route('/articles')
def get_articles():
    """Получить список всех уникальных артикулов (vendor_code) из WBGood"""
    try:
        articles = db.session.query(
            distinct(WBGood.vendor_code)
        ).filter(
            WBGood.vendor_code.isnot(None),
            WBGood.vendor_code != ''
        ).all()

        result = [a[0] for a in articles if a[0]]

        return jsonify({
            'success': True,
            'articles': result,
            'count': len(result)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@extension_api_bp.route('/product-info')
def get_product_info():
    """Получить информацию по товару для тултипа

    Query params:
        article: артикул (vendor_code)
        size: размер (как на OZON, например 65)
    """
    article = request.args.get('article', '').strip()
    size = request.args.get('size', '').strip()

    if not article:
        return jsonify({
            'success': False,
            'error': 'Не указан артикул'
        }), 400

    try:
        # Формируем варианты offer_id для поиска
        # В базе может быть: "12345/75", "'12345/75", "12345/7.5" и т.д.
        offer_id = f"{article}/{size}" if size else article
        offer_id_with_quote = f"'{article}/{size}" if size else f"'{article}"

        # Получаем все активные OZON токены
        ozon_tokens = Token.query.filter_by(
            marketplace='ozon',
            is_active=True
        ).all()
        ozon_token_ids = [t.id for t in ozon_tokens]

        if not ozon_token_ids:
            return jsonify({
                'success': False,
                'error': 'Нет активных OZON токенов'
            }), 404

        # 1. Остатки на сегодня
        today = datetime.now(timezone.utc).date()

        # Ищем по offer_id с учётом разных форматов (LIKE для гибкости)
        # offer_id в базе содержит полный артикул типа "12345/75" или "'12345/75"
        stock_query = db.session.query(
            func.sum(OzonStock.fbo_present + OzonStock.fbs_present).label('total_stock')
        ).filter(
            OzonStock.token_id.in_(ozon_token_ids),
            db.or_(
                OzonStock.offer_id == offer_id,
                OzonStock.offer_id == offer_id_with_quote,
                OzonStock.offer_id.like(f"%{article}/{size}") if size else OzonStock.offer_id.like(f"%{article}")
            ),
            func.date(OzonStock.date) == today
        ).first()

        stock = int(stock_query.total_stock or 0) if stock_query and stock_query.total_stock else 0

        # 2. Статистика заказов (все статусы)
        orders_stats = db.session.query(
            func.count(OzonOrder.id).label('total'),
            func.sum(db.case((OzonOrder.status == 'delivered', 1), else_=0)).label('delivered'),
            func.sum(db.case((OzonOrder.status == 'cancelled', 1), else_=0)).label('cancelled'),
            func.sum(db.case((OzonOrder.status.in_(['delivering', 'awaiting_deliver', 'awaiting_packaging']), 1), else_=0)).label('delivering')
        ).filter(
            OzonOrder.token_id.in_(ozon_token_ids),
            db.or_(
                OzonOrder.offer_id == offer_id,
                OzonOrder.offer_id == offer_id_with_quote,
                OzonOrder.offer_id.like(f"%{article}/{size}") if size else OzonOrder.offer_id.like(f"%{article}")
            )
        ).first()

        total_orders = int(orders_stats.total or 0) if orders_stats else 0
        delivered = int(orders_stats.delivered or 0) if orders_stats else 0
        cancelled = int(orders_stats.cancelled or 0) if orders_stats else 0
        delivering = int(orders_stats.delivering or 0) if orders_stats else 0

        # 3. Процент выкупа
        buyout_base = delivered + cancelled
        buyout_percent = round((delivered / buyout_base * 100), 1) if buyout_base > 0 else 0

        # 4. Проверяем существование товара в WBGood
        size_variants = get_size_variants(size)

        product_exists = db.session.query(WBGood).filter(
            WBGood.vendor_code == article,
            WBGood.tech_size.in_(size_variants) if size else True
        ).first() is not None

        return jsonify({
            'success': True,
            'article': article,
            'size': size,
            'offer_id': offer_id,
            'product_exists': product_exists,
            'stock': stock,
            'orders_total': total_orders,
            'delivered': delivered,
            'cancelled': cancelled,
            'delivering': delivering,
            'buyout_percent': buyout_percent
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@extension_api_bp.route('/wb/product-info')
def get_wb_product_info():
    """Получить информацию по товару WB для тултипа (по всем размерам и токенам)

    Query params:
        article: артикул (vendor_code / supplier_article)
    """
    article = request.args.get('article', '').strip()

    if not article:
        return jsonify({
            'success': False,
            'error': 'Не указан артикул'
        }), 400

    try:
        # Получаем все активные WB токены
        wb_tokens = Token.query.filter_by(
            marketplace='wildberries',
            is_active=True
        ).all()

        if not wb_tokens:
            return jsonify({
                'success': False,
                'error': 'Нет активных WB токенов'
            }), 404

        today = datetime.now(timezone.utc).date()

        # Находим все размеры для этого артикула
        products = WBGood.query.filter(
            WBGood.vendor_code == article
        ).order_by(WBGood.tech_size).all()

        if not products:
            return jsonify({
                'success': False,
                'error': 'Товар не найден в базе'
            }), 404

        sizes_data = []

        for product in products:
            size = product.tech_size or '-'
            product_id = product.id

            tokens_data = []

            for token in wb_tokens:
                token_id = token.id
                token_name = token.name or f"Токен {token.id}"

                # 1. Остатки на сегодня
                stock = 0
                in_way_to_client = 0
                stock_query = db.session.query(
                    func.sum(WBStock.quantity).label('total_stock'),
                    func.sum(WBStock.in_way_to_client).label('in_way')
                ).filter(
                    WBStock.token_id == token_id,
                    WBStock.product_id == product_id,
                    func.date(WBStock.date) == today
                ).first()

                if stock_query:
                    stock = int(stock_query.total_stock or 0)
                    in_way_to_client = int(stock_query.in_way or 0)

                # 2. Статистика заказов по размеру
                orders_query = db.session.query(
                    func.count(WBOrder.id).label('total'),
                    func.sum(db.case((WBOrder.is_cancel == True, 1), else_=0)).label('cancelled')
                ).filter(
                    WBOrder.token_id == token_id,
                    WBOrder.supplier_article == article,
                    WBOrder.tech_size == product.tech_size
                )

                orders_stats = orders_query.first()
                total_orders = int(orders_stats.total or 0) if orders_stats else 0
                cancelled = int(orders_stats.cancelled or 0) if orders_stats else 0

                # 3. Статистика продаж (выкуплено)
                sales_query = db.session.query(
                    func.count(WBSale.id).label('delivered')
                ).filter(
                    WBSale.token_id == token_id,
                    WBSale.product_id == product_id
                )

                sales_stats = sales_query.first()
                delivered = int(sales_stats.delivered or 0) if sales_stats else 0

                # 4. Процент выкупа
                buyout_base = delivered + cancelled
                buyout_percent = round((delivered / buyout_base * 100), 1) if buyout_base > 0 else 0

                tokens_data.append({
                    'token_id': token_id,
                    'token_name': token_name,
                    'stock': stock,
                    'in_way_to_client': in_way_to_client,
                    'orders_total': total_orders,
                    'delivered': delivered,
                    'cancelled': cancelled,
                    'buyout_percent': buyout_percent
                })

            sizes_data.append({
                'size': size,
                'tokens': tokens_data
            })

        return jsonify({
            'success': True,
            'article': article,
            'sizes': sizes_data,
            'token_names': [t.name or f"Токен {t.id}" for t in wb_tokens]
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@extension_api_bp.after_request
def add_cors_headers(response):
    """Добавляем CORS заголовки для доступа из расширения"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response
