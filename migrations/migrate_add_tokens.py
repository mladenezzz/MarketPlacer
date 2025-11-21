"""
Скрипт миграции для добавления таблицы tokens в базу данных.
Используется для обновления существующей базы данных с добавлением функциональности управления токенами.
"""

import sqlite3
import sys
from datetime import datetime

def migrate():
    """Выполнить миграцию базы данных"""
    try:
        # Подключение к базе данных
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        
        print("🔄 Начинаем миграцию базы данных...")
        print("=" * 60)
        
        # Проверка существования таблицы tokens
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='tokens'
        """)
        
        if cursor.fetchone():
            print("ℹ️  Таблица 'tokens' уже существует.")
            response = input("❓ Пересоздать таблицу? (yes/no): ").strip().lower()
            
            if response == 'yes':
                print("🗑️  Удаляем существующую таблицу...")
                cursor.execute("DROP TABLE tokens")
                print("✅ Таблица удалена.")
            else:
                print("❌ Миграция отменена.")
                conn.close()
                return
        
        # Создание таблицы tokens
        print("📝 Создаем таблицу 'tokens'...")
        cursor.execute("""
            CREATE TABLE tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                marketplace VARCHAR(50) NOT NULL,
                token VARCHAR(500) NOT NULL,
                client_id VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """)
        
        # Создание индексов для оптимизации запросов
        print("📊 Создаем индексы...")
        cursor.execute("""
            CREATE INDEX idx_tokens_user_id ON tokens(user_id)
        """)
        cursor.execute("""
            CREATE INDEX idx_tokens_marketplace ON tokens(marketplace)
        """)
        
        # Сохранение изменений
        conn.commit()
        
        print("=" * 60)
        print("✅ Миграция успешно завершена!")
        print()
        print("📋 Что было сделано:")
        print("   ✓ Создана таблица 'tokens'")
        print("   ✓ Добавлены индексы для оптимизации")
        print("   ✓ Настроена связь с таблицей 'users'")
        print()
        print("🚀 Теперь пользователи могут:")
        print("   • Добавлять токены Wildberries")
        print("   • Добавлять токены и Client ID для Ozon")
        print("   • Редактировать свои токены")
        print("   • Удалять токены из личного кабинета")
        print()
        print("📍 Токены доступны в меню: Профиль → Настройки → Токены API")
        
    except sqlite3.Error as e:
        print(f"❌ Ошибка при миграции базы данных: {e}")
        sys.exit(1)
    
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════════╗
║         МИГРАЦИЯ БАЗЫ ДАННЫХ - ДОБАВЛЕНИЕ ТОКЕНОВ         ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    migrate()
    
    print()
    print("✨ Готово! Можете запускать приложение:")
    print("   python run.py")
    print()

