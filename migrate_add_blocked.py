"""
Скрипт миграции для добавления поля is_blocked в таблицу users
"""
from app import app
from models import db
from sqlalchemy import text

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

