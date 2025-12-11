import sys
sys.path.insert(0, 'z:/')
from sqlalchemy import create_engine, text
from config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
with engine.connect() as conn:
    # Токен Елена = id 1, сегодня
    # Группируем по vendor_code (без размеров), суммируем остатки
    result = conn.execute(text("""
        SELECT
            LEFT(g.vendor_code, 4) as my_article,
            g.vendor_code,
            g.imt_id,
            COALESCE(SUM(s.quantity), 0) as stock
        FROM wb_goods g
        LEFT JOIN wb_stocks s ON s.product_id = g.id
            AND s.token_id = 1
            AND DATE(s.date) = CURRENT_DATE
        WHERE g.imt_id IS NOT NULL
        GROUP BY LEFT(g.vendor_code, 4), g.vendor_code, g.imt_id
        HAVING COALESCE(SUM(s.quantity), 0) > 0
        ORDER BY LEFT(g.vendor_code, 4), g.imt_id, g.vendor_code
    """))

    current_article = None
    current_imt_id = None
    lines = []
    for row in result:
        my_art, vendor, imt_id, stock = row
        if my_art != current_article:
            if current_article:
                lines.append("")
            lines.append(my_art)
            current_article = my_art
            current_imt_id = None
        if imt_id != current_imt_id:
            if current_imt_id is not None:
                lines.append("")
            lines.append(f"  imt_id={imt_id}")
            current_imt_id = imt_id
        lines.append(f"    {vendor} {stock}шт")

    with open("z:/wb_articles_imt_id.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Записано {len(lines)} строк в z:/wb_articles_imt_id.txt")
