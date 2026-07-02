"""
Queue processor service.

Simple task-based queue that runs in a background thread.

For each task it:
1. Picks the next queued task (priority DESC, created_at ASC)
2. Finds idle logged_in accounts that haven't already done this action
3. Executes up to max_concurrent (default 3) accounts concurrently
4. On success: increments workers_completed
5. On ban/suspend: marks account dead, replaces with a new account
6. On rate-limit: marks account rate_limited, replaces with a new account
7. On retryable error: retries N times before counting as failure
8. Continues until workers_needed satisfied or no accounts left
9. Marks task completed / partial / failed / cancelled
"""

import hashlib
import time
import logging
import threading
from datetime import datetime
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session, sessionmaker

from app.models import (
    Task, TaskStatus, TaskExecutionLog,
    Account, AccountStatus,
)
from app.modules.executor.browser import CamofoxClient
from app.modules.executor.actions import get_action_class
from app.modules.executor.rate_limiter import RateLimiter
from app.config import get_settings

logger = logging.getLogger("queue")

VOTE_ACTIONS = frozenset({
    "upvote_post", "downvote_post", "upvote_comment", "downvote_comment"
})

# Outcomes that permanently kill an account — replace it immediately
DEAD_OUTCOMES = frozenset({
    "popup_suspended", "header_suspended", "header_banned",
    "popup_account_locked",
})

# Outcomes that temporarily mark rate_limited — still replace for this task
RATE_LIMITED_OUTCOMES = frozenset({
    "popup_rate_limited",
})


def dedup_hash(account_id: int, action_type: str, target_url: str) -> str:
    """SHA-256[:16] of account_id:action_type:target_url."""
    raw = f"{account_id}:{action_type}:{target_url}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class QueueProcessor:
    """
    Background thread that consumes tasks one at a time from the DB.

    Concurrency: up to `max_concurrent` accounts run in parallel via
    ThreadPoolExecutor.  Accounts ARE the workers — no Worker model needed.
    """

    def __init__(self, db: Session, camofox: Optional[CamofoxClient] = None):
        self._session_factory = sessionmaker(bind=db.bind)
        self.camofox = camofox or CamofoxClient()
        self.rate_limiter = RateLimiter()

        settings = get_settings()
        self.max_concurrent: int = getattr(settings, "max_concurrent_per_task", 3)
        self.max_retries: int = 3

        self._stop_event = threading.Event()
        # Maps task_id → Event; set to signal that task should abort
        self._cancel_events: dict[int, threading.Event] = {}
        self._thread: Optional[threading.Thread] = None
        self._loop_errors = 0

        # Close the bootstrap db session — we create fresh ones per loop tick
        db.close()

    # ------------------------------------------------------------------
    # Public API (called from API routes via QueueManager)
    # ------------------------------------------------------------------

    def create_task(self, db: Session, action_type: str, target_url: str,
                    workers_needed: int = 1) -> Task:
        if not get_action_class(action_type):
            raise ValueError(f"Unknown action type: {action_type}")
        task = Task(
            action_type=action_type,
            target_url=target_url,
            workers_needed=workers_needed,
            status=TaskStatus.queued,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    def cancel_task(self, db: Session, task_id: int) -> Task:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        if task.status in (TaskStatus.completed, TaskStatus.cancelled):
            return task
        task.status = TaskStatus.cancelled
        task.completed_at = datetime.utcnow()
        # Signal the running thread to abort this task
        evt = self._cancel_events.get(task_id)
        if evt:
            evt.set()
        db.commit()
        db.refresh(task)
        return task

    def priority_boost(self, db: Session, task_id: int) -> Task:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError("Task not found")
        task.priority = (task.priority or 0) + 1000
        db.commit()
        db.refresh(task)
        return task

    def list_queue(self, db: Session) -> list[Task]:
        return (
            db.query(Task)
            .filter(Task.status.in_([TaskStatus.queued, TaskStatus.running]))
            .order_by(Task.priority.desc(), Task.created_at.asc())
            .all()
        )

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive() and not self._stop_event.is_set()

    def is_stopped(self) -> bool:
        return not self._thread or not self._thread.is_alive()

    # ------------------------------------------------------------------
    # Thread lifecycle
    # ------------------------------------------------------------------

    def start(self):
        if self.is_running():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="QueueProcessor")
        self._thread.start()
        logger.info("queue | processor_start")

    def stop(self, timeout: float = 300):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            if self._thread.is_alive():
                logger.warning("queue | processor_stop | thread did not exit within timeout")
        logger.info("queue | processor_stop")

    def _loop(self):
        """Main background loop — one task at a time, fresh DB session per tick."""
        while not self._stop_event.is_set():
            db = self._session_factory()
            try:
                task = (
                    db.query(Task)
                    .filter(Task.status == TaskStatus.queued)
                    .order_by(Task.priority.desc(), Task.created_at.asc())
                    .first()
                )
                if not task:
                    # Nothing queued — idle wait
                    if self._stop_event.wait(timeout=2):
                        break
                    continue
                self._process_task(task, db)
                self._loop_errors = 0
            except Exception as e:
                self._loop_errors += 1
                backoff = min(2 ** self._loop_errors, 30)
                logger.error(f"queue | loop_error | {e}", exc_info=True)
                if self._stop_event.wait(timeout=backoff):
                    break
            finally:
                db.close()

    # ------------------------------------------------------------------
    # Task processing
    # ------------------------------------------------------------------

    def _process_task(self, task: Task, db: Session):
        """Process a single task to completion (or cancellation)."""
        task_id = task.id

        # Mark running
        task.status = TaskStatus.running
        task.started_at = datetime.utcnow()
        db.commit()

        cancel_event = threading.Event()
        self._cancel_events[task_id] = cancel_event

        logger.info(
            f"queue | task_start | task_id={task_id} "
            f"action={task.action_type} needed={task.workers_needed}"
        )

        try:
            self._run_task_loop(task, db, cancel_event)
        finally:
            self._cancel_events.pop(task_id, None)
            # Re-read from DB to get the latest counts before finalising
            db.refresh(task)
            self._finalise_task(task, db, cancelled=cancel_event.is_set())

    def _run_task_loop(self, task: Task, db: Session, cancel_event: threading.Event):
        """
        Inner loop: keep assigning accounts and executing until either
        workers_completed reaches workers_needed, or no eligible accounts remain.
        """
        while not cancel_event.is_set():
            db.refresh(task)
            if task.workers_completed >= task.workers_needed:
                break

            slots_remaining = task.workers_needed - task.workers_completed
            batch_size = min(self.max_concurrent, slots_remaining)

            accounts = self._find_eligible_accounts(task, db, limit=batch_size)
            if not accounts:
                logger.info(
                    f"queue | no_eligible_accounts | task_id={task.id} "
                    f"completed={task.workers_completed}/{task.workers_needed}"
                )
                break

            results = self._execute_batch(task, accounts, db, cancel_event)

            for account_id, result in results:
                if cancel_event.is_set():
                    break
                self._handle_result(task, account_id, result, db)

    def _find_eligible_accounts(self, task: Task, db: Session, limit: int) -> list[Account]:
        """Find up to `limit` logged_in accounts that haven't already succeeded at this action."""
        succeeded_ids = (
            db.query(TaskExecutionLog.account_id)
            .filter(
                TaskExecutionLog.action_type == task.action_type,
                TaskExecutionLog.target_url == task.target_url,
                TaskExecutionLog.success == True,
            )
            .scalar_subquery()
        )

        candidates = (
            db.query(Account)
            .filter(
                Account.status == AccountStatus.logged_in,
                Account.id.not_in(succeeded_ids),
            )
            .order_by(Account.last_used.asc().nullsfirst(), Account.id)
            .limit(limit * 3)
            .all()
        )
        return candidates[:limit]

    def _execute_batch(
        self,
        task: Task,
        accounts: list[Account],
        db: Session,
        cancel_event: threading.Event,
    ) -> list[tuple[int, dict]]:
        """Execute actions for a batch of accounts concurrently."""
        task_id = task.id
        action_type = task.action_type
        target_url = task.target_url

        def run_one(account_id: int) -> tuple[int, dict]:
            thread_db = self._session_factory()
            try:
                account = thread_db.query(Account).filter(Account.id == account_id).first()
                task_obj = thread_db.query(Task).filter(Task.id == task_id).first()
                if not account or not task_obj:
                    return account_id, {"success": False, "outcome": "failed",
                                        "error": "Account or task not found",
                                        "attempts": 0, "duration_ms": 0}

                # Rate-limit check for vote actions
                if action_type in VOTE_ACTIONS:
                    allowed, reason = self.rate_limiter.check(account, thread_db)
                    if not allowed:
                        logger.info(f"queue | rate_limited | account_id={account_id} reason={reason}")
                        return account_id, {"success": False, "outcome": "rate_limited",
                                            "error": reason, "attempts": 0, "duration_ms": 0}

                result = self._execute_with_retries(
                    account, task_obj, cancel_event, thread_db
                )

                # Record vote in rate limiter on success
                if result["success"] and action_type in VOTE_ACTIONS:
                    self.rate_limiter.record_vote(account, thread_db)

                return account_id, result
            except Exception as e:
                logger.exception(f"queue | run_one_exception | account_id={account_id}")
                return account_id, {"success": False, "outcome": "failed",
                                    "error": str(e), "attempts": 0, "duration_ms": 0}
            finally:
                thread_db.close()

        max_workers = min(len(accounts), self.max_concurrent)
        results: list[tuple[int, dict]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(run_one, acct.id): acct.id for acct in accounts}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    account_id = futures[future]
                    logger.exception(f"queue | future_exception | account_id={account_id}")
                    results.append((account_id, {
                        "success": False, "outcome": "failed",
                        "error": str(e), "attempts": 0, "duration_ms": 0,
                    }))
        return results

    def _execute_with_retries(
        self,
        account: Account,
        task: Task,
        cancel_event: threading.Event,
        db: Session,
    ) -> dict:
        """Run the action with up to max_retries attempts."""
        action_cls = get_action_class(task.action_type)
        if not action_cls:
            return {"success": False, "outcome": "failed",
                    "error": f"Unknown action: {task.action_type}",
                    "attempts": 0, "duration_ms": 0}

        action = action_cls(self.camofox)
        last_result = None

        for attempt in range(1, self.max_retries + 1):
            if cancel_event.is_set():
                return {"success": False, "outcome": "cancelled",
                        "error": "Task cancelled", "attempts": attempt - 1, "duration_ms": 0}

            logger.info(
                f"queue | attempt | task_id={task.id} "
                f"account_id={account.id} attempt={attempt}/{self.max_retries}"
            )
            result = action.execute(account, task.target_url)
            last_result = result

            if result.success:
                break

            # Terminal outcomes — stop immediately, no retry
            if result.outcome in DEAD_OUTCOMES or result.outcome in RATE_LIMITED_OUTCOMES:
                break

            # Retryable — sleep with exponential backoff
            if attempt < self.max_retries:
                backoff = min(2 ** attempt, 30)
                logger.info(
                    f"queue | retry_backoff | task_id={task.id} "
                    f"account_id={account.id} backoff={backoff}s outcome={result.outcome}"
                )
                if cancel_event.wait(timeout=backoff):
                    return {"success": False, "outcome": "cancelled",
                            "error": "Task cancelled during backoff",
                            "attempts": attempt, "duration_ms": 0}

        if last_result is None:
            return {"success": False, "outcome": "failed",
                    "error": "No result", "attempts": 0, "duration_ms": 0}

        return {
            "success": last_result.success,
            "outcome": last_result.outcome,
            "error": last_result.error,
            "attempts": self.max_retries if not last_result.success else 1,
            "duration_ms": last_result.duration_ms,
        }

    def _handle_result(self, task: Task, account_id: int, result: dict, db: Session):
        """Persist execution log entry and update task + account status."""
        success = result["success"]
        outcome = result["outcome"]

        # Write execution log
        h = dedup_hash(account_id, task.action_type, task.target_url)
        existing = db.query(TaskExecutionLog).filter(
            TaskExecutionLog.dedup_hash == h,
            TaskExecutionLog.success == True,
        ).first()
        if not (existing and success):
            log = TaskExecutionLog(
                task_id=task.id,
                account_id=account_id,
                action_type=task.action_type,
                target_url=task.target_url,
                success=success,
                outcome=outcome,
                error=result.get("error"),
                attempts=result.get("attempts", 1),
                duration_ms=result.get("duration_ms"),
                dedup_hash=h,
            )
            db.add(log)

        # Update account status based on outcome
        account = db.query(Account).filter(Account.id == account_id).first()
        if account:
            if outcome in DEAD_OUTCOMES:
                account.status = AccountStatus.dead
                account.dead_reason = outcome
                logger.warning(
                    f"queue | account_dead | account_id={account_id} "
                    f"username={account.username} reason={outcome}"
                )
            elif outcome in RATE_LIMITED_OUTCOMES:
                account.status = AccountStatus.rate_limited
                logger.info(
                    f"queue | account_rate_limited | account_id={account_id} "
                    f"username={account.username}"
                )
            account.last_used = datetime.utcnow()

        # Update task counters
        if success:
            task.workers_completed += 1
        else:
            task.workers_failed += 1

        try:
            db.commit()
        except Exception:
            db.rollback()
            logger.exception(f"queue | handle_result_commit_failed | task_id={task.id}")

    def _finalise_task(self, task: Task, db: Session, cancelled: bool):
        """Set final task status and completed_at."""
        if cancelled:
            task.status = TaskStatus.cancelled
        elif task.workers_completed >= task.workers_needed:
            task.status = TaskStatus.completed
        elif task.workers_completed > 0:
            task.status = TaskStatus.partial
        else:
            task.status = TaskStatus.failed

        task.completed_at = datetime.utcnow()
        db.commit()
        logger.info(
            f"queue | task_done | task_id={task.id} status={task.status.value} "
            f"completed={task.workers_completed} failed={task.workers_failed} "
            f"needed={task.workers_needed}"
        )
