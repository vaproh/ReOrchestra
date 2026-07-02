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

### 1.1 Fix Login Proxy Injection ✅
- **Files:** `app/services/login.py`, `app/services/browser.py`
- **Issue:** Login doesn't pass proxies to Camofox session creation
- **Status:** VERIFIED - Proxy IS passed correctly via `set_user_proxy()` before `create_tab()`. Not an issue.
- **Breakdown:**
  - [x] Review `LoginService.create_session()` in login.py
  - [x] Ensure `proxy` parameter is passed when creating Camofox tab
  - [x] Verify `sticky-proxy` plugin receives proxy config
  - [x] Test login flow with proxy

### 1.2 Fix DB Session Lifecycle ✅
- **Files:** `app/services/queue_processor.py`
- **Issue:** QueueProcessor holds one `SessionLocal()` forever; uses `expire_all()` as band-aid
- **Breakdown:**
  - [x] Create fresh session per task in `_loop()`
  - [x] Pass session through `process_task()`
  - [x] Remove `expire_all()` calls
  - [x] Ensure proper close after each task

### 1.3 Parallel Worker Execution ✅
- **Files:** `app/services/queue_processor.py`
- **Issue:** Workers per task run sequentially, not in parallel
- **Status:** VERIFIED - ThreadPoolExecutor IS used with `as_completed`. Workers run in parallel.
- **Breakdown:**
  - [x] Add `from concurrent.futures import ThreadPoolExecutor, as_completed`
  - [x] Wrap `execute_for_worker()` calls in ThreadPoolExecutor
  - [x] Configurable max workers per task (from config)
  - [x] Wait for all workers to complete before finalizing task
  - [x] Handle exceptions from worker threads properly

---

## Phase 2: Rate Limiting ⚡

### 2.1 Integrate RateLimiter into Queue Loop ✅
- **Files:** `app/services/queue_processor.py`, `app/services/rate_limiter.py`
- **Issue:** `RateLimiter` class exists but queue doesn't use it
- **Status:** VERIFIED - RateLimiter IS integrated. `check()` called before execution, `record_vote()` called after success.
- **Breakdown:**
  - [x] Import `RateLimiter` in queue_processor.py
  - [x] Add `rate_limiter.check(worker)` call before `execute_for_worker()`
  - [x] Skip worker if rate limited (don't block task)
  - [x] Log rate limit skips
  - [x] Respect `votes_today`, `votes_this_week`, `active_hours`

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
  - [x] Remove `global settings` at module import - lazy load
  - [x] Make timeouts configurable in config
  - [x] Fix thread-unsafe `QueueManager` with proper locking
  - [x] Remove bare `except Exception` - fixed bare `except:` at account_service.py:168
  - [x] Fix WorkerPool thread safety - added locking

### 6.3 Testing ✅
- **Files:** `tests/` directory
- **Breakdown:**
  - [x] Unit tests for `RateLimiter` (13 tests)
  - [x] Unit tests for action classes (30 tests)
  - [x] Unit tests for deduplication logic (11 tests)
  - [x] All 54 tests pass

---

## Priority Order

### Completed ✅
1. ~~**1.1** (Login Proxy) - Verified working, not an issue~~ ✅
2. ~~**1.2** (DB Sessions) - Fixed: new session per task~~ ✅
3. ~~**1.3** (Parallel Workers) - Verified working, not an issue~~ ✅
4. ~~**2.1** (RateLimiter) - Verified integrated, not an issue~~ ✅
5. ~~**3.1** (Dead Letter Queue)~~ ✅
6. ~~**3.2** (Graceful Shutdown)~~ ✅
7. ~~**6** (Cleanup)~~ ✅ (6.1, 6.2 complete)
8. ~~**7.1** (WorkerPool thread safety) - Fixed with locking~~ ✅
9. ~~**7.2** (Bare except) - Fixed at account_service.py:168~~ ✅
10. ~~**7.3** (CORS security) - Fixed configurable origins~~ ✅
11. ~~**7.4** (Silent exception swallowing) - Fixed logging/context~~ ✅

### Still Outstanding
1. **2.2** (Session Health Monitoring) - Proactive session refresh
2. **3.3** (Cancellation Tokens) - Stop in-flight work on cancel
3. **4.1** (Dashboard) - UX for managing 500+ accounts
4. **4.2** (Health Check Endpoint) - DB/disk/Camofox health checks

---

## Phase 7: Verified Issues (2026-07-01) 🔍

### 7.1 WorkerPool Thread Safety ✅
- **Files:** `app/services/worker_pool.py`
- **Issue:** No locking around `assign_workers()`, `release_worker()`, `get_idle_workers()`, `can_worker_do_task()`
- **Risk:** HIGH - Concurrent calls can double-assign workers to tasks
- **Fix:** Added `threading.Lock()` and wrapped all state-modifying methods

### 7.2 Bare `except:` Clause ✅
- **Files:** `app/services/account_service.py:168`
- **Issue:** `except:` catches `KeyboardInterrupt`, `SystemExit` instead of `Exception`
- **Risk:** MEDIUM - Masks real errors, returns False silently
- **Fix:** Changed to `except Exception:`

### 7.3 CORS Security Vulnerability ✅
- **Files:** `app/main.py:36-42`, `app/config.py`
- **Issue:** `allow_origins=["*"]` with `allow_credentials=True` - browsers reject this
- **Risk:** HIGH - API exposed to CSRF
- **Fix:** Made origins configurable via `CORS_ALLOWED_ORIGINS` env var, set `allow_credentials=False` when wildcard

### 7.4 Silent Exception Swallowing (Multiple Locations) ✅
- **Files:** Various
- **Issue:** Exceptions caught but context lost (no stack traces, generic errors)
- **Locations:**
  - `queue_processor.py:431` - loop continues silently
  - `queue_actions/base.py:208-214` - returns generic "failed"
  - `browser.py:75-77` - returns `{"ok": False}` without error
  - `account_service.py:49-51` - uses `print()` instead of logger
- **Risk:** MEDIUM - Hard to debug production issues
- **Fix:** Preserve exception context, use proper logging

### 7.5 Critical Bug Fixes (2026-07-01) 🐛

#### 7.5.1 QueueProcessor.start() Inverted Logic ✅
- **File:** `app/services/queue_processor.py:404`
- **Issue:** `if not self._stop_event.is_set(): return` caused queue to NEVER start on fresh boot
- **Risk:** CRITICAL - Queue processor completely broken
- **Fix:** Changed to `if self.is_running(): return`

#### 7.5.2 RateLimiter Daily/Weekly Reset Bug ✅
- **File:** `app/services/rate_limiter.py:86,91`
- **Issue:** Used `.days >= 1` which returns 0 for same-day votes; daily never reset until next calendar day
- **Risk:** HIGH - Rate limiting ineffective, accounts hit limits incorrectly
- **Fix:** Changed to `.total_seconds() >= 86400` (24 hours) and `.total_seconds() >= 604800` (7 days)

#### 7.5.3 workers_assigned Stale Data Race ✅
- **File:** `app/services/queue_processor.py:289`
- **Issue:** `while len(assigned_ids) < task.workers_needed` used stale `assigned_ids` from before loop
- **Risk:** HIGH - Could cause wrong loop exit, tasks processed incorrectly
- **Fix:** Moved `assigned_ids` reload to TOP of while loop, changed to `while True` with break condition

---

## API Bugs Fixed (2026-07-01) 🔧

### Critical Fixes
1. **HTTPException args reversed** - `queue_tasks.py:61,63,65` - Fixed to use `status_code=400, detail=...`
2. **GUI doVote() called wrong endpoint** - Fixed to use `/api/tasks` with `upvote_post`/`downvote_post`
3. **GUI loginAccount() sent empty account_ids** - Fixed to use `/api/accounts/login/simple`

### Medium Fixes
4. **StatsResponse schema mismatch** - `admin.py` now uses correct field names, queries real slot data
5. **Inconsistent error responses** - Added `HTTPException` handler to normalize to `{"error": {...}}` format

---

## Removed from Scope

- Redis / horizontal scaling (single VPS)
- Prometheus metrics (simple logging is enough)
- WebSocket real-time (polling is fine for niche tool)
- Encrypted credentials (not a priority)
- API authentication (direct customers only)
- Horizontal scaling (single VPS only)
