from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required
from app.models import db, Token
from app.forms import TokenForm
from app.decorators import admin_required

tokens_bp = Blueprint('tokens', __name__, url_prefix='/settings/tokens')


@tokens_bp.route('/')
@login_required
@admin_required
def list_tokens():
    """Страница управления токенами маркетплейсов (только для админа)"""
    tokens = Token.query.order_by(Token.marketplace, Token.name).all()
    return render_template('tokens.html', tokens=tokens)


@tokens_bp.route('/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add():
    """Добавление нового токена (только для админа)"""
    form = TokenForm()

    if form.validate_on_submit():
        # Проверка, что для Ozon указан Client ID
        if form.marketplace.data == 'ozon' and not form.client_id.data:
            flash('Для Ozon необходимо указать Client ID.', 'warning')
            return render_template('add_token.html', form=form)

        token = Token(
            name=form.name.data if form.name.data else None,
            description=form.description.data if hasattr(form, 'description') and form.description.data else None,
            marketplace=form.marketplace.data,
            token=form.token.data,
            client_id=form.client_id.data if form.marketplace.data == 'ozon' else None,
            is_active=True
        )

        db.session.add(token)
        db.session.commit()

        token_display = f'"{token.name}"' if token.name else token.get_marketplace_display()
        flash(f'Токен {token_display} успешно добавлен.', 'success')
        return redirect(url_for('tokens.list_tokens'))

    return render_template('add_token.html', form=form)


@tokens_bp.route('/<int:token_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit(token_id):
    """Редактирование токена (только для админа)"""
    token = Token.query.get_or_404(token_id)
    form = TokenForm()

    if form.validate_on_submit():
        # Проверка, что для Ozon указан Client ID
        if form.marketplace.data == 'ozon' and not form.client_id.data:
            flash('Для Ozon необходимо указать Client ID.', 'warning')
            return render_template('edit_token.html', form=form, token=token)

        token.name = form.name.data if form.name.data else None
        if hasattr(form, 'description'):
            token.description = form.description.data if form.description.data else None
        token.marketplace = form.marketplace.data
        token.token = form.token.data
        token.client_id = form.client_id.data if form.marketplace.data == 'ozon' else None

        db.session.commit()

        token_display = f'"{token.name}"' if token.name else token.get_marketplace_display()
        flash(f'Токен {token_display} успешно обновлен.', 'success')
        return redirect(url_for('tokens.list_tokens'))

    # Заполнение формы текущими данными токена
    if request.method == 'GET':
        form.name.data = token.name
        if hasattr(form, 'description'):
            form.description.data = token.description
        form.marketplace.data = token.marketplace
        form.token.data = token.token
        form.client_id.data = token.client_id

    return render_template('edit_token.html', form=form, token=token)


@tokens_bp.route('/<int:token_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle(token_id):
    """Включение/выключение токена (только для админа)"""
    token = Token.query.get_or_404(token_id)
    token.is_active = not token.is_active
    db.session.commit()

    status = 'активирован' if token.is_active else 'деактивирован'
    token_display = f'"{token.name}"' if token.name else token.get_marketplace_display()
    flash(f'Токен {token_display} {status}.', 'success')
    return redirect(url_for('tokens.list_tokens'))


@tokens_bp.route('/<int:token_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete(token_id):
    """Удаление токена (только для админа)"""
    token = Token.query.get_or_404(token_id)

    token_display = f'"{token.name}"' if token.name else token.get_marketplace_display()
    db.session.delete(token)
    db.session.commit()

    flash(f'Токен {token_display} успешно удален.', 'success')
    return redirect(url_for('tokens.list_tokens'))
