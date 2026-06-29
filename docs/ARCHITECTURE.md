# Reddit Automation API - Architecture Document (V0.8)

## Overview

A scalable Reddit account management and automation system built with FastAPI, Camofox browser automation, and SQLite. The system manages Reddit accounts with a focus on detection avoidance and supports both direct action execution and a queue-based worker system for scalable task processing.

**Version:** 0.8  
**Tech Stack:** Python 3, FastAPI, SQLAlchemy, SQLite, Camofox (browser automation)

---

## 1. System Architecture

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FastAPI Application                                │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                         API Layer (app/api/)                             │ │
│  │                                                                          │ │
│  │  /api/accounts/*    - Account CRUD & login                              │ │
│  │  /api/actions/*    - Direct upvote/downvote                             │ │
│  │  /api/proxies/*    - Proxy management                                   │ │
│  │  /api/admin/*      - Health, stats, configuration                       │ │
│  │  /api/workers/*    - Worker pool management                             │ │
│  │  /api/tasks/*      - Queue task management                              │ │
│  │  /api/queue/*      - Queue processor control                            │ │
│  │                                                                          │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                          │
│                                    ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │                      Service Layer (app/services/)                       │ │
│  │                                                                          │ │
│  │  Core Services:                  Queue System:                            │ │
│  │  - AccountService               - QueueManager (singleton)               │ │
│  │  - LoginService                  - QueueProcessor (background thread)     │ │
│  │  - ActionService                 - WorkerPool                            │ │
│  │  - BrowserService (Camofox)                                             │ │
│  │                                                                            │ │
│  │  Support Services:                                                        │ │
│  │  - ProxyService                     - ConfigService                       │ │
│  │  - RateLimiter                      - TimingService                      │ │
│  │  - BurnDetector                     - SlotManager                        │ │
│  │  - StickyProxyClient                                                   │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         External Dependencies                                │
│                                                                              │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│   │   SQLite    │     │   Camofox   │     │   Reddit    │                   │
│   │  Database   │     │  Browser    │     │     API     │                   │
│   │  (data/)    │     │  Server    │     │  (www.reddit│                   │
│   └─────────────┘     │  (9377)    │     │   .com)     │                   │
│                       └─────────────┘     └─────────────┘                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Diagram

```
                                ┌──────────────┐
                                │   Client    │
                                └──────┬───────┘
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                             FastAPI Server                                 │
│                                                                            │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                    │
│  │  accounts.py │   │  actions.py  │   │   admin.py   │                    │
│  │  proxies.py  │   │ queue_tasks  │   │queue_workers │                    │
│  │  router.py  │   │ queue_queue  │   │              │                    │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘                    │
│         │                  │                  │                            │
│         └──────────────────┼──────────────────┘                            │
│                            │                                               │
│                            ▼                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                        Service Layer                                   │ │
│  │                                                                       │ │
│  │   ┌──────────────────┐    ┌──────────────────┐    ┌────────────────┐  │ │
│  │   │  LoginService    │    │  ActionService   │    │ AccountService │  │ │
│  │   │  (Camofox login) │    │  (Browser vote)  │    │   (CRUD)       │  │ │
│  │   └────────┬─────────┘    └────────┬─────────┘    └───────┬────────┘  │ │
│  │            │                       │                      │            │ │
│  │            └───────────┬──────────┘                      │            │ │
│  │                        ▼                                 │            │ │
│  │            ┌──────────────────────┐                       │            │ │
│  │            │  CamofoxClient       │                       │            │ │
│  │            │  (Browser REST API) │                       │            │ │
│  │            └──────────┬───────────┘                       │            │ │
│  │                       │                                  │            │ │
│  └───────────────────────┼──────────────────────────────────┴────────────┘ │
│                          │                                                     │
└──────────────────────────┼─────────────────────────────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   Camofox Browser      │
              │   (localhost:9377)     │
              │                        │
              │   Manages:             │
              │   - Tabs per user      │
              │   - Proxy injection    │
              │   - Session cookies    │
              └────────────────────────┘


┌────────────────────────────────────────────────────────────────────────────┐
│                      Queue System (Background Thread)                       │
│                                                                            │
│  ┌──────────────────┐    ┌──────────────────┐    ┌────────────────────┐  │
│  │  QueueManager     │───▶│ QueueProcessor   │───▶│   WorkerPool       │  │
│  │  (Singleton)      │    │  (Background)    │    │  (DB-backed)       │  │
│  └──────────────────┘    └────────┬─────────┘    └─────────┬──────────┘  │
│                                   │                      │               │
│                                   ▼                      ▼               │
│                        ┌──────────────────┐    ┌────────────────────┐    │
│                        │   Task/Worker    │    │  TaskActionLog    │    │
│                        │   Models        │    │                   │    │
│                        └──────────────────┘    └────────────────────┘    │
│                                                                            │
│  Queue Actions (app/services/queue_actions/):                              │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │  BaseAction ──── UpvotePost ──── DownvotePost ──── UpvoteComment   │  │
│  │       │              │                │                │            │  │
│  │       │              └────────────────┴────────────────┘            │  │
│  │       │                                                              │  │
│  │  FollowUser    UnfollowUser    JoinSubreddit    LeaveSubreddit      │  │
│  │       │                                                              │  │
│  │  SavePost ──────────────────────────────────────────────────────────│  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1 API Layer (app/api/)

The API layer is organized by resource type:

| File | Prefix | Description |
|------|--------|-------------|
| `accounts.py` | `/api/accounts` | Account CRUD, import, login |
| `actions.py` | `/api/actions` | Direct upvote/downvote actions |
| `proxies.py` | `/api/proxies` | Proxy import, management |
| `admin.py` | `/api/admin` | Health check, statistics |
| `queue_workers.py` | `/api/workers` | Worker pool management |
| `queue_tasks.py` | `/api/tasks` | Task creation, cancellation |
| `queue_queue.py` | `/api/queue` | Queue processor start/stop |
| `router.py` | - | Central router combining all routes |

### 2.2 Service Layer (app/services/)

#### Core Services

| Service | File | Responsibilities |
|---------|------|-----------------|
| **CamofoxClient** | `browser.py` | REST client for Camofox browser server |
| **LoginService** | `login.py` | Browser-based Reddit login |
| **ActionService** | `actions.py` | Browser-based upvote/downvote |
| **AccountService** | `account_service.py` | Account session management, login orchestration |

#### Queue System Services

| Service | File | Responsibilities |
|---------|------|-----------------|
| **QueueManager** | `queue_manager.py` | Singleton managing QueueProcessor lifecycle |
| **QueueProcessor** | `queue_processor.py` | Background thread processing tasks FIFO |
| **WorkerPool** | `worker_pool.py` | Manages workers (Reddit account proxies for queue) |
| **Queue Actions** | `queue_actions/base.py`, `queue_actions/actions.py` | Individual action executors |

#### Support Services

| Service | File | Responsibilities |
|---------|------|-----------------|
| **ProxyService** | `proxy_service.py` | Proxy import, Evomi session generation, assignment |
| **StickyProxyClient** | `sticky_proxy.py` | Proxy injection into Camofox sessions |
| **RateLimiter** | `rate_limiter.py` | Per-account vote limiting |
| **BurnDetector** | `burn_detector.py` | Ban/rate-limit detection, account health |
| **TimingService** | `timing_service.py` | S-curve timing, jitter calculation |
| **SlotManager** | `slot_manager.py` | Camofox slot health monitoring |
| **ConfigService** | `config_service.py` | YAML config loading, runtime overrides |

### 2.3 Browser Automation (Camofox)

The system uses **Camofox** as its browser automation layer instead of raw HTTP requests. This provides:
- Session cookie persistence
- Proxy injection per user
- JavaScript rendering for Reddit
- Accessibility snapshot for element finding

**CamofoxClient** (`browser.py`) provides:
- `create_tab()` - Open new browser tab
- `navigate()` - Navigate to URL
- `snapshot()` - Get accessibility tree
- `click()` / `type_text()` - Interact with elements
- `scroll()` - Scroll page
- `close_tab()` - Close tab

### 2.4 Queue System Architecture

The queue system enables scalable, distributed task processing:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Queue System Flow                            │
│                                                                  │
│  1. Task Created (via API /api/tasks)                           │
│           │                                                     │
│           ▼                                                     │
│  2. Task stored in DB (status=queued)                           │
│           │                                                     │
│           ▼                                                     │
│  3. QueueProcessor background thread picks task                  │
│           │                                                     │
│           ▼                                                     │
│  4. Assigns idle workers (up to workers_needed)                  │
│           │                                                     │
│           ▼                                                     │
│  5. Each worker executes action via Camofox                      │
│           │                                                     │
│           ▼                                                     │
│  6. Results logged to TaskActionLog                             │
│           │                                                     │
│           ▼                                                     │
│  7. Task marked: completed/partial/failed                        │
└─────────────────────────────────────────────────────────────────┘
```

**Supported Action Types:**
- `upvote_post` - Upvote a Reddit post
- `downvote_post` - Downvote a Reddit post
- `upvote_comment` - Upvote a Reddit comment
- `downvote_comment` - Downvote a Reddit comment
- `follow_user` - Follow a Reddit user
- `unfollow_user` - Unfollow a Reddit user
- `join_subreddit` - Join a subreddit
- `leave_subreddit` - Leave a subreddit
- `save_post` - Save a post

---

## 3. Data Models

### 3.1 Database Schema Overview

```
┌──────────────────┐     ┌──────────────────┐
│     Account      │     │      Post        │
├──────────────────┤     ├──────────────────┤
│ id (PK)          │     │ id (PK)          │
│ username         │     │ account_id (FK)  │
│ password         │     │ post_type        │
│ status           │     │ target_type      │
│ account_type     │     │ target           │
│ proxy            │     │ title            │
│ profile_id       │     │ status           │
│ ...              │     │ post_url         │
└────────┬─────────┘     │ ...              │
         │               └──────────────────┘
         │                        │
         │                        │
         ▼                        ▼
┌──────────────────────────────────────────────┐
│                   ActionLog                    │
├──────────────────────────────────────────────┤
│ id (PK)                                      │
│ account_id (FK) ──────────────────────────────┼──┐
│ action_type                                  │  │
│ target_id / target_url                       │  │
│ success / error / http_status                │  │
│ dedup_hash (unique)                          │  │
└──────────────────────────────────────────────┘  │
                                                     │
┌──────────────────────────────────────────────┐  │
│                  Proxy                         │  │
├──────────────────────────────────────────────┤  │
│ id (PK)                                      │  │
│ proxy_string                                 │  │
│ assigned_account_id (FK) ───────────────────┘  │
│ status / is_active / fail_count              │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│               CamofoxSlot                     │
├──────────────────────────────────────────────┤
│ id (PK)                                      │
│ port (unique)                                │
│ status                                       │
│ max_concurrent / current_load               │
│ process_id / memory_mb / cpu_percent         │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│                  Worker                        │
├──────────────────────────────────────────────┤
│ id (PK)                                      │
│ account_id (FK)                              │
│ username                                     │
│ status (idle/working/paused)                 │
│ current_task_id (FK)                        │
│ total_actions / failed_actions               │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│                    Task                        │
├──────────────────────────────────────────────┤
│ id (PK)                                      │
│ action_type                                  │
│ target_url                                   │
│ workers_needed                               │
│ workers_assigned (JSON)                      │
│ failed_workers (JSON)                        │
│ workers_completed                            │
│ status (queued/running/completed/partial/    │
│        failed/cancelled)                     │
│ priority                                     │
└──────────────────────────────────────────────┘

┌──────────────────────────────────────────────┐
│                TaskActionLog                  │
├──────────────────────────────────────────────┤
│ id (PK)                                      │
│ task_id (FK)                                 │
│ worker_id (FK)                               │
│ action_type                                  │
│ target_url                                   │
│ success / outcome / error                    │
│ attempts / duration_ms                       │
│ dedup_hash                                   │
└──────────────────────────────────────────────┘
```

### 3.2 Model Relationships

| Model | Relationships |
|-------|---------------|
| Account | has_many: Posts, ActionLogs, Workers |
| Post | belongs_to: Account |
| Proxy | assigned_to: Account (optional) |
| ActionLog | belongs_to: Account |
| Worker | belongs_to: Account, current_task (optional) |
| Task | has_many: TaskActionLogs |
| TaskActionLog | belongs_to: Task, Worker |

### 3.3 Enumerations

**AccountStatus:** `fresh`, `logged_in`, `session_expired`, `banned`, `dead`

**AccountType:** `upvoter`, `main`, `both`

**PostStatus:** `draft`, `posted`, `failed`, `deleted`

**WorkerStatus:** `idle`, `working`, `paused`

**TaskStatus:** `queued`, `running`, `completed`, `partial`, `failed`, `cancelled`

**ActionOutcome:** `success`, `failed`, `duplicate`, `popup_suspended`, `popup_rate_limited`

---

## 4. Request/Response Flow

### 4.1 Direct Action Flow (Upvote/Downvote)

```
Client                    API                      Service                   Camofox
  │                        │                          │                          │
  │ POST /api/actions/     │                          │                          │
  │ {account_ids, url}     │                          │                          │
  │───────────────────────▶│                          │                          │
  │                        │                          │                          │
  │                        │ For each account:        │                          │
  │                        │─────────────────────────▶│                          │
  │                        │                          │                          │
  │                        │                          │ create_tab(userId)       │
  │                        │                          │─────────────────────────▶│
  │                        │                          │                          │
  │                        │                          │ navigate(url)             │
  │                        │                          │─────────────────────────▶│
  │                        │                          │                          │
  │                        │                          │ snapshot()               │
  │                        │                          │◀─────────────────────────│
  │                        │                          │                          │
  │                        │                          │ find & click upvote      │
  │                        │                          │─────────────────────────▶│
  │                        │                          │                          │
  │                        │                          │ close_tab()              │
  │                        │                          │─────────────────────────▶│
  │                        │                          │                          │
  │                        │◀─────────────────────────│ ActionResult              │
  │◀──────────────────────│ {success, message}       │                          │
  │ 200 OK                │                          │                          │
```

### 4.2 Queue Task Flow

```
Client              API              QueueProcessor         WorkerPool           Camofox
   │                │                     │                    │                  │
   │ POST /api/tasks │                     │                    │                  │
   │ {action, url,   │                     │                    │                  │
   │  workers_needed}│                     │                    │                  │
   │────────────────▶│                     │                    │                  │
   │ 201 Created    │                     │                    │                  │
   │◀────────────────│                     │                    │                  │
   │                │                     │                    │                  │
   │                │ (background)        │                    │                  │
   │                │────────────────────▶│                    │                  │
   │                │                     │                    │                  │
   │                │                     │ next_task()        │                  │
   │                │                     │◀───────────────────│                  │
   │                │                     │                    │                  │
   │                │                     │ assign_workers()   │                  │
   │                │                     │───────────────────▶│                  │
   │                │                     │                    │                  │
   │                │                     │                    │ idle workers     │
   │                │                     │                    │◀─────────────────│
   │                │                     │                    │                  │
   │                │                     │ For each worker:   │                  │
   │                │                     │───────────────────▶│                  │
   │                │                     │                    │                  │
   │                │                     │                    │ execute_action()│
   │                │                     │                    │────────┐        │
   │                │                     │                    │        │        │
   │                │                     │                    │◀───────┴───────│
   │                │                     │                    │ ActionResult   │
   │                │                     │◀───────────────────│                  │
   │                │                     │                    │                  │
   │                │                     │ update task status │                  │
   │                │                     │◀───────────────────│                  │
   │                │                     │                    │                  │
```

### 4.3 Login Flow

```
Client              API              LoginService            Camofox
   │                │                     │                    │
   │ POST /api/accounts/login             │                    │
   │ {account_ids}  │                     │                    │
   │────────────────▶│                     │                    │
   │                │                     │                    │
   │                │ for each account:   │                    │
   │                │────────────────────▶│                    │
   │                │                     │                    │
   │                │                     │ create_tab()       │
   │                │                     │───────────────────▶│
   │                │                     │                    │
   │                │                     │ navigate(login)    │
   │                │                     │───────────────────▶│
   │                │                     │                    │
   │                │                     │ snapshot()         │
   │                │                     │◀───────────────────│
   │                │                     │                    │
   │                │                     │ type credentials   │
   │                │                     │ click login         │
   │                │                     │───────────────────▶│
   │                │                     │                    │
   │                │                     │ save session       │
   │                │                     │◀───────────────────│
   │                │                     │                    │
   │◀────────────────│ {results}           │                    │
   │ 200 OK         │                     │                    │
```

---

## 5. Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Framework | FastAPI | REST API server |
| Database | SQLite + SQLAlchemy | Data persistence |
| Browser Automation | Camofox | Headless browser control |
| Background Processing | Python threading | Queue processor loop |
| Configuration | YAML + Pydantic | Settings management |
| API Documentation | OpenAPI/Swagger | Auto-generated docs at `/docs` |

### 5.1 Environment Variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/reddit.db` | Database connection |
| `SESSION_DIR` | `data/sessions` | Cookie storage |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `CAMOFOX_PORT` | `9377` | Camofox server port |
| `PROXY_MODE` | `sticky` | Proxy assignment mode |
| `VNC_ENABLED` | `false` | VNC server for debugging |

---

## 6. File Structure

```
reddit-api/
├── config/
│   ├── default.yaml              # Default configuration
│   ├── custom.yaml               # User overrides (gitignored)
│   └── proxies.yaml              # Proxy configuration
│
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI entry point
│   ├── config.py                 # Pydantic settings
│   ├── database.py               # SQLAlchemy exports
│   ├── gui.py                    # Dashboard HTML
│   │
│   ├── models/
│   │   └── __init__.py          # All SQLAlchemy models
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── account.py           # Account schemas
│   │   ├── action.py            # Action schemas
│   │   └── common.py            # Common response schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── browser.py           # CamofoxClient
│   │   ├── login.py             # LoginService
│   │   ├── actions.py           # ActionService
│   │   ├── account_service.py   # AccountService
│   │   ├── proxy_service.py     # ProxyService
│   │   ├── sticky_proxy.py      # StickyProxyClient
│   │   ├── rate_limiter.py      # RateLimiter
│   │   ├── burn_detector.py     # BurnDetector
│   │   ├── timing_service.py    # TimingService
│   │   ├── slot_manager.py      # SlotManager
│   │   ├── config_service.py    # ConfigService
│   │   │
│   │   ├── queue_manager.py     # QueueManager singleton
│   │   ├── queue_processor.py   # QueueProcessor (background)
│   │   ├── worker_pool.py       # WorkerPool
│   │   │
│   │   └── queue_actions/
│   │       ├── __init__.py
│   │       ├── base.py          # BaseAction class
│   │       └── actions.py        # Action implementations
│   │
│   └── api/
│       ├── __init__.py
│       ├── router.py            # Central router
│       ├── accounts.py          # /api/accounts/*
│       ├── actions.py           # /api/actions/*
│       ├── proxies.py           # /api/proxies/*
│       ├── admin.py             # /api/admin/*
│       ├── queue_workers.py     # /api/workers/*
│       ├── queue_tasks.py       # /api/tasks/*
│       └── queue_queue.py       # /api/queue/*
│
├── data/
│   ├── reddit.db                # SQLite database
│   ├── sessions/                # Session cookies
│   └── logs/                    # Application logs
│
├── requirements.txt
├── setup_camofox.sh             # Camofox setup script
└── README.md
```

---

## 7. Detection Avoidance

### 7.1 Rate Limits (Per Account)

| Metric | Default | Description |
|--------|---------|-------------|
| Max votes/day | 15 | Maximum upvotes in 24 hours |
| Max votes/week | 100 | Maximum upvotes in 7 days |
| Min between votes | 120s | Cooldown between votes |
| Max vote-only ratio | 30% | Votes vs total actions |

### 7.2 Timing Entropy

| Technique | Config Key | Purpose |
|-----------|-------------|---------|
| Gaussian jitter | `timing.jitter_sigma` (120s) | Avoid uniform intervals |
| S-curve distribution | `s_curve.*` | Research-backed upvote timing |
| 8% skip chance | `timing.skip_cycle_chance` | Random non-deterministic behavior |
| 15% clump chance | `timing.clump_chance` | Simulate organic cluster discovery |
| Micro-jitter | `timing.micro_jitter_*` (100-900ms) | Network-level noise |

### 7.3 Account Protection

| Technique | Description |
|-----------|-------------|
| Active hours | Accounts vote only within configured hours (default 7-23) |
| Consecutive failure tracking | Marks account dead after 5 consecutive failures |
| Success rate monitoring | Marks account dead if 7-day success rate < 80% |
| Session age limits | Sessions expire after 72 hours |
