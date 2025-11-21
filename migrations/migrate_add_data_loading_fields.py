"""
Миграция для добавления полей отслеживания загрузки данных в таблицу tokens
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, Token
import sqlite3

app = create_app()

def migrate():
    """Выполнить миграцию базы данных"""
    with app.app_context():
        try:
            # Получаем путь к базе данных
            db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
            
            if not os.path.exists(db_path):
                print("База данных не найдена. Создайте её сначала.")
                return
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Проверяем, существует ли таблица tokens
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='tokens'
            """)
            
            if not cursor.fetchone():
                print("Таблица 'tokens' не найдена.")
                print("Пожалуйста, сначала выполните migrate_add_tokens.py")
                conn.close()
                return
            
            # Проверяем, существуют ли уже новые поля
            cursor.execute("PRAGMA table_info(tokens)")
            columns = [column[1] for column in cursor.fetchall()]
            
            fields_to_add = [
                ('data_loading_status', 'VARCHAR(20) DEFAULT "pending"'),
                ('data_loading_progress', 'INTEGER DEFAULT 0'),
                ('data_loading_total_periods', 'INTEGER DEFAULT 0'),
                ('data_loading_loaded_periods', 'INTEGER DEFAULT 0'),
                ('data_loading_started_at', 'TIMESTAMP'),
                ('data_loading_completed_at', 'TIMESTAMP'),
                ('data_loading_error', 'TEXT')
            ]
            
            added_fields = []
            for field_name, field_type in fields_to_add:
                if field_name not in columns:
                    try:
                        cursor.execute(f"ALTER TABLE tokens ADD COLUMN {field_name} {field_type}")
                        added_fields.append(field_name)
                        print(f"  ✓ Добавлено поле: {field_name}")
                    except sqlite3.Error as e:
                        print(f"  ✗ Ошибка при добавлении поля {field_name}: {e}")
                else:
                    print(f"  - Поле {field_name} уже существует")
            
            if added_fields:
                conn.commit()
                print("\n" + "=" * 60)
                print("✅ Миграция успешно завершена!")
                print(f"   Добавлено полей: {len(added_fields)}")
            else:
                print("\n" + "=" * 60)
                print("ℹ️  Все поля уже существуют. Миграция не требуется.")
            
            conn.close()
            
        except sqlite3.Error as e:
            print(f"\n❌ Ошибка SQLite: {e}")
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("  MIGRATION: ADD DATA LOADING FIELDS TO TOKENS")
    print("=" * 60)
    print()
    migrate()

