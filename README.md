# ReOrchestra — Your Accounts, In Harmony

A white-label bulk Reddit account automation SaaS platform. Manage thousands of Reddit accounts at scale with a robust queue system, stealth browser automation, and intelligent detection avoidance.

## Key Features

| Feature | Description |
|---------|-------------|
| **Queue System** | FIFO task processing with priority boost, deduplication, and automatic retry with exponential backoff |
| **9 Action Types** | Upvote/downvote posts and comments, follow/unfollow users, join/leave subreddits, save posts |
| **Camofox Browser Automation** | Stealth headless browser with session persistence, proxy injection, and fingerprint spoofing |
| **Session Persistence** | Sessions persist across restarts — no re-login required |
| **Proxy Management** | Sticky-proxy per session with automatic rotation on failure |
| **Detection Avoidance** | Per-account rate limiting, S-curve timing with jitter, account health monitoring, and burn detection |

## Tech Stack

| Component | Technology |
|-----------|------------|
| API Framework | Python 3 + FastAPI |
| Database | SQLite + SQLAlchemy ORM |
| Browser Automation | Camofox (headless browser server) |
| Background Processing | Python threading (QueueProcessor) |
| Configuration | YAML + Pydantic settings |

## Quick Start

### Prerequisites

- Python 3.9+
- Camofox browser server (port 9377)

### Installation

```bash
# Clone and navigate to project
cd reddit-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Create data directories
mkdir -p data/sessions data/logs

# Configure environment
cp .env.example .env
```

### Running

```bash
# Start Camofox browser server
camofox --port 9377

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Access Points

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | Swagger UI API documentation |
| `http://localhost:8000/gui` | Web-based dashboard |
| `http://localhost:8000/` | API root |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Server                           │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │Accounts  │  │Actions   │  │Queue     │  │Admin     │         │
│  │/api/    │  │/api/    │  │/api/    │  │/api/    │         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
│       └─────────────┴─────────────┴─────────────┘               │
│                           │                                      │
│                           ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Service Layer                          │   │
│  │                                                          │   │
│  │  LoginService  │  ActionService  │  QueueProcessor       │   │
│  │  CamofoxClient │  WorkerPool    │  RateLimiter/Burn    │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │    Camofox Browser       │
              │    (localhost:9377)      │
              │                          │
              │  • Tab per session       │
              │  • Proxy injection        │
              │  • Cookie persistence     │
              └─────────────────────────┘
```

## Key Concepts

### Workers

A **worker** is a Reddit account registered with the queue system. Workers process tasks from the queue and execute actions via the Camofox browser.

```
Worker lifecycle: idle → working → idle (or paused/dead)
```

### Tasks

A **task** represents a single action to be performed on a target URL. Tasks are processed FIFO with priority support.

```
Supported action_types:
  upvote_post, downvote_post, upvote_comment, downvote_comment
  follow_user, unfollow_user, join_subreddit, leave_subreddit, save_post
```

### Queue

The **queue** manages task distribution to workers. The QueueProcessor runs as a background thread, assigning idle workers to tasks until completion.

```
Task states: queued → running → completed | partial | failed | cancelled
```

## Supported Actions

| Action | Description |
|--------|-------------|
| `upvote_post` | Upvote a Reddit post |
| `downvote_post` | Downvote a Reddit post |
| `upvote_comment` | Upvote a Reddit comment |
| `downvote_comment` | Downvote a Reddit comment |
| `follow_user` | Follow a Reddit user |
| `unfollow_user` | Unfollow a Reddit user |
| `join_subreddit` | Join a subreddit |
| `leave_subreddit` | Leave a subreddit |
| `save_post` | Save a post |

## Configuration

Configuration files (in `config/`):

| File | Purpose |
|------|---------|
| `default.yaml` | Default configuration values |
| `custom.yaml` | Runtime overrides (gitignored) |

Key environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/reddit.db` | Database path |
| `SESSION_DIR` | `data/sessions` | Cookie storage |
| `CAMOFOX_PORT` | `9377` | Camofox server port |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## Documentation

| Document | Description |
|----------|-------------|
| `docs/ARCHITECTURE.md` | System architecture, components, data models |
| `docs/IMPLEMENTATION.md` | Setup guide, API reference, queue usage |

## Directory Structure

```
reddit-api/
├── app/
│   ├── api/              # REST API endpoints
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── services/        # Business logic
│   │   ├── queue_actions/  # 9 action executors
│   │   ├── queue_processor.py
│   │   ├── worker_pool.py
│   │   └── browser.py
│   └── main.py           # FastAPI entry point
├── config/              # YAML configuration
├── data/                # SQLite DB, sessions, logs
├── docs/                # Architecture & implementation docs
└── requirements.txt
```

---

**ReOrchestra** — Your Accounts, In Harmony

For support, contact: support@reorchestra.io
