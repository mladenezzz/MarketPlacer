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
    ).all()

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

    def size_sort_key(item):
        """Ключ сортировки размера: запятая = точка"""
        size = item['size'].replace(',', '.')
        try:
            return (0, float(size))
        except ValueError:
            return (1, size)

    result.sort(key=lambda x: (x['article'], size_sort_key(x)))

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


@marking_bp.route('/kiz-search')
@login_required
def kiz_search():
    """Страница поиска КИЗ"""
    return render_template('marking/kiz_search.html')


@marking_bp.route('/api/search-kiz')
@login_required
def search_kiz():
    """API для поиска КИЗ по артикулу или коду маркировки"""
    query = request.args.get('query', '').strip()
    search_type = request.args.get('type', 'article')  # 'article' или 'marking_code'

    if not query:
        return jsonify({'success': True, 'data': []})

    # Путь к папке КМ на SMB шаре
    km_path = current_app.config['SMB_KIZ_KM_PATH']

    results = []

    try:
        with SMBService() as smb:
            if search_type == 'article':
                # Поиск по артикулу - ищем GTIN через базу данных
                goods = WBGood.query.filter(
                    WBGood.vendor_code.ilike(f'{query}%'),
                    WBGood.gtin.isnot(None)
                ).all()

                if not goods:
                    return jsonify({'success': True, 'data': []})

                # Собираем все GTIN для поиска
                gtins = set()
                gtin_to_article = {}
                for good in goods:
                    gtin = good.gtin
                    # Нормализуем GTIN до 14 символов
                    if len(gtin) == 13:
                        gtin = '0' + gtin
                    gtins.add(gtin)
                    gtin_to_article[gtin] = {
                        'article': good.vendor_code,
                        'size': good.tech_size or '',
                        'gtin': good.gtin
                    }

                # Ищем в папках
                results = _search_in_km_folders_smb(smb, km_path, gtins, gtin_to_article)

            else:
                # Поиск по коду маркировки
                results = _search_marking_code_smb(smb, km_path, query)

    except Exception as e:
        return jsonify({'success': False, 'error': f'Ошибка поиска: {str(e)}'})

    return jsonify({'success': True, 'data': results})


def _search_in_km_folders_smb(smb, km_path, gtins, gtin_to_article):
    """Поиск GTIN в CSV файлах в папках КМ через SMB"""
    results = []
    # gtin -> {folder -> count}
    found_folders = {}

    try:
        # Получаем список папок
        folders = smb.list_files(km_path)
    except Exception:
        return results

    for folder_info in folders:
        if not folder_info['is_directory']:
            continue

        folder_name = folder_info['filename']
        folder_path = f"{km_path}/{folder_name}"

        try:
            # Получаем список файлов в папке
            files = smb.list_files(folder_path)
        except Exception:
            continue

        for file_info in files:
            file_name = file_info['filename']
            if file_name.endswith('.csv') and 'Коды_идентификации' in file_name:
                csv_path = f"{folder_path}/{file_name}"

                try:
                    # Читаем CSV файл
                    file_content = smb.read_file(csv_path)
                    content = file_content.read().decode('utf-8')

                    for line in content.split('\n'):
                        line = line.strip()
                        if not line:
                            continue

                        # Код маркировки начинается с 01 + GTIN (14 символов)
                        if line.startswith('01') and len(line) >= 16:
                            gtin_in_code = line[2:16]

                            if gtin_in_code in gtins:
                                if gtin_in_code not in found_folders:
                                    found_folders[gtin_in_code] = {}
                                if folder_name not in found_folders[gtin_in_code]:
                                    found_folders[gtin_in_code][folder_name] = 0
                                found_folders[gtin_in_code][folder_name] += 1
                except Exception:
                    continue

    # Формируем результаты
    for gtin, folders_counts in found_folders.items():
        article_info = gtin_to_article.get(gtin, {})
        for folder, count in folders_counts.items():
            results.append({
                'folder': folder,
                'article': article_info.get('article', ''),
                'size': article_info.get('size', ''),
                'gtin': article_info.get('gtin', gtin),
                'count': count
            })

    # Сортируем по папке
    results.sort(key=lambda x: x['folder'])

    return results


def _search_marking_code_smb(smb, km_path, query):
    """Поиск по части кода маркировки через SMB (регистрозависимый)"""
    results = []
    found_items = []

    try:
        # Получаем список папок
        folders = smb.list_files(km_path)
    except Exception:
        return results

    for folder_info in folders:
        if not folder_info['is_directory']:
            continue

        folder_name = folder_info['filename']
        folder_path = f"{km_path}/{folder_name}"

        try:
            # Получаем список файлов в папке
            files = smb.list_files(folder_path)
        except Exception:
            continue

        for file_info in files:
            file_name = file_info['filename']
            if file_name.endswith('.csv') and 'Коды_идентификации' in file_name:
                csv_path = f"{folder_path}/{file_name}"

                try:
                    # Читаем CSV файл
                    file_content = smb.read_file(csv_path)
                    content = file_content.read().decode('utf-8')

                    for line_num, line in enumerate(content.split('\n'), start=1):
                        line = line.strip()
                        if not line:
                            continue

                        # Ищем совпадение в любой части кода (регистрозависимый поиск)
                        if query in line:
                            gtin = ''
                            if line.startswith('01') and len(line) >= 16:
                                gtin = line[2:16]

                            found_items.append({
                                'folder': folder_name,
                                'marking_code': line,
                                'gtin': gtin,
                                'line_number': line_num
                            })
                except Exception:
                    continue

    # Получаем информацию об артикулах по GTIN
    gtins = set(item['gtin'] for item in found_items if item['gtin'])
    gtin_to_article = {}

    if gtins:
        # Нормализуем GTIN для поиска (убираем ведущий ноль если есть)
        normalized_gtins = set()
        for gtin in gtins:
            normalized_gtins.add(gtin)
            if gtin.startswith('0'):
                normalized_gtins.add(gtin[1:])

        goods = WBGood.query.filter(WBGood.gtin.in_(normalized_gtins)).all()
        for good in goods:
            gtin = good.gtin
            if len(gtin) == 13:
                gtin_to_article['0' + gtin] = {
                    'article': good.vendor_code,
                    'size': good.tech_size or ''
                }
            gtin_to_article[gtin] = {
                'article': good.vendor_code,
                'size': good.tech_size or ''
            }

    # Формируем результаты
    for item in found_items:
        article_info = gtin_to_article.get(item['gtin'], {})
        results.append({
            'folder': item['folder'],
            'marking_code': item['marking_code'],
            'article': article_info.get('article', ''),
            'size': article_info.get('size', ''),
            'gtin': item['gtin'],
            'line_number': item['line_number']
        })

    # Сортируем по папке
    results.sort(key=lambda x: x['folder'])

    return results
