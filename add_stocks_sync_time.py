"""Add stocks_sync_time column to tokens table"""
from sqlalchemy import create_engine, text
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)

with engine.connect() as conn:
    try:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='tokens' AND column_name='stocks_sync_time'
        """))

        if result.fetchone():
            print("Column stocks_sync_time already exists")
        else:
            # Add column with default value 03:00:00
            conn.execute(text("""
                ALTER TABLE tokens
                ADD COLUMN stocks_sync_time TIME DEFAULT '03:00:00'
            """))
            conn.commit()
            print("Column stocks_sync_time added successfully")

    except Exception as e:
        print(f"Error: {e}")
