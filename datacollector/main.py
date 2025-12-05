import logging
import time
import signal
import sys
import threading
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datacollector.config import DataCollectorConfig
from datacollector.collectors.wildberries import WildberriesCollector
from datacollector.collectors.ozon import OzonCollector
from datacollector.queue_manager import TaskQueue, Task, TaskPriority
from datacollector.worker import WorkerPool
from app.models import Token, WBStock, OzonStock
from app.models.sync import ManualTask

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)

running = True
collectors = {}
task_queue = None
worker_pool = None


def signal_handler(sig, frame):
    global running
    logger.info("Shutting down gracefully...")
    running = False


def initialize_collectors():
    """Initialize collectors for all tokens"""
    logger.info("Initializing collectors for all tokens...")

    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Initialize Wildberries collectors
        wb_tokens = session.query(Token).filter_by(marketplace='wildberries').all()
        logger.info(f"Found {len(wb_tokens)} Wildberries tokens")

        for token in wb_tokens:
            logger.info(f"Creating Wildberries collector for token {token.id} ({token.name})")
            collector = WildberriesCollector(
                token_id=token.id,
                token=token.token,
                database_uri=DataCollectorConfig.DATABASE_URI
            )
            collectors[token.id] = collector

        # Initialize Ozon collectors
        ozon_tokens = session.query(Token).filter_by(marketplace='ozon').all()
        logger.info(f"Found {len(ozon_tokens)} Ozon tokens")

        for token in ozon_tokens:
            logger.info(f"Creating Ozon collector for token {token.id} ({token.name})")
            collector = OzonCollector(
                token_id=token.id,
                client_id=token.client_id,
                api_key=token.token,
                database_uri=DataCollectorConfig.DATABASE_URI
            )
            collectors[token.id] = collector

    except Exception as e:
        logger.error(f"Error initializing collectors: {e}")
    finally:
        session.close()

    logger.info("Initialization complete")


def check_and_load_today_stocks():
    """Check if today's stocks exist, if not - load goods first, then stocks"""
    logger.info("Checking today's stocks...")

    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        today = datetime.now(timezone.utc).date()

        # Check Wildberries stocks
        wb_tokens = session.query(Token).filter_by(marketplace='wildberries').all()
        for token in wb_tokens:
            stocks_count = session.query(WBStock).filter_by(
                token_id=token.id,
                date=today
            ).count()

            if stocks_count == 0:
                logger.info(f"No WB stocks found for token {token.id} ({token.name}) for today, adding goods and stocks to queue")
                # Сначала товары, потом остатки
                task_queue.add_task(Task(token.id, 'goods', TaskPriority.HIGH))
                task_queue.add_task(Task(token.id, 'stocks', TaskPriority.HIGH))
            else:
                logger.info(f"WB stocks for token {token.id} ({token.name}) already exist for today ({stocks_count} records)")

        # Check Ozon stocks
        ozon_tokens = session.query(Token).filter_by(marketplace='ozon').all()
        for token in ozon_tokens:
            stocks_count = session.query(OzonStock).filter_by(
                token_id=token.id,
                date=today
            ).count()

            if stocks_count == 0:
                logger.info(f"No Ozon stocks found for token {token.id} ({token.name}) for today, adding to queue")
                task = Task(token.id, 'ozon_stocks', TaskPriority.HIGH)
                task_queue.add_task(task)
            else:
                logger.info(f"Ozon stocks for token {token.id} ({token.name}) already exist for today ({stocks_count} records)")

    except Exception as e:
        logger.error(f"Error checking today's stocks: {e}")
    finally:
        session.close()


def schedule_initial_tasks():
    """Schedule initial data collection tasks"""
    logger.info("Scheduling initial tasks...")

    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        from app.models import SyncState

        # Schedule Wildberries tasks - only sales and orders initially
        wb_tokens = session.query(Token).filter_by(marketplace='wildberries').all()
        for token in wb_tokens:
            sync_state = session.query(SyncState).filter_by(
                token_id=token.id,
                endpoint='sales'
            ).first()

            if not sync_state or not sync_state.last_successful_sync:
                logger.info(f"Scheduling initial WB collection for token {token.id} ({token.name})")
                task_queue.add_task(Task(token.id, 'sales', TaskPriority.HIGH))
                task_queue.add_task(Task(token.id, 'orders', TaskPriority.HIGH))
            else:
                logger.info(f"WB token {token.id} ({token.name}) already synced, scheduling normal updates")
                task_queue.add_task(Task(token.id, 'sales', TaskPriority.NORMAL))
                task_queue.add_task(Task(token.id, 'orders', TaskPriority.NORMAL))

        # Schedule Ozon tasks - sales and orders
        ozon_tokens = session.query(Token).filter_by(marketplace='ozon').all()
        for token in ozon_tokens:
            sync_state = session.query(SyncState).filter_by(
                token_id=token.id,
                endpoint='ozon_sales'
            ).first()

            if not sync_state or not sync_state.last_successful_sync:
                logger.info(f"Scheduling initial Ozon collection for token {token.id} ({token.name})")
                task_queue.add_task(Task(token.id, 'ozon_sales', TaskPriority.HIGH))
                task_queue.add_task(Task(token.id, 'ozon_orders', TaskPriority.HIGH))
            else:
                logger.info(f"Ozon token {token.id} ({token.name}) already synced, scheduling normal updates")
                task_queue.add_task(Task(token.id, 'ozon_sales', TaskPriority.NORMAL))
                task_queue.add_task(Task(token.id, 'ozon_orders', TaskPriority.NORMAL))

    except Exception as e:
        logger.error(f"Error scheduling initial tasks: {e}")
    finally:
        session.close()


def schedule_regular_updates_10min():
    """Schedule 10-minute data updates (sales and orders only)"""
    logger.info("Scheduling 10-minute updates (sales and orders)...")

    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Schedule Wildberries sales and orders
        wb_tokens = session.query(Token).filter_by(marketplace='wildberries').all()
        for token in wb_tokens:
            task_queue.add_task(Task(token.id, 'sales', TaskPriority.NORMAL))
            task_queue.add_task(Task(token.id, 'orders', TaskPriority.NORMAL))

        # Schedule Ozon sales and orders
        ozon_tokens = session.query(Token).filter_by(marketplace='ozon').all()
        for token in ozon_tokens:
            task_queue.add_task(Task(token.id, 'ozon_sales', TaskPriority.NORMAL))
            task_queue.add_task(Task(token.id, 'ozon_orders', TaskPriority.NORMAL))

        logger.info(f"Scheduled 10-min updates for {len(wb_tokens)} WB tokens and {len(ozon_tokens)} Ozon tokens")

    except Exception as e:
        logger.error(f"Error scheduling 10-min updates: {e}")
    finally:
        session.close()


def schedule_hourly_updates():
    """Schedule hourly updates (goods, stocks and supply orders)"""
    logger.info("Scheduling hourly updates (goods, stocks and supply orders)...")

    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Schedule Wildberries goods (first), then stocks and incomes
        wb_tokens = session.query(Token).filter_by(marketplace='wildberries').all()
        for token in wb_tokens:
            # Сначала собираем товары, потом остатки
            task_queue.add_task(Task(token.id, 'goods', TaskPriority.NORMAL))
            task_queue.add_task(Task(token.id, 'stocks', TaskPriority.NORMAL))
            task_queue.add_task(Task(token.id, 'incomes', TaskPriority.NORMAL))

        # Schedule Ozon stocks and supply orders
        ozon_tokens = session.query(Token).filter_by(marketplace='ozon').all()
        for token in ozon_tokens:
            task_queue.add_task(Task(token.id, 'ozon_stocks', TaskPriority.NORMAL))
            task_queue.add_task(Task(token.id, 'ozon_supply_orders', TaskPriority.NORMAL))

        logger.info(f"Scheduled hourly updates for {len(wb_tokens)} WB tokens and {len(ozon_tokens)} Ozon tokens")

    except Exception as e:
        logger.error(f"Error scheduling hourly updates: {e}")
    finally:
        session.close()


def schedule_daily_stocks():
    """Schedule daily stocks collection at configured time"""
    logger.info("Scheduling daily stocks collection...")

    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Schedule Wildberries goods first, then stocks
        wb_tokens = session.query(Token).filter_by(marketplace='wildberries').all()
        for token in wb_tokens:
            # Сначала товары, потом остатки
            task_queue.add_task(Task(token.id, 'goods', TaskPriority.HIGH))
            task_queue.add_task(Task(token.id, 'stocks', TaskPriority.HIGH))
            logger.info(f"Scheduled WB goods and stocks collection for token {token.id} ({token.name})")

        # Schedule Ozon stocks
        ozon_tokens = session.query(Token).filter_by(marketplace='ozon').all()
        for token in ozon_tokens:
            task = Task(token.id, 'ozon_stocks', TaskPriority.HIGH)
            task_queue.add_task(task)
            logger.info(f"Scheduled Ozon stocks collection for token {token.id} ({token.name})")

        logger.info(f"Scheduled stocks collection for {len(wb_tokens)} WB tokens and {len(ozon_tokens)} Ozon tokens")

    except Exception as e:
        logger.error(f"Error scheduling daily stocks: {e}")
    finally:
        session.close()


def retry_queue_processor():
    """Background thread to process retry queue"""
    logger.info("Retry queue processor started")

    while running:
        try:
            task_queue.process_retry_queue()
            time.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Error in retry queue processor: {e}")
            time.sleep(60)

    logger.info("Retry queue processor stopped")


def process_manual_tasks():
    """Background thread to process manual tasks from database"""
    logger.info("Manual tasks processor started")

    while running:
        try:
            engine = create_engine(DataCollectorConfig.DATABASE_URI)
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                # Получаем pending задачи
                pending_tasks = session.query(ManualTask).filter_by(status='pending').all()

                for manual_task in pending_tasks:
                    # Помечаем как processing
                    manual_task.status = 'processing'
                    manual_task.started_at = datetime.now(timezone.utc)
                    session.commit()

                    # Получаем токен
                    token = session.query(Token).filter_by(id=manual_task.token_id).first()
                    if not token:
                        manual_task.status = 'failed'
                        manual_task.error_message = 'Token not found'
                        manual_task.finished_at = datetime.now(timezone.utc)
                        session.commit()
                        continue

                    # Добавляем задачи в очередь
                    if token.marketplace == 'wildberries':
                        if manual_task.task_type == 'stocks':
                            task_queue.add_task(Task(token.id, 'goods', TaskPriority.HIGH))
                            task_queue.add_task(Task(token.id, 'stocks', TaskPriority.HIGH))
                        else:
                            task_queue.add_task(Task(token.id, manual_task.task_type, TaskPriority.HIGH))
                    elif token.marketplace == 'ozon':
                        if manual_task.task_type == 'stocks':
                            task_queue.add_task(Task(token.id, 'ozon_stocks', TaskPriority.HIGH))
                        else:
                            task_queue.add_task(Task(token.id, f'ozon_{manual_task.task_type}', TaskPriority.HIGH))

                    # Помечаем как completed
                    manual_task.status = 'completed'
                    manual_task.finished_at = datetime.now(timezone.utc)
                    session.commit()

                    logger.info(f"Manual task {manual_task.id} processed: {token.marketplace} {manual_task.task_type}")

            except Exception as e:
                logger.error(f"Error processing manual tasks: {e}")
                session.rollback()
            finally:
                session.close()

            time.sleep(5)  # Check every 5 seconds

        except Exception as e:
            logger.error(f"Error in manual tasks processor: {e}")
            time.sleep(5)

    logger.info("Manual tasks processor stopped")


def stocks_scheduler():
    """Background thread to schedule daily stocks collection"""
    logger.info("Stocks scheduler started")

    last_stocks_date = None

    while running:
        try:
            now = datetime.now(timezone.utc)
            today = now.date()

            # Check if we need to run stocks collection
            # Default time is 3:00 AM UTC, but can be configured per token
            if last_stocks_date != today and now.hour >= 3:
                logger.info("Time for daily stocks collection")
                schedule_daily_stocks()
                last_stocks_date = today

            time.sleep(300)  # Check every 5 minutes

        except Exception as e:
            logger.error(f"Error in stocks scheduler: {e}")
            time.sleep(300)

    logger.info("Stocks scheduler stopped")


def main():
    global task_queue, worker_pool

    logger.info("Starting MarketPlacer DataCollector...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Initialize task queue
    task_queue = TaskQueue()

    # Initialize collectors
    initialize_collectors()

    # Check and load today's stocks if needed
    check_and_load_today_stocks()

    # Schedule initial tasks
    schedule_initial_tasks()

    # Start worker pool (3 workers)
    worker_pool = WorkerPool(num_workers=3, task_queue=task_queue, collectors=collectors)
    worker_pool.start()

    # Start retry queue processor in background
    retry_thread = threading.Thread(target=retry_queue_processor, daemon=True)
    retry_thread.start()

    # Start stocks scheduler in background (daily at 3 AM)
    stocks_thread = threading.Thread(target=stocks_scheduler, daemon=True)
    stocks_thread.start()

    # Start manual tasks processor in background
    manual_tasks_thread = threading.Thread(target=process_manual_tasks, daemon=True)
    manual_tasks_thread.start()

    # Main loop - two different intervals
    last_10min_update = time.time()
    last_hourly_update = time.time()
    interval_10min = 600   # 10 minutes
    interval_hourly = 3600  # 1 hour

    # Schedule first hourly update immediately
    schedule_hourly_updates()

    while running:
        try:
            current_time = time.time()

            # 10-minute updates (sales and orders)
            if current_time - last_10min_update >= interval_10min:
                schedule_regular_updates_10min()
                last_10min_update = current_time

            # Hourly updates (stocks and supply orders)
            if current_time - last_hourly_update >= interval_hourly:
                schedule_hourly_updates()
                last_hourly_update = current_time

            time.sleep(60)

        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            time.sleep(60)

    # Shutdown
    logger.info("Stopping worker pool...")
    worker_pool.stop()

    logger.info("DataCollector stopped")


if __name__ == '__main__':
    main()
