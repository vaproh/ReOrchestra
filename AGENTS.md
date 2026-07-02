# AGENTS.md — ReOrchestra

## What Is This Project?

**ReOrchestra** is a bulk Reddit account automation tool for managing 500-1000 Reddit accounts on a single VPS.

> *"Your Accounts, In Harmony"*

**Philosophy:**
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

**Queue behavior:**
- FIFO + priority
- Max 3 concurrent accounts per task (configurable)
- Auto-retry 3 times before marking failed
- Failed accounts (ban/suspend) replaced automatically
- Deduplication by `{account_id}:{action_type}:{target_url}`

**Single VPS:** SQLite for DB, one QueueProcessor.

---

## API Endpoints

### Accounts

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/accounts/import` | Import accounts |
| POST | `/api/accounts/login` | Login via Camofox |
| GET | `/api/accounts` | List accounts |
| GET | `/api/accounts/{id}` | Get account details |
| PATCH | `/api/accounts/{id}` | Update account |
| DELETE | `/api/accounts/{id}` | Delete account |

### Tasks

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/tasks` | Create task |
| GET | `/api/tasks` | List tasks |
| GET | `/api/tasks/{id}` | Get task status |
| POST | `/api/tasks/{id}/cancel` | Cancel task |

### Queue

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/queue/start` | Start queue |
| POST | `/api/queue/stop` | Stop queue |
| GET | `/api/queue/status` | Queue status |

### Admin

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/admin/health` | Health check |
| GET | `/api/admin/stats` | Statistics |

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

| Outcome | Meaning |
|---------|---------|
| `success` | Action completed |
| `popup_suspended` | Account locked via popup |
| `popup_rate_limited` | Rate limited via popup |
| `header_banned` | Banned via header banner |
| `header_suspended` | Suspended via header banner |
| `click_timeout` | Button click timed out |
| `element_not_found` | Target element not found |

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
| `just logs` | Tail logs |
| `just logs-clear` | Clear logs |
| `just clean` | Clean cache |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Console log level (set `DEBUG` for verbose) |

---

## Code Conventions

- Python 3.x, type hints everywhere
- Pydantic v2 for schemas
- SQLAlchemy 2.x declarative base
- Logging: `logger = logging.getLogger("name")`
- Format: `%(asctime)s | %(levelname)s | %(name)s | %(message)s`
- Import order: stdlib → third-party → local

---

## Gotchas

- **Click timeout**: Camofox click can take 30-60s on suspended accounts
- **Popup vs Banner**: Popup appears AFTER vote. Banner appears BEFORE non-vote.
- **Session persistence**: Handled by Camofox persistence plugin
- **Proxy per session**: Via sticky-proxy plugin
- **Database**: SQLite at `data/reddit.db`
- **CORS**: Set `CORS_ALLOWED_ORIGINS` in `.env`
