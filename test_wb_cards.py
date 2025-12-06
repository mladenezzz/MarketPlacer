"""
Тестовый скрипт для получения карточек товаров с Wildberries
и сохранения данных в Excel
"""
import requests
import pandas as pd
import time
from sqlalchemy import create_engine, text
from datetime import datetime

# Подключение к БД
DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'


def get_wb_token_by_name(token_name: str) -> tuple:
    """Получить WB токен по имени из БД"""
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, token
                FROM tokens
                WHERE marketplace = 'wildberries'
                AND name ILIKE :name
                LIMIT 1
            """),
            {"name": f"%{token_name}%"}
        )
        row = result.fetchone()
        if row:
            return row[0], row[1]
        return None, None


def get_wb_cards(api_key: str) -> list:
    """
    Получить все карточки товаров с WB через API

    Используется эндпоинт: POST /content/v2/get/cards/list
    Документация: https://openapi.wildberries.ru/content/api/ru/
    """
    url = "https://content-api.wildberries.ru/content/v2/get/cards/list"

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    all_cards = []
    cursor = {
        "limit": 100  # Максимальный лимит
    }

    while True:
        payload = {
            "settings": {
                "cursor": cursor,
                "filter": {
                    "withPhoto": -1  # Все карточки (с фото и без)
                }
            }
        }

        print(f"Запрос карточек... (получено: {len(all_cards)})")

        # Цикл с обработкой ошибки 429 (Too Many Requests)
        while True:
            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 429:
                print("Ошибка 429 (Too Many Requests), ждем 15 секунд...")
                time.sleep(15)
                continue
            break

        if response.status_code != 200:
            print(f"Ошибка API: {response.status_code}")
            print(response.text)
            break

        data = response.json()
        cards = data.get("cards", [])
        cursor_data = data.get("cursor", {})

        print(f"  Получено в этом запросе: {len(cards)}, total: {cursor_data.get('total')}")

        if not cards:
            print("Карточки закончились")
            break

        all_cards.extend(cards)

        # Получаем курсор для следующей страницы
        # Если получили меньше чем limit - значит это последняя страница
        if len(cards) < 100:
            print("Последняя страница (получено меньше 100)")
            break

        # Если нет данных для курсора - выходим
        if not cursor_data.get("updatedAt") and not cursor_data.get("nmID"):
            print("Нет данных для следующей страницы")
            break

        # Обновляем курсор для следующего запроса
        cursor = {
            "limit": 100,
            "updatedAt": cursor_data.get("updatedAt"),
            "nmID": cursor_data.get("nmID")
        }

    print(f"Всего получено карточек: {len(all_cards)}")
    return all_cards


def cards_to_dataframe(cards: list) -> pd.DataFrame:
    """Преобразовать карточки в DataFrame для сохранения в Excel"""
    rows = []

    for card in cards:
        # Базовая информация о карточке
        nm_id = card.get("nmID")
        imt_id = card.get("imtID")
        vendor_code = card.get("vendorCode", "")
        brand = card.get("brand", "")
        title = card.get("title", "")
        description = card.get("description", "")
        created_at = card.get("createdAt", "")
        updated_at = card.get("updatedAt", "")

        # Размеры (sizes)
        sizes = card.get("sizes", [])

        if sizes:
            for size in sizes:
                # Для каждого размера создаем отдельную строку
                size_name = size.get("techSize", "")
                wb_size = size.get("wbSize", "")
                skus = size.get("skus", [])
                barcode = skus[0] if skus else ""

                rows.append({
                    "nmID": nm_id,
                    "imtID": imt_id,
                    "Артикул поставщика": vendor_code,
                    "Бренд": brand,
                    "Название": title,
                    "Описание": description,
                    "Размер (техн.)": size_name,
                    "Размер WB": wb_size,
                    "Баркод": barcode,
                    "Создан": created_at,
                    "Обновлен": updated_at
                })
        else:
            # Если размеров нет, все равно добавляем карточку
            rows.append({
                "nmID": nm_id,
                "imtID": imt_id,
                "Артикул поставщика": vendor_code,
                "Бренд": brand,
                "Название": title,
                "Описание": description,
                "Размер (техн.)": "",
                "Размер WB": "",
                "Баркод": "",
                "Создан": created_at,
                "Обновлен": updated_at
            })

    return pd.DataFrame(rows)


def main():
    # Ищем токен "ИП Веретельникова"
    token_name = "Веретельникова"

    print(f"Поиск токена с именем '{token_name}'...")
    token_id, api_key = get_wb_token_by_name(token_name)

    if not api_key:
        print(f"Токен с именем '{token_name}' не найден!")
        return

    print(f"Найден токен ID: {token_id}")

    # Получаем карточки товаров
    print("\nПолучение карточек товаров с WB...")
    cards = get_wb_cards(api_key)

    if not cards:
        print("Карточки не найдены!")
        return

    # Преобразуем в DataFrame
    print("\nПреобразование данных...")
    df = cards_to_dataframe(cards)

    # Сохраняем в Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"wb_cards_{token_name}_{timestamp}.xlsx"

    print(f"\nСохранение в файл: {filename}")
    df.to_excel(filename, index=False, engine='openpyxl')

    print(f"\nГотово! Сохранено {len(df)} строк в файл {filename}")
    print(f"Уникальных карточек (nmID): {df['nmID'].nunique()}")


if __name__ == "__main__":
    main()
