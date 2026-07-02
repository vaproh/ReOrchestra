import logging
import json
from datetime import datetime, timezone


class StructuredFormatter(logging.Formatter):
    """Logs to JSON in file, readable format to console."""

    def format(self, record):
        if hasattr(record, '_json'):
            return json.dumps(record._json)
        parts = [
            datetime.now(timezone.utc).isoformat(),
            record.levelname,
            record.name,
            record.getMessage(),
        ]
        extra = {k: v for k, v in record.__dict__.items()
                 if k not in ('name', 'msg', 'args', 'created', 'filename',
                             'funcName', 'levelname', 'levelno', 'lineno',
                             'module', 'msecs', 'pathname', 'process',
                             'processName', 'relativeCreated', 'thread',
                             'threadName', 'message', 'exc_text')}
        if extra:
            parts.append(' '.join(f'{k}={v}' for k, v in extra.items()))
        return ' | '.join(parts)
