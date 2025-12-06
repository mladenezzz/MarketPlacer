"""
Скрипт для создания таблицы wb_goods в базе данных
"""
from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://marketplacer_user:MarketPlacer2024!Secure@192.168.0.44:5432/marketplacer'

engine = create_engine(DATABASE_URL)

create_table_sql = """
CREATE TABLE IF NOT EXISTS wb_goods (
    id SERIAL PRIMARY KEY,
    token_id INTEGER NOT NULL REFERENCES tokens(id),

    -- Идентификаторы WB
    nm_id BIGINT NOT NULL,
    imt_id BIGINT,

    -- Информация о товаре
    vendor_code VARCHAR(200),
    brand VARCHAR(200),
    title VARCHAR(500),
    description TEXT,

    -- Размер
    tech_size VARCHAR(50),
    wb_size VARCHAR(50),
    barcode VARCHAR(200),

    -- Даты из API
    card_created_at TIMESTAMP,
    card_updated_at TIMESTAMP,

    -- Системные даты
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Уникальный constraint
    CONSTRAINT uq_wb_goods_nm_barcode UNIQUE (nm_id, barcode)
);

-- Создание индексов
CREATE INDEX IF NOT EXISTS idx_wb_goods_token ON wb_goods(token_id);
CREATE INDEX IF NOT EXISTS idx_wb_goods_nm_id ON wb_goods(nm_id);
CREATE INDEX IF NOT EXISTS idx_wb_goods_vendor_code ON wb_goods(vendor_code);
CREATE INDEX IF NOT EXISTS idx_wb_goods_barcode ON wb_goods(barcode);
"""

with engine.connect() as conn:
    conn.execute(text(create_table_sql))
    conn.commit()
    print("Таблица wb_goods успешно создана!")
