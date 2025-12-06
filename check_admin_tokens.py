from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Находим пользователя Admin
    result = conn.execute(text("SELECT id, username FROM users WHERE username = 'Admin'"))
    user = result.fetchone()
    if user:
        print(f"User: id={user[0]}, username={user[1]}")

        # Находим токены этого пользователя
        result = conn.execute(text("""
            SELECT id, name, marketplace
            FROM tokens
            WHERE user_id = :user_id
        """), {"user_id": user[0]})
        tokens = result.fetchall()
        print(f"\nТокены пользователя Admin:")
        for t in tokens:
            print(f"  id={t[0]}, name={t[1]}, marketplace={t[2]}")
    else:
        print("Пользователь Admin не найден")
