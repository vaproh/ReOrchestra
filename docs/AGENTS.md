# AGENTS.md — ReOrchestra

## Project

**ReOrchestra** is a white-label bulk Reddit account automation SaaS. Accounts execute actions (upvote, follow, join, etc.) via a queue system backed by Camofox stealth browser.

- FastAPI + SQLAlchemy + SQLite
- Camofox headless browser (session persistence, proxy injection, fingerprint spoofing)
- Background `QueueProcessor` thread handles FIFO task queue
- White-label: customers bring their own Reddit accounts + proxies

---

## Quick Start

```bash
# 1. Setup venv
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Camofox (separate process, sibling directory)
cd ../camofox && npm start

# 3. Run API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Required env vars (`.env`): `DATABASE_URL`, `CAMOFOX_PORT` (default `9377`).

---

## Key Concepts

| Term | Definition |
|------|------------|
| **Account** | Reddit credentials + proxy + status tracking |
| **Worker** | Queue actor bound to one Account |
| **Task** | Job: `{action_type, target_url, workers_needed}` |
| **TaskActionLog** | Per-worker execution result (success, outcome, error, attempts) |
| **Deduplication** | SHA256 of `{worker_id}:{action_type}:{target_url}` — prevents same worker succeeding same action twice |

**Supported actions** (9): `upvote_post`, `downvote_post`, `upvote_comment`, `downvote_comment`, `follow_user`, `unfollow_user`, `join_subreddit`, `leave_subreddit`, `save_post`

---

## Architecture

```
Request → API → Services → Camofox REST API → Browser → Reddit
                ↓
         QueueProcessor (background thread)
                ↓
         WorkerPool.assign_workers() → execute_for_worker()
                ↓
         BaseAction.execute() → click → detect_popup/banner
```

**Queue behavior:**
- FIFO + priority (`priority DESC, created_at ASC`)
- Max 3 concurrent workers per task
- 3 retries with exponential backoff (2s, 4s, 8s)
- Vote actions: click first, check popup AFTER
- Non-vote actions: check header banner BEFORE clicking

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
| `app/services/queue_actions/base.py` | `BaseAction` with `execute()`, `detect_popup()`, `detect_header_banner()` |
| `app/services/queue_actions/actions.py` | 9 action subclasses + `ACTIONS` dict + `get_action_class()` |
| `app/services/browser.py` | `CamofoxClient` — wraps all Camofox HTTP calls |
| `app/api/router.py` | Combines all route prefixes under `/api` |

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

3. **Vote actions** (upvote/downvote): override `action_blocked_by_banner()` to return `None` — they click first, detect popup after

---

## Camofox Snapshot Format

Element refs are `e{NUMBER}` — match with regex:
```python
r'button\s+"upvote"\s+\[e(\d+)\]'
r'link\s+"join"\s+\[e(\d+)\]'
```

`BaseAction.find_ref_by_pattern(snapshot, pattern)` finds the first match.

---

## Testing

```bash
# Run all tests
pytest

# Run specific test
pytest tests/test_database.py -v

# Manual verification
curl http://localhost:8000/api/admin/health
```

Test files: `tests/test_accounts.py`, `test_actions.py`, `test_config.py`, `test_database.py`, `test_login.py`

---

## Code Conventions

- Python 3.14, type hints everywhere
- Pydantic v2 for schemas (`from pydantic import BaseModel`)
- SQLAlchemy 2.x declarative base
- Logging: `logger = logging.getLogger("component_name")`, format: `%(asctime)s | %(levelname)s | %(name)s | %(message)s`
- Import order: stdlib → third-party → local

---

## Gotchas

- **Click timeout**: Camofox click can take 30-60s on suspended accounts — timeout is set to 60s in `browser.py`
- **Popup vs Banner**: Popup appears AFTER vote click (suspended/rate limited). Banner appears BEFORE non-vote clicks (suspended/banned header text)
- **Session persistence**: Handled by Camofox persistence plugin — cookies survive restarts
- **Proxy per session**: Via sticky-proxy plugin, assigned via `POST /users/{userId}/proxy`
- **Database path**: SQLite at `data/reddit.db` (configured in `config.py`)