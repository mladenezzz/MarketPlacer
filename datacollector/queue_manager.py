import logging
import queue
import threading
import time
from datetime import datetime, timedelta, timezone
from enum import IntEnum

logger = logging.getLogger(__name__)


class TaskPriority(IntEnum):
    """Task priority levels"""
    HIGH = 1
    NORMAL = 2
    LOW = 3


class Task:
    """Task for data collection"""

    def __init__(self, token_id: int, endpoint: str, priority: TaskPriority = TaskPriority.NORMAL):
        self.token_id = token_id
        self.endpoint = endpoint
        self.priority = priority
        self.created_at = datetime.now(timezone.utc)
        self.attempts = 0
        self.max_attempts = 5
        self.next_retry = None

    def __lt__(self, other):
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_at < other.created_at

    def can_retry(self) -> bool:
        """Check if task can be retried"""
        if self.attempts >= self.max_attempts:
            return False
        if self.next_retry and datetime.now(timezone.utc) < self.next_retry:
            return False
        return True

    def schedule_retry(self):
        """Schedule next retry with exponential backoff"""
        self.attempts += 1
        backoff_seconds = min(60 * (2 ** self.attempts), 3600)
        self.next_retry = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
        logger.info(f"Task {self.token_id}:{self.endpoint} scheduled for retry #{self.attempts} at {self.next_retry}")


class TaskQueue:
    """Priority queue for tasks"""

    def __init__(self):
        self.queue = queue.PriorityQueue()
        self.lock = threading.Lock()
        self.retry_queue = []

    def add_task(self, task: Task):
        """Add task to queue"""
        self.queue.put(task)

    def get_task(self, timeout: int = 1) -> Task:
        """Get task from queue"""
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def task_done(self):
        """Mark task as done"""
        self.queue.task_done()

    def add_to_retry(self, task: Task):
        """Add task to retry queue"""
        with self.lock:
            self.retry_queue.append(task)

    def process_retry_queue(self):
        """Process retry queue and move ready tasks to main queue"""
        with self.lock:
            ready_tasks = []
            remaining_tasks = []

            for task in self.retry_queue:
                if task.can_retry() and (not task.next_retry or datetime.now(timezone.utc) >= task.next_retry):
                    ready_tasks.append(task)
                elif task.attempts < task.max_attempts:
                    remaining_tasks.append(task)

            self.retry_queue = remaining_tasks

            for task in ready_tasks:
                self.queue.put(task)
                logger.info(f"Task {task.token_id}:{task.endpoint} moved from retry queue to main queue")

    def size(self) -> int:
        """Get queue size"""
        return self.queue.qsize()
