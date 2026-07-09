# ReOrchestra 🚀

**Your Accounts, In Harmony**

Bulk Reddit account automation for managing 500-1000 accounts on a single VPS.

![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/fastAPI-0.100%2B-green?logo=fastapi)
![Tests](https://img.shields.io/badge/tests-93%20passed-brightgreen?logo=pytest)
![License](https://img.shields.io/badge/license-MIT-blue?logo=open-source-initiative)

---

## ✨ Features

| Feature             | Description                                          |
| :------------------ | :----------------------------------------------------|
| **Web Dashboard**   | HTMX + Jinja2 UI at `http://localhost:8000/dashboard`|
| **Queue System**    | Task-based: specify action + URL + accounts needed   |
| **9 Actions**       | Upvote/downvote, follow/unfollow, join/leave, save   |
| **Camofox Browser** | Stealth headless browser with fingerprint spoofing   |
| **Auto-Retry**      | 3 retries with exponential backoff                   |
| **Deduplication**   | Same account can't do same action twice              |
| **Account Health**  | Auto-mark dead on ban/suspend, replace accounts      |

---

## 🚀 Quick Start

### Prerequisites

- 🐍 Python 3.10+
- 🌐 [Camofox](https://github.com/jo-inc/camofox-browser) browser server (port 9377)
- 📋 [`just`](https://just.systems/) — command runner
- ⚡ [`uv`](https://astral.sh/uv/install.sh) — fast package manager

### Install

```bash
# 1. Clone
cd ReOrchestra

# 2. Install uv (one-time)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies (including dev)
just install

# 4. Configure
cp .env.example .env
```

### Run

```bash
just dev      # 🚀 Start with auto-reload + dashboard
just run      # 🏭 Start production server
just debug    # 🔍 Start with DEBUG logging
just logs     # 📋 Tail logs
```

Dashboard: `http://localhost:8000`

Or manually:

```bash
camofox --port 9377                          # Start browser
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📌 Commands

| Command           | Description               |
| :---------------- | :------------------------ |
| `just install`    | Setup venv + install deps |
| `just run`        | Start production server   |
| `just dev`        | Start with auto-reload    |
| `just debug`      | Start with DEBUG logging  |
| `just logs`       | Tail logs                 |
| `just logs-clear` | Clear logs                |
| `just clean`      | Clean cache               |

---

## 📖 Usage

### Import Accounts

```bash
curl -X POST http://localhost:8000/api/accounts/import \
  -H "Content-Type: application/json" \
  -d '{
    "accounts": [
      {"username": "user1", "password": "pass", "proxy": "http://proxy:8080"}
    ],
    "account_type": "upvoter"
  }'
```

### Login Accounts

```bash
curl -X POST http://localhost:8000/api/accounts/login \
  -H "Content-Type: application/json" \
  -d '{"account_ids": [1, 2, 3]}'
```

### Create Task

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "upvote_post",
    "target_url": "https://old.reddit.com/r/...",
    "workers_needed": 50
  }'
```

### Monitor

```bash
curl http://localhost:8000/api/tasks/1          # Get task
curl http://localhost:8000/api/tasks              # List tasks
```

---

## 🔌 API Endpoints

### Accounts

| Method   | Endpoint               | Description       |
| :------- | :--------------------- | :---------------- |
| `POST`   | `/api/accounts/import` | Import accounts   |
| `POST`   | `/api/accounts/login`  | Login via Camofox |
| `GET`    | `/api/accounts`        | List accounts     |
| `GET`    | `/api/accounts/{id}`   | Get account       |
| `PATCH`  | `/api/accounts/{id}`   | Update account    |
| `DELETE` | `/api/accounts/{id}`   | Delete account    |

### Tasks

| Method | Endpoint                 | Description |
| :----- | :----------------------- | :---------- |
| `POST` | `/api/tasks`             | Create task |
| `GET`  | `/api/tasks`             | List tasks  |
| `GET`  | `/api/tasks/{id}`        | Get task    |
| `POST` | `/api/tasks/{id}/cancel` | Cancel task |

### Queue

| Method | Endpoint            | Description     |
| :----- | :------------------ | :-------------- |
| `POST` | `/api/queue/start`  | Start processor |
| `POST` | `/api/queue/stop`   | Stop processor  |
| `GET`  | `/api/queue/status` | Status          |

### Admin

| Method | Endpoint            | Description  |
| :----- | :------------------ | :----------- |
| `GET`  | `/api/admin/health` | Health check |
| `GET`  | `/api/admin/stats`  | Statistics   |

---

## 🎯 Supported Actions

| Action             | Description               |
| :----------------- | :------------------------ |
| `upvote_post`      | Upvote a Reddit post      |
| `downvote_post`    | Downvote a Reddit post    |
| `upvote_comment`   | Upvote a Reddit comment   |
| `downvote_comment` | Downvote a Reddit comment |
| `follow_user`      | Follow a Reddit user      |
| `unfollow_user`    | Unfollow a Reddit user    |
| `join_subreddit`   | Join a subreddit          |
| `leave_subreddit`  | Leave a subreddit         |
| `save_post`        | Save a post               |

---

## ⚙️ Configuration

### Environment Variables

| Variable              | Default                      | Description                             |
| :-------------------- | :--------------------------- | :-------------------------------------- |
| `DATABASE_URL`        | `sqlite:///./data/reddit.db` | Database                                |
| `LOG_DIR`             | `data/logs`                  | Log directory                           |
| `CAMOFOX_PORT`        | `9377`                       | Camofox port                            |
| `CAMOFOX_DIR`         | `../camofox`                 | Camofox installation path               |
| `PROXY_MODE`          | `sticky`                     | Proxy mode (`sticky` or `dynamic`)      |
| `USE_PROXIES_BY_DEFAULT` | `true`                   | Inject proxies into sessions by default |
| `VNC_ENABLED`         | `false`                      | Enable VNC server                       |
| `ACTION_DELAY_MS_MIN` | `1000`                       | Min delay between actions (ms)          |
| `ACTION_DELAY_MS_MAX` | `3000`                       | Max delay between actions (ms)          |
| `LOG_LEVEL`           | `INFO`                       | Console log level (`DEBUG` for verbose)|
| `CORS_ALLOWED_ORIGINS` | `*`                       | CORS allowed origins                    |

---

## 🏗️ Architecture

```
Request → FastAPI → Task Queue → QueueProcessor → Executor → Camofox → Reddit
```

**Flow:**

1. Task created via API
2. QueueProcessor picks it up
3. Assigns idle accounts (max 3 concurrent)
4. Executes actions via Camofox
5. On ban/suspend: marks dead, replaces account
6. On retryable error: retries 3x

---

## 📁 Project Structure

```
ReOrchestra/
├── app/
│   ├── main.py              # FastAPI entry
│   ├── config.py           # Settings
│   ├── database.py         # SQLAlchemy
│   ├── api/                # API routers
│   │   ├── accounts.py
│   │   ├── queue_tasks.py
│   │   ├── queue_queue.py
│   │   ├── proxies.py
│   │   ├── admin.py
│   │   └── frontend.py     # Dashboard routes
│   ├── models/             # DB models
│   ├── schemas/            # Pydantic schemas
│   ├── templates/           # Jinja2 templates
│   │   ├── base.html
│   │   ├── pages/          # Dashboard pages
│   │   └── components/     # Reusable components
│   ├── static/             # CSS, JS
│   └── modules/
│       ├── accounts/        # Account service + login
│       ├── queue/           # QueueProcessor
│       └── executor/        # Camofox + actions
├── tests/                   # 93 tests
├── data/                    # SQLite + sessions + logs
├── justfile                # Command runner
└── pyproject.toml         # Dependencies
```

---

## 📋 Logging

Logs are written to `data/logs/app_YYYYMMDD_HHMMSS.log`

- **File:** Always DEBUG level
- **Console:** INFO level by default, DEBUG when `LOG_LEVEL=DEBUG`

### Sensitive Data

Passwords and proxy credentials are automatically redacted:

```
password: "secret123" → password: "****23"
proxy: "http://user:pass@host:8080" → proxy: "host:8080"
```

---

## 🧪 Testing

```bash
cd ReOrchestra && uv run pytest tests/ -v
```

**93 tests** covering:
- Account import, retrieval, update, deletion, status transitions
- Task creation, retrieval, cancellation, progress tracking
- Queue processing with mocked Camofox (no real browser)
- Deduplication logic
- Rate limiting integration tests

All tests use **mocked Camofox** (no browser needed), **in-memory SQLite** (fresh per test).

---

## 📚 Docs

- [API Documentation](http://localhost:8000/docs) — Swagger UI
- `AGENTS.md` — AI-friendly project overview
- `PRD.md` — Product requirements

---

**ReOrchestra** — _Your Accounts, In Harmony_
