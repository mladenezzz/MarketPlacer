from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.models import Token
from app.services.marketplace_api import MarketplaceAPI

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Главная страница"""
    # Если пользователь авторизован, показываем статистику заказов
    if current_user.is_authenticated:
        # Получаем токены пользователя
        user_tokens = Token.query.filter_by(user_id=current_user.id).order_by(Token.marketplace, Token.name).all()
        
        # Получаем данные о заказах для каждого токена
        orders_data = []
        total_sum = 0.0
        total_count = 0
        
        for token in user_tokens:
            # Фильтруем только Wildberries и Ozon
            if token.marketplace not in ['wildberries', 'ozon']:
                continue
                
            # Получаем данные о заказах
            order_info = MarketplaceAPI.get_today_orders_total(token)
            
            # Формируем данные для отображения
            token_name = token.name if token.name else token.get_marketplace_display()
            
            orders_data.append({
                'token_id': token.id,
                'token_name': token_name,
                'marketplace': token.get_marketplace_display(),
                'success': order_info['success'],
                'total': order_info['total'],
                'count': order_info['count'],
                'error': order_info['error']
            })
            
            # Добавляем к общей сумме, если запрос успешен
            if order_info['success']:
                total_sum += order_info['total']
                total_count += order_info['count']
        
        return render_template('index.html', 
                             orders_data=orders_data,
                             total_sum=total_sum,
                             total_count=total_count,
                             has_tokens=len(user_tokens) > 0)
    
    return render_template('index.html')


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

