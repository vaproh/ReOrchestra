"""
Queue processor service.

Runs in a background thread and processes queued tasks in FIFO order
(higher priority first). For each task it:
1. Assigns idle workers (up to max_concurrent per task)
2. Executes the action via Camofox
3. Retries on failure (max_retries, exponential backoff)
4. Logs each attempt
5. Updates task status when all workers are done
"""

import json
import time
import logging
import threading
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    Task, TaskStatus, Worker, WorkerStatus,
    TaskActionLog, ActionOutcome,
)
from app.services.browser import CamofoxClient
from app.services.worker_pool import WorkerPool
from app.services.queue_actions import get_action_class, dedup_hash

logger = logging.getLogger("queue")


class QueueProcessor:
    def __init__(self, db: Session, camofox: Optional[CamofoxClient] = None):
        self.db = db
        self.camofox = camofox or CamofoxClient()
        self.pool = WorkerPool(db)
        self.max_retries = 3
        self.max_concurrent_per_task = 3
        self.action_timeout = 120
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Queue inspection
    # ------------------------------------------------------------------

    def list_queue(self) -> list[Task]:
        return (
            self.db.query(Task)
            .filter(Task.status.in_([TaskStatus.queued, TaskStatus.running]))
            .order_by(Task.priority.desc(), Task.created_at.asc())
            .all()
        )

    def next_task(self) -> Optional[Task]:
        return (
            self.db.query(Task)
            .filter(Task.status == TaskStatus.queued)
            .order_by(Task.priority.desc(), Task.created_at.asc())
            .first()
        )

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    def create_task(self, action_type: str, target_url: str, workers_needed: int = 1) -> Task:
        if not get_action_class(action_type):
            raise ValueError(f"Unknown action type: {action_type}")
        task = Task(
            action_type=action_type,
            target_url=target_url,
            workers_needed=workers_needed,
            status=TaskStatus.queued,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def cancel_task(self, task_id: int) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        task.status = TaskStatus.cancelled
        task.completed_at = datetime.utcnow()
        # release assigned workers
        for wid in json.loads(task.workers_assigned or "[]"):
            self.pool.release_worker(wid, success=False)
        self.db.commit()
        self.db.refresh(task)
        return task

    def priority_boost(self, task_id: int) -> Task:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        task.priority = (task.priority or 0) + 1000
        self.db.commit()
        self.db.refresh(task)
        return task

    # ------------------------------------------------------------------
    # Single task execution
    # ------------------------------------------------------------------

    def execute_for_worker(self, task: Task, worker: Worker) -> dict:
        """
        Execute the task action for a single worker.
        Returns a dict with success, outcome, error, attempts, duration_ms.
        Caller is responsible for inserting the log.
        """
        action_cls = get_action_class(task.action_type)
        if not action_cls:
            logger.error(f"No action class for {task.action_type}")
            return {"success": False, "outcome": "failed", "error": "No action class", "attempts": 0, "duration_ms": 0}

        action = action_cls(self.camofox)
        total_attempts = 0
        final_result = None

        for attempt in range(1, self.max_retries + 1):
            logger.info(
                f"Task {task.id} worker {worker.id} attempt {attempt}/{self.max_retries}"
            )
            total_attempts = attempt
            result = action.execute(worker, task.target_url)
            final_result = result

            if result.success:
                break

            if result.outcome == "popup_suspended":
                logger.warning(f"Worker {worker.id} suspended - pausing")
                self.pool.mark_worker_suspended(worker.id)
                break

            if result.outcome == "duplicate":
                break

            if attempt < self.max_retries:
                backoff = min(2 ** attempt, 30)
                logger.info(f"Retrying in {backoff}s")
                time.sleep(backoff)

        return {
            "success": final_result.success if final_result else False,
            "outcome": final_result.outcome if final_result else "failed",
            "error": final_result.error if final_result else "No result",
            "attempts": total_attempts,
            "duration_ms": final_result.duration_ms if final_result else 0,
        }

    def process_task(self, task: Task):
        """Process a single task to completion."""
        task.status = TaskStatus.running
        task.started_at = datetime.utcnow()
        self.db.commit()

        logger.info(f"Processing task {task.id} ({task.action_type})")

        assigned_ids = json.loads(task.workers_assigned or "[]")
        failed_ids = json.loads(task.failed_workers or "[]")

        # Assign workers in batches until workers_needed is met
        while len(assigned_ids) < task.workers_needed:
            assigned = self.pool.assign_workers(task, self.max_concurrent_per_task)
            if not assigned:
                logger.info(f"No more idle workers for task {task.id}")
                break
            assigned_ids = json.loads(task.workers_assigned or "[]")

            for worker in assigned:
                result = self.execute_for_worker(task, worker)
                success = result["success"]

                # Insert log
                h = dedup_hash(worker.id, task.action_type, task.target_url)
                log = TaskActionLog(
                    task_id=task.id,
                    worker_id=worker.id,
                    action_type=task.action_type,
                    target_url=task.target_url,
                    success=success,
                    outcome=result["outcome"],
                    error=result["error"],
                    attempts=result["attempts"],
                    duration_ms=result["duration_ms"],
                    dedup_hash=h,
                )
                self.db.add(log)

                # Handle banner outcomes (non-vote actions fail early with header_*) and popup outcomes
                outcome = result["outcome"]
                if outcome in ("popup_suspended", "header_suspended"):
                    self.pool.mark_worker_suspended(worker.id)
                elif outcome == "header_banned":
                    self.pool.mark_worker_dead(worker.id)

                self.pool.release_worker(worker.id, success)
                failed_ids = json.loads(task.failed_workers or "[]")
                if not success:
                    failed_ids.append(worker.id)
                    task.failed_workers = json.dumps(failed_ids)
                task.workers_completed += 1
                self.db.commit()
                assigned_ids = json.loads(task.workers_assigned or "[]")

        # Finalize
        total = task.workers_completed
        failed = len(failed_ids)
        succeeded = total - failed

        if total == 0:
            task.status = TaskStatus.failed
        elif failed == 0:
            task.status = TaskStatus.completed
        elif succeeded == 0:
            task.status = TaskStatus.failed
        else:
            task.status = TaskStatus.partial
        task.completed_at = datetime.utcnow()
        self.db.commit()
        logger.info(
            f"Task {task.id} {task.status.value} - {succeeded} ok, {failed} failed"
        )

    # ------------------------------------------------------------------
    # Background loop
    # ------------------------------------------------------------------

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("Queue processor started")

    def stop(self):
        self._running = False
        logger.info("Queue processor stopped")

    def is_running(self) -> bool:
        return self._running

    def _loop(self):
        while self._running:
            try:
                self.db.expire_all()
                task = self.next_task()
                if not task:
                    time.sleep(2)
                    continue
                self.process_task(task)
            except Exception as e:
                logger.error(f"Queue loop error: {e}", exc_info=True)
                time.sleep(5)