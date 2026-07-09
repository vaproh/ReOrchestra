# AGENTS.md — ReOrchestra 🚀

## What Is This Project?

**ReOrchestra** is a bulk Reddit account automation tool for managing 500-1000 Reddit accounts on a single VPS.

> *"Your Accounts, In Harmony"*

### Philosophy
- Simple, not enterprise
- Single VPS deployment
- Direct customers only
- Reliable, not instant
- Task-based queue — accounts ARE the workers

---

## Who Is This For?

**Customers:** Social media managers, SEO agencies, content creators — people who need bulk Reddit engagement.

**Not for:** Public marketplace SaaS. Direct relationships only.

---

## Core Problem It Solves

Managing hundreds of Reddit accounts without getting them banned. Reddit detects:
- Uniform voting patterns
- Datacenter proxies
- Bot-like behavior

ReOrchestra solves this with:
- Per-account rate limiting (15 votes/day, 100/week)
- S-curve timing with jitter
- Stealth browser (Camofox with fingerprint spoofing)
- Proxy injection per session
- Account health monitoring (burn detection)

---

## The 9 Supported Actions

| Category | Action | Detection |
|----------|--------|-----------|
| **Voting** | `upvote_post`, `downvote_post`, `upvote_comment`, `downvote_comment` | Popup AFTER click |
| **Social** | `follow_user`, `unfollow_user` | Banner BEFORE click |
| **Community** | `join_subreddit`, `leave_subreddit` | Banner BEFORE click |
| **Content** | `save_post` | Banner BEFORE click |

---

## Key Concepts

| Term | Definition |
|------|------------|
| **Account** | Reddit credentials + proxy + status |
| **Task** | Job: `{action_type, target_url, workers_needed}` |
| **TaskExecutionLog** | Per-account execution result |
| **Deduplication** | SHA256 of `{account_id}:{action_type}:{target_url}` |
| **QueueProcessor** | Background loop that processes tasks |

---

## Architecture

```
Request → FastAPI → Task Queue (SQLite)
                    ↓
              QueueProcessor (background loop)
                    ↓
              Account Executor (max 3 concurrent)
                    ↓
              CamofoxClient → Reddit
```

### Queue Behavior
- FIFO + priority
- Max 3 concurrent accounts per task (configurable)
- Auto-retry 3 times before marking failed
- Failed accounts (ban/suspend) replaced automatically
- Deduplication by `{account_id}:{action_type}:{target_url}`

**Single VPS:** SQLite for DB, one QueueProcessor.

---

## Dashboard

Web UI at `http://localhost:8000` built with HTMX + Jinja2 + Tailwind + Flowbite.

### Pages

| Route | Purpose |
|-------|---------|
| `/dashboard` | Stats overview, queue control, recent activity |
| `/accounts` | Account list, import, login, delete |
| `/tasks` | Task list, create task, cancel/retry |
| `/tasks/{id}` | Task detail with execution logs |
| `/proxies` | Proxy list, import, mark dead |
| `/system` | System health, log streaming |

### Tech Stack
- **Templates**: Jinja2 with FastHX helpers
- **Styling**: Tailwind CSS + Flowbite components
- **Interactivity**: HTMX with auto-refresh

### HTMX Patterns
- Forms submit via HTMX to API endpoints
- Auto-refresh stats every 30s
- Running tasks auto-refresh every 5s
- Delete/cancel with confirmation dialogs

---

## Project Structure

```
app/
├── main.py                    # FastAPI entry, CORS, lifespan
├── config.py                 # Pydantic Settings from .env
├── database.py               # SQLAlchemy engine, get_db
├── logging_config.py         # Logging setup
│
├── logging/                  # Logging utilities
│   ├── __init__.py
│   ├── audit.py             # audit() for audit trail
│   ├── redact.py            # redact_password(), redact_proxy()
│   ├── structured.py        # StructuredFormatter
│   └── timing.py           # timed_operation() context manager
│
├── api/                      # FastAPI routers
│   ├── accounts.py           # /api/accounts/*
│   ├── queue_tasks.py       # /api/tasks/*
│   ├── queue_queue.py       # /api/queue/*
│   ├── proxies.py          # /api/proxies/*
│   ├── admin.py            # /api/admin/*
│   ├── frontend.py         # /dashboard, /accounts, /tasks, /proxies
│   └── router.py           # Central router
│
├── models/                   # SQLAlchemy models
│   └── __init__.py          # Account, Proxy, Task, TaskExecutionLog
│
├── schemas/                  # Pydantic schemas
│   ├── account.py
│   ├── common.py
│   └── proxy.py
│
├── templates/                # Jinja2 templates (HTMX + Flowbite)
│   ├── base.html
│   ├── pages/              # dashboard, accounts, tasks, proxies
│   └── components/         # stat_card, status_badge, modal, etc.
│
├── static/                   # CSS, JS
│   └── css/
│       └── custom.css
│
└── modules/
    ├── accounts/            # Account management
    │   └── login.py         # LoginService
    │
    ├── queue/              # Queue processing
    │   ├── __init__.py     # QueueManager singleton
    │   └── processor.py    # QueueProcessor (background loop)
    │
    ├── executor/            # Browser automation
    │   ├── browser.py      # CamofoxClient
    │   ├── rate_limiter.py # RateLimiter
    │   └── actions/
    │       ├── base.py     # BaseAction
    │       └── actions.py  # 9 action classes + ACTIONS dict
    │
    └── shared/              # Shared utilities
        ├── config.py       # ConfigService (YAML)
        └── exceptions.py   # Custom exceptions
```

---

## API Endpoints

### Accounts

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/accounts/import` | Import accounts |
| `POST` | `/api/accounts/login` | Login via Camofox |
| `GET` | `/api/accounts` | List accounts |
| `GET` | `/api/accounts/{id}` | Get account details |
| `PATCH` | `/api/accounts/{id}` | Update account |
| `DELETE` | `/api/accounts/{id}` | Delete account |

### Tasks

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/tasks` | Create task |
| `GET` | `/api/tasks` | List tasks |
| `GET` | `/api/tasks/{id}` | Get task status |
| `POST` | `/api/tasks/{id}/cancel` | Cancel task |

### Queue

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `POST` | `/api/queue/start` | Start queue |
| `POST` | `/api/queue/stop` | Stop queue |
| `GET` | `/api/queue/status` | Queue status |

### Admin

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/admin/health` | Health check |
| `GET` | `/api/admin/stats` | Statistics |

---

## Important Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI entry, CORS, lifespan |
| `app/config.py` | Pydantic Settings from `.env` |
| `app/database.py` | SQLAlchemy engine, `get_db` |
| `app/models/__init__.py` | All models + enums + `ACTION_TYPES` |
| `app/modules/queue/processor.py` | QueueProcessor (background loop) |
| `app/modules/queue/__init__.py` | QueueManager singleton |
| `app/modules/executor/actions/base.py` | BaseAction |
| `app/modules/executor/actions/actions.py` | 9 action classes + `ACTIONS` dict |
| `app/modules/executor/browser.py` | CamofoxClient |
| `app/modules/accounts/login.py` | LoginService |
| `app/modules/executor/rate_limiter.py` | RateLimiter |
| `app/logging/__init__.py` | Logging utilities exports |
| `app/logging/redact.py` | Sensitive data redaction |
| `app/logging/timing.py` | Performance tracking |
| `app/logging/audit.py` | Audit trail logging |

---

## Logging

Logs are written to `data/logs/app_YYYYMMDD_HHMMSS.log`

### Loggers

| Logger | Module |
|--------|--------|
| `accounts` | API accounts endpoints |
| `tasks` | API task endpoints |
| `queue_api` | API queue endpoints |
| `proxies` | API proxy endpoints |
| `admin` | API admin endpoints |
| `queue` | QueueProcessor |
| `queue_manager` | QueueManager |
| `login` | LoginService |
| `browser` | CamofoxClient |
| `rate_limiter` | RateLimiter |
| `base_action` | BaseAction |
| `actions` | Action implementations |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Console log level (set `DEBUG` for verbose) |

### Sensitive Data Redaction

Passwords and proxy credentials are automatically redacted:

```python
from app.logging.redact import redact_password, redact_proxy

redact_password("secret123")  # "****23"
redact_proxy("http://user:pass@host:8080")  # "host:8080"
```

---

## How Actions Execute

### Vote Actions

```
1. Create Camofox tab with session
2. Navigate to target URL
3. Sleep 5-7s (page load jitter)
4. Get snapshot
5. Find upvote/downvote button ref
6. Click button (60s timeout)
7. Sleep 2-3s
8. Get post-click snapshot
9. Detect popup (suspended/rate limited)
10. Close tab
```

### Non-Vote Actions

```
1. Create Camofox tab with session
2. Navigate to target URL
3. Sleep 5-7s
4. Get snapshot
5. Check header banner FIRST (suspended/banned)
6. If banner found → fail early with "header_{banner}"
7. Find target button ref
8. Click button
9. Sleep 2-3s
10. Verify success
11. Close tab
```

---

## Camofox Integration

**Camofox** is a headless Firefox with C++ anti-detection:
- Spoofs navigator.hardwareConcurrency, WebGL, AudioContext
- Screen geometry, WebRTC all spoofed
- Runs on port 9377 (configurable)

**Session:** `s_{account_id}` (e.g., `s_42`)
**Tab:** `wq_{account_id}_{action_type}`

**Proxy injection:** Via sticky-proxy plugin at `POST /users/{userId}/proxy`.

---

## Outcome Codes

| Outcome | Meaning | Action |
|---------|---------|--------|
| `success` | Action completed | - |
| `popup_suspended` | Account locked via popup | Mark dead, replace |
| `popup_rate_limited` | Rate limited via popup | Mark rate_limited, replace |
| `header_banned` | Banned via header banner | Mark dead, replace |
| `header_suspended` | Suspended via header banner | Mark dead, replace |
| `click_timeout` | Button click timed out | Retry 3x |
| `element_not_found` | Target element not found | Retry 3x |

---

## Browser Detection: Popup vs Banner

| Detection | When | Actions |
|-----------|------|---------|
| **Popup** | AFTER vote click | upvote/downvote post/comment |
| **Banner** | BEFORE non-vote click | follow/unfollow/join/leave/save |

---

## Adding a New Action

1. **Create class** in `app/modules/executor/actions/actions.py`:
```python
class MyAction(BaseAction):
    action_type = "my_action"
    target_pattern = r'button\s+"MyButton"\s+\[e(\d+)\]'
    use_old_reddit = True

    def verify_success(self, snapshot):
        banner = self.detect_header_banner(snapshot)
        if banner:
            return False, f"header_{banner}"
        if 'button "Done"' in snapshot:
            return True, None
        return False, "Did not complete"
```

2. **Register** in `ACTIONS` dict in `actions.py`

3. **Add** to `ACTION_TYPES` list in `app/models/__init__.py`

---

## Camofox Snapshot Format

Element refs are `e{NUMBER}` — match with regex:
```python
r'button\s+"upvote"\s+\[e(\d+)\]'
r'link\s+"join"\s+\[e(\d+)\]'
```

`BaseAction.find_ref_by_pattern(snapshot, pattern)` finds matches.

---

## Running

Commands via [`just`](https://just.systems/):

| Command | Description |
|---------|-------------|
| `just install` | Setup venv + install deps |
| `just run` | Start production server |
| `just dev` | Start with auto-reload |
| `just debug` | Start with DEBUG logging |
| `just test` | Run tests |
| `just lint` | Lint code |
| `just fmt` | Format code |
| `just logs` | Tail logs |
| `just logs-clear` | Clear logs |
| `just clean` | Clean cache |
| `just cleanup` | Full cleanup (removes venv + data) |

Dashboard: `http://localhost:8000`
API docs: `http://localhost:8000/docs`

---

## Testing

```bash
cd ReOrchestra && uv run pytest tests/ -v
```

**93 tests** across 4 test files:

| File | Tests | Coverage |
|------|-------|----------|
| `test_accounts.py` | 25 | Import, CRUD, status transitions |
| `test_tasks.py` | 25 | Creation, retrieval, cancellation |
| `test_queue.py` | 33 | Processing, deduplication, rate limiting |
| `test_dedup.py` | 10 | Deduplication logic |

### Test Approach

- **Mocked Camofox** — no real browser, no actual Reddit API calls
- **In-memory SQLite** — fresh database per test
- **Real RateLimiter** — tested with config overrides, not mocked
- **Fast** — full suite runs in ~3 seconds

### Running Specific Tests

```bash
uv run pytest tests/test_accounts.py -v              # All account tests
uv run pytest tests/test_queue.py::TestRateLimiterIntegration -v  # Rate limit tests
uv run pytest tests/ -k "test_import" -v            # Filter by name
```

---

## Code Conventions

- Python 3.10+, type hints everywhere
- Pydantic v2 for schemas
- SQLAlchemy 2.x declarative base
- Logging: `logger = logging.getLogger("name")`
- Format: `%(asctime)s | %(levelname)-8s | %(name)s | %(message)s`
- Import order: stdlib → third-party → local

---

## Gotchas

- **Click timeout**: Camofox click can take 30-60s on suspended accounts
- **Popup vs Banner**: Popup appears AFTER vote. Banner appears BEFORE non-vote.
- **Session persistence**: Handled by Camofox persistence plugin
- **Proxy per session**: Via sticky-proxy plugin
- **Database**: SQLite at `data/reddit.db`
- **CORS**: Set `CORS_ALLOWED_ORIGINS` in `.env`
- **Logs**: Written to `data/logs/` with rotation
- **Sensitive data**: Passwords/proxies automatically redacted in logs
