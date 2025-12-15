# -*- coding: utf-8 -*-
import pandas as pd

df = pd.read_excel(r"z:\Отчет продаж.xlsx")

# Фильтруем только продажи и возвраты (где есть артикул)
sales_returns = df[df['Тип документа'].isin(['Продажа', 'Возврат'])].copy()

# Группируем продажи по артикулу
sales_df = sales_returns[sales_returns['Тип документа'] == 'Продажа']
sales_grouped = sales_df.groupby('Артикул поставщика').agg({
    'Вайлдберриз реализовал Товар (Пр)': 'sum',
    'К перечислению Продавцу за реализованный Товар': 'sum',
    'Кол-во': 'sum'
}).reset_index()
sales_grouped.columns = ['Артикул', 'Реализация_продаж', 'К_перечислению_продаж', 'Кол_во_продаж']

# Группируем возвраты по артикулу
returns_df = sales_returns[sales_returns['Тип документа'] == 'Возврат']
returns_grouped = returns_df.groupby('Артикул поставщика').agg({
    'Вайлдберриз реализовал Товар (Пр)': 'sum',
    'К перечислению Продавцу за реализованный Товар': 'sum',
    'Кол-во': 'sum'
}).reset_index()
returns_grouped.columns = ['Артикул', 'Реализация_возвр', 'К_перечислению_возвр', 'Кол_во_возвр']

# Объединяем
grouped = sales_grouped.merge(returns_grouped, on='Артикул', how='left')
grouped = grouped.fillna(0)

# Считаем количество продаж и возвратов
sales_count = sales_df.groupby('Артикул поставщика').size()
returns_count = returns_df.groupby('Артикул поставщика').size()
grouped['Продаж'] = grouped['Артикул'].map(sales_count).fillna(0).astype(int)
grouped['Возвратов'] = grouped['Артикул'].map(returns_count).fillna(0).astype(int)

# Чистые значения (продажи МИНУС возвраты)
grouped['Реализация'] = grouped['Реализация_продаж'] - grouped['Реализация_возвр']
grouped['К_перечислению'] = grouped['К_перечислению_продаж'] - grouped['К_перечислению_возвр']

# Общая логистика
total_logistics = df['Услуги по доставке товара покупателю'].sum()

# Распределим логистику пропорционально реализации
total_realization = grouped['Реализация'].sum()
grouped['Логистика'] = grouped['Реализация'] / total_realization * total_logistics

# Итого к оплате по артикулу (приблизительно)
grouped['Итого'] = grouped['К_перечислению'] - grouped['Логистика']

# Сортируем по итого (убыванию)
grouped = grouped.sort_values('Итого', ascending=False)

# Убираем строки без артикула
grouped = grouped[grouped['Артикул'].notna()]

# Прочие расходы
storage = df['Хранение'].sum()
deductions = df['Удержания'].sum()
fines = df['Общая сумма штрафов'].sum()
compensation = df['Компенсация скидки по программе лояльности'].sum()

# Создаем Excel файл
with pd.ExcelWriter(r'z:\Анализ_по_артикулам.xlsx', engine='openpyxl') as writer:
    # Лист 1: Отчет по артикулам
    report_df = grouped[['Артикул', 'Продаж', 'Возвратов', 'Реализация', 'К_перечислению', 'Логистика', 'Итого']].copy()
    report_df.columns = ['Артикул', 'Продаж', 'Возвратов', 'Реализация', 'К перечислению', 'Логистика', 'Итого']

    # Точные суммы из исходных данных
    sales_total = df[df['Тип документа'] == 'Продажа']['К перечислению Продавцу за реализованный Товар'].sum()
    returns_total = df[df['Тип документа'] == 'Возврат']['К перечислению Продавцу за реализованный Товар'].sum()
    total_k_perech = sales_total - returns_total
    total_itogo = total_k_perech - total_logistics

    # Добавляем итоговую строку с точными суммами
    totals = pd.DataFrame([{
        'Артикул': 'ИТОГО',
        'Продаж': int(grouped['Продаж'].sum()),
        'Возвратов': int(grouped['Возвратов'].sum()),
        'Реализация': grouped['Реализация'].sum(),
        'К перечислению': total_k_perech,
        'Логистика': total_logistics,
        'Итого': total_itogo
    }])
    report_df = pd.concat([report_df, totals], ignore_index=True)

    report_df.to_excel(writer, sheet_name='По артикулам', index=False)

    # Лист 2: Прочие расходы
    expenses_data = {
        'Статья расходов': ['Хранение', 'Удержания', 'Штрафы', 'Компенсация лояльности (в К перечислению)', 'ИТОГО ПРОЧИХ РАСХОДОВ'],
        'Сумма': [storage, deductions, fines, compensation, storage + deductions + fines]
    }
    expenses_df = pd.DataFrame(expenses_data)
    expenses_df.to_excel(writer, sheet_name='Прочие расходы', index=False)

    # Лист 3: Финальный расчет (используем точные суммы из исходных данных)
    sales_total = df[df['Тип документа'] == 'Продажа']['К перечислению Продавцу за реализованный Товар'].sum()
    returns_total = df[df['Тип документа'] == 'Возврат']['К перечислению Продавцу за реализованный Товар'].sum()
    к_перечислению = sales_total - returns_total
    логистика = total_logistics
    итого_товар = к_перечислению - логистика
    итого_final = итого_товар - storage - deductions - fines

    final_data = {
        'Показатель': [
            'К перечислению за товар',
            'Логистика',
            'После логистики',
            'Хранение',
            'Удержания',
            'Штрафы',
            'ИТОГО К ОПЛАТЕ (расчет)',
            'Итого к оплате (ЛК WB)'
        ],
        'Сумма': [
            к_перечислению,
            -логистика,
            итого_товар,
            -storage,
            -deductions,
            -fines,
            итого_final,
            482209.38
        ]
    }
    final_df = pd.DataFrame(final_data)
    final_df.to_excel(writer, sheet_name='Итоговый расчет', index=False)

print("Отчёт сохранен в z:\\Анализ_по_артикулам.xlsx")
