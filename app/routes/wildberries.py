"""Маршруты для раздела Wildberries"""
from flask import Blueprint, render_template
from flask_login import login_required
from datetime import datetime
from app.models import Token, db
from app.models.wildberries import WBGood, WBStock
from app.decorators import section_required
from sqlalchemy import func, text
from collections import defaultdict

wildberries_bp = Blueprint('wildberries', __name__, url_prefix='/wildberries')


@wildberries_bp.route('/article-grouping')
@login_required
@section_required('statistics')
def article_grouping():
    """Страница группировки артикулов WB по imt_id"""
    today = datetime.now().date()

    # Получаем все активные WB токены
    wb_tokens = Token.query.filter_by(
        marketplace='wildberries',
        is_active=True
    ).order_by(Token.name).all()

    if not wb_tokens:
        return render_template('wildberries/article_grouping.html',
                             tokens=[],
                             articles_data={},
                             total_articles=0,
                             total_vendor_codes=0)

    # Словарь данных по артикулам
    # {my_article: {imt_id: [{vendor_code, stocks: {token_id: qty}}]}}
    articles_data = defaultdict(lambda: defaultdict(list))

    # Получаем данные для всех токенов
    token_ids = [t.id for t in wb_tokens]
    token_names = {t.id: t.name or f"Токен {t.id}" for t in wb_tokens}

    # Запрос: vendor_code, imt_id, tech_size, остатки по каждому токену
    # Группируем по vendor_code (суммируем все размеры)
    result = db.session.execute(text("""
        SELECT
            LEFT(g.vendor_code, 4) as my_article,
            g.vendor_code,
            g.imt_id,
            s.token_id,
            COALESCE(SUM(s.quantity), 0) as stock
        FROM wb_goods g
        LEFT JOIN wb_stocks s ON s.product_id = g.id
            AND DATE(s.date) = :today
        WHERE g.imt_id IS NOT NULL
        GROUP BY LEFT(g.vendor_code, 4), g.vendor_code, g.imt_id, s.token_id
        HAVING COALESCE(SUM(s.quantity), 0) > 0
        ORDER BY LEFT(g.vendor_code, 4), g.imt_id, g.vendor_code
    """), {'today': today})

    # Словарь для накопления данных
    # {(my_article, imt_id, vendor_code): {token_id: stock}}
    vendor_stocks = defaultdict(lambda: defaultdict(int))

    for row in result:
        my_article = row.my_article
        vendor_code = row.vendor_code
        imt_id = row.imt_id
        token_id = row.token_id
        stock = int(row.stock)

        key = (my_article, imt_id, vendor_code)
        if token_id:
            vendor_stocks[key][token_id] = stock

    # Преобразуем в структуру для шаблона
    for (my_article, imt_id, vendor_code), stocks in vendor_stocks.items():
        total_stock = sum(stocks.values())
        if total_stock > 0:
            articles_data[my_article][imt_id].append({
                'vendor_code': vendor_code,
                'stocks': dict(stocks),
                'total_stock': total_stock
            })

    # Сортируем vendor_code внутри каждого imt_id
    for my_article in articles_data:
        for imt_id in articles_data[my_article]:
            articles_data[my_article][imt_id].sort(key=lambda x: x['vendor_code'])

    # Преобразуем defaultdict в обычный dict для шаблона
    articles_data = {k: dict(v) for k, v in articles_data.items()}

    # Подсчет статистики
    total_articles = len(articles_data)
    total_vendor_codes = sum(
        len(vendors)
        for imt_groups in articles_data.values()
        for vendors in imt_groups.values()
    )

    return render_template('wildberries/article_grouping.html',
                         tokens=wb_tokens,
                         token_names=token_names,
                         articles_data=articles_data,
                         total_articles=total_articles,
                         total_vendor_codes=total_vendor_codes)
