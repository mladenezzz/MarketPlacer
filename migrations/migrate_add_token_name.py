"""
Скрипт миграции для добавления поля 'name' в таблицу tokens.
Позволяет пользователям давать каждому токену уникальное название.
"""

import sqlite3
import sys

def migrate():
    """Perform database migration"""
    try:
        # Connect to database
        conn = sqlite3.connect('app.db')
        cursor = conn.cursor()
        
        print("Starting migration...")
        print("=" * 60)
        
        # Check if tokens table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='tokens'
        """)
        
        if not cursor.fetchone():
            print("ERROR: Table 'tokens' not found!")
            print("Please run migrate_add_tokens.py first")
            conn.close()
            sys.exit(1)
        
        # Check if name field already exists
        cursor.execute("PRAGMA table_info(tokens)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'name' in columns:
            print("INFO: Field 'name' already exists in 'tokens' table.")
            print("Migration not required.")
            conn.close()
            return
        
        # Add name field
        print("Adding 'name' field to 'tokens' table...")
        cursor.execute("""
            ALTER TABLE tokens ADD COLUMN name VARCHAR(100)
        """)
        
        # Commit changes
        conn.commit()
        
        print("=" * 60)
        print("Migration completed successfully!")
        print()
        print("What was done:")
        print("  - Added 'name' field to 'tokens' table")
        print()
        print("Users can now:")
        print("  - Give each token a unique name")
        print("  - Use multiple tokens for one marketplace")
        print("  - Easily distinguish tokens by their names")
        print()
        
    except sqlite3.Error as e:
        print(f"ERROR during migration: {e}")
        sys.exit(1)
    
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("  MIGRATION: ADD TOKEN NAME FIELD")
    print("=" * 60)
    print()
    
    migrate()
    
    print()
    print("Done! You can now run the application:")
    print("   python run.py")
    print()

