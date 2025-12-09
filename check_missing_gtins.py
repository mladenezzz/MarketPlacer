import json
import psycopg2

# Загружаем GTIN из файла
with open(r'c:\Users\Mike01\PycharmProjects\MarketPlaceApp\data\gtins.json', 'r', encoding='utf-8') as f:
    gtins_data = json.load(f)

# Функция нормализации размера
def normalize_size(size):
    """Нормализует размер: 9,5 -> 9.5"""
    if size is None:
        return None
    return str(size).replace(',', '.')

# Подключаемся к базе данных PostgreSQL
conn = psycopg2.connect(
    host='192.168.0.44',
    port=5432,
    database='marketplacer',
    user='marketplacer_user',
    password='MarketPlacer2024!Secure'
)
cursor = conn.cursor()

# Получаем все товары WB с артикулами и размерами
cursor.execute('''
    SELECT id, vendor_code, tech_size, gtin
    FROM wb_goods
''')
db_goods = cursor.fetchall()

# Создаём словарь для быстрого поиска: (normalized_article, normalized_size) -> (id, current_gtin, original_size)
db_dict = {}
for row in db_goods:
    id_, vendor_code, tech_size, current_gtin = row
    if vendor_code and tech_size:
        key = (vendor_code.strip(), normalize_size(tech_size))
        db_dict[key] = (id_, current_gtin, tech_size)  # сохраняем оригинальный размер из БД

# Ищем GTIN из файла, которые должны быть в базе, но отсутствуют или отличаются
missing_gtins = []

for item in gtins_data:
    article = item['article']
    gtins = item.get('gtins', {})

    for size, gtin in gtins.items():
        normalized_size = normalize_size(size)
        key = (article, normalized_size)

        if key in db_dict:
            id_, current_gtin, size_in_db = db_dict[key]
            if current_gtin != str(gtin) and current_gtin != gtin:
                missing_gtins.append({
                    'id': id_,
                    'article': article,
                    'size_in_file': size,
                    'size_in_db': size_in_db,
                    'size_normalized': normalized_size,
                    'gtin_from_file': gtin,
                    'current_gtin_in_db': current_gtin
                })

# Обновляем GTIN в базе данных
print(f"Найдено {len(missing_gtins)} GTIN для обновления\n")

updated_count = 0
for item in missing_gtins:
    cursor.execute(
        "UPDATE wb_goods SET gtin = %s WHERE id = %s",
        (str(item['gtin_from_file']), item['id'])
    )
    updated_count += 1
    print(f"Обновлён ID {item['id']}: {item['article']} размер {item['size_in_db']} -> GTIN {item['gtin_from_file']}")

conn.commit()
conn.close()

print(f"\n{'='*50}")
print(f"Обновлено записей: {updated_count}")
