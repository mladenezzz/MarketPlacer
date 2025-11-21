"""
Скрипт для создания первого администратора
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, User

app = create_app()

def create_admin():
    """Создать администратора"""
    with app.app_context():
        # Проверяем, существует ли уже пользователь с таким email или username
        existing_user = User.query.filter(
            (User.email == 'mveretelnikov@gmail.com') | 
            (User.username == 'Admin')
        ).first()
        
        if existing_user:
            # Обновляем существующего пользователя
            existing_user.username = 'Admin'
            existing_user.email = 'mveretelnikov@gmail.com'
            existing_user.set_password('Lvl23party')
            existing_user.role = 'admin'
            existing_user.is_blocked = False
            db.session.commit()
            print(f"[OK] Пользователь '{existing_user.username}' обновлен и назначен администратором!")
            print(f"     Email: {existing_user.email}")
            print(f"     Роль: {existing_user.get_role_display()}")
        else:
            # Создаем нового администратора
            admin = User(
                username='Admin',
                email='mveretelnikov@gmail.com',
                role='admin',
                is_blocked=False
            )
            admin.set_password('Lvl23party')
            
            db.session.add(admin)
            db.session.commit()
            
            print(f"[OK] Администратор '{admin.username}' успешно создан!")
            print(f"     Email: {admin.email}")
            print(f"     Роль: {admin.get_role_display()}")
            print(f"     ID: {admin.id}")

if __name__ == '__main__':
    create_admin()

