"""Background folder watcher for auto‑ingestion."""
import time
import logging
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

class FolderWatcher:
    def __init__(self, base_upload_folder: Path, indexing_queue,
                 document_repo, vector_store, db_manager,
                 chunk_size=500, overlap=100,
                 scan_interval: int = 30):
        self.base_folder = Path(base_upload_folder)
        self.indexing_queue = indexing_queue
        self.scan_interval = scan_interval
        self._running = False
        self._thread = None
        self._processed = set()
        # Store dependencies for indexing
        self.document_repo = document_repo
        self.vector_store = vector_store
        self.db_manager = db_manager
        self.chunk_size = chunk_size
        self.overlap = overlap

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._watch, daemon=True)
        self._thread.start()
        logger.info("Folder watcher started (interval=%ds)", self.scan_interval)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Folder watcher stopped")

    def _watch(self):
        while self._running:
            try:
                self._scan()
            except Exception as e:
                logger.error("Folder watcher error: %s", e)
            time.sleep(self.scan_interval)

    def _scan(self):
        if not self.base_folder.exists():
            return
        for subject_folder in self.base_folder.iterdir():
            if not subject_folder.is_dir():
                continue
            subject = subject_folder.name
            for file_path in subject_folder.iterdir():
                if not file_path.is_file():
                    continue
                mtime = file_path.stat().st_mtime
                key = (str(file_path), mtime)
                if key in self._processed:
                    continue
                self._processed.add(key)
                # Enqueue indexing task with captured dependencies
                self.indexing_queue.enqueue(
                    self._index_file,
                    file_path, file_path.name, subject,
                    self.document_repo, self.vector_store, self.db_manager,
                    self.chunk_size, self.overlap
                )
                logger.info("Auto‑detected file: %s (subject=%s)", file_path.name, subject)

    @staticmethod
    def _index_file(file_path, original_filename, subject,
                    document_repo, vector_store, db_manager,
                    chunk_size, overlap):
        from services.indexing_service import IndexingService
        try:
            indexing_service = IndexingService(document_repo, vector_store, db_manager, chunk_size, overlap)
            indexing_service.index_document(file_path, original_filename, subject)
        except Exception as e:
            logger.exception("Indexing failed for %s: %s", file_path, e)