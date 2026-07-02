# AGENTS.md — ReOrchestra

## What Is This Project?

**ReOrchestra** is a white-label bulk Reddit account automation tool for managing 500-1000 Reddit accounts reliably on a single VPS.

> *"Your Accounts, In Harmony"*

**Philosophy:**
- Niche tool, not enterprise
- Single VPS deployment
- Direct customers (pay me directly, I give access)
- No over-engineering — reliable, not instant
- Subscription model: 500 accounts max per customer, but sell as "unlimited" to commercial users

---

## Who Is This For?

**Customers:** Social media managers, SEO agencies, content creators, onlyfans promoters, reputation managers — people who need bulk Reddit engagement but don't want to build their own infrastructure.

**Not for:** Public marketplace SaaS. Direct relationships only.

---

## Core Problem It Solves

Managing hundreds of Reddit accounts without getting them banned. Reddit actively detects:
- Uniform voting patterns
- Datacenter proxies
- Bot-like behavior
- Accounts that only vote (no organic activity)

ReOrchestra solves this with:
- Per-account rate limiting (max 15 votes/day, 100/week)
- S-curve timing with jitter (avoids uniform patterns)
- Stealth browser (Camofox with fingerprint spoofing)
- Proxy injection per session
- Account health monitoring (burn detection)

---

## The 9 Supported Actions

| Category | Action | How It Works |
|----------|--------|--------------|
| **Voting** | `upvote_post`, `downvote_post`, `upvote_comment`, `downvote_comment` | Click first, detect popup AFTER |
| **Social** | `follow_user`, `unfollow_user` | Check banner BEFORE clicking |
| **Community** | `join_subreddit`, `leave_subreddit` | Check banner BEFORE clicking |
| **Content** | `save_post` | Check banner BEFORE clicking |

---

## Key Concepts

| Term | Definition |
|------|------------|
| **Account** | Reddit credentials + proxy + status tracking |
| **Task** | Job: `{action_type, target_url, workers_needed}` |
| **TaskExecutionLog** | Per-account execution result (success, outcome, error, attempts) |
| **Deduplication** | SHA256 of `{account_id}:{action_type}:{target_url}` — prevents same account succeeding same action twice |

---

## Architecture

```
Request → FastAPI → Task Queue (in-memory + DB persistence)
                    ↓
              Task Processor (background loop)
                    ↓
              Account Executor (max 3 concurrent)
                    ↓
              CamofoxClient → Reddit
```

**Queue behavior:**
- FIFO + priority (`priority DESC, created_at ASC`)
- Max 3 concurrent accounts per task (configurable)
- Auto-retry N times (default 3) before marking failed
- Failed accounts replaced automatically
- Deduplication by `{account_id}:{action_type}:{target_url}`
- Vote actions: click first, check popup AFTER (popup only appears after click)
- Non-vote actions: check header banner BEFORE clicking (banner shows before action)

**Single VPS design:** No Redis, no horizontal scaling. SQLite for DB, one QueueProcessor thread.

---

## API Endpoints

### Core Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/accounts/import` | Import account (username, password, proxy) |
| `POST` | `/api/accounts/login` | Login account via Camofox |
| `POST` | `/api/accounts/{id}/status` | Update account status |
| `GET` | `/api/accounts` | List all accounts |
| `GET` | `/api/accounts/{id}` | Get account details |
| `DELETE` | `/api/accounts/{id}` | Delete account |

### Worker Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/workers/bulk` | Create workers from accounts |
| `GET` | `/api/workers` | List workers |
| `POST` | `/api/workers/{id}/pause` | Pause worker |
| `POST` | `/api/workers/{id}/resume` | Resume worker |

### Queue Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/tasks` | Create task (action + target + workers_needed) |
| `GET` | `/api/tasks` | List tasks |
| `GET` | `/api/tasks/{id}` | Get task status + results |
| `POST` | `/api/tasks/{id}/cancel` | Cancel task |
| `POST` | `/api/queue/start` | Start queue processor |
| `POST` | `/api/queue/stop` | Stop queue processor |
| `GET` | `/api/queue/status` | Queue processor status |

### Health Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/admin/health` | Camofox + DB health check |
| `GET` | `/gui` | Web dashboard |

---

## Important Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI entry, CORS, lifespan handler |
| `app/config.py` | Pydantic Settings from `.env` |
| `app/database.py` | SQLAlchemy engine, `get_db` dependency |
| `app/models/__init__.py` | All models + enums + `ACTION_TYPES` |
| `app/services/queue_processor.py` | Background task loop, retries |
| `app/services/worker_pool.py` | Worker assign/release/suspend |
| `app/services/queue_manager.py` | Singleton managing processor |
| `app/services/queue_actions/base.py` | `BaseAction` with `execute()`, `detect_popup()`, `detect_header_banner()` |
| `app/services/queue_actions/actions.py` | 9 action subclasses + `ACTIONS` dict |
| `app/services/browser.py` | `CamofoxClient` — wraps all Camofox HTTP calls |
| `app/services/login.py` | Login via Camofox with proxy injection |
| `app/services/rate_limiter.py` | Per-account rate limiting (exists but NOT YET integrated) |
| `config/default.yaml` | App config (ReOrchestra branding, rate limits, timing) |

---

## How Actions Execute

### Vote Actions (upvote/downvote)

```
1. Create Camofox tab with session
2. Navigate to target URL
3. Sleep 5-7s (page load jitter)
4. Get snapshot
5. Find upvote/downvote button ref via regex
6. Click button (60s timeout)
7. Sleep 2-3s
8. Get post-click snapshot
9. Detect popup (account locked, password compromise)
10. Close tab
```

### Non-Vote Actions (follow/join/save)

```
1. Create Camofox tab with session
2. Navigate to target URL
3. Sleep 5-7s (page load jitter)
4. Get snapshot
5. Check header banner FIRST (suspended/banned shows here)
6. If banner found → fail early with "header_{banner}"
7. Find target button ref via regex
8. Click button (60s timeout)
9. Sleep 2-3s
10. Verify success
11. Close tab
```

---

## Camofox Integration

**Camofox** is a headless Firefox with C++-level anti-detection patches:
- Spoofs `navigator.hardwareConcurrency`, WebGL renderers, AudioContext
- Screen geometry, WebRTC all spoofed before JavaScript sees them
- Runs as separate process on port 9377 (configurable)

**Session format:** `s_{account_id}` (e.g., `s_42` for account 42)
**Worker tab format:** `wq_{worker_id}_{action_type}` (e.g., `wq_15_upvote_post`)

**Proxy injection:** Via `sticky-proxy` plugin. Each user/session gets assigned proxy via `POST /users/{userId}/proxy`.

---

## Outcome Codes

| Outcome | Meaning |
|---------|---------|
| `success` | Action completed |
| `popup_suspended` | Account locked via popup after click |
| `popup_rate_limited` | Rate limited via popup |
| `popup_password_compromised` | Password changed externally |
| `header_suspended` | Suspended via header banner (non-vote) |
| `header_banned` | Banned via header banner (non-vote) |
| `click_timeout` | Button click timed out |
| `element_not_found` | Target element not in snapshot |

---

## Browser Detection: Popup vs Banner

| Detection | When | Actions |
|-----------|------|---------|
| **Popup** | AFTER clicking vote button | upvote_post, downvote_post, upvote_comment, downvote_comment |
| **Header banner** | BEFORE clicking non-vote | follow_user, unfollow_user, join_subreddit, leave_subreddit, save_post |

---

## Adding a New Action

1. **Create class** in `app/services/queue_actions/actions.py`:
   ```python
   class MyAction(BaseAction):
       action_type = "my_action"
       target_pattern = r'button\s+"MyButton"\s+\[e(\d+)\]'
       use_old_reddit = True  # or False for www.reddit.com

       def verify_success(self, snapshot):
           # Non-vote: check banner first
           banner = self.detect_header_banner(snapshot)
           if banner:
               return False, f"header_{banner}"
           # Check success indicator
           if 'button "Done"' in snapshot:
               return True, None
           return False, "Did not complete"
   ```

2. **Register** in `ACTIONS` dict and `ACTION_TYPES` list in `app/models/__init__.py`

3. **Vote actions:** Override `action_blocked_by_banner()` to return `None`

---

## Camofox Snapshot Format

Element refs are `e{NUMBER}` — match with regex:
```python
r'button\s+"upvote"\s+\[e(\d+)\]'
r'link\s+"join"\s+\[e(\d+)\]'
```

`BaseAction.find_ref_by_pattern(snapshot, pattern)` finds the first match.

---

## Current TODO (Priority Order)

1. ~~**1.1** Fix Login Proxy Injection — verified working, proxies passed to Camofox~~ (done)
2. ~~**1.2** Fix DB Session Lifecycle — QueueProcessor session management~~ (done)
3. ~~**1.3** Parallel Worker Execution — verified working with ThreadPoolExecutor~~ (done)
4. ~~**2.1** Integrate RateLimiter into Queue Loop — verified integrated~~ (done)
5. **2.2** Session Health Monitoring — proactive session refresh
6. **3.3** Cancellation Tokens — stop in-flight work on cancel
7. **4.1** Dashboard improvements — better UX for 500+ accounts
8. **4.2** Health Check Endpoint — DB/disk/Camofox monitoring

Full list: `TODO.md`

---

## Code Conventions

- Python 3.x, type hints everywhere
- Pydantic v2 for schemas
- SQLAlchemy 2.x declarative base
- Logging: `logger = logging.getLogger("component_name")`, format: `%(asctime)s | %(levelname)s | %(name)s | %(message)s`
- Import order: stdlib → third-party → local

---

## Gotchas

- **Click timeout**: Camofox click can take 30-60s on suspended accounts — timeout is 60s in `browser.py`
- **Popup vs Banner**: Popup appears AFTER vote click. Banner appears BEFORE non-vote clicks.
- **Session persistence**: Handled by Camofox persistence plugin — cookies survive restarts
- **Proxy per session**: Via sticky-proxy plugin, assigned via `POST /users/{userId}/proxy`
- **Database path**: SQLite at `data/reddit.db`
- **RateLimiter integrated**: `check()` called before vote actions, `record_vote()` after success
- **CORS configurable**: Set `CORS_ALLOWED_ORIGINS` in `.env` (comma-separated); credentials disabled when wildcard
- **WorkerPool thread-safe**: All state-modifying methods use `threading.Lock()`
