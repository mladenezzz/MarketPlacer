import logging
import threading
import time
from datetime import datetime
from datacollector.queue_manager import Task, TaskQueue
from datacollector.collectors.wildberries import WildberriesCollector
from datacollector.collectors.ozon import OzonCollector
from datacollector.config import DataCollectorConfig

logger = logging.getLogger(__name__)


class Worker(threading.Thread):
    """Worker thread for processing tasks from queue"""

    def __init__(self, worker_id: int, task_queue: TaskQueue, collectors: dict):
        super().__init__(daemon=True)
        self.worker_id = worker_id
        self.task_queue = task_queue
        self.collectors = collectors
        self.running = True
        self.last_request_time = {}

    def stop(self):
        """Stop worker gracefully"""
        self.running = False

    def wait_for_rate_limit(self, token_id: int):
        """Wait for rate limit between requests"""
        now = time.time()
        last_time = self.last_request_time.get(token_id, 0)
        time_since_last = now - last_time

        if time_since_last < DataCollectorConfig.WILDBERRIES_RATE_LIMIT:
            wait_time = DataCollectorConfig.WILDBERRIES_RATE_LIMIT - time_since_last
            logger.info(f"Worker {self.worker_id}: Waiting {wait_time:.1f}s for rate limit (token {token_id})")
            time.sleep(wait_time)

        self.last_request_time[token_id] = time.time()

    def process_task(self, task: Task) -> bool:
        """Process single task, return True if successful"""
        try:
            collector = self.collectors.get(task.token_id)
            if not collector:
                logger.error(f"Worker {self.worker_id}: No collector found for token {task.token_id}")
                return False

            logger.info(f"Worker {self.worker_id}: Processing {task.endpoint} for token {task.token_id}")

            # Wait for rate limit
            self.wait_for_rate_limit(task.token_id)

            # Execute collection based on endpoint
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            engine = create_engine(DataCollectorConfig.DATABASE_URI)
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                # Wildberries endpoints
                if task.endpoint == 'incomes':
                    collector.collect_incomes(session)
                elif task.endpoint == 'sales':
                    collector.collect_sales(session)
                elif task.endpoint == 'orders':
                    collector.collect_orders(session)
                elif task.endpoint == 'stocks':
                    collector.collect_stocks(session)
                # Ozon endpoints
                elif task.endpoint == 'ozon_stocks':
                    collector.collect_stocks(session)
                elif task.endpoint == 'ozon_sales':
                    collector.collect_sales(session)
                elif task.endpoint == 'ozon_supply_orders':
                    collector.collect_supply_orders(session)
                else:
                    logger.error(f"Worker {self.worker_id}: Unknown endpoint {task.endpoint}")
                    return False

                logger.info(f"Worker {self.worker_id}: Successfully processed {task.endpoint} for token {task.token_id}")
                return True

            except Exception as e:
                # Check if it's a 429 rate limit error
                if '429' in str(e) or 'Too Many Requests' in str(e):
                    logger.warning(f"Worker {self.worker_id}: Rate limit hit for token {task.token_id}, scheduling retry")
                    raise
                else:
                    logger.error(f"Worker {self.worker_id}: Error processing task: {e}")
                    raise
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Worker {self.worker_id}: Task failed: {e}")
            return False

    def run(self):
        """Main worker loop"""
        logger.info(f"Worker {self.worker_id}: Started")

        while self.running:
            task = self.task_queue.get_task(timeout=1)

            if task is None:
                continue

            try:
                success = self.process_task(task)

                if not success:
                    # Task failed, schedule retry if possible
                    if task.can_retry():
                        task.schedule_retry()
                        self.task_queue.add_to_retry(task)
                        logger.info(f"Worker {self.worker_id}: Task added to retry queue")
                    else:
                        logger.error(f"Worker {self.worker_id}: Task exhausted all retries")

            except Exception as e:
                logger.error(f"Worker {self.worker_id}: Exception in task processing: {e}")
                # Schedule retry for 429 errors
                if task.can_retry() and ('429' in str(e) or 'Too Many Requests' in str(e)):
                    task.schedule_retry()
                    self.task_queue.add_to_retry(task)
                    logger.info(f"Worker {self.worker_id}: Task added to retry queue after rate limit")

            finally:
                self.task_queue.task_done()

        logger.info(f"Worker {self.worker_id}: Stopped")


class WorkerPool:
    """Pool of worker threads"""

    def __init__(self, num_workers: int, task_queue: TaskQueue, collectors: dict):
        self.num_workers = num_workers
        self.task_queue = task_queue
        self.collectors = collectors
        self.workers = []

    def start(self):
        """Start all workers"""
        logger.info(f"Starting {self.num_workers} workers...")
        for i in range(self.num_workers):
            worker = Worker(i + 1, self.task_queue, self.collectors)
            worker.start()
            self.workers.append(worker)
        logger.info(f"All {self.num_workers} workers started")

    def stop(self):
        """Stop all workers gracefully"""
        logger.info("Stopping all workers...")
        for worker in self.workers:
            worker.stop()

        # Wait for all workers to finish
        for worker in self.workers:
            worker.join(timeout=5)

        logger.info("All workers stopped")
