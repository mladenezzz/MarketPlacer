"""
Скрипт для загрузки карточек товаров с Wildberries по всем токенам
и сохранения в таблицу wb_goods
"""
import requests
import time
from sqlalchemy import create_engine, text
from datetime import datetime

# Подключение к БД
DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'


def get_all_wb_tokens() -> list:
    """Получить все WB токены из БД"""
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, name, token
                FROM tokens
                WHERE marketplace = 'wildberries'
                ORDER BY id
            """)
        )
        return [(row[0], row[1], row[2]) for row in result.fetchall()]


def get_wb_cards(api_key: str) -> list:
    """
    Получить все карточки товаров с WB через API
    """
    url = "https://content-api.wildberries.ru/content/v2/get/cards/list"

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    all_cards = []
    cursor = {
        "limit": 100
    }

    while True:
        payload = {
            "settings": {
                "cursor": cursor,
                "filter": {
                    "withPhoto": -1
                }
            }
        }

        print(f"  Запрос карточек... (получено: {len(all_cards)})")

        # Цикл с обработкой ошибки 429 (Too Many Requests) с ограничением попыток
        max_retries = 5
        retry_count = 0
        response = None

        while retry_count < max_retries:
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=30)

                if response.status_code == 429:
                    retry_count += 1
                    print(f"  Ошибка 429 (Too Many Requests), попытка {retry_count}/{max_retries}, ждем 15 секунд...")
                    time.sleep(15)
                    continue
                break
            except requests.exceptions.Timeout:
                retry_count += 1
                print(f"  Таймаут запроса, попытка {retry_count}/{max_retries}...")
                time.sleep(5)
            except requests.exceptions.RequestException as e:
                print(f"  Ошибка запроса: {e}")
                return all_cards

        if response is None or retry_count >= max_retries:
            print("  Превышено количество попыток, пропускаем токен")
            break

        if response.status_code != 200:
            print(f"  Ошибка API: {response.status_code}")
            print(f"  {response.text[:500]}")
            break

        data = response.json()
        cards = data.get("cards", [])
        cursor_data = data.get("cursor", {})

        if not cards:
            print("  Карточки закончились")
            break

        all_cards.extend(cards)

        if len(cards) < 100:
            break

        if not cursor_data.get("updatedAt") and not cursor_data.get("nmID"):
            break

        cursor = {
            "limit": 100,
            "updatedAt": cursor_data.get("updatedAt"),
            "nmID": cursor_data.get("nmID")
        }

    return all_cards


def parse_datetime(dt_str: str):
    """Парсинг даты из API"""
    if not dt_str:
        return None
    try:
        dt_str = dt_str.replace('Z', '+00:00')
        return datetime.fromisoformat(dt_str)
    except (ValueError, TypeError):
        return None


def get_photos_string(card: dict) -> str:
    """Извлечь все ссылки на фото из карточки и объединить в строку"""
    photos = card.get("photos", [])
    if not photos:
        return ""
    # Берём big версию фото, если есть
    photo_urls = []
    for photo in photos:
        url = photo.get("big") or photo.get("c246x328") or photo.get("c516x688") or ""
        if url:
            photo_urls.append(url)
    return ",".join(photo_urls)


def save_cards_to_db(cards: list):
    """Сохранить карточки в БД (без token_id, nm_id, imt_id, с фото)"""
    engine = create_engine(DATABASE_URL)

    inserted = 0
    updated = 0
    skipped = 0

    with engine.connect() as conn:
        for card in cards:
            vendor_code = card.get("vendorCode", "")
            brand = card.get("brand", "")
            title = card.get("title", "")
            description = card.get("description", "")
            card_created_at = parse_datetime(card.get("createdAt"))
            card_updated_at = parse_datetime(card.get("updatedAt"))
            photos = get_photos_string(card)

            sizes = card.get("sizes", [])

            if sizes:
                for size in sizes:
                    tech_size = size.get("techSize", "")
                    wb_size = size.get("wbSize", "")
                    skus = size.get("skus", [])
                    barcode = skus[0] if skus else ""

                    # Проверяем существование записи по barcode
                    existing = conn.execute(
                        text("""
                            SELECT id, photos FROM wb_goods
                            WHERE barcode = :barcode
                        """),
                        {"barcode": barcode}
                    ).fetchone()

                    if existing:
                        # Если запись есть, но фото пустое - обновляем
                        if not existing[1] and photos:
                            conn.execute(
                                text("""
                                    UPDATE wb_goods SET photos = :photos, updated_at = NOW()
                                    WHERE id = :id
                                """),
                                {"photos": photos, "id": existing[0]}
                            )
                            updated += 1
                        else:
                            skipped += 1
                        continue

                    # Вставляем новую запись
                    conn.execute(
                        text("""
                            INSERT INTO wb_goods
                            (vendor_code, brand, title, description,
                             tech_size, wb_size, barcode, photos, card_created_at, card_updated_at)
                            VALUES
                            (:vendor_code, :brand, :title, :description,
                             :tech_size, :wb_size, :barcode, :photos, :card_created_at, :card_updated_at)
                        """),
                        {
                            "vendor_code": vendor_code,
                            "brand": brand,
                            "title": title,
                            "description": description,
                            "tech_size": tech_size,
                            "wb_size": wb_size,
                            "barcode": barcode,
                            "photos": photos,
                            "card_created_at": card_created_at,
                            "card_updated_at": card_updated_at
                        }
                    )
                    inserted += 1
            else:
                # Карточка без размеров - пропускаем, т.к. нет barcode
                skipped += 1

        conn.commit()

    return inserted, updated, skipped


def main():
    print("Загрузка карточек товаров с WB по всем токенам\n")

    # Получаем все WB токены
    tokens = get_all_wb_tokens()
    print(f"Найдено {len(tokens)} WB токенов\n")

    if not tokens:
        print("WB токены не найдены!")
        return

    total_inserted = 0
    total_updated = 0
    total_skipped = 0

    for token_id, token_name, api_key in tokens:
        print(f"Обработка токена: {token_name} (ID: {token_id})")

        # Получаем карточки товаров
        cards = get_wb_cards(api_key)
        print(f"  Получено карточек: {len(cards)}")

        if cards:
            # Сохраняем в БД
            inserted, updated, skipped = save_cards_to_db(cards)
            print(f"  Добавлено: {inserted}, обновлено фото: {updated}, пропущено: {skipped}")
            total_inserted += inserted
            total_updated += updated
            total_skipped += skipped
        else:
            print("  Карточки не найдены")

        print()

    print("=" * 50)
    print(f"Итого добавлено: {total_inserted}")
    print(f"Итого обновлено фото: {total_updated}")
    print(f"Итого пропущено: {total_skipped}")


if __name__ == "__main__":
    main()
