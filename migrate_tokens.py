"""Migrate tokens from SQLite to PostgreSQL"""
import sqlite3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import Config

# SQLite connection
sqlite_conn = sqlite3.connect('app.db')
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

# PostgreSQL connection
pg_engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
PgSession = sessionmaker(bind=pg_engine)
pg_session = PgSession()

try:
    # Get all tokens from SQLite
    sqlite_cursor.execute('SELECT * FROM tokens')
    tokens = sqlite_cursor.fetchall()

    print(f"Found {len(tokens)} tokens in SQLite database")

    migrated = 0
    skipped = 0

    for token_row in tokens:
        token_id = token_row['id']
        user_id = token_row['user_id']
        marketplace = token_row['marketplace']
        token = token_row['token']

        # Check if token already exists in PostgreSQL
        existing = pg_session.execute(
            text("SELECT id FROM tokens WHERE id = :id"),
            {'id': token_id}
        ).fetchone()

        if existing:
            print(f"Token {token_id} already exists in PostgreSQL, skipping")
            skipped += 1
            continue

        # Get optional fields safely
        name = token_row['name'] if 'name' in token_row.keys() and token_row['name'] else None
        client_id = token_row['client_id'] if 'client_id' in token_row.keys() and token_row['client_id'] else None

        # Insert token into PostgreSQL
        pg_session.execute(
            text("""
            INSERT INTO tokens (id, user_id, name, marketplace, token, client_id, created_at, updated_at)
            VALUES (:id, :user_id, :name, :marketplace, :token, :client_id, :created_at, :updated_at)
            """),
            {
                'id': token_row['id'],
                'user_id': token_row['user_id'],
                'name': name,
                'marketplace': token_row['marketplace'],
                'token': token_row['token'],
                'client_id': client_id,
                'created_at': token_row['created_at'],
                'updated_at': token_row['updated_at']
            }
        )

        print(f"Migrated token {token_id} (user: {user_id}, marketplace: {marketplace})")
        migrated += 1

    pg_session.commit()

    print(f"\nMigration complete:")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped: {skipped}")
    print(f"  Total: {len(tokens)}")

except Exception as e:
    print(f"Error during migration: {e}")
    pg_session.rollback()
finally:
    sqlite_conn.close()
    pg_session.close()
