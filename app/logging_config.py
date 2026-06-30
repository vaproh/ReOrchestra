"""
Centralized logging setup for ReOrchestra.
"""
import os
import sys
import logging
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler

from app.config import get_settings


def setup_logging(name: str = None, level: int = logging.DEBUG) -> logging.Logger:
    """
    Setup logging with both file and console handlers.
    
    Args:
        name: Logger name (default: root logger)
        level: Logging level (default: DEBUG)
    
    Returns:
        Configured logger instance
    """
    settings = get_settings()
    
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"app_{timestamp}.log"
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.
    If not already configured, sets up logging first.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        setup_logging()
    return logger
