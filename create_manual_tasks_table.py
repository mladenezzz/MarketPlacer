"""
Скрипт для создания таблицы manual_tasks в базе данных
"""
import os
import sys

# Добавляем корневую директорию проекта в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from datacollector.config import DataCollectorConfig

def create_manual_tasks_table():
    """Создание таблицы manual_tasks"""
    engine = create_engine(DataCollectorConfig.DATABASE_URI)

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS manual_tasks (
        id SERIAL PRIMARY KEY,
        token_id INTEGER NOT NULL REFERENCES tokens(id),
        task_type VARCHAR(50) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        started_at TIMESTAMP,
        finished_at TIMESTAMP,
        error_message TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_manual_tasks_status ON manual_tasks(status);
    CREATE INDEX IF NOT EXISTS idx_manual_tasks_created ON manual_tasks(created_at);
    """

    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
        print("Таблица manual_tasks успешно создана")

if __name__ == '__main__':
    create_manual_tasks_table()
