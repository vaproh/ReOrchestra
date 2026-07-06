import time
import logging
from contextlib import contextmanager

logger = logging.getLogger("timing")


@contextmanager
def timed_operation(operation: str, slow_threshold: float = 10.0, **context):
    """Context manager for timing operations."""
    start = time.time()
    try:
        yield
    finally:
        duration_ms = int((time.time() - start) * 1000)
        ctx_str = " ".join(f"{k}={v}" for k, v in context.items())
        if duration_ms > slow_threshold * 1000:
            logger.warning(
                f"slow_operation | operation={operation} duration_ms={duration_ms} {ctx_str}"
            )
        else:
            logger.debug(
                f"operation | operation={operation} duration_ms={duration_ms} {ctx_str}"
            )
