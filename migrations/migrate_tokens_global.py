"""
Скрипт миграции для изменения структуры токенов:
- Удаление привязки токенов к пользователям (user_id)
- Добавление поля is_active для активации/деактивации токенов
- Добавление поля description для описания токенов

Токены становятся глобальными для всех пользователей,
а управление ими доступно только администраторам.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import db
from sqlalchemy import text

app = create_app()


def migrate_tokens_global():
    """Миграция токенов на глобальную структуру"""
    with app.app_context():
        print("=" * 60)
        print("МИГРАЦИЯ: ГЛОБАЛЬНЫЕ ТОКЕНЫ")
        print("=" * 60)
        print()

        try:
            with db.engine.connect() as conn:
                # 1. Добавляем поле is_active, если его нет
                print("1. Проверка поля 'is_active'...")
                try:
                    conn.execute(text(
                        "ALTER TABLE tokens ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL"
                    ))
                    conn.commit()
                    print("   + Поле 'is_active' добавлено")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print("   * Поле 'is_active' уже существует")
                    else:
                        print(f"   ! Предупреждение: {e}")

                # 2. Добавляем поле description, если его нет
                print("2. Проверка поля 'description'...")
                try:
                    conn.execute(text(
                        "ALTER TABLE tokens ADD COLUMN description VARCHAR(500)"
                    ))
                    conn.commit()
                    print("   + Поле 'description' добавлено")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print("   * Поле 'description' уже существует")
                    else:
                        print(f"   ! Предупреждение: {e}")

                # 3. Удаляем внешний ключ user_id (если существует)
                print("3. Удаление привязки к пользователям...")

                # Для PostgreSQL: удаляем constraint и индекс
                try:
                    # Пытаемся удалить foreign key constraint
                    conn.execute(text(
                        "ALTER TABLE tokens DROP CONSTRAINT IF EXISTS tokens_user_id_fkey"
                    ))
                    conn.commit()
                    print("   + Constraint 'tokens_user_id_fkey' удален")
                except Exception as e:
                    print(f"   * Constraint: {e}")

                try:
                    # Пытаемся удалить индекс
                    conn.execute(text(
                        "DROP INDEX IF EXISTS idx_tokens_user_id"
                    ))
                    conn.commit()
                    print("   + Индекс 'idx_tokens_user_id' удален")
                except Exception as e:
                    print(f"   * Индекс: {e}")

                # 4. Удаляем колонку user_id
                print("4. Удаление колонки 'user_id'...")
                try:
                    conn.execute(text(
                        "ALTER TABLE tokens DROP COLUMN IF EXISTS user_id"
                    ))
                    conn.commit()
                    print("   + Колонка 'user_id' удалена")
                except Exception as e:
                    if "does not exist" in str(e).lower():
                        print("   * Колонка 'user_id' уже отсутствует")
                    else:
                        print(f"   ! Предупреждение: {e}")

                # 5. Активируем все существующие токены
                print("5. Активация всех существующих токенов...")
                result = conn.execute(text(
                    "UPDATE tokens SET is_active = TRUE WHERE is_active IS NULL"
                ))
                conn.commit()
                print(f"   + Обновлено токенов: {result.rowcount}")

            print()
            print("=" * 60)
            print("МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!")
            print("=" * 60)
            print()
            print("Что изменилось:")
            print("  - Токены теперь глобальные (не привязаны к пользователям)")
            print("  - Добавлено поле is_active для включения/выключения токенов")
            print("  - Добавлено поле description для описания")
            print()
            print("Доступ к токенам:")
            print("  - Управление токенами: только администраторы")
            print("  - Просмотр данных: все пользователи видят данные со всех активных токенов")
            print()

        except Exception as e:
            print(f"\nОШИБКА при миграции: {e}")
            print("\nПроверьте:")
            print("  1. Подключение к базе данных")
            print("  2. Права доступа к таблице tokens")
            sys.exit(1)


if __name__ == '__main__':
    migrate_tokens_global()
