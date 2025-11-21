from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from sqlalchemy import func, and_
from app.models import db, Token, Order, Sale
from app.services.marketplace_api import MarketplaceAPI

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
    """API endpoint для получения данных о заказах по токену"""
    # Проверяем, что токен принадлежит текущему пользователю
    token = Token.query.filter_by(id=token_id, user_id=current_user.id).first()
    
    if not token:
        return jsonify({'success': False, 'error': 'Токен не найден'}), 404
    
    # Получаем дату из параметров или используем сегодняшнюю
    date_str = request.args.get('date')
    
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            selected_date = datetime.now().date()
    else:
        selected_date = datetime.now().date()
    
    today = datetime.now().date()
    
    # Если выбран сегодняшний день - используем API
    if selected_date == today:
        order_info = MarketplaceAPI.get_today_orders_total(token)
        return jsonify(order_info)
    else:
        # Для прошлых дней берем из базы данных
        start_datetime = datetime.combine(selected_date, datetime.min.time())
        end_datetime = datetime.combine(selected_date, datetime.max.time())
        
        orders_query = Order.query.filter(
            and_(
                Order.token_id == token.id,
                Order.order_date >= start_datetime,
                Order.order_date <= end_datetime
            )
        )
        
        orders_count = orders_query.count()
        orders_total = db.session.query(func.sum(Order.price)).filter(
            and_(
                Order.token_id == token.id,
                Order.order_date >= start_datetime,
                Order.order_date <= end_datetime
            )
        ).scalar() or 0.0
        
        return jsonify({
            'success': True,
            'count': orders_count,
            'total': float(orders_total),
            'error': None
        })


@main_bp.route('/api/sales/<int:token_id>')
@login_required
def get_token_sales(token_id):
    """API endpoint для получения данных о продажах по токену"""
    # Проверяем, что токен принадлежит текущему пользователю
    token = Token.query.filter_by(id=token_id, user_id=current_user.id).first()
    
    if not token:
        return jsonify({'success': False, 'error': 'Токен не найден'}), 404
    
    # Получаем дату из параметров или используем сегодняшнюю
    date_str = request.args.get('date')
    
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            selected_date = datetime.now().date()
    else:
        selected_date = datetime.now().date()
    
    today = datetime.now().date()
    
    # Если выбран сегодняшний день - используем API
    if selected_date == today:
        sales_info = MarketplaceAPI.get_today_sales_total(token)
        return jsonify(sales_info)
    else:
        # Для прошлых дней берем из базы данных
        start_datetime = datetime.combine(selected_date, datetime.min.time())
        end_datetime = datetime.combine(selected_date, datetime.max.time())
        
        sales_query = Sale.query.filter(
            and_(
                Sale.token_id == token.id,
                Sale.sale_date >= start_datetime,
                Sale.sale_date <= end_datetime
            )
        )
        
        sales_count = sales_query.count()
        sales_total = db.session.query(func.sum(Sale.price)).filter(
            and_(
                Sale.token_id == token.id,
                Sale.sale_date >= start_datetime,
                Sale.sale_date <= end_datetime
            )
        ).scalar() or 0.0
        
        return jsonify({
            'success': True,
            'count': sales_count,
            'total': float(sales_total),
            'error': None
        })


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


@main_bp.route('/statistics/daily')
@login_required
def daily_statistics():
    """Подневный просмотр статистики"""
    # Получаем дату из параметров или используем сегодняшнюю
    date_str = request.args.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except:
            selected_date = datetime.now().date()
    else:
        selected_date = datetime.now().date()
    
    # Получаем токены пользователя
    user_tokens = Token.query.filter_by(user_id=current_user.id).order_by(Token.marketplace, Token.name).all()
    
    # Фильтруем только токены с данными
    tokens_with_data = []
    for token in user_tokens:
        if token.marketplace in ['wildberries', 'ozon']:
            tokens_with_data.append(token)
    
    return render_template('daily_statistics.html', 
                         selected_date=selected_date,
                         tokens=tokens_with_data)


@main_bp.route('/api/statistics/daily')
@login_required
def get_daily_statistics():
    """API endpoint для получения подневной статистики"""
    # Получаем параметры
    date_str = request.args.get('date')
    token_id = request.args.get('token_id', type=int)
    
    if not date_str:
        return jsonify({'success': False, 'error': 'Не указана дата'}), 400
    
    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except:
        return jsonify({'success': False, 'error': 'Неверный формат даты'}), 400
    
    # Начало и конец дня
    start_datetime = datetime.combine(selected_date, datetime.min.time())
    end_datetime = datetime.combine(selected_date, datetime.max.time())
    
    result = {
        'success': True,
        'date': date_str,
        'tokens': []
    }
    
    # Если указан token_id, возвращаем данные только для него
    if token_id:
        token = Token.query.filter_by(id=token_id, user_id=current_user.id).first()
        if not token:
            return jsonify({'success': False, 'error': 'Токен не найден'}), 404
        
        tokens_to_process = [token]
    else:
        # Получаем все токены пользователя
        tokens_to_process = Token.query.filter_by(user_id=current_user.id).all()
    
    for token in tokens_to_process:
        if token.marketplace not in ['wildberries', 'ozon']:
            continue
        
        # Получаем заказы за день
        orders_query = Order.query.filter(
            and_(
                Order.token_id == token.id,
                Order.order_date >= start_datetime,
                Order.order_date <= end_datetime
            )
        )
        
        orders_count = orders_query.count()
        orders_total = db.session.query(func.sum(Order.price)).filter(
            and_(
                Order.token_id == token.id,
                Order.order_date >= start_datetime,
                Order.order_date <= end_datetime
            )
        ).scalar() or 0.0
        
        # Получаем продажи за день
        sales_query = Sale.query.filter(
            and_(
                Sale.token_id == token.id,
                Sale.sale_date >= start_datetime,
                Sale.sale_date <= end_datetime
            )
        )
        
        sales_count = sales_query.count()
        sales_total = db.session.query(func.sum(Sale.price)).filter(
            and_(
                Sale.token_id == token.id,
                Sale.sale_date >= start_datetime,
                Sale.sale_date <= end_datetime
            )
        ).scalar() or 0.0
        
        token_name = token.name if token.name else token.get_marketplace_display()
        
        result['tokens'].append({
            'token_id': token.id,
            'token_name': token_name,
            'marketplace': token.get_marketplace_display(),
            'orders': {
                'count': orders_count,
                'total': float(orders_total)
            },
            'sales': {
                'count': sales_count,
                'total': float(sales_total)
            }
        })
    
    return jsonify(result)

