"""Background queue for document indexing using thread pool.
Provides a global `indexing_queue` instance that can be configured once.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)

class IndexingQueue:
    def __init__(self, max_workers: int = 2):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures = []
        logger.info("Indexing queue started with %d workers", max_workers)

    def enqueue(self, task_func: Callable, *args, **kwargs) -> Future:
        future = self.executor.submit(task_func, *args, **kwargs)
        self._futures.append(future)
        logger.debug("Task enqueued: %s", task_func.__name__)
        return future

    def stop(self, wait: bool = True):
        self.executor.shutdown(wait=wait)
        logger.info("Indexing queue stopped")
    def is_healthy(self) -> bool:
        """Return True if executor is not shut down."""
        return not self.executor._shutdown  # type: ignore

    def get_stats(self) -> dict:
        """Return current queue statistics."""
        # Count futures that are still pending (not done)
        pending = sum(1 for f in self._futures if not f.done())
        running = sum(1 for f in self._futures if f.running())
        return {
            "workers": self.executor._max_workers,  # type: ignore
            "active_futures": running,
            "pending_tasks": pending,
            "total_submitted": len(self._futures),
            "shutdown": self.executor._shutdown      # type: ignore
        }
# Global instance (initially None)
_indexing_queue_instance = None

def init_queue(max_workers: int = 2):
    """Initialize the global indexing queue (must be called once)."""
    global _indexing_queue_instance
    if _indexing_queue_instance is None:
        _indexing_queue_instance = IndexingQueue(max_workers=max_workers)
    else:
        logger.warning("Queue already initialized, ignoring new max_workers")
    return _indexing_queue_instance

def get_queue() -> IndexingQueue:
    """Return the global indexing queue instance (raises if not initialized)."""
    if _indexing_queue_instance is None:
        raise RuntimeError("Indexing queue not initialized. Call init_queue() first.")
    return _indexing_queue_instance

# For backward compatibility with code that imports `indexing_queue` directly
# This will be set after init_queue is called. Initially None.
indexing_queue = None
