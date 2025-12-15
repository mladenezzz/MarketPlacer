from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from functools import wraps
import subprocess
import logging
from app.models import db, User
from app.forms import ChangeRoleForm, CreateUserForm

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Декоратор для проверки прав администратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Пожалуйста, войдите в систему.', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin():
            flash('У вас нет прав для доступа к этой странице.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Страница управления пользователями (только для администраторов)"""
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=all_users)


@admin_bp.route('/users/<int:user_id>/change-role', methods=['GET', 'POST'])
@login_required
@admin_required
def change_user_role(user_id):
    """Изменение роли пользователя"""
    user = User.query.get_or_404(user_id)
    
    # Запретить изменение своей собственной роли
    if user.id == current_user.id:
        flash('Вы не можете изменить свою собственную роль.', 'warning')
        return redirect(url_for('admin.users'))
    
    form = ChangeRoleForm()
    
    if form.validate_on_submit():
        old_role = user.get_role_display()
        user.role = form.role.data
        db.session.commit()
        
        flash(f'Роль пользователя {user.username} изменена с "{old_role}" на "{user.get_role_display()}".', 'success')
        return redirect(url_for('admin.users'))
    
    # Установить текущую роль пользователя в форме
    form.role.data = user.role
    
    return render_template('change_role.html', form=form, user=user)


@admin_bp.route('/users/<int:user_id>/block', methods=['POST'])
@login_required
@admin_required
def block_user(user_id):
    """Блокировка пользователя"""
    user = User.query.get_or_404(user_id)
    
    # Запретить блокировку самого себя
    if user.id == current_user.id:
        flash('Вы не можете заблокировать сами себя.', 'warning')
        return redirect(url_for('admin.users'))
    
    if user.is_blocked:
        flash(f'Пользователь {user.username} уже заблокирован.', 'info')
    else:
        user.is_blocked = True
        db.session.commit()
        flash(f'Пользователь {user.username} успешно заблокирован.', 'success')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/unblock', methods=['POST'])
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

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Создание нового пользователя администратором"""
    form = CreateUserForm()

    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            role=form.role.data
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        flash(f'Пользователь "{user.username}" успешно создан с ролью "{user.get_role_display()}".', 'success')
        return redirect(url_for('admin.users'))

    return render_template('admin_create_user.html', form=form)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Удаление пользователя"""
    user = User.query.get_or_404(user_id)

    # Запретить удаление самого себя
    if user.id == current_user.id:
        flash('Вы не можете удалить сами себя.', 'warning')
        return redirect(url_for('admin.users'))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    flash(f'Пользователь "{username}" успешно удален.', 'success')
    return redirect(url_for('admin.users'))



@admin_bp.route('/monitoring')
@login_required
@admin_required
def monitoring():
    """Страница мониторинга Grafana (только для администраторов)"""
    return render_template('admin_monitoring.html')


# Список разрешённых сервисов для управления
ALLOWED_SERVICES = ['datacollector', 'marketplacer']


@admin_bp.route('/service/<service_name>/status', methods=['GET'])
@login_required
@admin_required
def service_status(service_name):
    """Получить статус сервиса"""
    if service_name not in ALLOWED_SERVICES:
        return jsonify({'error': 'Недопустимый сервис'}), 400

    try:
        result = subprocess.run(
            ['/usr/bin/sudo', '/bin/systemctl', 'status', f'{service_name}.service'],
            capture_output=True,
            text=True,
            timeout=10
        )

        is_active = 'active (running)' in result.stdout

        return jsonify({
            'service': service_name,
            'active': is_active,
            'status': 'running' if is_active else 'stopped'
        })
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Таймаут при получении статуса'}), 500
    except Exception as e:
        logger.error(f"Ошибка получения статуса {service_name}: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/service/<service_name>/restart', methods=['POST'])
@login_required
@admin_required
def restart_service(service_name):
    """Перезапустить сервис"""
    if service_name not in ALLOWED_SERVICES:
        return jsonify({'error': 'Недопустимый сервис'}), 400

    try:
        logger.info(f"Пользователь {current_user.username} перезапускает сервис {service_name}")

        # Для самого marketplacer используем отложенный перезапуск,
        # чтобы успеть отправить ответ клиенту до остановки сервиса
        if service_name == 'marketplacer':
            # Запускаем перезапуск в фоне с задержкой 1 секунда
            subprocess.Popen(
                ['/bin/bash', '-c', 'sleep 1 && /usr/bin/sudo /bin/systemctl restart marketplacer.service'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.info(f"Запланирован перезапуск сервиса {service_name}")
            return jsonify({
                'success': True,
                'message': f'Сервис {service_name} будет перезапущен через 1 секунду'
            })

        # Для других сервисов - синхронный перезапуск
        result = subprocess.run(
            ['/usr/bin/sudo', '/bin/systemctl', 'restart', f'{service_name}.service'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            logger.info(f"Сервис {service_name} успешно перезапущен")
            return jsonify({
                'success': True,
                'message': f'Сервис {service_name} успешно перезапущен'
            })
        else:
            logger.error(f"Ошибка перезапуска {service_name}: {result.stderr}")
            return jsonify({
                'success': False,
                'error': result.stderr or 'Неизвестная ошибка'
            }), 500

    except subprocess.TimeoutExpired:
        logger.error(f"Таймаут при перезапуске {service_name}")
        return jsonify({'error': 'Таймаут при перезапуске сервиса'}), 500
    except Exception as e:
        logger.error(f"Ошибка перезапуска {service_name}: {e}")
        return jsonify({'error': str(e)}), 500
