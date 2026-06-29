"""Queue API endpoints - view and control the queue processor."""

import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db, Task, TaskStatus
from app.services.queue_manager import QueueManager
from app.schemas.common import SuccessResponse

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
                "status": t.status.value,
                "priority": t.priority,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for i, t in enumerate(tasks)
        ],
    })


@router.post("/start", response_model=SuccessResponse)
async def start_queue():
    manager = QueueManager.get()
    manager.start()
    return SuccessResponse(data={"processing": True})


@router.post("/stop", response_model=SuccessResponse)
async def stop_queue():
    manager = QueueManager.get()
    manager.stop()
    return SuccessResponse(data={"processing": False})


@router.get("/status", response_model=SuccessResponse)
async def queue_status():
    manager = QueueManager.get()
    return SuccessResponse(data={"processing": manager.is_running()})