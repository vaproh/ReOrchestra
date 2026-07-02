# ReOrchestra Queue System Design

The queue system in ReOrchestra manages bulk Reddit account operations reliably on a single VPS. It transitions the architecture from a complex, worker-pool-based system to a simpler, task-based queue.

## Key Design Principles

1. **Task-based Execution**: Tasks are the unit of execution. Instead of mapping accounts to dedicated worker actors, accounts *are* the workers.
2. **Accounts as Workers**: No dedicated `Worker` DB model is required. Accounts in `logged_in` status are selected dynamically to process tasks.
3. **Concurrency Control**: A configurable concurrency limit (default: 3 concurrent actions) is enforced globally by the queue processor to avoid CPU/memory spike and proxy overload on a single VPS.
4. **Auto-Replacement**: When an account fails because it is banned, suspended, or rate-limited, the system automatically marks its status accordingly and assigns a new idle account to fill the slot.

---

## Architecture Diagram

```
Request ──▶ FastAPI Route
               │
               ▼
       Task Created (DB)
               │
               ▼
     QueueProcessor Loop
      ┌────────┴────────┐
      ▼ (Concurrently, max 3)
   Account Executor
      │
      ▼
   Camofox Client ──▶ Reddit (headless automation)
```

---

## Queue Processor Lifecycle

The `QueueProcessor` runs as a background loop:

1. **Task Retrieval**: The processor queries the database for the next available task (ordered by `priority DESC, created_at ASC`).
2. **Account Selection**: The processor looks for active, idle accounts that:
   - Have a status of `logged_in`.
   - Are not currently processing any action.
   - Have not already executed this action successfully on the target URL (deduplication check).
3. **Concurrent Execution**:
   - Up to 3 accounts execute actions concurrently.
   - Each action runs inside a tab on the Camofox browser.
4. **Failure & Reassignment Handling**:
   - If an account encounters a terminal error (e.g., banned/suspended), it is marked `dead` or `banned`, and a *new* account is queried and assigned to execute the action.
   - If an account encounters a rate limit popup or error, it is marked `rate_limited`, and a *new* account is assigned to replace it.
   - If an action fails with a temporary network error, it retries up to $N$ times (default 3) before counting as a failed slot attempt.
5. **Completion**:
   - The loop continues until `workers_completed` equals `workers_needed` or no eligible accounts remain.
   - The task status is updated to `completed`, `partial`, or `failed` accordingly.

---

## Error Actions & Account Status Flow

### Error Handling Protocol

| Error | Outcome | Next Action |
|-------|---------|-------------|
| `popup_suspended` | Account marked `dead` / `banned` | Terminate session, replace with new account |
| `popup_rate_limited` | Account marked `rate_limited` | Cooldown period, replace with new account |
| `header_banned` | Account marked `dead` / `banned` | Terminate session, replace with new account |
| `header_suspended` | Account marked `dead` / `banned` | Terminate session, replace with new account |
| `click_timeout` | Retryable error | Retry up to N times, then replace |
| `element_not_found` | Retryable error | Retry up to N times, then replace |

### State Transitions

```
 fresh ──▶ logged_in ──▶ session_expired ──▶ banned/dead
              │▲
              ▼│
         rate_limited (temp cooldown)
```

- **fresh**: Newly imported account, login required.
- **logged_in**: Active session verified, ready to work.
- **rate_limited**: Encountered Reddit rate limits. Placed in cooldown.
- **session_expired**: Session credentials invalid/expired, requires re-login.
- **banned/dead**: Account permanently suspended or banned by Reddit.
