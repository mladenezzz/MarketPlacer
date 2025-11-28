import logging
import time
import signal
import sys
import threading
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datacollector.config import DataCollectorConfig
from datacollector.collectors.wildberries import WildberriesCollector
from datacollector.queue_manager import TaskQueue, Task, TaskPriority
from datacollector.worker import WorkerPool
from app.models import Token, WBStock

logging.basicConfig(
    level=logging.INFO,
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
        tokens = session.query(Token).filter_by(marketplace='wildberries').all()
        logger.info(f"Found {len(tokens)} Wildberries tokens")

        for token in tokens:
            logger.info(f"Creating collector for token {token.id} ({token.name})")
            collector = WildberriesCollector(
                token_id=token.id,
                token=token.token,
                database_uri=DataCollectorConfig.DATABASE_URI
            )
            collectors[token.id] = collector

    except Exception as e:
        logger.error(f"Error initializing collectors: {e}")
    finally:
        session.close()

    logger.info("Initialization complete")


def check_and_load_today_stocks():
    """Check if today's stocks exist, if not - load them"""
    logger.info("Checking today's stocks...")

    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        today = datetime.utcnow().date()
        tokens = session.query(Token).filter_by(marketplace='wildberries').all()

        for token in tokens:
            # Check if stocks for today exist
            stocks_count = session.query(WBStock).filter_by(
                token_id=token.id,
                date=today
            ).count()

            if stocks_count == 0:
                logger.info(f"No stocks found for token {token.id} ({token.name}) for today, adding to queue")
                task = Task(token.id, 'stocks', TaskPriority.HIGH)
                task_queue.add_task(task)
            else:
                logger.info(f"Stocks for token {token.id} ({token.name}) already exist for today ({stocks_count} records)")

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
        tokens = session.query(Token).filter_by(marketplace='wildberries').all()

        for token in tokens:
            # Check if initial sync has been done
            from app.models import SyncState
            sync_state = session.query(SyncState).filter_by(
                token_id=token.id,
                endpoint='incomes'
            ).first()

            if not sync_state or not sync_state.last_successful_sync:
                logger.info(f"Scheduling initial collection for token {token.id} ({token.name})")
                # Initial collection with high priority
                task_queue.add_task(Task(token.id, 'incomes', TaskPriority.HIGH))
                task_queue.add_task(Task(token.id, 'sales', TaskPriority.HIGH))
                task_queue.add_task(Task(token.id, 'orders', TaskPriority.HIGH))
            else:
                logger.info(f"Token {token.id} ({token.name}) already synced, scheduling normal updates")
                # Regular updates with normal priority
                task_queue.add_task(Task(token.id, 'incomes', TaskPriority.NORMAL))
                task_queue.add_task(Task(token.id, 'sales', TaskPriority.NORMAL))
                task_queue.add_task(Task(token.id, 'orders', TaskPriority.NORMAL))

    except Exception as e:
        logger.error(f"Error scheduling initial tasks: {e}")
    finally:
        session.close()


def schedule_regular_updates():
    """Schedule regular data updates for all tokens"""
    logger.info("Scheduling regular updates...")

    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        tokens = session.query(Token).filter_by(marketplace='wildberries').all()

        for token in tokens:
            task_queue.add_task(Task(token.id, 'incomes', TaskPriority.NORMAL))
            task_queue.add_task(Task(token.id, 'sales', TaskPriority.NORMAL))
            task_queue.add_task(Task(token.id, 'orders', TaskPriority.NORMAL))

        logger.info(f"Scheduled updates for {len(tokens)} tokens")

    except Exception as e:
        logger.error(f"Error scheduling regular updates: {e}")
    finally:
        session.close()


def schedule_daily_stocks():
    """Schedule daily stocks collection at configured time"""
    logger.info("Scheduling daily stocks collection...")

    engine = create_engine(DataCollectorConfig.DATABASE_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        tokens = session.query(Token).filter_by(marketplace='wildberries').all()

        for token in tokens:
            task = Task(token.id, 'stocks', TaskPriority.HIGH)
            task_queue.add_task(task)
            logger.info(f"Scheduled stocks collection for token {token.id} ({token.name})")

        logger.info(f"Scheduled stocks collection for {len(tokens)} tokens")

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


def stocks_scheduler():
    """Background thread to schedule daily stocks collection"""
    logger.info("Stocks scheduler started")

    last_stocks_date = None

    while running:
        try:
            now = datetime.utcnow()
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

    # Start stocks scheduler in background
    stocks_thread = threading.Thread(target=stocks_scheduler, daemon=True)
    stocks_thread.start()

    # Main loop - schedule regular updates every 10 minutes
    last_update = time.time()
    update_interval = 600  # 10 minutes

    while running:
        try:
            current_time = time.time()

            if current_time - last_update >= update_interval:
                schedule_regular_updates()
                last_update = current_time

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
