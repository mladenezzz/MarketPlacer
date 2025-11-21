from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models import db, Token
from app.forms import TokenForm

tokens_bp = Blueprint('tokens', __name__, url_prefix='/settings/tokens')


@tokens_bp.route('/')
@login_required
def list_tokens():
    """Страница управления токенами маркетплейсов"""
    user_tokens = Token.query.filter_by(user_id=current_user.id).order_by(Token.created_at.desc()).all()
    return render_template('tokens.html', tokens=user_tokens)


@tokens_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    """Добавление нового токена"""
    form = TokenForm()
    
    if form.validate_on_submit():
        # Проверка, что для Ozon указан Client ID
        if form.marketplace.data == 'ozon' and not form.client_id.data:
            flash('Для Ozon необходимо указать Client ID.', 'warning')
            return render_template('add_token.html', form=form)
        
        token = Token(
            user_id=current_user.id,
            name=form.name.data if form.name.data else None,
            marketplace=form.marketplace.data,
            token=form.token.data,
            client_id=form.client_id.data if form.marketplace.data == 'ozon' else None
        )
        
        db.session.add(token)
        db.session.commit()
        
        token_display = f'"{token.name}"' if token.name else token.get_marketplace_display()
        flash(f'Токен {token_display} успешно добавлен.', 'success')
        return redirect(url_for('tokens.list_tokens'))
    
    return render_template('add_token.html', form=form)


@tokens_bp.route('/<int:token_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(token_id):
    """Редактирование токена"""
    token = Token.query.get_or_404(token_id)
    
    # Проверка, что токен принадлежит текущему пользователю
    if token.user_id != current_user.id:
        flash('У вас нет прав для редактирования этого токена.', 'danger')
        return redirect(url_for('tokens.list_tokens'))
    
    form = TokenForm()
    
    if form.validate_on_submit():
        # Проверка, что для Ozon указан Client ID
        if form.marketplace.data == 'ozon' and not form.client_id.data:
            flash('Для Ozon необходимо указать Client ID.', 'warning')
            return render_template('edit_token.html', form=form, token=token)
        
        token.name = form.name.data if form.name.data else None
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
        form.marketplace.data = token.marketplace
        form.token.data = token.token
        form.client_id.data = token.client_id
    
    return render_template('edit_token.html', form=form, token=token)


@tokens_bp.route('/<int:token_id>/delete', methods=['POST'])
@login_required
def delete(token_id):
    """Удаление токена"""
    token = Token.query.get_or_404(token_id)
    
    # Проверка, что токен принадлежит текущему пользователю
    if token.user_id != current_user.id:
        flash('У вас нет прав для удаления этого токена.', 'danger')
        return redirect(url_for('tokens.list_tokens'))
    
    token_display = f'"{token.name}"' if token.name else token.get_marketplace_display()
    db.session.delete(token)
    db.session.commit()
    
    flash(f'Токен {token_display} успешно удален.', 'success')
    return redirect(url_for('tokens.list_tokens'))

