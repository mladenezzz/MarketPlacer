from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
from app.models import Token, OzonOrder, db
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

    # Получаем уникальные сочетания артикул+размер для Ozon токенов с подсчётом статусов
    ozon_products = []
    if ozon_token_ids:
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
            query = query.filter(
                OzonOrder.in_process_at >= date_from,
                OzonOrder.in_process_at < date_to + func.cast('1 day', db.Interval)
            )

        orders = query.all()

        # Словарь для подсчёта статусов: {(article, size): {'delivered': count, 'cancelled': count}}
        stats = {}
        for order in orders:
            article, size = parse_offer_id(order.offer_id)
            if not article:  # Пропускаем если артикул пустой
                continue

            key = (article, size)
            if key not in stats:
                stats[key] = {'delivered': 0, 'cancelled': 0, 'delivering': 0}

            # Подсчитываем статусы
            if order.status == 'delivered':
                stats[key]['delivered'] += 1
            elif order.status == 'cancelled':
                stats[key]['cancelled'] += 1
            elif order.status == 'delivering':
                stats[key]['delivering'] += 1

        # Сортируем по артикулу и размеру (используем умную сортировку для размеров)
        sorted_keys = sorted(stats.keys(), key=lambda x: (x[0], get_size_sort_key(x[1])))

        # Формируем результат с преобразованием размеров для отображения
        ozon_products = [
            (article, parse_size_display(size), stats[(article, size)]['delivered'], stats[(article, size)]['cancelled'])
            for article, size in sorted_keys
        ]

    return render_template('buyouts.html', tokens=tokens_list, ozon_products=ozon_products)


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

