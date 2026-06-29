# ReOrchestra Implementation TODO

**Philosophy:** Niche tool, single VPS, direct customers. No over-engineering. Reliable, not instant.

---

## Configuration

All settings are managed via `.env` file and `app/config.py`.

### Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `APP_MODE` | `production` | `production` or `test` |
| `CAMOFOX_DIR` | `../camofox` | Path to Camofox directory |
| `CAMOFOX_PORT` | `9377` | Camofox server port |
| `TEST_SERVER_URL` | `http://localhost:8080` | Test server URL |
| `TEST_SERVER_PORT` | `8080` | Test server port |
| `TEST_DB_URL` | `sqlite:///./data/test.db` | Test database |
| `TEST_SESSION_DIR` | `data/test_sessions` | Test sessions directory |
| `TEST_PROXY` | `http://test_proxy:8080` | Test proxy |
| `TUNNEL_DOMAIN` | `vaproh.space` | Tunnel domain |
| `TUNNEL_SUBDOMAIN` | `reorchestra-test` | Tunnel subdomain |
| `TUNNEL_NAME` | `reorchestra-test` | Cloudflare tunnel name |

### Starting Test Mode

```bash
# 1. Set mode
export APP_MODE=test
export TEST_SERVER_URL=https://reorchestra-test.vaproh.space

# 2. Start tunnel (Terminal 1)
python tests/start_permanent_tunnel.py

# 3. Start test server (Terminal 2)
uvicorn tests.server:app --port 8080

# 4. Run tests (Terminal 3)
pytest tests/ -v
```

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

## Phase 5: Test Mode 🧪 ✅

### 5.1 Test Server
- [x] Create FastAPI server (`tests/server.py`)
- [x] Create 9 HTML test pages (one per action)
- [x] Support `?scenario=suspended|locked|rate_limited|banned` query params
- [x] Track per-session state (upvoted, followed, etc.)
- [x] Provide `/api/state/{session}` endpoint for assertions
- [x] Provide `/api/reset/{session}` for resetting state

### 5.2 Test Mode Config
- [x] Add `APP_MODE` env var (`production` | `test`)
- [x] Add `TEST_SERVER_URL` env var (default `http://localhost:8080`)
- [x] Add `is_test_mode` property to Settings

### 5.3 URL Routing for Test Mode
- [x] Add `_get_test_path()` method mapping action_type to test URL
- [x] Modify `normalize_url()` to route to test server when `APP_MODE=test`

### 5.4 Login Bypass for Test Mode
- [x] Add `_fake_login()` method that creates session without Reddit
- [x] Skip `_do_login_sync()` when `APP_MODE=test`

### 5.5 Test Database & Fixtures
- [x] Use separate `data/test.db` SQLite file
- [x] Session-scoped DB (shared between tests)
- [x] Auto-generate test accounts with real proxy format
- [x] Auto-generate test workers
- [x] `test_server` fixture to start/stop FastAPI server
- [x] Session cleanup (removes test sessions from Camofox data dir)

### 5.6 Pytest Suite
- [x] Test all 9 actions with success scenario
- [x] Test all 9 actions with failure scenarios (suspended, locked, etc.)
- [x] Test deduplication
- [x] Test parallel worker execution

### 5.7 Tunnel Integration
- [x] Temporary tunnel: `tests/start_tunnel.py` (trycloudflare.com)
- [x] Permanent tunnel: `tests/start_permanent_tunnel.py` (reorchestra-test.vaproh.space)

---

## Phase 6: Cleanup 🧹

### 6.1 Remove Legacy Action System
- **Files:** `app/api/actions.py`, `app/services/action_service.py`
- **Issue:** Duplicate action systems
- **Breakdown:**
  - [ ] Audit all usages of `ActionService`
  - [ ] Remove legacy files
  - [ ] Update router to remove `/api/actions/*` routes

### 6.2 Fix Technical Debt
- **Files:** Various
- **Breakdown:**
  - [ ] Remove bare `except Exception` - catch specific exceptions
  - [ ] Remove `global settings` at module import - lazy load
  - [ ] Make timeouts configurable in config
  - [ ] Fix thread-unsafe `QueueManager` with proper locking

### 6.3 Testing
- **Files:** `tests/` directory
- **Breakdown:**
  - [ ] Unit tests for `RateLimiter`
  - [ ] Unit tests for action classes
  - [ ] Unit tests for deduplication logic

---

## Priority Order

1. **5** (Test Mode) - Verify everything works without touching Reddit
2. **1.2** (DB Sessions) - Stability
3. **2.1** (RateLimiter) - Prevent account burning
4. **3.1** (Dead Letter Queue) - Failed task visibility
5. **3.2** (Graceful Shutdown) - Production reliability
6. **4.1** (Dashboard) - UX for managing 500+ accounts
7. **6** (Cleanup) - Technical debt

---

## Removed from Scope

- Redis / horizontal scaling (single VPS)
- Prometheus metrics (simple logging is enough)
- WebSocket real-time (polling is fine for niche tool)
- Encrypted credentials (not a priority)
- API authentication (direct customers only)
- Horizontal scaling (single VPS only)
