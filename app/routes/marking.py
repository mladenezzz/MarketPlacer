from flask import Blueprint, render_template
from flask_login import login_required

marking_bp = Blueprint('marking', __name__, url_prefix='/marking')


@marking_bp.route('/batch-order')
@login_required
def batch_order():
    """Страница создания пакетного заказа КИЗ"""
    return render_template('marking/batch_order.html')
