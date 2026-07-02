"""Queue API endpoints — view and control the queue processor."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import logging

from app.database import get_db, Task, TaskStatus, Account, AccountStatus
from app.modules.queue import QueueManager
from app.schemas.common import SuccessResponse

logger = logging.getLogger("queue_api")

router = APIRouter()


@router.get("", response_model=SuccessResponse)
async def view_queue(db: Session = Depends(get_db)):
    tasks = (
        db.query(Task)
        .filter(Task.status.in_([TaskStatus.queued, TaskStatus.running]))
        .order_by(Task.priority.desc(), Task.created_at.asc())
        .all()
    )
    manager = QueueManager.get()
    return SuccessResponse(data={
        "total": len(tasks),
        "processing": manager.is_running(),
        "tasks": [
            {
                "id": t.id,
                "position": i + 1,
                "action_type": t.action_type,
                "target_url": t.target_url,
                "workers_needed": t.workers_needed,
                "workers_completed": t.workers_completed or 0,
                "workers_failed": t.workers_failed or 0,
                "status": t.status.value,
                "priority": t.priority,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "started_at": t.started_at.isoformat() if t.started_at else None,
            }
            for i, t in enumerate(tasks)
        ],
    })


@router.post("/start", response_model=SuccessResponse)
async def start_queue():
    logger.info("Queue start requested")
    manager = QueueManager.get()
    manager.start()
    return SuccessResponse(data={"processing": True})


@router.post("/stop", response_model=SuccessResponse)
async def stop_queue():
    logger.info("Queue stop requested")
    manager = QueueManager.get()
    manager.stop()
    return SuccessResponse(data={"processing": False})


@router.get("/status", response_model=SuccessResponse)
async def queue_status(db: Session = Depends(get_db)):
    manager = QueueManager.get()

    # Account availability stats
    total_accounts = db.query(Account).count()
    logged_in = db.query(Account).filter(Account.status == AccountStatus.logged_in).count()
    rate_limited = db.query(Account).filter(Account.status == AccountStatus.rate_limited).count()
    dead = db.query(Account).filter(Account.status.in_([AccountStatus.dead, AccountStatus.banned])).count()

    # Task stats
    queued_count = db.query(Task).filter(Task.status == TaskStatus.queued).count()
    running_count = db.query(Task).filter(Task.status == TaskStatus.running).count()

    return SuccessResponse(data={
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
    })