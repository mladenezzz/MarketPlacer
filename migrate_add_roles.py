"""
Скрипт миграции для добавления ролей к существующим пользователям
"""
from app import app
from models import db, User
from sqlalchemy import text

def migrate_add_roles():
    """Добавить поле роли к существующим пользователям"""
    with app.app_context():
        print("Начало миграции...")
        
        # Пробуем добавить колонку role, если её ещё нет
        try:
            # Проверяем, существует ли колонка role
            with db.engine.connect() as conn:
                # Пытаемся добавить колонку role
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user' NOT NULL"))
                    conn.commit()
                    print("Колонка 'role' успешно добавлена в таблицу users.")
                except Exception as e:
                    if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                        print("Колонка 'role' уже существует.")
                    else:
                        print(f"Предупреждение при добавлении колонки: {e}")
            
            # Получаем все пользователи
            users = User.query.all()
            
            if not users:
                print("Нет пользователей в базе данных.")
                print("Создайте первого администратора...")
                
                # Создаем первого администратора
                username = input("Введите имя пользователя для первого администратора: ")
                email = input("Введите email: ")
                password = input("Введите пароль: ")
                
                admin = User(username=username, email=email, role='admin')
                admin.set_password(password)
                
                db.session.add(admin)
                db.session.commit()
                
                print(f"\nПервый администратор '{username}' успешно создан!")
            else:
                print(f"Найдено пользователей: {len(users)}")
                
                # Проверяем, есть ли хотя бы один администратор
                admin_exists = any(user.role == 'admin' for user in users if hasattr(user, 'role'))
                
                if not admin_exists:
                    print("\nВ системе нет администраторов.")
                    print("Список пользователей:")
                    for i, user in enumerate(users, 1):
                        print(f"{i}. {user.username} ({user.email})")
                    
                    choice = input("\nВведите номер пользователя, которого сделать администратором: ")
                    try:
                        user_index = int(choice) - 1
                        if 0 <= user_index < len(users):
                            selected_user = users[user_index]
                            selected_user.role = 'admin'
                            db.session.commit()
                            print(f"\nПользователь '{selected_user.username}' назначен администратором!")
                        else:
                            print("Неверный номер пользователя.")
                    except ValueError:
                        print("Ошибка: введите число.")
                else:
                    print("\nВ системе уже есть администратор(ы).")
                    
                print("\nМиграция завершена успешно!")
                
        except Exception as e:
            print(f"Ошибка при миграции: {e}")
            print("\nПопробуйте удалить файл app.db и запустить приложение заново.")

if __name__ == '__main__':
    migrate_add_roles()

