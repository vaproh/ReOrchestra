# Reddit Automation API - Implementation Guide (V0.8)

## Overview

This guide covers setup, configuration, API usage, and operation of the Reddit Automation API system.

**Version:** 0.8

---

## 1. Setup Instructions

### 1.1 Prerequisites

- Python 3.9+
- Camofox browser server running on port 9377
- SQLite (included with Python)

### 1.2 Installation

```bash
# Navigate to project directory
cd reddit-api

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Create data directories
mkdir -p data/sessions data/logs
```

### 1.3 Camofox Setup

The system requires Camofox browser server. Use the provided setup script:

```bash
chmod +x setup_camofox.sh
./setup_camofox.sh
```

Or manually start Camofox:
```bash
# Default port is 9377
camofox --port 9377
```

### 1.4 Configuration

Copy `.env.example` to `.env` and adjust as needed:
```bash
cp .env.example .env
```

Key environment variables:
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/reddit.db` | Database path |
| `SESSION_DIR` | `data/sessions` | Cookie storage |
| `CAMOFOX_PORT` | `9377` | Camofox server port |
| `LOG_LEVEL` | `INFO` | Logging level |

### 1.5 Running the Server

```bash
# Start the API server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Access the API
# - API docs: http://localhost:8000/docs
# - GUI dashboard: http://localhost:8000/gui
```

---

## 2. API Endpoints Reference

Base URL: `http://localhost:8000/api`

### 2.1 Account Endpoints

#### Import Accounts
```
POST /api/accounts/import
```
Import multiple accounts at once.

**Request:**
```json
{
  "accounts": [
    {
      "username": "user1",
      "password": "pass123",
      "email": "user1@email.com",
      "email_password": "email_pass",
      "proxy": "http://user:pass@host:port",
      "profile_id": "win10-in"
    }
  ],
  "account_type": "upvoter"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "imported": 10,
    "skipped": 0,
    "accounts": [...],
    "errors": []
  }
}
```

#### List Accounts
```
GET /api/accounts?status=alive&type=upvoter&search=user&page=1&per_page=50
```

Query parameters:
- `status` - Filter by status: `fresh`, `logged_in`, `session_expired`, `banned`, `dead`, `alive`
- `type` - Filter by type: `upvoter`, `main`, `both`
- `search` - Search username
- `sort` - Sort field (default: `id`)
- `order` - `asc` or `desc` (default: `desc`)
- `page` - Page number (default: 1)
- `per_page` - Results per page (default: 50, max: 200)

#### Get Account
```
GET /api/accounts/{account_id}
```

#### Update Account
```
PATCH /api/accounts/{account_id}
```
Update account fields (status, account_type, proxy, etc.)

#### Delete Account
```
DELETE /api/accounts/{account_id}
```

#### Batch Delete
```
POST /api/accounts/batch-delete
```
```json
{
  "ids": [1, 2, 3]  // OR
  "filters": {"status": "dead", "type": "upvoter"}
}
```

#### Login Accounts
```
POST /api/accounts/login
```
```json
{
  "account_ids": [1, 2, 3],
  "force": false,
  "options": {"headless": false}
}
```

#### Simple Login
```
POST /api/accounts/login/simple
```
Login with username/password directly (no account ID needed).
```json
{
  "username": "user1",
  "password": "pass123",
  "headless": false
}
```

#### Batch Login
```
POST /api/accounts/login/batch
```
```json
{
  "filters": {"status": "fresh"},
  "force": false,
  "options": {"headless": false}
}
```

#### Check Session
```
GET /api/accounts/{account_id}/session
```

---

### 2.2 Action Endpoints

#### Upvote
```
POST /api/actions/upvote
```
```json
{
  "account_ids": [1, 2, 3],
  "target_url": "https://www.reddit.com/r/subreddit/comments/abc123/title/",
  "random_order": true
}
```

Alternative filters:
```json
{
  "filters": {"status": "logged_in", "type": "upvoter"},
  "target_url": "https://www.reddit.com/..."
}
```

Or single account by username:
```json
{
  "username": "user1",
  "target_url": "https://www.reddit.com/..."
}
```

#### Downvote
```
POST /api/actions/downvote
```
Same format as upvote.

---

### 2.3 Proxy Endpoints

#### List Proxies
```
GET /api/proxies?status=active&assigned=true
```

#### Import Proxies
```
POST /api/proxies/import
```
```json
{
  "proxies": [
    "http://user:pass@host:port",
    "host:port:username:password"
  ]
}
```

#### Replace Dead Proxies
```
POST /api/proxies/replace
```
Replace dead proxies with new ones (maintains count).
```json
{
  "proxies": ["http://new:proxy@host:port", ...]
}
```

#### Delete Proxy
```
DELETE /api/proxies/{proxy_id}
```

#### Mark Proxy Dead
```
POST /api/proxies/mark-dead
```
```json
{
  "proxy_id": 123,
  "error": "connection_timeout"
}
```

---

### 2.4 Admin Endpoints

#### Health Check
```
GET /api/admin/health
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "version": "1.0.0",
    "timestamp": "2024-...",
    "camofox": {"connected": true, "port": 9377},
    "vnc": {"enabled": false, "port": 5999}
  }
}
```

#### Statistics
```
GET /api/admin/stats
```

**Response:**
```json
{
  "success": true,
  "data": {
    "accounts": {
      "total": 100,
      "active": 85,
      "dead": 15,
      "by_type": {"upvoter": 80, "main": 15, "both": 5},
      "by_status": {"fresh": 10, "logged_in": 75, ...}
    },
    "actions": {
      "today": 150,
      "this_week": 1000,
      "this_month": 4500,
      "by_type": {"upvote": 4000, "downvote": 500}
    },
    "posts": {...},
    "slots": {...}
  }
}
```

---

### 2.5 Queue Worker Endpoints

#### List Workers
```
GET /api/workers?status=idle
```

#### Get Worker
```
GET /api/workers/{worker_id}
```

#### Create Worker
```
POST /api/workers
```
```json
{
  "account_id": 1
}
```

#### Bulk Create Workers
```
POST /api/workers/bulk
```
Creates workers for all logged-in accounts.

#### Pause Worker
```
POST /api/workers/{worker_id}/pause
```

#### Resume Worker
```
POST /api/workers/{worker_id}/resume
```

---

### 2.6 Queue Task Endpoints

#### List Tasks
```
GET /api/tasks?status=queued
```
Status filter: `queued`, `running`, `completed`, `partial`, `failed`, `cancelled`

#### Create Task
```
POST /api/tasks
```
```json
{
  "action_type": "upvote_post",
  "target_url": "https://www.reddit.com/r/sub/comments/abc123/title/",
  "workers_needed": 5
}
```

**Supported action_types:**
- `upvote_post`
- `downvote_post`
- `upvote_comment`
- `downvote_comment`
- `follow_user`
- `unfollow_user`
- `join_subreddit`
- `leave_subreddit`
- `save_post`

#### Get Task
```
GET /api/tasks/{task_id}
```
Returns task details with action logs.

#### Cancel Task
```
POST /api/tasks/{task_id}/cancel
```

#### Boost Priority
```
POST /api/tasks/{task_id}/priority
```

---

### 2.7 Queue Control Endpoints

#### View Queue
```
GET /api/queue
```
Lists all queued and running tasks.

#### Start Queue Processor
```
POST /api/queue/start
```

#### Stop Queue Processor
```
POST /api/queue/stop
```

#### Queue Status
```
GET /api/queue/status
```

---

## 3. Queue System Usage

### 3.1 Overview

The queue system allows scalable, distributed task processing. Instead of executing actions directly, you create tasks that are processed by a pool of workers in the background.

### 3.2 Workflow

1. **Create workers** from your logged-in accounts
2. **Create tasks** specifying the action and target
3. **Start the queue processor**
4. **Monitor progress** via API

### 3.3 Example: Upvote with Queue

```bash
# Step 1: Ensure accounts are logged in
curl -X POST http://localhost:8000/api/accounts/login/batch \
  -H "Content-Type: application/json" \
  -d '{"filters": {"status": "logged_in"}, "force": false}'

# Step 2: Create workers for all logged-in accounts
curl -X POST http://localhost:8000/api/workers/bulk

# Step 3: Create an upvote task
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "upvote_post",
    "target_url": "https://www.reddit.com/r/askreddit/comments/abc123/title/",
    "workers_needed": 10
  }'

# Step 4: Start the queue processor
curl -X POST http://localhost:8000/api/queue/start

# Step 5: Monitor the task
curl http://localhost:8000/api/tasks/1

# Step 6: Stop when done
curl -X POST http://localhost:8000/api/queue/stop
```

### 3.4 Deduplication

The queue system prevents duplicate actions:
- Each worker can only succeed at an action on a target once
- Failed attempts can be retried
- `duplicate` outcome means worker already succeeded

### 3.5 Worker States

| State | Description |
|-------|-------------|
| `idle` | Available for task assignment |
| `working` | Currently executing a task |
| `paused` | Manually paused, not available |

### 3.6 Task States

| State | Description |
|-------|-------------|
| `queued` | Waiting in queue |
| `running` | Currently being processed |
| `completed` | All workers succeeded |
| `partial` | Some workers succeeded |
| `failed` | All workers failed |
| `cancelled` | Manually cancelled |

---

## 4. Creating Tasks and Managing Workers

### 4.1 Worker Pool Management

Workers are created from existing logged-in accounts:

```bash
# Create single worker
curl -X POST http://localhost:8000/api/workers \
  -d '{"account_id": 1}'

# Create workers for all logged-in accounts
curl -X POST http://localhost:8000/api/workers/bulk

# List workers
curl http://localhost:8000/api/workers

# Pause a worker (e.g., if account has issues)
curl -X POST http://localhost:8000/api/workers/1/pause

# Resume worker
curl -X POST http://localhost:8000/api/workers/1/resume
```

### 4.2 Task Execution

When a task is created:
1. It enters `queued` status
2. Queue processor assigns idle workers
3. Each worker executes the action via Camofox
4. Results are logged
5. Task status updates to `completed`/`partial`/`failed`

### 4.3 Action Outcomes

| Outcome | Description |
|---------|-------------|
| `success` | Action completed successfully |
| `failed` | Action failed |
| `duplicate` | Worker already did this action |
| `popup_suspended` | Reddit suspended the account (popup) |
| `popup_rate_limited` | Rate limited (popup) |
| `header_suspended` | Account suspended (header banner) |
| `header_banned` | Account banned (header banner) |

---

## 5. Configuration Options

### 5.1 Configuration Files

| File | Purpose | Gitignored |
|------|---------|------------|
| `config/default.yaml` | Default values | No |
| `config/custom.yaml` | Overrides | **Yes** |
| `config/proxies.yaml` | Proxy settings | **Yes** |

### 5.2 Config Loading Priority

1. Runtime overrides (via API)
2. `config/custom.yaml`
3. `config/default.yaml`

### 5.3 Default Configuration (config/default.yaml)

```yaml
app:
  name: "Reddit Automation API"
  version: "1.0.0"

rate_limits:
  max_votes_per_day: 15
  max_votes_per_week: 100
  min_seconds_between_votes: 120
  max_vote_only_ratio: 0.3

concurrency:
  max_concurrent_per_slot: 10
  slots_auto_scale: true
  accounts_per_slot: 50

timing:
  jitter_sigma: 120
  skip_cycle_chance: 0.08
  clump_chance: 0.15
  micro_jitter_min_ms: 100
  micro_jitter_max_ms: 900

s_curve:
  enabled: true
  initial_burst: 0.30
  peak: 0.45
  decay: 0.20
  tail: 0.05

activation:
  batch_size: 50
  spread_days: 3

burn_detection:
  consecutive_failures: 5
  rate_limit_backoff_hours: 24
  success_rate_threshold: 0.8

session:
  max_age_hours: 72
  refresh_before_hours: 12

account_limits:
  max_fail_count: 10
  dead_after_ban: true

logging:
  level: "INFO"
  file: "data/logs/app.log"
  max_bytes: 10485760
  backup_count: 5
```

### 5.4 Settings (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/reddit.db` | Database connection |
| `SESSION_DIR` | `data/sessions` | Session cookie storage |
| `LOG_DIR` | `data/logs` | Log file location |
| `MAX_SESSION_AGE_HOURS` | `72` | Session expiry |
| `CAMOFOX_PORT` | `9377` | Camofox server port |
| `VNC_ENABLED` | `false` | Enable VNC |
| `VNC_PORT` | `5999` | VNC port |

---

## 6. Troubleshooting

### 6.1 Common Issues

#### Camofox Connection Failed
```
Error: Cannot connect to Camofox at localhost:9377
```
**Solution:** Ensure Camofox server is running:
```bash
camofox --port 9377
```

#### Login Failed
- Check username/password are correct
- Verify proxy is working
- Check if account is banned
- Ensure Camofox is running

#### Task Stuck in Running
- Check workers are available (not all paused)
- Restart queue processor:
```bash
curl -X POST http://localhost:8000/api/queue/stop
curl -X POST http://localhost:8000/api/queue/start
```

#### All Actions Failing
- Check account status (`/api/accounts/{id}`)
- Verify session is valid (`/api/accounts/{id}/session`)
- Check proxy is working
- Review BurnDetector status

### 6.2 API Error Codes

| Code | Description |
|------|-------------|
| `INTERNAL_ERROR` | Unhandled exception |
| `ACCOUNT_NOT_FOUND` | Account ID doesn't exist |
| `WORKER_NOT_FOUND` | Worker ID doesn't exist |
| `TASK_NOT_FOUND` | Task ID doesn't exist |
| `INVALID_ACTION_TYPE` | Action type not supported |
| `NO_ACCOUNTS` | No accounts matched filters |

### 6.3 Logging

Logs are written to `data/logs/app.log`. Check there for detailed error information.

```bash
# View recent logs
tail -f data/logs/app.log

# Increase verbosity
# Set LOG_LEVEL=DEBUG in .env
```

### 6.4 Database Inspection

```bash
# Using sqlite3
sqlite3 data/reddit.db

# List tables
sqlite> .tables

# View account status
sqlite> SELECT id, username, status FROM accounts;

# View queue tasks
sqlite> SELECT id, action_type, status, workers_needed, workers_completed FROM queue_tasks;
```

---

## 7. Service Details

### 7.1 LoginService

Handles browser-based Reddit login via Camofox:

1. Creates Camofox tab
2. Navigates to old.reddit.com/login
3. Checks for existing session
4. Fills credentials if needed
5. Saves session cookies

### 7.2 ActionService

Browser-based voting:

1. Creates/uses existing session
2. Navigates to target URL
3. Scrolls to find upvote/downvote button
4. Clicks the button
5. Verifies success

### 7.3 RateLimiter

Per-account vote limiting:
- Tracks votes per day/week
- Enforces cooldown between votes
- Checks active hours
- Monitors vote-only ratio

### 7.4 BurnDetector

Account health monitoring:
- Tracks consecutive failures
- Detects bans (401/403)
- Detects rate limits (429)
- Marks accounts as dead when thresholds exceeded

### 7.5 QueueProcessor

Background task processor:
- Runs in separate thread
- Processes tasks FIFO (priority first)
- Assigns workers to tasks
- Handles retries with exponential backoff
- Updates task status on completion

### 7.6 WorkerPool

Worker lifecycle management:
- Creates workers from accounts
- Assigns idle workers to tasks
- Tracks worker status
- Handles deduplication
- Manages worker pause/resume

---

## 8. GUI Dashboard

Access the web-based dashboard at `/gui`:

- Account overview
- Action statistics
- Queue status
- Proxy management

The dashboard provides a visual interface for most API operations.
