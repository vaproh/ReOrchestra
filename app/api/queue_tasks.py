"""Task API endpoints for the queue system."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
import logging

from datetime import datetime, UTC

from app.database import get_db, Task, TaskStatus, TaskExecutionLog, ACTION_TYPES
from app.schemas.common import SuccessResponse

logger = logging.getLogger("tasks")

router = APIRouter()


def _task_dict(t: Task) -> dict:
    completed = t.workers_completed or 0
    failed = t.workers_failed or 0
    return {
        "id": t.id,
        "action_type": t.action_type,
        "target_url": t.target_url,
        "workers_needed": t.workers_needed,
        "workers_completed": completed,
        "workers_failed": failed,
        "status": t.status.value if t.status else None,
        "priority": t.priority,
        "progress": {
            "total": t.workers_needed,
            "completed": completed,
            "failed": failed,
            "remaining": max(0, t.workers_needed - completed - failed),
        },
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "started_at": t.started_at.isoformat() if t.started_at else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
    }


@router.get("", response_model=SuccessResponse)
async def list_tasks(
    status: str = Query(None, description="queued, running, completed, partial, failed, cancelled"),
    db: Session = Depends(get_db),
):
    q = db.query(Task)
    if status:
        try:
            q = q.filter(Task.status == TaskStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {[s.value for s in TaskStatus]}")
    tasks = q.order_by(Task.created_at.desc()).limit(100).all()
    return SuccessResponse(data={
        "total": len(tasks),
        "tasks": [_task_dict(t) for t in tasks],
    })


@router.post("", response_model=SuccessResponse)
async def create_task(request: dict, db: Session = Depends(get_db)):
    action_type = request.get("action_type")
    target_url = request.get("target_url")
    workers_needed = request.get("workers_needed", 1)
    priority = request.get("priority", 0)

    if not action_type:
        raise HTTPException(status_code=400, detail="action_type required")
    if action_type not in ACTION_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid action_type. Valid: {ACTION_TYPES}")
    if not target_url:
        raise HTTPException(status_code=400, detail="target_url required")
    if not isinstance(workers_needed, int) or workers_needed < 1:
        raise HTTPException(status_code=400, detail="workers_needed must be a positive integer")

    logger.info(f"Creating task: {action_type} on {target_url} with {workers_needed} workers")

    task = Task(
        action_type=action_type,
        target_url=target_url,
        workers_needed=workers_needed,
        priority=priority,
        status=TaskStatus.queued,
    )
    db.add(task)
    db.flush()
    db.refresh(task)

    queue_pos = (
        db.query(Task)
        .filter(Task.status == TaskStatus.queued, Task.id <= task.id)
        .count()
    )

    return SuccessResponse(data={
        "task_id": task.id,
        "status": task.status.value,
        "queue_position": queue_pos,
        "workers_needed": task.workers_needed,
    })


@router.get("/{task_id}", response_model=SuccessResponse)
async def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    data = _task_dict(task)

    logs = (
        db.query(TaskExecutionLog)
        .filter(TaskExecutionLog.task_id == task_id)
        .order_by(TaskExecutionLog.created_at.desc())
        .limit(50)
        .all()
    )
    data["logs"] = [
        {
            "id": log.id,
            "account_id": log.account_id,
            "success": log.success,
            "outcome": log.outcome,
            "error": log.error,
            "attempts": log.attempts,
            "duration_ms": log.duration_ms,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
    return SuccessResponse(data=data)


@router.post("/{task_id}/cancel", response_model=SuccessResponse)
async def cancel_task(task_id: int, db: Session = Depends(get_db)):
    from app.modules.queue import QueueManager
    manager = QueueManager.get()
    processor = manager.processor

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in (TaskStatus.completed, TaskStatus.cancelled):
        return SuccessResponse(data={"status": task.status.value, "message": "Task already finished"})

    task.status = TaskStatus.cancelled
    task.completed_at = datetime.now(UTC)

    # Signal the running processor thread if active
    if processor:
        evt = processor._cancel_events.get(task_id)
        if evt:
            evt.set()

    db.commit()
    logger.info("Cancel task %s", task_id)
    return SuccessResponse(data={"status": task.status.value, "message": "Task cancelled"})


@router.post("/{task_id}/priority", response_model=SuccessResponse)
async def priority_boost(task_id: int, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.priority = (task.priority or 0) + 1000
    db.commit()
    db.refresh(task)
    logger.info(f"Priority boost task {task_id}")
    return SuccessResponse(data={"task_id": task.id, "priority": task.priority})


@router.post("/{task_id}/retry", response_model=SuccessResponse)
async def retry_task(task_id: int, db: Session = Depends(get_db)):
    """Re-queue a failed, partial, or cancelled task."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status not in (TaskStatus.failed, TaskStatus.partial, TaskStatus.cancelled):
        raise HTTPException(
            status_code=400,
            detail=f"Task cannot be retried (status: {task.status.value})"
        )

    task.status = TaskStatus.queued
    task.started_at = None
    task.completed_at = None
    task.workers_completed = 0
    task.workers_failed = 0
    db.commit()

    return SuccessResponse(data={"task_id": task.id, "status": task.status.value})