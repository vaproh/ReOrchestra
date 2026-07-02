# ReOrchestra — Product Requirements Document

## 1. Product Overview

**ReOrchestra** is a bulk Reddit account automation tool that enables customers to manage 500-1000 Reddit accounts reliably on a single VPS.

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

**Note:** Single VPS can handle ~500-1000 accounts.

### Unit Economics

| Cost | Amount |
|------|--------|
| VPS (Hetzner CX22) | $3.20/mo |
| Residential proxies | $1/GB |
| **Total per 500 accounts** | ~$10-20/mo |

**Margin:** ~95%+ at 500 accounts.

---

## 4. What ReOrchestra Does

### Core Features

1. **Account Management**
   - Import Reddit accounts (username + password + proxy)
   - Login via Camofox stealth browser
   - Track account health (active/dead/banned)
   - Automatic session renewal

2. **Queue-Based Action Execution**
   - Submit tasks: `{action_type, target_url, workers_needed}`
   - Background processor handles FIFO queue
   - Automatic retries (3x with exponential backoff)
   - Deduplication prevents double-execution
   - Failed accounts replaced automatically

3. **9 Supported Actions**
   - Voting: upvote_post, downvote_post, upvote_comment, downvote_comment
   - Social: follow_user, unfollow_user
   - Community: join_subreddit, leave_subreddit
   - Content: save_post

4. **Detection Avoidance**
   - Per-account rate limiting (15 votes/day, 100/week)
   - S-curve timing with jitter
   - Proxy injection per session
   - Camofox fingerprint spoofing

5. **Account Health Intelligence**
   - Burn detection (consecutive failures → dead)
   - Success rate monitoring
   - Automatic mark on suspension/banned

---

## 5. Technical Architecture

### Stack

| Component | Technology |
|-----------|------------|
| API | FastAPI + Uvicorn |
| Database | SQLite + SQLAlchemy 2.x |
| Browser | Camofox (headless Firefox) |
| Deployment | Single VPS |
| Sessions | Camofox persistence plugin |
| Proxy | Per-account via sticky-proxy |

### Design Philosophy

- **Simple, not enterprise** — no over-engineering
- **Reliable, not instant** — queue processes in background
- **Single VPS** — no Redis, no horizontal scaling
- **Direct customers** — no API key auth

### Constraints

- Single Camofox instance (port 9377)
- Max ~1000 accounts per VPS
- SQLite single-writer

---

## 6. Queue System Design

### How It Works

```
USER: "upvote this post with 100 accounts"

SYSTEM:
  1. Create task: { action: "upvote_post", url: "...", workers_needed: 100 }
  2. Pick 100 idle accounts (that haven't already upvoted this)
  3. Execute concurrently (max 3 at a time)
  4. If account fails (ban/suspend):
     - Mark account dead/banned
     - Assign NEW account to replace it
  5. If rate limit/retryable: retry 3 times
  6. Continue until workers_needed satisfied or no accounts left
```

### Core Behaviors

1. **Task Creation** — saved to DB with status `queued`
2. **Account Selection** — idle accounts that haven't done this action
3. **Concurrent Execution** — max 3 at a time (configurable)
4. **Auto-Replacement** — ban/suspend → mark dead, assign new account
5. **Retry with Backoff** — 3 retries for retryable errors
6. **Deduplication** — SHA256 of `{account_id}:{action_type}:{target_url}`

### Error Handling

| Error | Action |
|-------|--------|
| `popup_suspended` | Mark `dead`, replace account |
| `popup_rate_limited` | Mark `rate_limited`, replace account |
| `header_banned` | Mark `dead`, replace account |
| `header_suspended` | Mark `dead`, replace account |
| `click_timeout` | Retry 3x |
| `element_not_found` | Retry 3x |

### Account Status Flow

```
fresh → logged_in → session_expired → dead
              ↓
        rate_limited (temp)
              ↓
        logged_in (after cooldown)
```

### Task States

```
queued → running → completed | partial | failed | cancelled
```

---

## 7. User Workflow

```
1. IMPORT ACCOUNTS
   → POST /api/accounts/import
   { accounts: [{ username, password, proxy }] }

2. LOGIN ACCOUNTS
   → POST /api/accounts/login
   { account_ids: [1,2,3] }

3. CREATE TASK
   → POST /api/tasks
   {
     "action_type": "upvote_post",
     "target_url": "https://old.reddit.com/r/...",
     "workers_needed": 50
   }

4. MONITOR
   → GET /api/tasks/{id}
   → Status: queued → running → completed | partial | failed
```

---

## 8. Anti-Detection

### Rate Limits (per account)

```yaml
max_votes_per_day: 15
max_votes_per_week: 100
min_seconds_between_votes: 120
max_vote_only_ratio: 0.3
```

### Timing

```yaml
jitter_sigma: 120        # Gaussian jitter (seconds)
skip_cycle_chance: 0.08  # 8% skip chance
clump_chance: 0.15       # 15% clump chance
```

### Burn Detection

```yaml
consecutive_failures_threshold: 5
success_rate_window_days: 7
min_success_rate: 0.80
cooldown_hours: 24
```

---

## 9. Key Decisions

| Decision | Rationale |
|----------|-----------|
| SQLite | Single VPS, ~1000 accounts, no scaling needed |
| Camofox | C++-level fingerprint spoofing |
| Task-based queue | Simple: accounts ARE the workers |
| 3 retries | Balance success rate vs queue depth |
| Dedup by account+action+target | Prevents duplicate work |
| Popup AFTER vote | Popup only appears after click |
| Banner BEFORE non-vote | Banner shows before action |

---

## 10. What Success Looks Like

- Queue processes 500+ accounts reliably
- Accounts survive weeks/months without burning
- Minimal manual intervention
- Task success rate > 90%
- Single VPS handles all load

---

## 11. Out of Scope

- Redis / horizontal scaling
- WebSocket real-time updates
- Encrypted credentials
- API authentication
- Account creation (customers bring their own)
- Public marketplace
- Payment processing

---

## 12. Roadmap

### Phase 1: Foundation
- [x] Account import/login
- [x] Queue processor
- [x] 9 actions
- [x] Rate limiting

### Phase 2: Reliability
- [ ] Graceful shutdown
- [ ] True cancellation (stop in-flight)
- [ ] Session health monitoring

### Phase 3: Frontend
- [ ] HTMX + Jinja2 dashboard
- [ ] Real-time task progress
- [ ] Account management UI
