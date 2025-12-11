# -*- coding: utf-8 -*-
import pandas as pd
import os
from pathlib import Path

# Папка с файлами
folder = Path(r'Y:\YandexDisk\Work\Ольга Бухгалтер')

# Читаем файл себестоимости (без заголовков)
cost_df = pd.read_excel(folder / 'Себестоимость.xlsx', header=None)
# Первый столбец - номер модели, третий - себестоимость
cost_df.columns = ['model', 'unknown', 'cost']
# Создаём словарь модель -> себестоимость
cost_map = dict(zip(cost_df['model'].astype(int), cost_df['cost']))

print(f"Загружено {len(cost_map)} моделей с себестоимостью")
print(f"Примеры: {list(cost_map.items())[:5]}")
print()

# Список отчётов
reports = [
    'Отчет от 02.11.xlsx',
    'Отчет от 09.11.xlsx',
    'Отчет от 16.11.xlsx',
    'Отчет от 23.11.xlsx',
    'Отчет от 30.11.xlsx',
]

# Собираем артикулы без себестоимости
all_missing = set()

for report_name in reports:
    report_path = folder / report_name
    if not report_path.exists():
        print(f"Файл не найден: {report_name}")
        continue

    print(f"Обработка: {report_name}")

    # Читаем отчёт
    df = pd.read_excel(report_path)

    # Находим позицию столбца "Артикул поставщика"
    article_col = 'Артикул поставщика'
    if article_col not in df.columns:
        print(f"  Столбец '{article_col}' не найден!")
        continue

    col_idx = df.columns.get_loc(article_col)

    # Функция для извлечения номера модели из артикула
    def get_model_number(article):
        if pd.isna(article) or str(article).strip() == '':
            return None
        # Берём первые 4 цифры
        article_str = str(article).strip()
        # Извлекаем только цифры в начале
        digits = ''
        for ch in article_str:
            if ch.isdigit():
                digits += ch
            else:
                break
        if len(digits) >= 4:
            return int(digits[:4])
        return None

    # Функция для получения себестоимости
    def get_cost(article):
        if pd.isna(article) or str(article).strip() == '':
            return None  # Не ставим себестоимость если артикул пустой
        model = get_model_number(article)
        if model is None:
            return None
        return cost_map.get(model, None)

    # Добавляем столбец себестоимости
    cost_values = df[article_col].apply(get_cost)

    # Вставляем столбец сразу после "Артикул поставщика"
    # Сначала удаляем если уже есть
    if 'Себестоимость' in df.columns:
        df = df.drop(columns=['Себестоимость'])
        # Пересчитываем индекс
        col_idx = df.columns.get_loc(article_col)

    # Вставляем новый столбец
    df.insert(col_idx + 1, 'Себестоимость', cost_values)

    # Находим артикулы без себестоимости (где артикул есть, но себестоимости нет)
    missing = df[(df[article_col].notna()) &
                 (df[article_col].astype(str).str.strip() != '') &
                 (df['Себестоимость'].isna())][article_col].unique()

    if len(missing) > 0:
        for m in missing:
            all_missing.add(str(m))
        print(f"  Артикулов без себестоимости: {len(missing)}")

    # Сохраняем файл
    df.to_excel(report_path, index=False)
    print(f"  Сохранено: {report_name}")
    print()

print("=" * 50)
print("АРТИКУЛЫ БЕЗ СЕБЕСТОИМОСТИ:")
print("=" * 50)
if all_missing:
    for article in sorted(all_missing):
        model = None
        digits = ''
        for ch in str(article):
            if ch.isdigit():
                digits += ch
            else:
                break
        if len(digits) >= 4:
            model = digits[:4]
        print(f"  {article} (модель: {model})")
else:
    print("  Все артикулы имеют себестоимость")
