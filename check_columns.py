import sys
sys.path.insert(0, 'z:/')
from sqlalchemy import create_engine, text
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
with engine.connect() as conn:
    result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'wb_goods' ORDER BY ordinal_position"))
    for row in result:
        print(row[0])
