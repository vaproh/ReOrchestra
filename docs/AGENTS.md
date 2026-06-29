# AGENTS.md — ReOrchestra

## Project Overview

**ReOrchestra** is a Reddit account automation SaaS platform. It manages pools of Reddit accounts and executes actions (upvote, downvote, follow, join, etc.) via a browser automation layer (Camofox). Built with FastAPI, SQLAlchemy, SQLite, and a custom worker queue system.

---

## Key Concepts & Terminology

| Term | Definition |
|------|------------|
| **Account** | A Reddit account with username, password, cookies, proxy, and status tracking |
| **Worker** | A queue worker bound to one account; executes actions on behalf of that account |
| **Task** | A queued automation job (e.g., "upvote post X" across N accounts) |
| **TaskActionLog** | Per-worker execution log for a task (success, outcome, error, duration, attempts) |
| **Camofox** | Headless stealth browser; handles session persistence, fingerprint spoofing, proxy injection |
| **ActionType** | Supported Reddit actions: upvote_post, downvote_post, upvote_comment, downvote_comment, follow_user, unfollow_user, join_subreddit, leave_subreddit, save_post |
| **Slot** | A Camofox browser slot (port-based); manages concurrent browser contexts |
| **Deduplication** | Prevents duplicate actions via SHA256 hash of `{worker_id}:{action_type}:{target_url}` |

---

## How to Run Locally

```bash
# 1. Setup virtualenv
cd reddit-api
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Start Camofox (browser automation server — must be running separately)
cd ../camofox && npm start

# 3. Start the API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Access:
# - API docs: http://localhost:8000/docs
# - GUI:      http://localhost:8000/gui
```

**Required environment variables** (see `.env`):
- `DATABASE_URL` — SQLite connection string (default: `sqlite:///./data/reddit.db`)
- `CAMOFOX_PORT` — Camofox server port (default: `9377`)

---

## Important Files & Their Purposes

### Core Application
| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app setup, CORS, lifespan, global exception handler |
| `app/config.py` | Settings via pydantic-settings; reads from `.env` |
| `app/database.py` | SQLAlchemy engine, session factory, `get_db` dependency |

### API Endpoints (`app/api/`)
| File | Purpose |
|------|---------|
| `router.py` | Combines all sub-routers under `/api` |
| `accounts.py` | Account CRUD, login, session management |
| `actions.py` | Direct action endpoints (upvote/downvote with browser) |
| `queue_tasks.py` | Task creation, cancellation, priority boost |
| `queue_workers.py` | Worker status, suspension, dead marking |
| `queue_queue.py` | Queue inspection (list, pause, resume) |
| `proxies.py` | Proxy CRUD and assignment |
| `admin.py` | System-level operations |

### Services (`app/services/`)
| File | Purpose |
|------|---------|
| `queue_manager.py` | Singleton managing the background `QueueProcessor` |
| `queue_processor.py` | Background thread processing tasks FIFO (priority-boosted) |
| `worker_pool.py` | Worker lifecycle (assign, release, suspend, mark dead) |
| `queue_actions/base.py` | `BaseAction` class — all action executors inherit from here |
| `queue_actions/actions.py` | 9 action subclasses + `ACTIONS` registry dict + `get_action_class()` |
| `actions.py` | `ActionService` — direct browser-based action execution |
| `login.py` | Reddit login flow via Camofox |
| `browser.py` | `CamofoxClient` — wraps all Camofox HTTP API calls |
| `rate_limiter.py` | Per-account rate limiting |
| `timing_service.py` | Timing/delay utilities |

### Schemas (`app/schemas/`)
| File | Purpose |
|------|---------|
| `action.py` | `ActionRequest`, `DownvoteRequest`, `CommentRequest`, `FollowRequest`, `JoinSubredditRequest`, `ActionResult`, `BatchActionResponse` |
| `account.py` | Account-related Pydantic models |
| `common.py` | `SuccessResponse`, `ErrorResponse` |

### Models (`app/models/__init__.py`)
SQLAlchemy models: `Account`, `Post`, `Proxy`, `CamofoxSlot`, `ActionLog`, `Config`, `Worker`, `Task`, `TaskActionLog`

Enums: `AccountStatus`, `AccountType`, `PostStatus`, `WorkerStatus`, `TaskStatus`, `ActionOutcome`

---

## How to Add a New Action Type

### 1. Add the action class

Create/edit `app/services/queue_actions/actions.py`:

```python
class MyNewAction(BaseAction):
    action_type = "my_new_action"
    use_old_reddit = True  # or False for www.reddit.com
    target_pattern = r'button\s+"MyButton"\s+\[e(\d+)\]'

    def verify_success(self, snapshot: str) -> tuple[bool, Optional[str]]:
        banner = self.detect_header_banner(snapshot)
        if banner:
            return False, f"header_{banner}"
        # Check for success indicator in snapshot
        if 'button "Done"' in snapshot:
            return True, None
        return False, "Button did not change to Done"
```

### 2. Register it

In the same file, add to the `ACTIONS` dict and `get_action_class()`:

```python
ACTIONS = {
    # ... existing ...
    "my_new_action": MyNewAction,
}
```

### 3. Add to supported action types

In `app/models/__init__.py`, add to `ACTION_TYPES` list.

### 4. Add API endpoint (optional)

If you need a direct REST endpoint (not queued), add to `app/api/actions.py`:

```python
@router.post("/my_new_action", response_model=SuccessResponse)
async def my_new_action(request: MyNewActionRequest, db: Session = Depends(get_db)):
    ...
```

### Key patterns for finding elements

- `BaseAction.find_ref_by_pattern()` — regex scan of Camofox snapshot
- `BaseAction.find_ref_after_text()` — find element ref after a marker string
- Snapshot format: `'button "upvote" [e123]'` — match with `r'button\s+"upvote"\s+\[e(\d+)\]'`

---

## How the Queue System Works

```
API Request → Task Created (queued) → QueueProcessor._loop()
                                            ↓
                                    Fetch next_task() (FIFO + priority)
                                            ↓
                                    process_task() → assign_workers()
                                            ↓
                                    For each worker: execute_for_worker()
                                            ↓
                                    action.execute() → Camofox browser
                                            ↓
                                    Log result → release_worker()
                                            ↓
                                    Update Task status (completed/partial/failed)
```

**Key behaviors:**
- **FIFO + priority**: Tasks sorted by `priority DESC, created_at ASC`
- **Max concurrent per task**: 3 workers at a time (`max_concurrent_per_task`)
- **Retries**: Up to 3 attempts with exponential backoff (1, 2, 4s)
- **Deduplication**: SHA256 hash prevents duplicate action logs
- **Banner detection**: Non-vote actions check header banner BEFORE clicking; vote actions check AFTER
- **Worker state**: Workers marked `suspended` on popup, `dead` on banned, re-idled on success

---

## Common Tasks for an AI Agent

### Add an endpoint
1. Create/extend schema in `app/schemas/`
2. Add route function in appropriate `app/api/*.py`
3. Register router in `app/api/router.py`

### Fix a bug in action execution
1. Check `app/services/queue_actions/base.py` for the base execution flow
2. Check `app/services/queue_actions/actions.py` for the specific action subclass
3. Look at `app/services/browser.py` for Camofox API calls
4. Check `TaskActionLog` records for failure patterns

### Add a feature (e.g., new action type)
See "How to Add a New Action Type" above.

### Modify queue behavior
- `app/services/queue_processor.py` — task scheduling, retries, finalization
- `app/services/worker_pool.py` — worker assignment/release lifecycle
- `app/services/queue_manager.py` — singleton orchestrating the processor

### Database changes
- Models defined in `app/models/__init__.py` using SQLAlchemy
- Run `from app.models import init_db; init_db()` to create tables

---

## Testing Approach

**No formal test suite found.** To verify changes:
1. Start the API and Camofox servers locally
2. Use `/docs` interactive API to trigger actions
3. Check `TaskActionLog` and `ActionLog` tables for results
4. Monitor server logs for errors

If adding a test suite, place it in `tests/` and use `pytest`.

---

## Code Style & Conventions

- **Python 3.14** with type hints
- **Pydantic v2** for request/response schemas (import from `pydantic`)
- **SQLAlchemy 2.x** with declarative base pattern
- **FastAPI** with async endpoints where applicable
- **Pydantic Settings** for config (`.env` file)
- **Logging format**: `%(asctime)s | %(levelname)s | %(name)s | %(message)s`
- **Logger names**: Typically the module name (e.g., `logger = logging.getLogger("queue")`)
- **Enums**: Use `str, enum.Enum` for database-compatible enums
- **Dataclasses**: Use `@dataclass` for `ActionResult`
- **Snapshots**: Camofox returns element references as `e{NUMBER}` format
- **Deduplication**: SHA256 hash of `{worker_id}:{action_type}:{target_url[:16]}` stored in `dedup_hash` column

### Import order
1. Standard library
2. Third-party (fastapi, sqlalchemy, pydantic, etc.)
3. Local app imports

---

## Architecture Summary

```
reddit-api/
├── app/
│   ├── main.py           # FastAPI app entry
│   ├── config.py         # Settings
│   ├── database.py       # DB session
│   ├── api/              # REST endpoints
│   │   ├── router.py     # Combines all routes
│   │   ├── accounts.py   # Account management
│   │   ├── actions.py    # Direct action endpoints
│   │   ├── queue_*.py    # Queue system endpoints
│   │   └── proxies.py    # Proxy management
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic models
│   └── services/         # Business logic
│       ├── queue_manager.py       # Queue singleton
│       ├── queue_processor.py     # Background task processor
│       ├── worker_pool.py         # Worker lifecycle
│       ├── queue_actions/
│       │   ├── base.py            # BaseAction class
│       │   └── actions.py         # 9 action subclasses
│       └── browser.py              # CamofoxClient
├── docs/                 # Architecture docs
├── data/                 # SQLite DB, sessions (gitignored)
└── requirements.txt
```
