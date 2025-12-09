"""
Скрипт для обновления размеров и GTIN в таблице wb_goods
"""
import sys
sys.path.insert(0, 'z:/')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import Config
from app.models.wildberries import WBGood

def main():
    engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Сначала проверим текущее состояние
        vendor_codes = ['3032030003', '3032030004', '3032070014']
        goods = session.query(WBGood).filter(WBGood.vendor_code.in_(vendor_codes)).all()

        print("Текущее состояние:")
        for g in goods:
            print(f"  {g.vendor_code} | tech_size={g.tech_size} | wb_size={g.wb_size} | gtin={g.gtin}")

        print("\nГотово!")

    except Exception as e:
        session.rollback()
        print(f"Ошибка: {e}")
        raise
    finally:
        session.close()

if __name__ == '__main__':
    main()
