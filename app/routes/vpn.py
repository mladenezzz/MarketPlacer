from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from app.models import db, VPNUser
from app.services.vps_service import VPSService, generate_xray_config
import uuid

vpn_bp = Blueprint('vpn', __name__, url_prefix='/server')


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


def get_vps_service():
    """Получить сервис VPS с настройками из конфига"""
    return VPSService(
        host=current_app.config['VPS_HOST'],
        port=current_app.config['VPS_SSH_PORT'],
        username=current_app.config['VPS_SSH_USER'],
        password=current_app.config['VPS_SSH_PASSWORD'],
        private_key=current_app.config['VPS_SSH_KEY']
    )


def sync_xray_config():
    """Синхронизировать конфиг Xray с VPS"""
    users = VPNUser.query.filter_by(is_active=True).all()

    # Защита от записи пустого конфига
    if not users:
        return False, "В базе нет активных пользователей. Сначала импортируйте пользователей с VPS или создайте новых."

    config = generate_xray_config(
        users=users,
        private_key=current_app.config['VLESS_PRIVATE_KEY'],
        short_id=current_app.config['VLESS_SHORT_ID']
    )

    vps = get_vps_service()
    try:
        with vps:
            vps.update_xray_config(config)
        return True, f"Конфигурация успешно обновлена ({len(users)} пользователей)"
    except Exception as e:
        return False, str(e)


@vpn_bp.route('/vless')
@login_required
@admin_required
def vless_users():
    """Страница управления VLESS пользователями"""
    users = VPNUser.query.order_by(VPNUser.created_at.desc()).all()

    # Проверяем статус VPS
    vps_status = None
    try:
        vps = get_vps_service()
        with vps:
            vps_status = vps.get_xray_status()
    except Exception as e:
        vps_status = {'is_active': False, 'error': str(e)}

    return render_template('vpn_users.html',
                          users=users,
                          server_ip=current_app.config['VPS_HOST'],
                          public_key=current_app.config['VLESS_PUBLIC_KEY'],
                          vps_status=vps_status)


@vpn_bp.route('/vless/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_vless_user():
    """Добавление нового VLESS пользователя"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        access_mode = request.form.get('access_mode', 'proxy_only')
        auto_sync = request.form.get('auto_sync') == 'on'

        if not name:
            flash('Имя пользователя обязательно.', 'danger')
            return redirect(url_for('vpn.add_vless_user'))

        # Генерируем уникальный email для Xray
        email = f"{name.lower().replace(' ', '_')}@{access_mode}"

        # Проверяем уникальность email
        existing = VPNUser.query.filter_by(email=email).first()
        if existing:
            flash('Пользователь с таким именем и режимом уже существует.', 'danger')
            return redirect(url_for('vpn.add_vless_user'))

        # Создаём пользователя
        vpn_user = VPNUser(
            name=name,
            email=email,
            access_mode=access_mode,
            created_by_id=current_user.id
        )

        db.session.add(vpn_user)
        db.session.commit()

        flash(f'Пользователь "{name}" успешно создан.', 'success')

        # Автоматическая синхронизация если включена
        if auto_sync:
            success, message = sync_xray_config()
            if success:
                flash('Конфигурация VPS обновлена.', 'success')
            else:
                flash(f'Ошибка синхронизации: {message}', 'warning')

        return redirect(url_for('vpn.vless_users'))

    return render_template('vpn_add_user.html')


@vpn_bp.route('/vless/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def toggle_vless_user(user_id):
    """Включить/выключить пользователя"""
    user = VPNUser.query.get_or_404(user_id)
    user.is_active = not user.is_active
    db.session.commit()

    status = "активирован" if user.is_active else "деактивирован"
    flash(f'Пользователь "{user.name}" {status}.', 'success')
    return redirect(url_for('vpn.vless_users'))


@vpn_bp.route('/vless/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_vless_user(user_id):
    """Удаление пользователя"""
    user = VPNUser.query.get_or_404(user_id)
    name = user.name

    db.session.delete(user)
    db.session.commit()

    flash(f'Пользователь "{name}" удалён.', 'success')
    return redirect(url_for('vpn.vless_users'))


@vpn_bp.route('/vless/<int:user_id>/link')
@login_required
@admin_required
def get_vless_link(user_id):
    """Получить VLESS ссылку для пользователя"""
    user = VPNUser.query.get_or_404(user_id)
    link = user.generate_vless_link(
        server_ip=current_app.config['VPS_HOST'],
        server_port=current_app.config['VLESS_PORT'],
        public_key=current_app.config['VLESS_PUBLIC_KEY'],
        short_id=current_app.config['VLESS_SHORT_ID']
    )
    return jsonify({'link': link, 'name': user.name})


@vpn_bp.route('/vless/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_vless_user(user_id):
    """Редактирование пользователя"""
    user = VPNUser.query.get_or_404(user_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        access_mode = request.form.get('access_mode', user.access_mode)

        if not name:
            flash('Имя пользователя обязательно.', 'danger')
            return redirect(url_for('vpn.edit_vless_user', user_id=user_id))

        # Обновляем email если изменился режим
        new_email = f"{name.lower().replace(' ', '_')}@{access_mode}"

        # Проверяем уникальность нового email (если он изменился)
        if new_email != user.email:
            existing = VPNUser.query.filter_by(email=new_email).first()
            if existing:
                flash('Пользователь с таким именем и режимом уже существует.', 'danger')
                return redirect(url_for('vpn.edit_vless_user', user_id=user_id))

        user.name = name
        user.email = new_email
        user.access_mode = access_mode
        db.session.commit()

        flash(f'Пользователь "{name}" обновлён.', 'success')
        return redirect(url_for('vpn.vless_users'))

    return render_template('vpn_edit_user.html', user=user)


@vpn_bp.route('/vless/sync', methods=['POST'])
@login_required
@admin_required
def sync_vless_config():
    """Синхронизировать конфигурацию с VPS"""
    success, message = sync_xray_config()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': success, 'message': message})

    if success:
        flash(message, 'success')
    else:
        flash(f'Ошибка: {message}', 'danger')

    return redirect(url_for('vpn.vless_users'))


@vpn_bp.route('/vless/status')
@login_required
@admin_required
def vless_status():
    """Получить статус VPS и Xray"""
    try:
        vps = get_vps_service()
        with vps:
            status = vps.get_xray_status()
        return jsonify({'success': True, **status})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@vpn_bp.route('/vless/export-config')
@login_required
@admin_required
def export_xray_config():
    """Экспорт конфигурации Xray для всех активных пользователей"""
    users = VPNUser.query.all()
    config = generate_xray_config(
        users=users,
        private_key=current_app.config['VLESS_PRIVATE_KEY'],
        short_id=current_app.config['VLESS_SHORT_ID']
    )
    return jsonify(config)


@vpn_bp.route('/vless/import', methods=['POST'])
@login_required
@admin_required
def import_vless_users():
    """Импортировать пользователей с VPS сервера"""
    try:
        vps = get_vps_service()
        with vps:
            config = vps.get_xray_config()

        if not config:
            flash('Не удалось прочитать конфигурацию Xray с сервера.', 'danger')
            return redirect(url_for('vpn.vless_users'))

        # Получаем список клиентов из конфига
        clients = []
        for inbound in config.get('inbounds', []):
            if inbound.get('protocol') == 'vless':
                clients.extend(inbound.get('settings', {}).get('clients', []))

        if not clients:
            flash('На сервере не найдено пользователей.', 'warning')
            return redirect(url_for('vpn.vless_users'))

        imported = 0
        skipped = 0

        for client in clients:
            client_uuid = client.get('id')
            client_email = client.get('email', '')

            # Проверяем, существует ли уже пользователь с таким UUID
            existing = VPNUser.query.filter_by(uuid=client_uuid).first()
            if existing:
                skipped += 1
                continue

            # Определяем режим доступа из email
            if '@' in client_email:
                name_part, mode_part = client_email.rsplit('@', 1)
                name = name_part.replace('_', ' ').title()
                if mode_part == 'full':
                    access_mode = 'full'
                elif mode_part == 'lan_only':
                    access_mode = 'lan_only'
                else:
                    access_mode = 'proxy_only'
            else:
                name = client_email or f"User-{client_uuid[:8]}"
                access_mode = 'proxy_only'

            # Создаём пользователя
            vpn_user = VPNUser(
                name=name,
                uuid=client_uuid,
                email=client_email or f"{client_uuid[:8]}@imported",
                access_mode=access_mode,
                created_by_id=current_user.id
            )

            db.session.add(vpn_user)
            imported += 1

        db.session.commit()

        if imported > 0:
            flash(f'Импортировано {imported} пользователей.', 'success')
        if skipped > 0:
            flash(f'Пропущено {skipped} существующих пользователей.', 'info')

    except Exception as e:
        flash(f'Ошибка импорта: {str(e)}', 'danger')

    return redirect(url_for('vpn.vless_users'))
