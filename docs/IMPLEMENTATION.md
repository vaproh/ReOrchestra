# Reddit Automation API - Implementation Plan

## Overview

A scalable Reddit account management and karma automation system. Built with FastAPI, Camofox browser automation, and SQLite. Manages 5 to 1,000 accounts with sticky proxy-per-account assignment and detection avoidance.

---

## 1. Architecture

### 1.1 System Design

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Reddit API (Python/FastAPI)                    │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    API Layer                                    │  │
│  │  /api/accounts/*  │  /api/actions/*  │  /api/proxies/*       │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                  Service Layer                                  │  │
│  │  AccountService  │  ActionService  │  ProxyService          │  │
│  │  SlotManager     │  RateLimiter   │  BurnDetector           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              Camofox Client (Python)                          │  │
│  │  userId = "s_{account_id}"  ←  decoupled from username      │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
         │
         │  REST API
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 Camofox Browser Server (Node.js)                     │
│                                                                      │
│  ONE instance on port 9377                                          │
│  MAX_SESSIONS = 50 (configurable)                                   │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  sticky-proxy plugin                                          │  │
│  │  userProxyMap: { "s_1" → proxy_config, ... }  ← IN-MEMORY  │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  Sessions (via persistence plugin):                                 │
│    ~/.camofox/profiles/{hashed_userId}/storage_state.json          │
│    → Cookies + localStorage, persists on restart                     │
│                                                                      │
│  Each session = one userId = one account = one proxy                │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

```
Import Accounts (CSV)
    ↓
Create Account rows in DB (status=fresh)

Import Proxies (CSV)
    ↓
Create Proxy rows + auto-assign 1:1 to accounts (proxy[i] → account[i])

Push Proxy to Camofox (per action)
    ↓
POST /users/{userId}/proxy
    ↓
Camofox stores in userProxyMap (IN-MEMORY)

Login / Vote Action
    ↓
CamofoxClient.create_tab(userId="s_{account_id}")
    ↓
sticky-proxy plugin intercepts session:creating
    ↓
Injects proxy from userProxyMap into browser context
    ↓
Reddit login/vote with correct proxy
    ↓
Session cookies saved to disk (persistence plugin)
```

### 1.3 Session Lifecycle

```
First Use:
  push_proxy(userId, proxy) → create_tab(userId) → login → cookies saved

Subsequent Use:
  push_proxy(userId, proxy) → create_tab(userId) → cookies loaded → vote

After Camofox Restart:
  push_proxy(userId, proxy) → create_tab(userId) → cookies on disk intact → resume
```

---

## 2. Database Models

### 2.1 Account

```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(20) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,
    email VARCHAR(128),
    proxy_id INTEGER REFERENCES proxies(id),

    status VARCHAR(20) DEFAULT 'fresh',
    -- 'fresh', 'logged_in', 'session_expired', 'banned', 'dead'

    votes_today INTEGER DEFAULT 0,
    votes_this_week INTEGER DEFAULT 0,
    total_votes INTEGER DEFAULT 0,
    last_vote_at TIMESTAMP,

    fail_count INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    last_failure_at TIMESTAMP,

    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_status (status),
    INDEX idx_proxy (proxy_id)
);
```

### 2.2 Proxy

```sql
CREATE TABLE proxies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proxy_string VARCHAR(512) NOT NULL,
    account_id INTEGER UNIQUE REFERENCES accounts(id),
    status VARCHAR(20) DEFAULT 'active',

    fail_count INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_account (account_id),
    INDEX idx_status (status)
);
```

### 2.3 ActionLog

```sql
CREATE TABLE action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id),

    action_type VARCHAR(20) NOT NULL,
    -- 'upvote', 'downvote', 'comment_upvote', 'comment_downvote', 'comment', 'login'

    target_id VARCHAR(64),
    target_url TEXT,

    success BOOLEAN NOT NULL,
    error TEXT,
    http_status INTEGER,

    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,

    dedup_hash VARCHAR(64) UNIQUE,

    INDEX idx_account (account_id),
    INDEX idx_action_type (action_type),
    INDEX idx_created (created_at)
);
```

### 2.4 Config

```sql
CREATE TABLE config (
    key VARCHAR(64) PRIMARY KEY,
    value TEXT,
    source VARCHAR(20) DEFAULT 'runtime',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. Configuration

### 3.1 Config Files

| File | Purpose |
|------|---------|
| `config/default.yaml` | All defaults |
| `config/custom.yaml` | User overrides (gitignored) |

### 3.2 Default Config (`config/default.yaml`)

```yaml
rate_limits:
  max_votes_per_day: 15
  max_votes_per_week: 100
  min_seconds_between_votes: 120

concurrency:
  max_sessions: 50          # Max Camofox sessions per instance
  max_concurrent_per_slot: 10

timing:
  jitter_sigma: 120         # Gaussian jitter std dev (seconds)
  skip_cycle_chance: 0.08   # 8% chance to skip vote
  clump_chance: 0.15        # 15% chance to vote sooner

s_curve:
  enabled: true
  initial_burst: 0.30       # 30% in first 30 min
  peak: 0.45               # 45% in 30min-2h
  decay: 0.20              # 20% in 2-4h
  tail: 0.05               # 5% after 4h

burn_detection:
  consecutive_failures: 5   # Mark dead after N failures
  rate_limit_backoff_hours: 24
  success_rate_threshold: 0.8

session:
  max_age_hours: 72
  refresh_before_hours: 12
```

---

## 4. Camofox Plugin: `sticky-proxy`

### 4.1 Purpose

Inject a specific proxy into each Camofox session based on `userId`.

### 4.2 Location

```
camofox-browser/plugins/sticky-proxy/
└── index.js
```

### 4.3 Logic

```javascript
// In-memory map: userId → proxy config
const userProxyMap = new Map();

// Hook: before session is created, inject that user's proxy
events.on('session:creating', async ({ userId, contextOptions }) => {
  const proxy = userProxyMap.get(userId)
  if (proxy) {
    contextOptions.proxy = {
      server: `http://${proxy.host}:${proxy.port}`,
      username: proxy.username,
      password: proxy.password,
    }
  }
})

// API: Push proxy config for a userId
app.post('/users/:userId/proxy', (req, res) => {
  const { host, port, username, password } = req.body
  userProxyMap.set(req.params.userId, { host, port, username, password })
  res.json({ ok: true, userId: req.params.userId })
})

// API: Get proxy config for a userId
app.get('/users/:userId/proxy', (req, res) => {
  const proxy = userProxyMap.get(req.params.userId)
  res.json(proxy || null)
})

// API: Delete proxy config for a userId
app.delete('/users/:userId/proxy', (req, res) => {
  userProxyMap.delete(req.params.userId)
  res.json({ ok: true })
})
```

### 4.4 Proxy Format

Proxy string from DB: `http://user:pass_session-ABC123_lifetime-40@gateway.evomi.com:1000`

Parsed into:
```
host: gateway.evomi.com
port: 1000
username: user
password: pass_session-ABC123_lifetime-40
```

### 4.5 Camofox Session Naming

Camofox `userId` = `s_{account_id}` (not username)

```
account_id=1  → userId="s_1"
account_id=42 → userId="s_42"
```

This decouples Camofox session from Reddit username.

---

## 5. API Endpoints

### 5.1 Accounts

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/accounts` | List accounts (paginated) |
| GET | `/api/accounts/{id}` | Get single account |
| POST | `/api/accounts/import` | Bulk import accounts |
| POST | `/api/accounts/login` | Login accounts |
| PATCH | `/api/accounts/{id}` | Update account |
| DELETE | `/api/accounts/{id}` | Delete account |

### 5.2 Proxies

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/proxies` | List proxies |
| POST | `/api/proxies/import` | Bulk import proxies |
| POST | `/api/proxies/assign` | Assign proxies to accounts (1:1) |

### 5.3 Actions

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/actions/upvote` | Upvote with accounts |
| POST | `/api/actions/downvote` | Downvote with accounts |

### 5.4 Admin

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/health` | System health |
| GET | `/api/admin/stats` | Dashboard statistics |
| GET | `/api/admin/config` | Get config |
| PUT | `/api/admin/config` | Update runtime config |

---

## 6. Services

### 6.1 ProxyService

```python
class ProxyService:
    def import_bulk_accounts(csv_lines: list[str]) -> tuple[int, int]
        # Parse: username,password
        # Create Account rows
        # Return: (imported, skipped)

    def import_bulk_proxies(csv_lines: list[str]) -> tuple[int, int]
        # Parse: proxy_string
        # Create Proxy rows (unassigned)
        # Return: (imported, skipped)

    def import_combined(csv_lines: list[str]) -> tuple[int, int]
        # Parse: username,password,proxy_string,email(optional)
        # Create Account + Proxy + assign 1:1
        # Return: (imported, skipped)

    def auto_assign_proxies_to_accounts() -> None
        # Find unassigned proxies (ordered by id)
        # Find unassigned accounts (ordered by id)
        # Assign proxy[i] → account[i]
        # Raise if counts don't match

    def push_proxy_to_camofox(userId: str, proxy_string: str) -> bool
        # Parse proxy_string → host, port, username, password
        # POST /users/{userId}/proxy → Camofox
        # Return: success

    def get_proxy_for_account(account_id: int) -> Proxy
        # Return assigned proxy from DB
```

### 6.2 AccountService

```python
class AccountService:
    def login(account_id: int, force: bool = False) -> tuple[bool, str]
        # 1. Get account + proxy from DB
        # 2. Push proxy to Camofox: push_proxy_to_camofox("s_{id}", proxy_string)
        # 3. Create Camofox tab with userId="s_{id}"
        # 4. Navigate to old.reddit.com/login
        # 5. Check "already logged in" dialog
        # 6. If not logged in: fill credentials, click login
        # 7. Save session (Camofox persistence handles this)
        # 8. Update account status

    def resume_session(account_id: int) -> bool
        # 1. Push proxy to Camofox
        # 2. Create tab with userId="s_{id}"
        # 3. Camofox loads existing cookies from disk
        # 4. Return: tab created successfully

    def check_session_valid(account_id: int) -> bool
        # Create temp tab, check if logged in, close tab

    def get_account(account_id: int) -> Account
    def list_accounts(filters: dict) -> list[Account]
    def delete_account(account_id: int) -> bool
```

### 6.3 RateLimiter

```python
class RateLimiter:
    def check(account: Account) -> tuple[bool, str]
        # Check votes_today < max_votes_per_day
        # Check votes_this_week < max_votes_per_week
        # Check seconds_since_last_vote >= min_seconds_between_votes
        # Check within active hours (7-23)
        # Return: (allowed, reason_if_blocked)

    def record_vote(account: Account) -> None
        # Increment votes_today, votes_this_week, total_votes
        # Update last_vote_at
        # Reset counters at midnight/week boundaries
```

### 6.4 BurnDetector

```python
class BurnDetector:
    def record_result(account: Account, success: bool, error: str, http_status: int)
        # If success: reset consecutive_failures
        # If failure: increment consecutive_failures
        # If consecutive_failures >= 5: mark dead
        # If 401/403: mark banned
        # If 429: mark rate_limited, backoff

    def check_success_rate(account: Account) -> float
        # Return success rate over last 7 days

    def mark_if_dead(account: Account) -> bool
        # If fail_count >= 10: mark dead
        # If success_rate < 0.8: mark dead
```

### 6.5 SlotManager

```python
class SlotManager:
    # Note: For now, we use ONE Camofox instance
    # This manages the connection and health checking

    def get_slot_stats() -> dict
        # Return: {total, running, stopped, max_concurrent, total_capacity}
```

---

## 7. Voting Flow

### 7.1 Upvote Action

```
POST /api/actions/upvote
{
  "account_ids": [1, 2, 3],
  "target_url": "https://old.reddit.com/r/.../comments/xxx/title/"
}

↓

For each account (async, concurrent):
  1. Check rate limit (RateLimiter.check)
  2. Check session valid (or re-login)
  3. Push proxy to Camofox
  4. Create tab (userId="s_{account_id}")
  5. Navigate to target_url
  6. Scroll to find upvote button
  7. Click upvote
  8. Close tab
  9. Record vote (RateLimiter.record_vote)
  10. Record result (BurnDetector.record_result)
```

### 7.2 Per-Account Timing

```
Vote happens at T+0
Tab stays open T+0 to T+120 (2 min cooldown)
Close tab at T+120
Next vote on same account: earliest T+120
```

During the 2-min window, account is "busy" (tab open). Other accounts can still vote concurrently up to MAX_SESSIONS limit.

---

## 8. Import Workflows

### 8.1 Separate Imports (Auto-assign by Index)

```
Step 1: POST /api/accounts/import
  CSV:
    username,password
    alice,pass123
    bob,pass456
    charlie,pass789
  → Creates 3 accounts (fresh)

Step 2: POST /api/proxies/import
  CSV:
    proxy_string
    http://user:pass_session-A@gateway:1000
    http://user:pass_session-B@gateway:1000
    http://user:pass_session-C@gateway:1000
  → Creates 3 proxies (unassigned)

Step 3: POST /api/proxies/assign
  → Auto-assigns: proxy[1]→account[1], proxy[2]→account[2], etc.
```

### 8.2 Combined Import (One-step)

```
POST /api/accounts/import
CSV:
  username,password,proxy_string,email
  alice,pass123,http://user:pass_session-A@gateway:1000
  bob,pass456,http://user:pass_session-B@gateway:1000
  charlie,pass789,http://user:pass_session-C@gateway:1000
→ Creates accounts + proxies + assigns 1:1 in one step
```

---

## 9. File Structure

```
reddit-api/
├── config/
│   ├── default.yaml
│   └── custom.yaml
│
├── camofox/                           # Forked/Patched Camofox
│   └── plugins/
│       └── sticky-proxy/
│           └── index.js
│
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   │
│   ├── models/
│   │   └── __init__.py
│   │
│   ├── schemas/
│   │   ├── account.py
│   │   ├── action.py
│   │   ├── proxy.py
│   │   └── common.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── config_service.py
│   │   ├── proxy_service.py
│   │   ├── account_service.py
│   │   ├── actions.py
│   │   ├── rate_limiter.py
│   │   ├── burn_detector.py
│   │   ├── slot_manager.py
│   │   └── sticky_proxy.py        # Push proxy to Camofox
│   │
│   ├── api/
│   │   ├── accounts.py
│   │   ├── actions.py
│   │   ├── proxies.py
│   │   └── admin.py
│   │
│   └── gui.py
│
├── data/
│   ├── reddit.db
│   ├── sessions/
│   └── logs/
│
└── requirements.txt
```

---

## 10. Implementation Order

### Phase 1: Foundation
1. Fork/clone Camofox browser
2. Create `sticky-proxy` plugin
3. Test plugin manually

### Phase 2: Database & Config
4. Update database models
5. Create ConfigService for YAML loading

### Phase 3: Core Services
6. ProxyService (import, assign, push to Camofox)
7. StickyProxy Python client (push proxy to Camofox)
8. AccountService (login, session resume)
9. RateLimiter + BurnDetector

### Phase 4: Actions
10. Action flow (upvote/downvote with session management)
11. API endpoints

### Phase 5: GUI
12. Update dashboard

---

## 11. Questions & Decisions

| Question | Decision |
|----------|----------|
| Camofox session naming | `s_{account_id}` (decoupled from username) |
| Proxy storage | DB is source of truth; Camofox holds in-memory only |
| Proxy persistence | Proxy pushed to Camofox on every action (survives restart) |
| Concurrent votes | Hardware-limited (RAM/CPU) |
| Vote cooldown | 2 min tab-open, then close |
| On ban | Status → `banned` |
| Account type | Removed (all accounts can do all actions) |
| Total votes | Added (`total_votes` cumulative counter) |
| Import: accounts | CSV: `username,password` |
| Import: proxies | CSV: `proxy_string` |
| Import: combined | CSV: `username,password,proxy_string,email` |
| Proxy assign | Auto 1:1 by import order |

---

## 12. Detection Avoidance Summary

| Technique | Value |
|----------|-------|
| Max votes/day | 15 |
| Min between votes | 120s |
| Jitter sigma | 120s |
| Skip chance | 8% |
| Clump chance | 15% |
| S-curve distribution | 30% first 30min, 45% in 2h, 20% in 4h, 5% tail |
| Session naming | `s_{id}` (no username in Camofox) |
| Per-account proxy | 1:1 Evomi hardsession |
| Tab cooldown | 2 min open after vote |
