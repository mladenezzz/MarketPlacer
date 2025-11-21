from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User
from forms import RegistrationForm, LoginForm, ChangeRoleForm
from config import Config
from functools import wraps
import os

def create_app():
    """Фабрика приложения"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Инициализация расширений
    db.init_app(app)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Создание таблиц базы данных
    with app.app_context():
        db.create_all()
    
    return app

app = create_app()

def admin_required(f):
    """Декоратор для проверки прав администратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Пожалуйста, войдите в систему.', 'warning')
            return redirect(url_for('login'))
        if not current_user.is_admin():
            flash('У вас нет прав для доступа к этой странице.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Поздравляем! Вы успешно зарегистрированы. Теперь можете войти.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Попытка найти пользователя по имени или email
        user = User.query.filter(
            (User.username == form.username.data) | 
            (User.email == form.username.data)
        ).first()
        
        if user and user.check_password(form.password.data):
            # Проверка на блокировку пользователя
            if user.is_blocked:
                flash('Ваш аккаунт заблокирован администратором. Обратитесь в поддержку.', 'danger')
                return render_template('login.html', form=form)
            
            login_user(user, remember=form.remember_me.data)
            user.update_last_login()
            
            flash(f'Добро пожаловать, {user.username}!', 'success')
            
            # Перенаправление на страницу, с которой пришел пользователь
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    """Личный кабинет пользователя"""
    return render_template('dashboard.html')

@app.route('/profile')
@login_required
def profile():
    """Профиль пользователя"""
    return render_template('profile.html')

@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы успешно вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    """Страница управления пользователями (только для администраторов)"""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users)

@app.route('/admin/users/<int:user_id>/change-role', methods=['GET', 'POST'])
@login_required
@admin_required
def change_user_role(user_id):
    """Изменение роли пользователя"""
    user = User.query.get_or_404(user_id)
    
    # Запретить изменение своей собственной роли
    if user.id == current_user.id:
        flash('Вы не можете изменить свою собственную роль.', 'warning')
        return redirect(url_for('admin_users'))
    
    form = ChangeRoleForm()
    
    if form.validate_on_submit():
        old_role = user.get_role_display()
        user.role = form.role.data
        db.session.commit()
        
        flash(f'Роль пользователя {user.username} изменена с "{old_role}" на "{user.get_role_display()}".', 'success')
        return redirect(url_for('admin_users'))
    
    # Установить текущую роль пользователя в форме
    form.role.data = user.role
    
    return render_template('change_role.html', form=form, user=user)

@app.route('/admin/users/<int:user_id>/block', methods=['POST'])
@login_required
@admin_required
def block_user(user_id):
    """Блокировка пользователя"""
    user = User.query.get_or_404(user_id)
    
    # Запретить блокировку самого себя
    if user.id == current_user.id:
        flash('Вы не можете заблокировать сами себя.', 'warning')
        return redirect(url_for('admin_users'))
    
    if user.is_blocked:
        flash(f'Пользователь {user.username} уже заблокирован.', 'info')
    else:
        user.is_blocked = True
        db.session.commit()
        flash(f'Пользователь {user.username} успешно заблокирован.', 'success')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/unblock', methods=['POST'])
@login_required
@admin_required
def unblock_user(user_id):
    """Разблокировка пользователя"""
    user = User.query.get_or_404(user_id)
    
    if not user.is_blocked:
        flash(f'Пользователь {user.username} не заблокирован.', 'info')
    else:
        user.is_blocked = False
        db.session.commit()
        flash(f'Пользователь {user.username} успешно разблокирован.', 'success')
    
    return redirect(url_for('admin_users'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

