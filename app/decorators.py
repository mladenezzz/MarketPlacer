"""Декораторы для контроля доступа"""
from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user


def section_required(section):
    """Декоратор для проверки доступа к разделу

    Args:
        section: название раздела ('dashboard', 'wildberries', 'ozon',
                 'marking', 'reports', 'settings', 'tokens', 'users', 'server')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Пожалуйста, войдите в систему.', 'warning')
                return redirect(url_for('auth.login'))

            if not current_user.has_access_to(section):
                flash('У вас нет прав для доступа к этому разделу.', 'danger')
                return redirect(url_for('main.dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


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


def manager_required(f):
    """Декоратор для проверки прав менеджера или выше"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Пожалуйста, войдите в систему.', 'warning')
            return redirect(url_for('auth.login'))

        if not (current_user.is_admin() or current_user.is_manager()):
            flash('У вас нет прав для доступа к этой странице.', 'danger')
            return redirect(url_for('main.dashboard'))

        return f(*args, **kwargs)
    return decorated_function
