"""
Скрипт для назначения пользователя администратором
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db, User

app = create_app()

def make_admin():
    """Назначить пользователя администратором"""
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("В базе данных нет пользователей.")
            return
        
        print(f"Найдено пользователей: {len(users)}")
        print("\nСписок пользователей:")
        
        for user in users:
            role_display = user.get_role_display() if hasattr(user, 'role') else 'Не установлена'
            print(f"  - {user.username} ({user.email}) - Роль: {role_display}")
        
        # Если у первого пользователя нет роли или роль 'user', назначим администратором
        first_user = users[0]
        if not hasattr(first_user, 'role') or first_user.role == 'user':
            first_user.role = 'admin'
            db.session.commit()
            print(f"\n[OK] Пользователь '{first_user.username}' назначен администратором!")
        else:
            print(f"\n[OK] Администратор уже есть: {first_user.username}")

if __name__ == '__main__':
    make_admin()

