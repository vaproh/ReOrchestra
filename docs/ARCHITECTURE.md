# Reddit Automation API - Architecture Document

## Overview

A scalable Reddit account management and karma farming system. Built with FastAPI, Camofox browser automation, and SQLite. Designed to handle 5 to 1,000 accounts on a single host with anti-detection measures.

---

## 1. System Architecture

### 1.1 High-Level Design

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FastAPI Server                                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      API Layer                                     │   │
│  │  /api/accounts/*  │  /api/actions/*  │  /api/proxies/*  │ admin│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Service Layer                                  │   │
│  │  AccountService  │  ActionService  │  ProxyService  │ SlotManager│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │               Detection Avoidance Layer                          │   │
│  │  RateLimiter  │  TimingService  │  S-curve  │  BurnDetector  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                  Camofox Slot Pool                                │   │
│  │  Slot 0 (Port 9377)  │  Slot 1 (Port 9378)  │  ...          │   │
│  │  Max 10 concurrent per slot, configurable concurrent limit       │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
         │
         │                    │                    │
┌────────▼────┐      ┌──────▼──────┐      ┌─────▼─────┐
│   SQLite     │      │  Raw HTTP   │      │  Camofox  │
│   Database   │      │  (Reddit)  │      │  Browser  │
└─────────────┘      └─────────────┘      └───────────┘
```

### 1.2 Request Flow

```
Client Request
      │
      ▼
┌─────────────────────┐
│   API Endpoint       │ ← Validates input
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Service Layer      │ ← Business logic
└──────────┬──────────┘
           │
     ┌─────┴─────┐
     │            │
     ▼            ▼
┌─────────┐  ┌──────────────┐
│ Rate     │  │ Timing       │ ← Check limits, calculate delays
│ Limiter  │  │ Service     │
└────┬────┘  └──────┬───────┘
     │               │
     └───────┬───────┘
             │
             ▼
┌─────────────────────┐
│  SlotManager         │ ← Acquire semaphore (max concurrent)
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  ActionService       │ ← HTTP upvote/downvote
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  BurnDetector       │ ← Detect bans/rate limits
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Response           │
└─────────────────────┘
```

---

## 2. Configuration System

### 2.1 Config Files

| File | Purpose | Gitignored |
|------|---------|------------|
| `config/default.yaml` | All defaults | No |
| `config/custom.yaml` | User overrides | **Yes** |
| `config/profiles.json` | Browser fingerprint profiles | No |

### 2.2 Config Loading Priority (Highest to Lowest)

1. Runtime API overrides (`/api/admin/config`)
2. `config/custom.yaml`
3. `config/default.yaml`

### 2.3 Default Configuration (`config/default.yaml`)

```yaml
# Reddit Automation API - Default Configuration

app:
  name: "Reddit Automation API"
  version: "1.0.0"

# Rate limiting per account
rate_limits:
  max_votes_per_day: 15          # Safe zone 10-20
  max_votes_per_week: 100       # ~15/day * 7
  min_seconds_between_votes: 120  # 2 minutes minimum
  max_vote_only_ratio: 0.3      # 30% max pure votes, rest browsing

# Concurrent operation control
concurrency:
  max_concurrent_per_slot: 10   # Max operations per Camofox slot
  slots_auto_scale: true          # Auto-create slots based on account count
  accounts_per_slot: 50           # Target accounts per slot

# Timing and entropy for detection avoidance
timing:
  jitter_sigma: 120             # Gaussian jitter std dev in seconds
  skip_cycle_chance: 0.08       # 8% chance to skip a vote
  clump_chance: 0.15           # 15% chance to vote sooner
  micro_jitter_min_ms: 100      # Network-level noise
  micro_jitter_max_ms: 900

# S-curve upvote distribution (research-backed)
s_curve:
  enabled: true
  initial_burst: 0.30          # 30% in first 30 minutes
  peak: 0.45                    # 45% in 30min-2h
  decay: 0.20                   # 20% in 2-4h
  tail: 0.05                    # 5% after 4h

# Account activation staggering
activation:
  batch_size: 50               # Max accounts to activate per batch
  spread_days: 3                # Spread activation over N days

# Burn detection and recovery
burn_detection:
  consecutive_failures: 5       # Mark dead after N consecutive failures
  rate_limit_backoff_hours: 24 # Backoff time after 429
  success_rate_threshold: 0.8   # Mark dead if success rate < 80%

# Session settings
session:
  max_age_hours: 72           # Re-login after 72 hours
  refresh_before_hours: 12      # Refresh sessions 12 hours before expiry

# Account status thresholds
account_limits:
  max_fail_count: 10           # Mark dead after 10 total failures
  dead_after_ban: true          # Auto-mark banned accounts as dead

# Logging
logging:
  level: "INFO"
  file: "data/logs/app.log"
  max_bytes: 10485760           # 10MB
  backup_count: 5
```

### 2.4 Proxy Configuration (`config/proxies.yaml`)

```yaml
# Proxy settings
proxy:
  # Evomi configuration (auto-session generation)
  evomi:
    enabled: true
    host: ""                    # e.g., core-residential.evomi.com
    port: 1000
    username: ""
    password: ""

  # Bulk import format options
  bulk:
    enabled: true
    format: "host:port:username:password"  # or "http://user:pass@host:port"

  # Session parameters (Evomi)
  session:
    type: "session"           # or "hardsession"
    lifetime_minutes: 40       # Max 120, default 40

  # Proxy assignment
  assignment:
    sticky: true               # One proxy per account, never reassign
```

### 2.5 Browser Profiles (`config/profiles.json`)

```json
{
  "profiles": [
    {
      "id": "win10-in",
      "name": "Windows 10 — India",
      "os": "Windows 10",
      "timezone": "Asia/Kolkata",
      "locale": "en-IN",
      "gpu": "Intel HD Graphics 630",
      "viewport": {"width": 1366, "height": 768},
      "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
      "proxyRegion": "IN",
      "colorDepth": 24,
      "deviceMemory": 8,
      "hardwareConcurrency": 4
    }
  ]
}
```

---

## 3. Database Models

### 3.1 Account

```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(20) UNIQUE NOT NULL,
    password VARCHAR(128) NOT NULL,

    -- Email (for verification)
    email VARCHAR(128),
    email_password VARCHAR(128),
    email_verified BOOLEAN DEFAULT FALSE,

    -- Status
    status VARCHAR(20) DEFAULT 'fresh',
    -- 'fresh', 'logged_in', 'session_expired', 'banned', 'dead'

    account_type VARCHAR(20) DEFAULT 'upvoter',
    -- 'upvoter', 'main', 'both'

    -- Proxy and profile assignment
    proxy_id INTEGER REFERENCES proxies(id),
    profile_id VARCHAR(32),

    -- Karma
    karma_total INTEGER DEFAULT 0,
    karma_post INTEGER DEFAULT 0,
    karma_comment INTEGER DEFAULT 0,

    -- Voting statistics
    votes_today INTEGER DEFAULT 0,
    votes_this_week INTEGER DEFAULT 0,
    last_vote_at TIMESTAMP,

    -- Active hours (randomized on import)
    active_hours_start INTEGER DEFAULT 7,  -- e.g., 7 AM
    active_hours_end INTEGER DEFAULT 23,    -- e.g., 11 PM

    -- Session info
    cookies TEXT,                          -- JSON blob
    csrf_token VARCHAR(128),
    session_valid BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,

    -- Failure tracking
    fail_count INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    last_failure_at TIMESTAMP,

    -- Timestamps
    last_used TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_status (status),
    INDEX idx_account_type (account_type),
    INDEX idx_proxy (proxy_id)
);
```

### 3.2 Proxy

```sql
CREATE TABLE proxies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    proxy_string TEXT NOT NULL,
    -- Full URL: http://user:pass@host:port_session-XXX

    proxy_type VARCHAR(20) DEFAULT 'bulk',
    -- 'evomi', 'bulk'

    -- Metadata
    provider VARCHAR(50),
    country VARCHAR(10),
    region VARCHAR(50),

    -- Assignment
    assigned_account_id INTEGER REFERENCES accounts(id),
    session_id VARCHAR(32),  -- Evomi session ID

    -- Status
    status VARCHAR(20) DEFAULT 'active',
    -- 'active', 'dead'

    -- Health
    fail_count INTEGER DEFAULT 0,
    last_used TIMESTAMP,
    last_error TEXT,

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_status (status),
    INDEX idx_assigned (assigned_account_id)
);
```

### 3.3 Action Log

```sql
CREATE TABLE action_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL REFERENCES accounts(id),

    action_type VARCHAR(20) NOT NULL,
    -- 'upvote', 'downvote', 'comment', 'post', 'login', etc.

    target_id VARCHAR(64),           -- t3_xxx for posts
    target_url TEXT,

    -- Result
    success BOOLEAN NOT NULL,
    error TEXT,
    http_status INTEGER,

    -- Timing
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_ms INTEGER,

    -- Deduplication hash
    dedup_hash VARCHAR(64) UNIQUE,

    -- Indexes
    INDEX idx_account (account_id),
    INDEX idx_action_type (action_type),
    INDEX idx_target (target_id),
    INDEX idx_created (created_at),
    UNIQUE INDEX idx_dedup (dedup_hash)
);
```

### 3.4 Camofox Slot

```sql
CREATE TABLE camofox_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    port INTEGER UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'stopped',
    -- 'running', 'stopped', 'crashed', 'starting'

    max_concurrent INTEGER DEFAULT 10,
    current_load INTEGER DEFAULT 0,

    -- Process tracking
    process_id INTEGER,
    started_at TIMESTAMP,
    last_health_check TIMESTAMP,

    -- Resource usage
    memory_mb INTEGER,
    cpu_percent REAL,

    -- Indexes
    INDEX idx_status (status)
);
```

### 3.5 Config

```sql
CREATE TABLE config (
    key VARCHAR(64) PRIMARY KEY,
    value TEXT,                    -- JSON-encoded
    source VARCHAR(20) DEFAULT 'runtime',
    -- 'default', 'custom', 'runtime'

    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. Services

### 4.1 Service Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Services                                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ConfigService          │ Load/merge YAML + runtime config  │
│                          │                                │
│  ProxyService           │ Evomi session gen │ Bulk import │
│                          │ Sticky proxy assignment         │
│                                                              │
│  AccountService         │ CRUD │ Import │ Login orchestration│
│                                                              │
│  SlotManager            │ Spawn Camofox │ Semaphore control │
│                          │ Health monitoring │ Auto-recovery │
│                                                              │
│  RateLimiter            │ Per-account counting │ Day/week │
│                          │ Cooldown enforcement │ Active hours│
│                                                              │
│  TimingService          │ S-curve calculation │ Gaussian │
│                          │ jitter │ Micro-delay │ Skip/clump │
│                                                              │
│  ActionService          │ HTTP upvote/downvote │ Cookie │
│                          │ management │ Response handling   │
│                                                              │
│  BurnDetector           │ 401/403/429 detection │ Mark │
│                          │ dead │ Notify │ Recovery          │
│                                                              │
│  SessionManager         │ Cookie persistence │ Refresh │
│                          │ Validation │ Expiry tracking     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 ProxyService

**Responsibilities:**
- Generate Evomi proxy URLs with sticky session IDs
- Parse bulk import proxy formats
- Maintain sticky proxy→account assignments

**Evomi Session Format:**
```
http://host:port:username:password_session-{SESSION_ID}_lifetime-{MIN}@host:port
```

**Methods:**
```python
class ProxyService:
    def generate_evomi_session(self) -> str
        # Generate random 6-10 char session ID
        # Return full proxy URL with session

    def parse_bulk_proxy(self, proxy_str: str) -> dict
        # Parse host:port:user:pass or http://user:pass@host:port

    def assign_proxy(self, account_id: int, proxy_type: str) -> Proxy
        # Create proxy record, generate session for Evomi
        # Mark as assigned to account

    def get_proxy_for_account(self, account_id: int) -> Proxy
        # Return assigned proxy, generate new session if needed
```

### 4.3 SlotManager

**Responsibilities:**
- Manage Camofox instances across ports
- Enforce concurrent operation limits
- Health monitoring and auto-restart

**Concurrency Control:**
```python
class SlotManager:
    def __init__(self, max_per_slot: int = 10):
        self.slots: dict[int, CamofoxSlot]
        self.semaphores: dict[int, asyncio.Semaphore]

    async def acquire(self, slot_id: int) -> asyncio.Semaphore:
        # Wait for available slot
        await self.semaphores[slot_id].acquire()

    async def release(self, slot_id: int):
        # Release semaphore
        self.semaphores[slot_id].release()

    def get_slot_for_account(self, account_id: int) -> int:
        # Round-robin or consistent hashing
        return account_id % len(self.slots)
```

**Health Monitoring:**
```python
async def health_check_loop():
    while True:
        for slot in active_slots:
            try:
                resp = requests.get(f"http://localhost:{slot.port}/health")
                slot.update(status="running", memory=resp["memory"]["rssMb"])
            except:
                slot.update(status="crashed")
                restart_slot(slot)
```

### 4.4 RateLimiter

**Responsibilities:**
- Track votes per account per day/week
- Enforce minimum time between votes
- Check active hours
- Maintain vote-only ratio

**Logic:**
```python
class RateLimiter:
    def check(self, account: Account) -> tuple[bool, str]:
        """
        Returns (allowed, reason_if_blocked)
        """
        # 1. Check votes_today < max_votes_per_day
        if account.votes_today >= config.max_votes_per_day:
            return False, "daily_limit_reached"

        # 2. Check votes_this_week < max_votes_per_week
        if account.votes_this_week >= config.max_votes_per_week:
            return False, "weekly_limit_reached"

        # 3. Check seconds_since_last_vote >= min_seconds_between_votes
        if account.seconds_since_last_vote < config.min_seconds_between_votes:
            return False, "cooldown_active"

        # 4. Check within active hours
        if not self.is_within_active_hours(account):
            return False, "outside_active_hours"

        # 5. Check vote_only_ratio
        if self.get_vote_ratio(account) > config.max_vote_only_ratio:
            return False, "vote_only_ratio_exceeded"

        return True, ""

    def record_vote(self, account_id: int):
        # Increment votes_today, votes_this_week
        # Reset at midnight/week boundaries
```

### 4.5 TimingService

**Responsibilities:**
- Calculate S-curve vote distribution
- Apply gaussian jitter
- Micro-jitter for network noise
- Skip/clump randomization

**S-Curve Timing:**
```python
class TimingService:
    def calculate_delay(self, account: Account, post_age_hours: float) -> float:
        """
        Returns delay in seconds until next vote
        based on S-curve distribution + entropy
        """
        # S-curve weight based on post age
        remaining = max(4 - post_age_hours, 0.25)
        s_curve_weight = self._sigmoid(remaining)

        # Gaussian jitter
        jitter = random.gauss(config.timing.jitter_sigma)

        # Micro-jitter
        micro = random.randint(
            config.timing.micro_jitter_min_ms,
            config.timing.micro_jitter_max_ms
        ) / 1000

        # Skip cycle (8% chance)
        if random.random() < config.timing.skip_cycle_chance:
            return self.calculate_delay(account, post_age_hours) * 2

        # Clump (15% chance - vote sooner)
        if random.random() < config.timing.clump_chance:
            return random.uniform(0.2, 0.5) * base_delay

        return max(0, s_curve_weight * base_delay + jitter + micro)

    def _sigmoid(self, x: float) -> float:
        steepness = 8 / max(x, 1)
        return 1 - (1 / (1 + math.exp(-steepness * (x - 0.3))))
```

### 4.6 ActionService

**Responsibilities:**
- Execute HTTP upvote/downvote
- Manage cookies and CSRF tokens
- Handle responses

**Vote Endpoint:**
```
POST https://www.reddit.com/api/vote
Content-Type: application/x-www-form-urlencoded
X-CSRF-Token: {csrf_token}

Body: id=t3_{post_id}&dir={direction}
# direction: 1 = upvote, -1 = downvote, 0 = unvote
```

**Response Handling:**
```python
class ActionService:
    async def upvote(self, account: Account, target_url: str) -> ActionResult:
        # 1. Load cookies from account
        cookies = json.loads(account.cookies)

        # 2. Make HTTP request
        session = requests.Session()
        session.cookies.update(cookies)
        resp = session.post(
            'https://www.reddit.com/api/vote',
            data={'id': extract_post_id(target_url), 'dir': '1'},
            headers={'X-CSRF-Token': account.csrf_token}
        )

        # 3. Handle response
        if resp.status_code == 200:
            return ActionResult(success=True)
        elif resp.status_code == 401:
            # Session expired
            await self._handle_session_expired(account)
            return ActionResult(success=False, error="session_expired")
        elif resp.status_code == 403:
            # Banned
            return ActionResult(success=False, error="banned")
        elif resp.status_code == 429:
            # Rate limited
            return ActionResult(success=False, error="rate_limited")
        else:
            return ActionResult(success=False, error=f"http_{resp.status_code}")
```

### 4.7 BurnDetector

**Responsibilities:**
- Detect account bans (401/403)
- Detect rate limits (429)
- Mark accounts as dead
- Trigger recovery workflows

**Logic:**
```python
class BurnDetector:
    def record_result(self, account_id: int, success: bool, error: str):
        account = db.get_account(account_id)

        if success:
            account.consecutive_failures = 0
        else:
            account.consecutive_failures += 1
            account.last_failure_at = now()

            # Check for ban
            if error in ("401", "403", "banned"):
                if account.consecutive_failures >= config.burn_detection.consecutive_failures:
                    account.status = "dead"
                    account.dead_reason = "ban"
                    log.warning(f"Account {account.username} marked dead: ban detected")

            # Check for rate limit
            elif error == "429":
                account.status = "rate_limited"
                log.warning(f"Account {account.username} rate limited")
                # Automatic backoff
                schedule_retry(account_id, config.burn_detection.rate_limit_backoff_hours)
```

---

## 5. API Endpoints

### 5.1 Account Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/accounts` | List accounts (paginated, filterable) |
| GET | `/api/accounts/{id}` | Get single account |
| POST | `/api/accounts/import` | Bulk import accounts |
| PATCH | `/api/accounts/{id}` | Update account |
| DELETE | `/api/accounts/{id}` | Delete account |
| POST | `/api/accounts/login` | Login account(s) |
| GET | `/api/accounts/{id}/session` | Check session validity |

### 5.2 Action Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/actions/upvote` | Upvote with accounts |
| POST | `/api/actions/downvote` | Downvote with accounts |

**Request Format:**
```json
{
  "account_ids": [1, 2, 3],
  "target_url": "https://www.reddit.com/r/sub/comments/xxx/title/",
  "random_order": true
}
```

### 5.3 Proxy Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/proxies` | List proxies |
| POST | `/api/proxies/import` | Import bulk proxies |
| POST | `/api/proxies/evomi-config` | Configure Evomi credentials |

### 5.4 Admin Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/health` | System health |
| GET | `/api/admin/stats` | Dashboard statistics |
| GET | `/api/admin/config` | Get current config |
| PUT | `/api/admin/config` | Update runtime config |
| POST | `/api/admin/slots/restart` | Restart Camofox slots |

---

## 6. Concurrency Model

### 6.1 Slot-Based Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 SlotManager                                  │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Slot 0    │  │  Slot 1    │  │  Slot N    │        │
│  │  Port 9377 │  │  Port 9378 │  │  Port 9377+N│        │
│  │  Sem(10)   │  │  Sem(10)   │  │  Sem(10)   │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         │                  │                  │                │
│         └──────────────────┼──────────────────┘                │
│                            │                                   │
│              Max concurrent operations =                         │
│              slots × max_per_slot = N × 10                    │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Semaphore Usage

```python
class ActionExecutor:
    def __init__(self, slot_manager: SlotManager):
        self.slots = slot_manager

    async def execute_vote(self, account_id: int, action: str):
        slot_id = self.slots.get_slot_for_account(account_id)

        async with self.slots.acquire(slot_id):
            # Execute the vote
            result = await self.action_service.vote(account, action)

            # Release automatically via context manager
```

### 6.3 Scaling Logic

```
Account Count → Slots → Concurrent Capacity

  1-50    →   1   →   10
 51-100   →   2   →   20
 101-150  →   3   →   30
  ...
```

---

## 7. Detection Avoidance Summary

### 7.1 Rate Limits (Per Account)

| Metric | Value |
|--------|-------|
| Max votes/day | 15 |
| Max votes/week | 100 |
| Min between votes | 120s |
| Max vote-only ratio | 30% |

### 7.2 Timing Entropy

| Technique | Purpose |
|-----------|---------|
| Gaussian jitter (σ=120s) | Avoid uniform intervals |
| S-curve distribution | Front-load upvotes, taper off |
| 8% skip chance | Random non-deterministic behavior |
| 15% clump chance | Simulate organic cluster discovery |
| Micro-jitter (100-900ms) | Network-level noise |

### 7.3 Active Hours

Accounts assigned randomized active hours (6-10 hour window) to avoid 24/7 bot pattern.

### 7.4 Staggered Activation

New accounts activated in batches of 50 over 3 days to avoid creation timing correlation.

---

## 8. File Structure

```
reddit-api/
├── config/
│   ├── default.yaml              # Default configuration
│   ├── custom.yaml              # User overrides (gitignored)
│   └── profiles.json            # Browser fingerprint profiles
│
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings loader
│   ├── database.py              # SQLAlchemy setup
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── account.py
│   │   ├── proxy.py
│   │   ├── action_log.py
│   │   ├── camofox_slot.py
│   │   └── config.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── account.py
│   │   ├── action.py
│   │   ├── proxy.py
│   │   └── common.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── config_service.py   # YAML config loading
│   │   ├── proxy_service.py    # Proxy management
│   │   ├── account_service.py  # Account CRUD
│   │   ├── action_service.py   # Vote execution
│   │   ├── slot_manager.py    # Camofox slots
│   │   ├── rate_limiter.py   # Per-account rate limits
│   │   ├── timing_service.py  # S-curve + entropy
│   │   ├── burn_detector.py  # Ban/rate limit detection
│   │   └── session_manager.py # Cookie management
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── accounts.py
│   │   ├── actions.py
│   │   ├── proxies.py
│   │   └── admin.py
│   │
│   └── gui.py                 # Dashboard (existing, update only)
│
├── data/
│   ├── reddit.db              # SQLite database
│   ├── sessions/              # Cookie persistence
│   └── logs/                  # Application logs
│
├── requirements.txt
├── setup_camofox.sh           # Camofox setup script
└── README.md
```

---

## 9. Implementation Priorities

### Phase 1: Foundation
1. Config system (YAML loading, runtime overrides)
2. Database models
3. ProxyService (Evomi + Bulk)
4. SlotManager (Camofox slot management)

### Phase 2: Core Account Flow
5. AccountService (import, CRUD)
6. SessionManager (cookie persistence)
7. Login orchestration

### Phase 3: Voting with Protection
8. RateLimiter (per-account limits)
9. TimingService (S-curve + entropy)
10. ActionService (HTTP upvote/downvote)
11. BurnDetector (ban/rate limit handling)

### Phase 4: API & Dashboard
12. API endpoints
13. GUI updates (existing file only)

---

## 10. Testing Plan

### Unit Tests
- RateLimiter logic
- TimingService entropy calculations
- ProxyService parsing
- Config loading/merging

### Integration Tests
- Vote flow with mock HTTP
- SlotManager semaphore behavior
- BurnDetector state transitions

### E2E Tests
- Full upvote with real Reddit (after validation)
- Account import → login → vote flow
- Concurrent vote stress test
