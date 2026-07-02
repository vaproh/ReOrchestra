import logging

audit_logger = logging.getLogger("audit")


def audit(action: str, **fields):
    """Log an audit event."""
    fields_str = ' '.join(f'{k}={v}' for k, v in fields.items())
    audit_logger.info(f"audit | action={action} {fields_str}")
