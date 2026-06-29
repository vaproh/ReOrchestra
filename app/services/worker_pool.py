"""
Worker pool service.

Manages the pool of workers (Reddit accounts) available for queue tasks:
- Create workers from existing accounts
- Assign idle workers to tasks
- Check deduplication (worker hasn't already done this action on this target)
- Return workers to idle pool after completion
- Pause / resume workers
"""

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Worker, WorkerStatus, Account, AccountStatus,
    Task, TaskActionLog, ActionOutcome,
)
from app.services.queue_actions import dedup_hash

logger = logging.getLogger("worker_pool")


class WorkerPool:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Worker CRUD
    # ------------------------------------------------------------------

    def list_workers(self, status: Optional[str] = None) -> list[Worker]:
        q = self.db.query(Worker)
        if status:
            q = q.filter(Worker.status == WorkerStatus(status))
        return q.order_by(Worker.id).all()

    def get_worker(self, worker_id: int) -> Optional[Worker]:
        return self.db.query(Worker).filter(Worker.id == worker_id).first()

    def create_worker(self, account_id: int) -> Worker:
        account = self.db.query(Account).filter(Account.id == account_id).first()
        if not account:
            raise ValueError(f"Account {account_id} not found")

        existing = self.db.query(Worker).filter(Worker.account_id == account_id).first()
        if existing:
            raise ValueError(f"Worker already exists for account {account_id}")

        worker = Worker(
            account_id=account_id,
            username=account.username,
            status=WorkerStatus.idle,
        )
        self.db.add(worker)
        self.db.commit()
        self.db.refresh(worker)
        logger.info(f"worker_pool | create_worker | worker_id={worker.id} username={account.username}")
        return worker

    def create_workers_from_accounts(self) -> int:
        """Create a worker for every logged_in account."""
        accounts = self.db.query(Account).filter(
            Account.status == AccountStatus.logged_in
        ).all()

        created = 0
        for account in accounts:
            existing = self.db.query(Worker).filter(Worker.account_id == account.id).first()
            if existing:
                continue
            worker = Worker(
                account_id=account.id,
                username=account.username,
                status=WorkerStatus.idle,
            )
            self.db.add(worker)
            created += 1
        self.db.commit()
        logger.info(f"worker_pool | create_workers_from_accounts | created={created}")
        return created

    def pause_worker(self, worker_id: int) -> Worker:
        worker = self.get_worker(worker_id)
        if not worker:
            raise ValueError("Worker not found")
        worker.status = WorkerStatus.paused
        self.db.commit()
        self.db.refresh(worker)
        logger.info(f"worker_pool | pause_worker | worker_id={worker_id} username={worker.username}")
        return worker

    def resume_worker(self, worker_id: int) -> Worker:
        worker = self.get_worker(worker_id)
        if not worker:
            raise ValueError("Worker not found")
        if worker.status != WorkerStatus.working:
            worker.status = WorkerStatus.idle
        self.db.commit()
        self.db.refresh(worker)
        logger.info(f"worker_pool | resume_worker | worker_id={worker_id} username={worker.username}")
        return worker

    # ------------------------------------------------------------------
    # Assignment & deduplication
    # ------------------------------------------------------------------

    def get_idle_workers(self, limit: int) -> list[Worker]:
        return (
            self.db.query(Worker)
            .filter(Worker.status == WorkerStatus.idle)
            .order_by(Worker.last_action_at.asc().nullsfirst(), Worker.id)
            .limit(limit)
            .all()
        )

    def can_worker_do_task(self, worker: Worker, task: Task) -> bool:
        """Deduplication check - has this worker already SUCCEEDED at this action on this target?"""
        h = dedup_hash(worker.id, task.action_type, task.target_url)
        existing = (
            self.db.query(TaskActionLog)
            .filter(TaskActionLog.dedup_hash == h, TaskActionLog.success == True)
            .first()
        )
        return existing is None

    def assign_workers(self, task: Task, max_workers: int = 3) -> list[Worker]:
        """
        Assign up to `max_workers` idle workers to a task.
        Respects deduplication.
        """
        assigned_ids = json.loads(task.workers_assigned or "[]")
        needed = task.workers_needed - len(assigned_ids)
        if needed <= 0:
            return []

        to_assign = min(needed, max_workers)
        candidates = self.get_idle_workers(limit=to_assign * 3)

        assigned: list[Worker] = []
        for worker in candidates:
            if len(assigned) >= to_assign:
                break
            if not self.can_worker_do_task(worker, task):
                continue
            assigned.append(worker)

        for worker in assigned:
            worker.status = WorkerStatus.working
            worker.current_task_id = task.id
            assigned_ids.append(worker.id)

        task.workers_assigned = json.dumps(assigned_ids)
        self.db.commit()
        if assigned:
            worker_ids = [w.id for w in assigned]
            logger.info(f"worker_pool | assign_workers | task_id={task.id} worker_ids={worker_ids}")
        return assigned

    def release_worker(self, worker_id: int, success: bool):
        """Return a worker to the idle pool and update stats."""
        worker = self.get_worker(worker_id)
        if not worker:
            return
        worker.current_task_id = None
        worker.last_action_at = datetime.utcnow()
        worker.total_actions += 1
        if not success:
            worker.failed_actions += 1
        if worker.status == WorkerStatus.working:
            worker.status = WorkerStatus.idle
        self.db.commit()
        logger.info(f"worker_pool | release_worker | worker_id={worker_id} success={success}")

    def mark_worker_suspended(self, worker_id: int):
        """Mark worker paused - account is suspended, needs manual intervention."""
        worker = self.get_worker(worker_id)
        if not worker:
            return
        worker.status = WorkerStatus.paused
        worker.current_task_id = None
        self.db.commit()
        logger.warning(f"worker_pool | mark_worker_suspended | worker_id={worker_id} username={worker.username}")

    def mark_worker_dead(self, worker_id: int):
        """Mark worker paused - account is banned, cannot recover."""
        worker = self.get_worker(worker_id)
        if not worker:
            return
        worker.status = WorkerStatus.paused
        worker.current_task_id = None
        # Also mark the underlying account as dead/banned
        if worker.account:
            worker.account.status = AccountStatus.dead
            worker.account.dead_reason = "manual_intervention_required:banned"
        self.db.commit()
        logger.warning(f"worker_pool | mark_worker_dead | worker_id={worker_id} username={worker.username}")