from fastapi import APIRouter
from app.api import accounts, admin, proxies
from app.api import queue_tasks, queue_queue

router = APIRouter()

router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
router.include_router(proxies.router, prefix="/proxies", tags=["proxies"])

# Queue system
router.include_router(queue_tasks.router, prefix="/tasks", tags=["queue-tasks"])
router.include_router(queue_queue.router, prefix="/queue", tags=["queue"])
