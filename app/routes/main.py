from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
from app.models import Token
from app.services.sales_service import SalesService

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

