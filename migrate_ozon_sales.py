"""
Миграция структуры продаж и заказов Ozon:
1. Создание таблицы ozon_orders для хранения заказов (FBS/FBO постингов)
2. Очистка таблицы ozon_sales (будет заполнена данными из /v3/finance/transaction/list)
"""
from app import create_app, db
from app.models import OzonSale, OzonOrder

app = create_app()
app.app_context().push()

print("=" * 80)
print("МИГРАЦИЯ СТРУКТУРЫ OZON")
print("=" * 80)
print()

# Создание таблицы ozon_orders
print("1. Создание таблицы ozon_orders...")
try:
    db.create_all()
    print("   [OK] Таблица ozon_orders создана")
except Exception as e:
    print(f"   [ERROR] Ошибка при создании таблицы: {e}")

# Очистка таблицы ozon_sales
print("\n2. Очистка таблицы ozon_sales...")
try:
    count_before = OzonSale.query.count()
    print(f"   Записей до очистки: {count_before}")

    # Удаляем все записи
    OzonSale.query.delete()
    db.session.commit()

    count_after = OzonSale.query.count()
    print(f"   Записей после очистки: {count_after}")
    print("   [OK] Таблица ozon_sales очищена")
except Exception as e:
    db.session.rollback()
    print(f"   [ERROR] Ошибка при очистке таблицы: {e}")

print()
print("=" * 80)
print("МИГРАЦИЯ ЗАВЕРШЕНА")
print("=" * 80)
print()
print("ВАЖНО: Теперь нужно запустить datacollector для заполнения таблиц:")
print("  - ozon_sales будет заполнена данными о продажах из /v3/finance/transaction/list")
print("  - ozon_orders будет заполнена данными о заказах из /v2/posting/fbo/list")
