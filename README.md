# ReOrchestra — Your Accounts, In Harmony

A scalable Reddit account management and automation platform built with FastAPI, Camofox browser automation, and SQLite.

## Quick Start

```bash
# Install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start Camofox (browser automation server)
cd ../camofox && npm start

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Access the API
# - API docs: http://localhost:8000/docs
# - GUI dashboard: http://localhost:8000/gui
```

## Features

- **Worker Queue System** — FIFO task processing with priority boost and deduplication
- **9 Action Types** — Upvote/downvote posts & comments, follow/unfollow, join/leave, save
- **Browser Automation** — Camofox-powered stealth browser with fingerprint spoofing
- **Session Persistence** — Sessions persist across restarts via Camofox persistence plugin
- **Proxy Management** — Sticky-proxy per session (customers bring their own proxies)
- **Detection Avoidance** — Rate limiting, timing entropy, account health monitoring

## Architecture

```
├── app/
│   ├── api/          # REST API endpoints
│   ├── models/       # SQLAlchemy database models
│   ├── schemas/      # Pydantic request/response schemas
│   └── services/     # Business logic (queue, login, browser)
├── config/           # YAML configuration
├── data/             # SQLite DB, sessions (gitignored)
└── docs/             # Architecture & implementation docs
```

## Documentation

| Document | Content |
|----------|---------|
| `docs/ARCHITECTURE.md` | System architecture, components, data models |
| `docs/IMPLEMENTATION.md` | Setup, API reference, queue usage |

## Tech Stack

- **Python 3.14** + FastAPI
- **SQLAlchemy** + SQLite
- **Camofox** — Stealth headless browser
- **Sticky-Proxy** — Per-session proxy injection

---

ReOrchestra — Bulk Reddit Account Automation