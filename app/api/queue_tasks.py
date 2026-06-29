"""Task API endpoints for the queue system."""

import json
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, Task, TaskStatus, TaskActionLog, ACTION_TYPES
from app.schemas.common import SuccessResponse

router = APIRouter()


def _task_dict(t: Task) -> dict:
    assigned = json.loads(t.workers_assigned or "[]")
    failed = json.loads(t.failed_workers or "[]")
    completed = t.workers_completed or 0
    return {
        "id": t.id,
        "action_type": t.action_type,
        "target_url": t.target_url,
        "workers_needed": t.workers_needed,
        "workers_assigned": assigned,
        "failed_workers": failed,
        "workers_completed": completed,
        "status": t.status.value if t.status else None,
        "priority": t.priority,
        "progress": {
            "total": t.workers_needed,
            "completed": completed,
            "failed": len(failed),
            "remaining": max(0, t.workers_needed - completed),
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
        q = q.filter(Task.status == TaskStatus(status))
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

    if not action_type:
        raise HTTPException(400, "action_type required")
    if action_type not in ACTION_TYPES:
        raise HTTPException(400, f"Invalid action_type. Valid: {ACTION_TYPES}")
    if not target_url:
        raise HTTPException(400, "target_url required")

    # quick flush then count queue position
    task = Task(
        action_type=action_type,
        target_url=target_url,
        workers_needed=workers_needed,
        status=TaskStatus.queued,
    )
    db.add(task)
    db.commit()
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
        db.query(TaskActionLog)
        .filter(TaskActionLog.task_id == task_id)
        .order_by(TaskActionLog.created_at.desc())
        .limit(50)
        .all()
    )
    data["logs"] = [
        {
            "id": l.id,
            "worker_id": l.worker_id,
            "success": l.success,
            "outcome": l.outcome,
            "error": l.error,
            "attempts": l.attempts,
            "duration_ms": l.duration_ms,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
    return SuccessResponse(data=data)


@router.post("/{task_id}/cancel", response_model=SuccessResponse)
async def cancel_task(task_id: int, db: Session = Depends(get_db)):
    from app.services.queue_processor import QueueProcessor
    qp = QueueProcessor(db)
    try:
        task = qp.cancel_task(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    return SuccessResponse(data={"status": task.status.value})


@router.post("/{task_id}/priority", response_model=SuccessResponse)
async def priority_boost(task_id: int, db: Session = Depends(get_db)):
    from app.services.queue_processor import QueueProcessor
    qp = QueueProcessor(db)
    try:
        task = qp.priority_boost(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")
    return SuccessResponse(data={"queue_position": 1, "priority": task.priority})