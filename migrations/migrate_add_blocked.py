"""
Скрипт миграции для добавления поля is_blocked в таблицу users
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from sqlalchemy import text

app = create_app()

def migrate():
    with app.app_context():
        try:
            # Проверяем, существует ли уже колонка
            result = db.session.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result]
            
            if 'is_blocked' not in columns:
                print("Dobavlenie kolonki is_blocked v tablicu users...")
                db.session.execute(text("ALTER TABLE users ADD COLUMN is_blocked BOOLEAN DEFAULT 0 NOT NULL"))
                db.session.commit()
                print("[OK] Kolonka is_blocked uspeshno dobavlena")
            else:
                print("[OK] Kolonka is_blocked uzhe suschestvuet")
                
        except Exception as e:
            print(f"[ERROR] Oshibka pri migracii: {e}")
            db.session.rollback()
            raise

if __name__ == '__main__':
    migrate()

