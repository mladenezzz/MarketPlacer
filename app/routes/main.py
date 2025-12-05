from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app.models import Token, OzonOrder, OzonStock, db
from app.models.wildberries import WBStock, WBGood, WBOrder
from app.models.product import Product
from app.services.sales_service import SalesService
from sqlalchemy import distinct, func

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Главная страница"""
    # Если пользователь авторизован, получаем список токенов без запросов к API
    if current_user.is_authenticated:
        # Получаем токены пользователя
        user_tokens = Token.query.filter_by(user_id=current_user.id).order_by(Token.marketplace, Token.name).all()
        
        # Формируем базовую информацию о токенах без API запросов
        tokens_info = []
        for token in user_tokens:
            # Фильтруем только Wildberries и Ozon
            if token.marketplace not in ['wildberries', 'ozon']:
                continue
                
            token_name = token.name if token.name else token.get_marketplace_display()
            tokens_info.append({
                'token_id': token.id,
                'token_name': token_name,
                'marketplace': token.get_marketplace_display()
            })
        
        return render_template('index.html', 
                             tokens_info=tokens_info,
                             has_tokens=len(user_tokens) > 0)
    
    return render_template('index.html')


@main_bp.route('/api/orders/<int:token_id>')
@login_required
def get_token_orders(token_id):
    """API endpoint для получения данных о заказах по токену из базы данных"""
    # Проверяем, что токен принадлежит текущему пользователю
    token = Token.query.filter_by(id=token_id, user_id=current_user.id).first()

    if not token:
        return jsonify({'success': False, 'error': 'Токен не найден'}), 404

    # Получаем данные о заказах из базы данных
    # Для WB берем из wb_orders, для Ozon - из ozon_sales
    orders_info = SalesService.get_today_orders_by_token(token_id)

    return jsonify(orders_info)


@main_bp.route('/api/sales/<int:token_id>')
@login_required
def get_token_sales(token_id):
    """API endpoint для получения данных о продажах по токену из базы данных"""
    # Проверяем, что токен принадлежит текущему пользователю
    token = Token.query.filter_by(id=token_id, user_id=current_user.id).first()

    if not token:
        return jsonify({'success': False, 'error': 'Токен не найден'}), 404

    # Получаем данные о продажах из базы данных
    sales_info = SalesService.get_today_sales_by_token(token_id)

    return jsonify(sales_info)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Личный кабинет пользователя"""
    return render_template('dashboard.html')


@main_bp.route('/profile')
@login_required
def profile():
    """Профиль пользователя"""
    return render_template('profile.html')


def parse_offer_id(offer_id: str) -> tuple:
    """Парсинг offer_id для извлечения артикула и размера"""
    if not offer_id:
        return '', ''

    # Убираем лишние символы в начале (например, ')
    offer_id = offer_id.lstrip("'\"")

    # Обычно offer_id имеет формат "артикул/размер" или "артикул_размер"
    if '/' in offer_id:
        parts = offer_id.split('/')
        article = parts[0]
        size = parts[1] if len(parts) > 1 else ''
    elif '_' in offer_id:
        parts = offer_id.split('_')
        article = parts[0]
        size = parts[1] if len(parts) > 1 else ''
    else:
        article = offer_id
        size = ''

    return article, size


def parse_size_display(size: str) -> str:
    """Преобразование размера для отображения (например, 65 -> 6.5)"""
    if not size:
        return size

    # Проверяем специальные форматы размеров
    # 65 -> 6.5, 75 -> 7.5, 85 -> 8.5, 95 -> 9.5, 105 -> 10.5, 115 -> 11.5
    if size.isdigit() and len(size) in [2, 3]:
        try:
            num = int(size)
            # Размеры вида 65, 75, 85, 95
            if len(size) == 2 and num % 10 == 5 and num >= 65 and num <= 95:
                return f"{num // 10}.5"
            # Размеры вида 105, 115
            elif len(size) == 3 and num % 10 == 5 and num >= 105 and num <= 115:
                return f"{num // 10}.5"
        except ValueError:
            pass

    # Размеры вида 658 -> 6.5-8, 685 -> 6-8.5
    if size.isdigit() and len(size) == 3:
        try:
            # 658 -> 6.5-8
            if size[1] == '5':
                return f"{size[0]}.5-{size[2]}"
            # 685 -> 6-8.5
            elif size[2] == '5':
                return f"{size[0]}-{size[1]}.5"
        except (ValueError, IndexError):
            pass

    return size


def get_size_sort_key(size: str) -> tuple:
    """Получить ключ сортировки для размера"""
    if not size:
        return (999, 0, '')  # Пустые размеры в конец

    size_upper = size.upper().strip()

    # Определяем порядок для буквенных размеров
    letter_sizes = {
        'XS': (0, 0),
        'S': (1, 0),
        'M': (2, 0),
        'L': (3, 0),
        'XL': (4, 0),
        'XXL': (5, 0),
        'XXXL': (6, 0),
    }

    if size_upper in letter_sizes:
        priority, sub_priority = letter_sizes[size_upper]
        return (priority, sub_priority, size_upper)

    # Для числовых размеров
    try:
        # Проверяем специальные форматы (65 -> 6.5, 105 -> 10.5)
        if size.isdigit() and len(size) in [2, 3]:
            num = int(size)
            # Размеры вида 65, 75, 85, 95 -> преобразуем в 6.5, 7.5, 8.5, 9.5
            if len(size) == 2 and num % 10 == 5 and num >= 65 and num <= 95:
                return (10, num / 10, size)
            # Размеры вида 105, 115 -> преобразуем в 10.5, 11.5
            elif len(size) == 3 and num % 10 == 5 and num >= 105 and num <= 115:
                return (10, num / 10, size)
            # Размеры вида 658, 685 -> для сортировки берем первую часть
            elif len(size) == 3:
                first_digit = int(size[0])
                return (10, first_digit, size)
            else:
                return (10, num, size)
        # Проверяем, есть ли дробная часть (например, 6.5, 7.5)
        elif '.' in size:
            num = float(size)
            return (10, num, size)
        else:
            num = int(size)
            return (10, num, size)
    except ValueError:
        # Если не удалось распарсить как число, размещаем в конец
        return (999, 0, size_upper)


@main_bp.route('/statistics/buyouts')
@login_required
def buyouts():
    """Страница статистики выкупов"""
    # Получаем параметры дат из query string (если они есть)
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')

    date_from = None
    date_to = None

    if date_from_str and date_to_str:
        try:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
        except ValueError:
            pass  # Игнорируем неверный формат дат

    # Получаем все токены пользователя
    user_tokens = Token.query.filter_by(user_id=current_user.id).order_by(Token.marketplace, Token.name).all()

    # Формируем список токенов для отображения
    tokens_list = []
    ozon_token_ids = []
    ozon_tokens = []  # Список Ozon токенов с их данными
    wb_tokens = []  # Список WB токенов с их данными

    for token in user_tokens:
        # Фильтруем только Wildberries и Ozon
        if token.marketplace not in ['wildberries', 'ozon']:
            continue

        token_name = token.name if token.name else token.get_marketplace_display()
        tokens_list.append({
            'id': token.id,
            'name': token_name,
            'marketplace': token.marketplace,
            'marketplace_display': token.get_marketplace_display()
        })

        if token.marketplace == 'ozon':
            ozon_token_ids.append(token.id)
            ozon_tokens.append({'id': token.id, 'name': token_name})
        elif token.marketplace == 'wildberries':
            wb_tokens.append({'id': token.id, 'name': token_name})

    # Общий словарь для всех артикулов (из Ozon и WB)
    # {(article, size): {'ozon_delivered': 0, 'ozon_cancelled': 0, 'ozon_stock': 0}}
    all_products_stats = {}
    today = datetime.now().date()

    # Получаем данные Ozon
    if ozon_token_ids:
        # Получаем остатки на сегодня (только ненулевые)
        stocks = db.session.query(
            OzonStock.offer_id,
            func.sum(OzonStock.fbo_present + OzonStock.fbs_present).label('total_stock')
        ).filter(
            OzonStock.token_id.in_(ozon_token_ids),
            func.date(OzonStock.date) == today
        ).group_by(OzonStock.offer_id).having(
            func.sum(OzonStock.fbo_present + OzonStock.fbs_present) > 0
        ).all()

        # Добавляем остатки в статистику
        for stock in stocks:
            article, size = parse_offer_id(stock.offer_id)
            if not article:
                continue
            key = (article, size)
            if key not in all_products_stats:
                all_products_stats[key] = {'ozon_delivered': 0, 'ozon_cancelled': 0, 'ozon_stock': 0}
            all_products_stats[key]['ozon_stock'] = int(stock.total_stock or 0)

        # Строим запрос с учётом фильтрации по датам
        query = db.session.query(
            OzonOrder.offer_id,
            OzonOrder.status
        ).filter(
            OzonOrder.token_id.in_(ozon_token_ids),
            OzonOrder.status.in_(['cancelled', 'delivered', 'delivering'])
        )

        # Если указаны даты, добавляем фильтр по дате
        if date_from and date_to:
            from datetime import timedelta
            query = query.filter(
                OzonOrder.in_process_at >= date_from,
                OzonOrder.in_process_at < date_to + timedelta(days=1)
            )

        orders = query.all()

        # Добавляем заказы в статистику
        for order in orders:
            article, size = parse_offer_id(order.offer_id)
            if not article:
                continue

            key = (article, size)
            if key not in all_products_stats:
                all_products_stats[key] = {'ozon_delivered': 0, 'ozon_cancelled': 0, 'ozon_stock': 0}

            if order.status == 'delivered':
                all_products_stats[key]['ozon_delivered'] += 1
            elif order.status == 'cancelled':
                all_products_stats[key]['ozon_cancelled'] += 1

    # Получаем остатки WB для каждого токена
    wb_stocks_by_token = {}  # {token_id: {'name': ..., 'stocks': {key: qty}, 'orders': {key: {...}}}}
    wb_token_ids = [t['id'] for t in wb_tokens]

    for wb_token in wb_tokens:
        token_id = wb_token['id']
        token_name = wb_token['name']

        # Получаем остатки на сегодня для данного токена
        stocks = db.session.query(
            WBGood.vendor_code,
            WBGood.tech_size,
            func.sum(WBStock.quantity).label('total_quantity')
        ).join(
            WBStock, WBStock.product_id == WBGood.id
        ).filter(
            WBStock.token_id == token_id,
            func.date(WBStock.date) == today
        ).group_by(
            WBGood.vendor_code,
            WBGood.tech_size
        ).having(
            func.sum(WBStock.quantity) > 0
        ).all()

        # Формируем словарь остатков для этого токена
        token_stocks = {}
        for stock in stocks:
            if stock.vendor_code:
                key = f"{stock.vendor_code}|{stock.tech_size or ''}"
                token_stocks[key] = int(stock.total_quantity or 0)
                # Добавляем в общий список артикулов
                product_key = (stock.vendor_code, stock.tech_size or '')
                if product_key not in all_products_stats:
                    all_products_stats[product_key] = {'ozon_delivered': 0, 'ozon_cancelled': 0, 'ozon_stock': 0}

        # Получаем статистику заказов для данного токена
        orders_query = db.session.query(
            WBGood.vendor_code,
            WBGood.tech_size,
            func.count(WBOrder.id).label('total_orders'),
            func.sum(db.case((WBOrder.is_cancel == False, 1), else_=0)).label('delivered'),
            func.sum(db.case((WBOrder.is_cancel == True, 1), else_=0)).label('cancelled')
        ).select_from(WBOrder).join(
            Product, WBOrder.product_id == Product.id
        ).join(
            WBGood, Product.barcode == WBGood.barcode
        ).filter(
            WBOrder.token_id == token_id
        )

        # Если указаны даты, добавляем фильтр по дате
        if date_from and date_to:
            from datetime import timedelta as td
            orders_query = orders_query.filter(
                WBOrder.date >= date_from,
                WBOrder.date < date_to + td(days=1)
            )

        orders_stats = orders_query.group_by(
            WBGood.vendor_code,
            WBGood.tech_size
        ).all()

        # Формируем словарь статистики заказов для этого токена
        token_orders = {}
        for stat in orders_stats:
            if stat.vendor_code:
                key = f"{stat.vendor_code}|{stat.tech_size or ''}"
                total = int(stat.total_orders or 0)
                delivered = int(stat.delivered or 0)
                cancelled = int(stat.cancelled or 0)
                percent = (delivered / total * 100) if total > 0 else 0
                token_orders[key] = {
                    'total': total,
                    'delivered': delivered,
                    'cancelled': cancelled,
                    'percent': round(percent, 1)
                }
                # Добавляем в общий список артикулов
                product_key = (stat.vendor_code, stat.tech_size or '')
                if product_key not in all_products_stats:
                    all_products_stats[product_key] = {'ozon_delivered': 0, 'ozon_cancelled': 0, 'ozon_stock': 0}

        wb_stocks_by_token[token_id] = {
            'name': token_name,
            'stocks': token_stocks,
            'orders': token_orders
        }

    # Сортируем все артикулы и формируем итоговый список
    sorted_keys = sorted(all_products_stats.keys(), key=lambda x: (x[0], get_size_sort_key(x[1])))

    # Формируем ozon_products из общего списка (для совместимости с шаблоном)
    ozon_products = [
        (
            article,
            parse_size_display(size),
            all_products_stats[(article, size)]['ozon_delivered'],
            all_products_stats[(article, size)]['ozon_cancelled'],
            all_products_stats[(article, size)]['ozon_stock']
        )
        for article, size in sorted_keys
    ]

    return render_template('buyouts.html', tokens=tokens_list, ozon_products=ozon_products,
                          ozon_tokens=ozon_tokens, wb_tokens=wb_tokens, wb_stocks_by_token=wb_stocks_by_token)


@main_bp.route('/api/orders/<int:token_id>/range')
@login_required
def get_token_orders_range(token_id):
    """API endpoint для получения данных о заказах за период"""
    # Проверяем, что токен принадлежит текущему пользователю
    token = Token.query.filter_by(id=token_id, user_id=current_user.id).first()

    if not token:
        return jsonify({'success': False, 'error': 'Токен не найден'}), 404

    # Получаем параметры дат из query string
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')

    if not date_from_str or not date_to_str:
        return jsonify({'success': False, 'error': 'Не указаны параметры date_from и date_to'}), 400

    try:
        # Парсим даты в формате YYYY-MM-DD
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'error': 'Неверный формат даты. Используйте YYYY-MM-DD'}), 400

    # Получаем данные о заказах за период
    orders_info = SalesService.get_orders_by_date_range(token_id, date_from, date_to)

    return jsonify(orders_info)


@main_bp.route('/api/sales/<int:token_id>/range')
@login_required
def get_token_sales_range(token_id):
    """API endpoint для получения данных о продажах за период"""
    # Проверяем, что токен принадлежит текущему пользователю
    token = Token.query.filter_by(id=token_id, user_id=current_user.id).first()

    if not token:
        return jsonify({'success': False, 'error': 'Токен не найден'}), 404

    # Получаем параметры дат из query string
    date_from_str = request.args.get('date_from')
    date_to_str = request.args.get('date_to')

    if not date_from_str or not date_to_str:
        return jsonify({'success': False, 'error': 'Не указаны параметры date_from и date_to'}), 400

    try:
        # Парсим даты в формате YYYY-MM-DD
        date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        date_to = datetime.strptime(date_to_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'success': False, 'error': 'Неверный формат даты. Используйте YYYY-MM-DD'}), 400

    # Получаем данные о продажах за период
    sales_info = SalesService.get_sales_by_date_range(token_id, date_from, date_to)

    return jsonify(sales_info)


@main_bp.route('/api/stocks/refresh', methods=['POST'])
@login_required
def refresh_all_stocks():
    """API endpoint для обновления остатков по всем токенам пользователя.
    Создает задачи в БД, которые обрабатываются datacollector'ом.
    """
    from app.models.sync import ManualTask

    # Получаем все токены пользователя
    user_tokens = Token.query.filter_by(user_id=current_user.id).filter(
        Token.marketplace.in_(['wildberries', 'ozon'])
    ).all()

    if not user_tokens:
        return jsonify({'success': False, 'error': 'Нет токенов для обновления'}), 404

    # Создаем задачи на обновление остатков для каждого токена
    tasks_created = 0
    for token in user_tokens:
        # Создаем задачу с типом 'stocks'
        task = ManualTask(
            token_id=token.id,
            task_type='stocks',
            status='pending'
        )
        db.session.add(task)
        tasks_created += 1

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Создано {tasks_created} задач на обновление остатков. Datacollector обработает их в ближайшее время.'
    })

