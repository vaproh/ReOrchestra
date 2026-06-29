# ReOrchestra — Product Requirements Document

## 1. Product Overview

**ReOrchestra** is a white-label bulk Reddit account automation tool that enables customers to manage 500-1000 Reddit accounts reliably on a single VPS.

> *"Your Accounts, In Harmony"*

**Core value proposition:** Take the pain of managing hundreds of Reddit accounts — login, proxy rotation, rate limiting, ban detection — and abstract it behind a simple queue-based API.

---

## 2. Target Customer

**Primary:** Direct customers who pay the operator directly (no public marketplace).

| Customer Type | Use Case |
|--------------|----------|
| **Social media managers** | Bulk engagement for clients |
| **SEO agencies** | Manipulate post visibility |
| **Content creators / OnlyFans** | Build karma to promote content |
| **Reputation managers** | Suppress negative content |
| **Political campaigns** | Astroturfing (acknowledged risk) |

**Not target:** Public SaaS marketplace. Direct relationships only.

---

## 3. Business Model

### Subscription Tiers

| Tier | Accounts | Price Point |
|------|----------|-------------|
| **Basic** | Up to 50 | ~$50/mo |
| **Pro** | Up to 200 | ~$150/mo |
| **Business** | Up to 500 | ~$300/mo |
| **Enterprise** | Unlimited (sell as "unlimited", actual ~1000) | ~$500/mo |

**Note:** Single VPS can handle ~500-1000 accounts. Enterprise tier sells as "unlimited" to commercial users who don't probe the limit.

### Unit Economics (Operator View)

| Cost | Amount |
|------|--------|
| VPS (Hetzner CX22) | $3.20/mo |
| Residential proxies | $1/GB (shared pool) |
| **Total per 500 accounts** | ~$10-20/mo |

**Margin:** ~95%+ at 500 accounts, $300/mo revenue.

---

## 4. What ReOrchestra Does

### Core Features

1. **Account Management**
   - Import Reddit accounts (username + password + proxy)
   - Login via Camofox stealth browser
   - Track account health (active/paused/dead)
   - Automatic session renewal

2. **Queue-Based Action Execution**
   - Submit tasks: `{action_type, target_url, workers_needed}`
   - Background processor handles FIFO queue
   - Automatic retries (3x with exponential backoff)
   - Deduplication prevents double-execution

3. **9 Supported Actions**
   - Voting: upvote_post, downvote_post, upvote_comment, downvote_comment
   - Social: follow_user, unfollow_user
   - Community: join_subreddit, leave_subreddit
   - Content: save_post

4. **Detection Avoidance**
   - Per-account rate limiting (15 votes/day, 100/week)
   - S-curve timing with jitter
   - Proxy injection per session (sticky-proxy)
   - Camofox fingerprint spoofing

5. **Account Health Intelligence**
   - Burn detection (5 consecutive failures → dead)
   - Success rate monitoring
   - Automatic pause on suspension
   - Dead marking on banned

---

## 5. Technical Architecture

### Stack

| Component | Technology |
|-----------|------------|
| API | FastAPI + Uvicorn |
| Database | SQLite + SQLAlchemy 2.x |
| Browser | Camofox (headless Firefox with C++ anti-detection) |
| Deployment | Single VPS (Hetzner CX22) |
| Sessions | Camofox persistence plugin |
| Proxy | Per-account via sticky-proxy plugin |

### Design Philosophy

- **Niche tool, not enterprise** — no over-engineering
- **Reliable, not instant** — actions queue and process in background
- **Single VPS** — no Redis, no horizontal scaling
- **Direct customers** — no API key auth (internal use only)

### Constraints

- Single Camofox instance (port 9377)
- Max ~1000 accounts per VPS (memory/proxy pool constraint)
- SQLite single-writer (sufficient for this scale)
- No public marketplace (direct relationships only)

---

## 6. User Workflow

```
1. IMPORT ACCOUNTS
   → Customer provides: username, password, proxy
   → POST /api/accounts/import

2. LOGIN ACCOUNTS
   → Camofox automation logs in, saves cookies
   → POST /api/accounts/login

3. CREATE WORKERS
   → Workers bound to accounts, status = idle
   → POST /api/workers/bulk

4. CREATE TASK
   → Specify action + target URL + number of workers
   → POST /api/tasks
   {
     "action_type": "upvote_post",
     "target_url": "https://www.reddit.com/r/...",
     "workers_needed": 50
   }

5. MONITOR
   → GET /api/tasks/{id}
   → Task status: queued → running → completed | partial | failed
```

---

## 7. Anti-Detection Strategy

### Rate Limiting

```yaml
rate_limits:
  max_votes_per_day: 15
  max_votes_per_week: 100
  min_seconds_between_votes: 120
  max_vote_only_ratio: 0.3
```

### Timing Entropy

```yaml
timing:
  jitter_sigma: 120        # Gaussian jitter (seconds)
  skip_cycle_chance: 0.08   # 8% skip chance
  clump_chance: 0.15        # 15% clump chance
  micro_jitter_min_ms: 100
  micro_jitter_max_ms: 900
```

### Burn Detection

```yaml
burn_detection:
  consecutive_failures_threshold: 5
  success_rate_window_days: 7
  min_success_rate: 0.80
  cooldown_hours: 24
```

---

## 8. Key Decisions

| Decision | Rationale |
|----------|-----------|
| **SQLite over PostgreSQL** | Single VPS, ~1000 accounts, no horizontal scaling needed |
| **Camofox over Playwright** | C++-level fingerprint spoofing, better anti-detection |
| **FIFO + priority queue** | Simple, predictable ordering |
| **3 retries, exponential backoff** | Balance between success rate and queue depth |
| **Dedup by worker+action+target** | Prevents same worker doing same action twice |
| **Popup detection AFTER vote** | Popup only appears after attempting the action |
| **Banner detection BEFORE non-vote** | Banner is visible before attempting the action |

---

## 9. What Success Looks Like

- Queue processes 500+ accounts reliably
- Accounts survive weeks/months without burning
- Minimal manual intervention (pause dead accounts)
- Task success rate > 90%
- Single VPS handles all load
- Customer pays monthly subscription, gets results

---

## 10. Out of Scope

- Redis / horizontal scaling
- Prometheus metrics
- WebSocket real-time updates
- Encrypted credentials
- API authentication (direct customers only)
- Account creation (customers bring their own)
- Public marketplace / multi-tenant SaaS
- Payment processing (direct PayPal/crypto)

---

## 11. Roadmap

### Phase 1: Critical Fixes
- [x] Proxy injection in login
- [x] Parallel worker execution
- [x] DB session lifecycle fix
- [x] RateLimiter integration

### Phase 2: Reliability
- [ ] Dead letter queue
- [ ] Graceful shutdown
- [ ] Cancellation tokens

### Phase 3: Dashboard
- [ ] Better UX for 500+ accounts
- [ ] Real-time worker activity
- [ ] Dead letter queue view

### Phase 4: Cleanup
- [ ] Remove legacy action system
- [ ] Fix technical debt
- [ ] Unit tests
