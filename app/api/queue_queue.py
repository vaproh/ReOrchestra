"""Queue API endpoints — view and control the queue processor."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import logging

from app.database import get_db, Task, TaskStatus, Account, AccountStatus
from app.modules.queue import QueueManager
from app.schemas.common import SuccessResponse

logger = logging.getLogger("queue_api")

router = APIRouter()


@router.post("/start", response_model=SuccessResponse)
async def start_queue():
    logger.info("Queue start requested")
    manager = QueueManager.get()
    try:
        manager.start()
    except Exception as e:
        logger.error("Queue start failed | error=%s", e)
        return SuccessResponse(data={"processing": False})
    return SuccessResponse(data={"processing": True})


@router.post("/stop", response_model=SuccessResponse)
async def stop_queue(graceful: bool = False):
    logger.info(f"Queue stop requested (graceful={graceful})")
    manager = QueueManager.get()
    try:
        manager.stop(graceful=graceful)
    except Exception as e:
        logger.error("Queue stop failed | error=%s", e)
    return SuccessResponse(data={"processing": False})


@router.get("/status", response_model=SuccessResponse)
async def queue_status(db: Session = Depends(get_db)):
    manager = QueueManager.get()

    # Account availability stats
    total_accounts = db.query(Account).count()
    logged_in = (
        db.query(Account).filter(Account.status == AccountStatus.logged_in).count()
    )
    rate_limited = (
        db.query(Account).filter(Account.status == AccountStatus.rate_limited).count()
    )
    dead = db.query(Account).filter(Account.status == AccountStatus.dead).count()

    # Task stats
    queued_count = db.query(Task).filter(Task.status == TaskStatus.queued).count()
    running_count = db.query(Task).filter(Task.status == TaskStatus.running).count()

    return SuccessResponse(
        data={
            "processing": manager.is_running(),
            "queue": {
                "queued": queued_count,
                "running": running_count,
            },
            "accounts": {
                "total": total_accounts,
                "available": logged_in,
                "rate_limited": rate_limited,
                "dead": dead,
            },
        }
    )
