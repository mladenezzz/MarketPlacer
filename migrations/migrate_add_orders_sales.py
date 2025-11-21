"""
Скрипт миграции для добавления таблиц orders и sales в базу данных.
Используется для хранения исторических данных о заказах и продажах для каждого токена.
"""

import sqlite3
import sys
import os

def migrate():
    """Выполнить миграцию базы данных"""
    try:
        # Получаем путь к базе данных
        db_path = 'app.db'
        if not os.path.exists(db_path):
            print(f"[ERROR] База данных '{db_path}' не найдена.")
            print("   Создайте базу данных сначала, запустив приложение.")
            sys.exit(1)
        
        # Подключение к базе данных
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("[INFO] Начинаем миграцию базы данных...")
        print("=" * 60)
        
        # Проверка существования таблиц
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('orders', 'sales')
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        if 'orders' in existing_tables:
            print("[INFO] Таблица 'orders' уже существует.")
        else:
            # Создание таблицы orders
            print("[INFO] Создаем таблицу 'orders'...")
            cursor.execute("""
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_id INTEGER NOT NULL,
                    marketplace VARCHAR(50) NOT NULL,
                    order_type VARCHAR(20),
                    order_id VARCHAR(200) NOT NULL,
                    posting_number VARCHAR(200),
                    order_date TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    price REAL NOT NULL DEFAULT 0.0,
                    price_with_discount REAL,
                    finished_price REAL,
                    raw_data TEXT,
                    FOREIGN KEY (token_id) REFERENCES tokens (id) ON DELETE CASCADE,
                    UNIQUE(token_id, order_id, marketplace)
                )
            """)
            
            # Создание индексов для таблицы orders
            print("[INFO] Создаем индексы для 'orders'...")
            cursor.execute("""
                CREATE INDEX idx_orders_token_id ON orders(token_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_orders_order_id ON orders(order_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_orders_order_date ON orders(order_date)
            """)
            cursor.execute("""
                CREATE INDEX idx_orders_marketplace ON orders(marketplace)
            """)
            print("[OK] Таблица 'orders' создана.")
        
        if 'sales' in existing_tables:
            print("[INFO] Таблица 'sales' уже существует.")
        else:
            # Создание таблицы sales
            print("[INFO] Создаем таблицу 'sales'...")
            cursor.execute("""
                CREATE TABLE sales (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_id INTEGER NOT NULL,
                    marketplace VARCHAR(50) NOT NULL,
                    sale_type VARCHAR(20),
                    sale_id VARCHAR(200) NOT NULL,
                    posting_number VARCHAR(200),
                    sale_date TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    price REAL NOT NULL DEFAULT 0.0,
                    finished_price REAL,
                    raw_data TEXT,
                    FOREIGN KEY (token_id) REFERENCES tokens (id) ON DELETE CASCADE,
                    UNIQUE(token_id, sale_id, marketplace)
                )
            """)
            
            # Создание индексов для таблицы sales
            print("[INFO] Создаем индексы для 'sales'...")
            cursor.execute("""
                CREATE INDEX idx_sales_token_id ON sales(token_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_sales_sale_id ON sales(sale_id)
            """)
            cursor.execute("""
                CREATE INDEX idx_sales_sale_date ON sales(sale_date)
            """)
            cursor.execute("""
                CREATE INDEX idx_sales_marketplace ON sales(marketplace)
            """)
            print("[OK] Таблица 'sales' создана.")
        
        # Сохранение изменений
        conn.commit()
        
        print("=" * 60)
        print("[OK] Миграция успешно завершена!")
        print()
        print("Что было сделано:")
        if 'orders' not in existing_tables:
            print("   [+] Создана таблица 'orders' для хранения заказов")
            print("   [+] Добавлены индексы для оптимизации запросов")
        if 'sales' not in existing_tables:
            print("   [+] Создана таблица 'sales' для хранения продаж")
            print("   [+] Добавлены индексы для оптимизации запросов")
        print("   [+] Настроена связь с таблицей 'tokens'")
        print()
        print("Теперь при добавлении нового токена:")
        print("   - Исторические данные будут сохраняться в базу")
        print("   - Заказы и продажи будут доступны для анализа")
        print("   - Данные не будут теряться при перезапуске")
        print()
        
    except sqlite3.Error as e:
        print(f"[ERROR] Ошибка при миграции базы данных: {e}")
        sys.exit(1)
    
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("    МИГРАЦИЯ БАЗЫ ДАННЫХ - ДОБАВЛЕНИЕ ORDERS И SALES")
    print("=" * 60)
    print()
    
    migrate()
    
    print()
    print("Готово! Теперь данные будут сохраняться в базу.")
    print()

