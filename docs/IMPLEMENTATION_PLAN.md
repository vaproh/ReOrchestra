# ReOrchestra Queue Rewrite Implementation Plan

This document outlines the step-by-step rewrite plan to transition ReOrchestra from the legacy worker-pool architecture to a simplified, task-based queue system.

## Phase 1: Database Models

Goal: Modify database schema to reflect task-based execution and remove the `Worker` table.

1. **Modify `AccountStatus` Enum** in [models/__init__.py](file:///home/vaproh/Coding/reddit-automation-api/reddit-api/app/models/__init__.py):
   ```python
   class AccountStatus(str, Enum):
       fresh = "fresh"
       logged_in = "logged_in"
       session_expired = "session_expired"
       rate_limited = "rate_limited"
       banned = "banned"
       dead = "dead"
   ```
2. **Simplify `Task` Model** in [models/__init__.py](file:///home/vaproh/Coding/reddit-automation-api/reddit-api/app/models/__init__.py):
   - Remove `workers_assigned` and `failed_workers` JSON strings.
   - Retain `workers_needed` and `workers_completed` (rename or add `workers_failed`).
   - Keep status: `queued`, `running`, `completed`, `partial`, `failed`, `cancelled`.
3. **Add `TaskExecutionLog` Model** (replaces `TaskActionLog` / maps to accounts directly instead of workers):
   ```python
   class TaskExecutionLog(Base):
       __tablename__ = "queue_execution_log"
       id = Column(Integer, primary_key=True, autoincrement=True)
       task_id = Column(Integer, ForeignKey("queue_tasks.id"), nullable=False)
       account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
       success = Column(Boolean, default=False)
       outcome = Column(String(32), nullable=False)  # success, banned, suspended, rate_limited, error
       error_message = Column(Text, nullable=True)
       attempts = Column(Integer, default=1)
       created_at = Column(DateTime, default=datetime.utcnow)
       dedup_hash = Column(String(64), unique=True, nullable=False)
   ```
4. **Remove `Worker` Model**:
   - Delete `Worker` class from `app/models/__init__.py`.
   - Update database initialization.

---

## Phase 2: Queue Processor

Goal: Implement the background loop that fetches and executes tasks using asyncio concurrency.

1. **Implement `QueueProcessor` Loop** in [queue_processor.py](file:///home/vaproh/Coding/reddit-automation-api/reddit-api/app/services/queue_processor.py):
   - Replace thread-pool execution with a clean `while self.running:` loop.
   - Fetch next task via priority/FIFO: `priority DESC, created_at ASC`.
   - Track active tasks using an in-memory dictionary/set to enforce the global concurrency limit (max 3).
2. **Implement Account Selection and Deduping**:
   - Query for accounts where `status == AccountStatus.logged_in`.
   - Filter out accounts currently busy or that already have a successful entry in `TaskExecutionLog` for the current action type and target URL.
3. **Use asyncio for Concurrency**:
   - Process multiple task actions concurrently using `asyncio.gather` or `asyncio.as_completed` up to the max concurrency threshold.

---

## Phase 3: Executor Integration

Goal: Connect the Queue Processor with Camofox actions.

1. **Wrap Actions in Executor**:
   - Utilize existing `browser.py` and `CamofoxClient` to execute actions.
   - Wrap executions in retry-handler (default 3 retries for timeouts/not found).
2. **Handle Executed Action Outcomes**:
   - Map Camofox results to outcomes.
   - Update account status based on result:
     - `popup_suspended` / `header_suspended` / `header_banned` ➔ `dead` / `banned`.
     - `popup_rate_limited` ➔ `rate_limited`.
   - Record results in `TaskExecutionLog`.

---

## Phase 4: API Updates

Goal: Adjust API routes to match the simplified design.

1. **Update `/api/tasks`**:
   - Adjust request and response schemas to use the updated `Task` properties.
2. **Refactor/Remove `/api/workers`**:
   - Remove worker endpoints since the `Worker` model is deleted.
3. **Add Reliable Cancel Endpoint**:
   - Implement real-time task cancellation that updates status to `cancelled` and terminates running actions immediately.
4. **Add Queue Status Endpoint**:
   - Report queue state (active runs, concurrency load, pending tasks count).

---

## Phase 5: Testing

Goal: Verify the robustness of the new queue system.

1. **Test Concurrency Limits**:
   - Ensure no more than 3 executions run simultaneously.
2. **Test Account Replacement**:
   - Verify that when an account fails, another logged-in account is selected to take its place.
3. **Test Deduplication**:
   - Ensure an account never runs the same task action twice.
