from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from app.models import db
from app.models.wildberries import WBGood
from app.services.smb_service import SMBService
from datetime import datetime
import requests
import io

marking_bp = Blueprint('marking', __name__, url_prefix='/marking')


@marking_bp.route('/batch-order')
@login_required
def batch_order():
    """Страница создания пакетного заказа КИЗ"""
    return render_template('marking/batch_order.html')


@marking_bp.route('/api/search-goods')
@login_required
def search_goods():
    """API для поиска товаров по артикулу"""
    article = request.args.get('article', '').strip()

    if not article:
        return jsonify({'success': True, 'data': []})

    # Поиск товаров по началу артикула
    goods = WBGood.query.filter(
        WBGood.vendor_code.ilike(f'{article}%')
    ).order_by(WBGood.vendor_code, WBGood.tech_size).all()

    result = []
    for good in goods:
        if good.gtin:  # Только товары с GTIN
            result.append({
                'id': good.id,
                'article': good.vendor_code,
                'size': good.tech_size or '',
                'gtin': good.gtin,
                'barcode': good.barcode
            })

    return jsonify({'success': True, 'data': result})


@marking_bp.route('/api/invoices')
@login_required
def get_invoices():
    """API для получения списка накладных из 1С"""
    try:
        response = requests.get(
            f"{current_app.config['C1_API_URL']}/sales_list",
            auth=(current_app.config['C1_API_USER'], current_app.config['C1_API_PASSWORD']),
            timeout=10
        )
        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict) or not data.get('success', False):
            return jsonify({'success': False, 'error': 'Не удалось получить список накладных'})

        invoices = data.get('data', {}).get('Реализации', [])

        # Сортируем по дате (от новых к старым)
        invoices.sort(key=lambda x: datetime.fromisoformat(x.get('Дата', '')), reverse=True)

        # Форматируем для фронтенда
        result = []
        for inv in invoices:
            total_quantity = sum(item.get('Количество', 0) for item in inv.get('Товары', []))
            result.append({
                'number': inv.get('Номер', ''),
                'date': inv.get('Дата', ''),
                'total_quantity': total_quantity,
                'items': inv.get('Товары', [])
            })

        return jsonify({'success': True, 'data': result})

    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'error': f'Ошибка при запросе данных: {str(e)}'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Ошибка: {str(e)}'})


@marking_bp.route('/api/goods-by-barcodes', methods=['POST'])
@login_required
def get_goods_by_barcodes():
    """API для получения товаров по штрихкодам (для накладной)"""
    data = request.get_json()
    barcodes = data.get('barcodes', [])

    if not barcodes:
        return jsonify({'success': True, 'data': []})

    # Преобразуем в строки
    barcodes_str = [str(b) for b in barcodes]

    # Поиск товаров по штрихкодам
    goods = WBGood.query.filter(WBGood.barcode.in_(barcodes_str)).all()

    # Создаем маппинг barcode -> good
    barcode_to_good = {}
    for good in goods:
        if good.gtin:
            barcode_to_good[good.barcode] = {
                'id': good.id,
                'article': good.vendor_code,
                'size': good.tech_size or '',
                'gtin': good.gtin,
                'barcode': good.barcode
            }

    return jsonify({'success': True, 'data': barcode_to_good})


@marking_bp.route('/api/create-kiz-order', methods=['POST'])
@login_required
def create_kiz_order():
    """API для создания заказа КИЗ и сохранения на SMB"""
    try:
        data = request.get_json()
        items = data.get('items', [])

        if not items:
            return jsonify({'success': False, 'error': 'Нет позиций в заказе'})

        # Генерируем имя файла
        now = datetime.now()
        filename = now.strftime("KIZ_order_%Y-%m-%d_%H-%M-%S.xlsx")
        folder_name = filename.replace('.xlsx', '')

        # Подготавливаем данные для Excel
        import pandas as pd

        excel_data = []
        for item in items:
            gtin = str(item.get('gtin', ''))
            # Добавляем ведущий ноль если 13 символов
            if len(gtin) == 13:
                gtin = f'0{gtin}'

            excel_data.append({
                'gtin': gtin,
                'quantity': int(item.get('quantity', 0)),
                'cistype': 0,
                'inn_producer': '',
                'name': ''
            })

        # Создаем Excel файл
        df = pd.DataFrame(excel_data)
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)

        # Сохраняем на SMB
        with SMBService() as smb:
            order_path = current_app.config['SMB_KIZ_ORDER_PATH']
            km_path = current_app.config['SMB_KIZ_KM_PATH']

            # Сохраняем файл в папку Заказ КМ
            smb.save_file(f'{order_path}/{filename}', excel_buffer)

            # Создаем папку в КМ
            folder_path = f'{km_path}/{folder_name}'
            if not smb.directory_exists(folder_path):
                smb.create_directory(folder_path)

            # Копируем файл в созданную папку
            excel_buffer.seek(0)
            smb.save_file(f'{folder_path}/{filename}', excel_buffer)

        return jsonify({
            'success': True,
            'message': f'Заказ создан: {filename}',
            'filename': filename,
            'folder': folder_name
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Ошибка при создании заказа: {str(e)}'})
