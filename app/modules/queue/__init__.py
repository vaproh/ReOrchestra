"""
Queue module — exposes QueueManager singleton.

Usage:
    from app.modules.queue import QueueManager
"""

import logging
import threading
from typing import Optional

from app.models import SessionLocal
from app.modules.executor.browser import CamofoxClient
from app.modules.queue.processor import QueueProcessor

logger = logging.getLogger("queue_manager")


class QueueManager:
    _instance: Optional["QueueManager"] = None
    _instance_lock = threading.Lock()

    def __init__(self):
        self.camofox = CamofoxClient()
        self._processor: Optional[QueueProcessor] = None
        self._lock = threading.Lock()

    @classmethod
    def get(cls) -> "QueueManager":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start(self):
        with self._lock:
            if self._processor and self._processor.is_running():
                return
            db = SessionLocal()
            self._processor = QueueProcessor(db, self.camofox)
            self._processor.start()
            logger.info("queue_manager | start | processor_started")

    def stop(self):
        with self._lock:
            if self._processor:
                self._processor.stop()
                self._processor = None
                logger.info("queue_manager | stop | processor_stopped")

    def is_running(self) -> bool:
        with self._lock:
            return self._processor is not None and self._processor.is_running()

    @property
    def processor(self) -> Optional[QueueProcessor]:
        """Direct access to the processor for API endpoints that need it."""
        return self._processor


__all__ = ["QueueManager", "QueueProcessor"]
