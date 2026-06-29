"""
Queue manager singleton.

Holds a single QueueProcessor instance driving the background loop with
its own long-lived DB session. API endpoints call into this manager.
"""

import logging
from typing import Optional

from app.models import SessionLocal
from app.services.browser import CamofoxClient
from app.services.queue_processor import QueueProcessor

logger = logging.getLogger("queue_manager")


class QueueManager:
    _instance: Optional["QueueManager"] = None

    def __init__(self):
        self.camofox = CamofoxClient()
        self._processor: Optional[QueueProcessor] = None

    @classmethod
    def get(cls) -> "QueueManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start(self):
        if self._processor and self._processor.is_running():
            return
        db = SessionLocal()
        self._processor = QueueProcessor(db, self.camofox)
        self._processor.start()
        logger.info("queue_manager | start | processor_started")

    def stop(self):
        if self._processor:
            self._processor.stop()
            logger.info("queue_manager | stop | processor_stopped")
        self._processor = None

    def is_running(self) -> bool:
        return self._processor is not None and self._processor.is_running()