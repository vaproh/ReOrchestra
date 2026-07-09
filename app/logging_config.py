"""
Centralized logging setup for ReOrchestra.
"""

import os
import sys
import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler

LOG_DIR = Path("data/logs")
LOG_FILE: Path | None = None


def setup_logging(level: int = logging.DEBUG) -> None:
    global LOG_FILE
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    console_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    console_level = getattr(logging, console_level_str, logging.INFO)

    timestamp = __import__("time").strftime("%Y%m%d_%H%M%S")
    LOG_FILE = LOG_DIR / f"app_{timestamp}.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    if root_logger.handlers:
        return

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    if not logging.getLogger().handlers:
        setup_logging()
    return logging.getLogger(name)

def set_dynamic_log_level(level_str: str) -> None:
    level = getattr(logging, level_str.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)
