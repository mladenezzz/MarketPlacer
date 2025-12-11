# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path

folder = Path(r'Y:\YandexDisk\Work\Ольга Бухгалтер')

# Новые себестоимости
new_costs = {
    2015: 483.12,
    2019: 483.12,
    2020: 483.12,
    2044: 483.12,
    2054: 483.12,
}

reports = ["Отчет от 02.11.xlsx", "Отчет от 09.11.xlsx", "Отчет от 16.11.xlsx", "Отчет от 23.11.xlsx", "Отчет от 30.11.xlsx"]

for report_name in reports:
    report_path = folder / report_name
    df = pd.read_excel(report_path)

    updated = False
    for idx, row in df.iterrows():
        article = row["Артикул поставщика"]
        if pd.isna(article) or str(article).strip() == "":
            continue
        if pd.notna(row["Себестоимость"]):
            continue

        # Извлекаем модель
        article_str = str(article).strip()
        digits = ""
        for ch in article_str:
            if ch.isdigit():
                digits += ch
            else:
                break
        if len(digits) >= 4:
            model = int(digits[:4])
            if model in new_costs:
                df.at[idx, "Себестоимость"] = new_costs[model]
                updated = True

    if updated:
        df.to_excel(report_path, index=False)
        print(f"Обновлено: {report_name}")

print("Готово!")
