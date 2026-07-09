# ReOrchestra — Architecture Document

## Overview

ReOrchestra is a bulk Reddit account automation tool. It manages 500-1000 Reddit accounts on a single VPS, executing actions (upvote, follow, join, etc.) via a queue-based system.

**Version:** 1.0
**Stack:** Python 3, FastAPI, SQLite, Camofox

---

## Architecture

```
Client Request → FastAPI → Task Queue → QueueProcessor → Account Executor → Camofox → Reddit
```

**Simple flow:**
1. Task created via API: `{action_type, target_url, workers_needed}`
2. QueueProcessor picks up task
3. Assigns idle accounts to the task
4. Executes actions concurrently (max 3)
5. On failure: marks account dead/banned and replaces it
6. On success: marks task complete

---

## Module Structure

```
app/
├── main.py                 # FastAPI entry, CORS, lifespan
├── config.py               # Pydantic settings from .env
├── database.py             # SQLAlchemy engine
├── logging_config.py       # Logging setup
│
├── api/                    # FastAPI routers
│   ├── router.py           # Central router
│   ├── accounts.py         # /api/accounts/*
│   ├── queue_tasks.py     # /api/tasks/*
│   ├── queue_queue.py     # /api/queue/*
│   ├── proxies.py          # /api/proxies/*
│   ├── admin.py           # /api/admin/*
│   └── frontend.py        # Dashboard pages (/)
│
├── models/                 # SQLAlchemy models
│   └── __init__.py         # Account, Proxy, Task, TaskExecutionLog
│
├── schemas/                # Pydantic schemas
│   ├── account.py
│   ├── common.py
│   └── proxy.py
│
├── templates/               # Jinja2 templates (HTMX + Flowbite)
│   ├── base.html
│   ├── pages/             # dashboard, accounts, tasks, proxies
│   └── components/         # stat_card, status_badge, progress_bar
│
├── static/                  # CSS, JS
│   └── css/
│       └── custom.css
│
└── modules/                # Business logic modules
    ├── accounts/           # Account management
    │   └── login.py       # LoginService
    │
    ├── queue/             # Queue processing
    │   ├── __init__.py    # QueueManager
    │   └── processor.py    # QueueProcessor (background loop)
    │
    ├── executor/           # Browser automation
    │   ├── browser.py      # CamofoxClient
    │   ├── rate_limiter.py # RateLimiter
    │   └── actions/        # Action executors
    │       ├── base.py     # BaseAction
    │       └── actions.py  # 9 action classes
    │
    └── shared/             # Shared utilities
        ├── config.py       # ConfigService
        └── exceptions.py   # Custom exceptions
```

---

## Modules

### accounts
- **login.py** — LoginService for Camofox-based login

### queue
- **processor.py** — QueueProcessor background loop
- **__init__.py** — QueueManager singleton

### executor
- **browser.py** — CamofoxClient wrapping all Camofox HTTP calls
- **rate_limiter.py** — Per-account vote rate limiting
- **actions/** — BaseAction + 9 action implementations

---

## Data Models

### Account
Reddit credentials + status tracking:
```
status: fresh | logged_in | session_expired | rate_limited | banned | dead
```

### Task
Queue job:
```
action_type: upvote_post, follow_user, etc.
target_url: https://...
workers_needed: 100
status: queued → running → completed | partial | failed | cancelled
```

### TaskExecutionLog
Per-account execution result:
```
account_id, task_id, action_type, target_url
success: bool
outcome: success | popup_suspended | header_banned | click_timeout | etc.
dedup_hash: SHA256 of account_id:action_type:target_url
```

### Proxy
Proxy configuration per account.

---

## Queue Behavior

1. **Task creation** → saved to DB with status `queued`
2. **Pick task** → QueueProcessor fetches oldest queued task
3. **Assign accounts** → find idle accounts that haven't done this action
4. **Execute concurrently** → max 3 at a time
5. **Handle errors:**
   - Ban/suspend → mark account dead, replace with new account
   - Retryable error → retry N times (default 3)
6. **Complete** → when workers_needed satisfied or no accounts left

### Deduplication
SHA256 of `{account_id}:{action_type}:{target_url}`. Prevents same account doing same action twice.

### Error Outcomes

| Outcome | Action |
|---------|--------|
| `popup_suspended` | Mark account `dead`, replace |
| `popup_rate_limited` | Mark account `rate_limited`, replace |
| `header_banned` | Mark account `dead`, replace |
| `header_suspended` | Mark account `dead`, replace |
| `click_timeout` | Retry 3x |
| `element_not_found` | Retry 3x |

---

## API Endpoints

### Accounts
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/accounts/import` | Import accounts |
| POST | `/api/accounts/login` | Login accounts via Camofox |
| POST | `/api/accounts/logout` | Logout accounts |
| GET | `/api/accounts` | List accounts |
| GET | `/api/accounts/{id}` | Get account details |
| PATCH | `/api/accounts/{id}` | Update account |
| DELETE | `/api/accounts/{id}` | Delete account |
| POST | `/api/accounts/batch-delete` | Bulk delete |
| POST | `/api/accounts/batch-login` | Bulk login |

### Tasks
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/tasks` | Create task |
| GET | `/api/tasks` | List tasks |
| GET | `/api/tasks/{id}` | Get task status + logs |
| POST | `/api/tasks/{id}/cancel` | Cancel task |
| POST | `/api/tasks/{id}/retry` | Retry task |
| POST | `/api/tasks/{id}/priority` | Boost priority |

### Queue
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/queue/start` | Start queue processor |
| POST | `/api/queue/stop` | Stop queue processor |
| GET | `/api/queue/status` | Queue status |
| GET | `/api/queue` | View queued/running tasks |

### Proxies
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/proxies` | List proxies |
| POST | `/api/proxies/import` | Import proxies |
| DELETE | `/api/proxies/{id}` | Delete proxy |
| POST | `/api/proxies/replace` | Replace dead proxies |
| POST | `/api/proxies/mark-dead` | Mark proxy dead |

### Admin
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/admin/health` | Health check |
| GET | `/api/admin/stats` | Statistics |

### Dashboard (HTML Pages)
| Route | Purpose |
|-------|---------|
| `/` | Redirect to `/dashboard` |
| `/dashboard` | Stats overview, queue control |
| `/accounts` | Account management |
| `/tasks` | Task list + creation |
| `/tasks/{id}` | Task detail + logs |
| `/proxies` | Proxy management |
| `/system` | System health + logs |

### Dashboard HTMX Partials
| Route | Purpose |
|-------|---------|
| `/htmx/queue-status` | Queue status pill |
| `/htmx/stats` | Stats cards |

---

## Camofox Integration

**Camofox** is a headless Firefox with C++ anti-detection patches.

- Runs on port 9377 (configurable)
- Session format: `s_{account_id}`
- Tab format: `wq_{account_id}_{action_type}`

**Proxy injection:** Via sticky-proxy plugin, assigned via `POST /users/{userId}/proxy`.

---

## Detection Avoidance

### Rate Limits (per account)
- Max 15 votes/day
- Max 100 votes/week
- 120s minimum between votes

### Timing
- Gaussian jitter (sigma: 120s)
- 8% skip chance
- 15% clump chance

### Popup vs Banner
- **Popup** — AFTER vote click (suspended, rate limited)
- **Banner** — BEFORE non-vote click (banned, suspended)
