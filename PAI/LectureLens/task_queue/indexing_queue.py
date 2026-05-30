"""Simple background queue for document indexing using threading."""
import threading
import queue
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class IndexingQueue:
    """Singleton background worker that processes indexing tasks."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._queue = queue.Queue()
        self._worker_thread = None
        self._running = False
        self._initialized = True

    def start(self):
        """Start the background worker thread."""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._process, daemon=True)
        self._worker_thread.start()
        logger.info("Indexing queue worker started")

    def stop(self):
        """Stop the worker (waits for pending tasks)."""
        self._running = False
        self._queue.put(None)  # Sentinel to wake worker
        if self._worker_thread:
            self._worker_thread.join(timeout=10)
        logger.info("Indexing queue worker stopped")

    def enqueue(self, task_func: Callable, *args, **kwargs):
        """Add a task to the queue."""
        self._queue.put((task_func, args, kwargs))
        logger.debug("Task enqueued: %s", task_func.__name__)

    def _process(self):
        """Worker loop: fetch and execute tasks."""
        while self._running:
            try:
                item = self._queue.get(timeout=1)
                if item is None:
                    continue
                task_func, args, kwargs = item
                try:
                    task_func(*args, **kwargs)
                except Exception as e:
                    logger.exception("Error processing background task: %s", e)
                finally:
                    self._queue.task_done()
            except queue.Empty:
                continue

# Global singleton instance
indexing_queue = IndexingQueue()