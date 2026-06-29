"""Worker API endpoints for the queue system."""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db, Worker, WorkerStatus, TaskActionLog
from app.services.worker_pool import WorkerPool
from app.schemas.common import SuccessResponse

router = APIRouter()


def _worker_dict(w: Worker) -> dict:
    return {
        "id": w.id,
        "account_id": w.account_id,
        "username": w.username,
        "status": w.status.value if w.status else None,
        "current_task_id": w.current_task_id,
        "total_actions": w.total_actions,
        "failed_actions": w.failed_actions,
        "last_action_at": w.last_action_at.isoformat() if w.last_action_at else None,
        "created_at": w.created_at.isoformat() if w.created_at else None,
    }


@router.get("", response_model=SuccessResponse)
async def list_workers(
    status: str = Query(None, description="idle, working, paused"),
    db: Session = Depends(get_db),
):
    pool = WorkerPool(db)
    workers = pool.list_workers(status=status)
    counts = {"idle": 0, "working": 0, "paused": 0}
    for w in workers:
        key = w.status.value if w.status else "idle"
        counts[key] = counts.get(key, 0) + 1
    return SuccessResponse(data={
        "total": len(workers),
        **counts,
        "workers": [_worker_dict(w) for w in workers],
    })


@router.get("/{worker_id}", response_model=SuccessResponse)
async def get_worker(worker_id: int, db: Session = Depends(get_db)):
    pool = WorkerPool(db)
    worker = pool.get_worker(worker_id)
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    data = _worker_dict(worker)
    logs = (
        db.query(TaskActionLog)
        .filter(TaskActionLog.worker_id == worker_id)
        .order_by(TaskActionLog.created_at.desc())
        .limit(20)
        .all()
    )
    data["action_history"] = [
        {
            "id": l.id,
            "task_id": l.task_id,
            "action_type": l.action_type,
            "target_url": l.target_url,
            "success": l.success,
            "outcome": l.outcome,
            "error": l.error,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]
    return SuccessResponse(data=data)


@router.post("", response_model=SuccessResponse)
async def create_worker(request: dict, db: Session = Depends(get_db)):
    pool = WorkerPool(db)
    try:
        worker = pool.create_worker(account_id=request["account_id"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SuccessResponse(data=_worker_dict(worker))


@router.post("/bulk", response_model=SuccessResponse)
async def create_workers_bulk(db: Session = Depends(get_db)):
    pool = WorkerPool(db)
    created = pool.create_workers_from_accounts()
    return SuccessResponse(data={"created": created})


@router.post("/{worker_id}/pause", response_model=SuccessResponse)
async def pause_worker(worker_id: int, db: Session = Depends(get_db)):
    pool = WorkerPool(db)
    try:
        worker = pool.pause_worker(worker_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SuccessResponse(data={"status": worker.status.value})


@router.post("/{worker_id}/resume", response_model=SuccessResponse)
async def resume_worker(worker_id: int, db: Session = Depends(get_db)):
    pool = WorkerPool(db)
    try:
        worker = pool.resume_worker(worker_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SuccessResponse(data={"status": worker.status.value})