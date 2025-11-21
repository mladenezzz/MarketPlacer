from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from app.models import Token
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
    
    # Получаем данные о заказах
    order_info = MarketplaceAPI.get_today_orders_total(token)
    
    return jsonify(order_info)


@main_bp.route('/api/sales/<int:token_id>')
@login_required
def get_token_sales(token_id):
    """API endpoint для получения данных о продажах по токену"""
    # Проверяем, что токен принадлежит текущему пользователю
    token = Token.query.filter_by(id=token_id, user_id=current_user.id).first()
    
    if not token:
        return jsonify({'success': False, 'error': 'Токен не найден'}), 404
    
    # Получаем данные о продажах
    sales_info = MarketplaceAPI.get_today_sales_total(token)
    
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

