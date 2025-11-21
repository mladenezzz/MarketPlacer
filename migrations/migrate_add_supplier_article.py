# -*- coding: utf-8 -*-
"""
Migration to add supplier_article field to orders and sales tables
"""
from app import create_app
from app.models import db

app = create_app()

with app.app_context():
    print("Adding supplier_article field to orders and sales tables...")
    
    try:
        # Add supplier_article field to orders table
        with db.engine.connect() as conn:
            # Check if field exists
            result = conn.execute(db.text("PRAGMA table_info(orders)"))
            columns = [row[1] for row in result]
            
            if 'supplier_article' not in columns:
                conn.execute(db.text("ALTER TABLE orders ADD COLUMN supplier_article VARCHAR(200)"))
                conn.commit()
                print("+ supplier_article field added to orders table")
            else:
                print("+ supplier_article field already exists in orders table")
            
            # Add index
            try:
                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_orders_supplier_article ON orders (supplier_article)"))
                conn.commit()
                print("+ Index for supplier_article created in orders table")
            except Exception as e:
                print(f"  Index already exists or error: {e}")
        
        # Add supplier_article field to sales table
        with db.engine.connect() as conn:
            result = conn.execute(db.text("PRAGMA table_info(sales)"))
            columns = [row[1] for row in result]
            
            if 'supplier_article' not in columns:
                conn.execute(db.text("ALTER TABLE sales ADD COLUMN supplier_article VARCHAR(200)"))
                conn.commit()
                print("+ supplier_article field added to sales table")
            else:
                print("+ supplier_article field already exists in sales table")
            
            # Add index
            try:
                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_sales_supplier_article ON sales (supplier_article)"))
                conn.commit()
                print("+ Index for supplier_article created in sales table")
            except Exception as e:
                print(f"  Index already exists or error: {e}")
        
        print("\n+ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n- Error during migration: {e}")
        import traceback
        traceback.print_exc()

