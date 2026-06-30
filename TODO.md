# ReOrchestra Implementation TODO

**Philosophy:** Niche tool, single VPS, direct customers. No over-engineering. Reliable, not instant.

---

## Configuration

All settings are managed via `.env` file and `app/config.py`.

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `CAMOFOX_DIR` | `../camofox` | Path to Camofox directory |
| `CAMOFOX_PORT` | `9377` | Camofox server port |

---

## Phase 1: Critical Fixes 🔴

### 1.1 Fix Login Proxy Injection
- **Files:** `app/services/login.py`, `app/services/browser.py`
- **Issue:** Login doesn't pass proxies to Camofox session creation
- **Breakdown:**
  - [ ] Review `LoginService.create_session()` in login.py
  - [ ] Ensure `proxy` parameter is passed when creating Camofox tab
  - [ ] Verify `sticky-proxy` plugin receives proxy config
  - [ ] Test login flow with proxy

### 1.2 Fix DB Session Lifecycle
- **Files:** `app/services/queue_processor.py`
- **Issue:** QueueProcessor holds one `SessionLocal()` forever; uses `expire_all()` as band-aid
- **Breakdown:**
  - [ ] Create `db.get_task_session()` helper that returns a new session per task
  - [ ] Pass session through `process_task()` → `assign_workers()` → `execute_for_worker()`
  - [ ] Remove `expire_all()` calls
  - [ ] Ensure proper commit/close after each task

### 1.3 Parallel Worker Execution
- **Files:** `app/services/queue_processor.py`
- **Issue:** Workers per task run sequentially, not in parallel
- **Breakdown:**
  - [ ] Add `from concurrent.futures import ThreadPoolExecutor, as_completed`
  - [ ] Wrap `execute_for_worker()` calls in ThreadPoolExecutor
  - [ ] Configurable max workers per task (from config)
  - [ ] Wait for all workers to complete before finalizing task
  - [ ] Handle exceptions from worker threads properly

---

## Phase 2: Rate Limiting ⚡

### 2.1 Integrate RateLimiter into Queue Loop
- **Files:** `app/services/queue_processor.py`, `app/services/rate_limiter.py`
- **Issue:** `RateLimiter` class exists but queue doesn't use it
- **Breakdown:**
  - [ ] Import `RateLimiter` in queue_processor.py
  - [ ] Add `rate_limiter.check(worker)` call before `execute_for_worker()`
  - [ ] Skip worker if rate limited (don't block task)
  - [ ] Log rate limit skips
  - [ ] Respect `votes_today`, `votes_this_week`, `active_hours`

### 2.2 Session Health Monitoring
- **Files:** `app/services/login.py`
- **Issue:** Sessions age but aren't proactively refreshed
- **Breakdown:**
  - [ ] Check session file mtime against `max_session_age_hours` from config
  - [ ] If session > 50% of max_age, proactively renew
  - [ ] Add periodic session check in queue_manager

---

## Phase 3: Reliability 🛡️

### 3.1 Dead Letter Queue
- **Files:** `app/models/__init__.py`, `app/services/queue_processor.py`
- **Issue:** Failed tasks vanish after completion
- **Breakdown:**
  - [ ] Add `TaskStatus.dead_letter` to enum
  - [ ] Add `failure_reason`, `retry_count`, `last_error` fields to Task
  - [ ] After 3 retries with no success, move to dead_letter
  - [ ] Store last error message
  - [ ] Add API endpoint to list dead letter tasks
  - [ ] Add retry endpoint to resubmit

### 3.2 Graceful Shutdown
- **Files:** `app/services/queue_processor.py`
- **Issue:** `stop()` sets `_running=False` but doesn't wait for in-flight work
- **Breakdown:**
  - [ ] Add `_shutdown_event` (threading.Event)
  - [ ] On shutdown, set event and wait for current task
  - [ ] Configurable shutdown timeout (default 30s)

### 3.3 Cancellation Tokens
- **Files:** `app/services/queue_processor.py`, `app/services/queue_actions/base.py`
- **Issue:** Cancel sets status but doesn't stop in-flight work
- **Breakdown:**
  - [ ] Create `CancellationToken` class
  - [ ] Add token parameter to `BaseAction.execute()`
  - [ ] Check token between action steps
  - [ ] Handle cancellation gracefully

---

## Phase 4: Dashboard 📊

### 4.1 Improve Existing GUI
- **Files:** `app/gui/index.html`
- **Issue:** Basic, needs better UX for 500+ accounts
- **Breakdown:**
  - [ ] Show account list with status (idle/working/paused/dead)
  - [ ] Show task queue with progress
  - [ ] Show real-time worker activity
  - [ ] Quick actions: pause/resume accounts
  - [ ] Dead letter queue view
  - [ ] Session health indicators

### 4.2 Health Check Endpoint
- **Files:** `app/api/health.py`, `app/main.py`
- **Breakdown:**
  - [ ] Check DB connectivity
  - [ ] Check session directory disk space
  - [ ] Check Camofox connection
  - [ ] Return status for monitoring

---

## Phase 6: Cleanup 🧹 ✅

### 6.1 Remove Legacy Action System ✅
- **Files:** `app/api/actions.py`, `app/services/action_service.py`
- **Issue:** Duplicate action systems
- **Breakdown:**
  - [x] Audit all usages of `ActionService`
  - [x] Remove legacy files
  - [x] Update router to remove `/api/actions/*` routes

### 6.2 Fix Technical Debt ✅
- **Files:** Various
- **Breakdown:**
  - [x] Remove bare `except Exception` - catch specific exceptions
  - [x] Remove `global settings` at module import - lazy load
  - [x] Make timeouts configurable in config
  - [x] Fix thread-unsafe `QueueManager` with proper locking

### 6.3 Testing
- **Files:** `tests/` directory
- **Breakdown:**
  - [ ] Unit tests for `RateLimiter`
  - [ ] Unit tests for action classes
  - [ ] Unit tests for deduplication logic

---

## Priority Order

1. ~~**1.2** (DB Sessions) - Stability~~ ✅
2. ~~**2.1** (RateLimiter) - Prevent account burning~~ ✅
3. ~~**3.1** (Dead Letter Queue) - Failed task visibility~~ ✅
4. ~~**3.2** (Graceful Shutdown) - Production reliability~~ ✅
5. **4.1** (Dashboard) - UX for managing 500+ accounts
6. ~~**6** (Cleanup) - Technical debt~~ ✅ (6.1, 6.2 complete)

---

## Removed from Scope

- Redis / horizontal scaling (single VPS)
- Prometheus metrics (simple logging is enough)
- WebSocket real-time (polling is fine for niche tool)
- Encrypted credentials (not a priority)
- API authentication (direct customers only)
- Horizontal scaling (single VPS only)
