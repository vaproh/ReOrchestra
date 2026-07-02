"""
queue_workers.py — REMOVED

The /api/workers/* endpoints have been removed as part of the
queue system rewrite. The Worker model no longer exists.
Accounts are now queried directly by the QueueProcessor.

See: app/api/queue_tasks.py (GET /tasks/{id} now returns per-account logs)
     app/api/queue_queue.py (GET /queue/status shows account availability)
"""