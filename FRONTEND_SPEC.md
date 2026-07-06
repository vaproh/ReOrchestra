# ReOrchestra Frontend Specification

## 1. Project Overview

**Name:** ReOrchestra Frontend
**Type:** Server-rendered web dashboard
**Purpose:** Manage bulk Reddit accounts, create tasks, monitor queue

**Backend:** FastAPI at `http://localhost:8000/api`
**Frontend:** HTMX + Jinja2 + Tailwind + Flowbite

---

## 2. Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + SQLAlchemy |
| Templates | Jinja2 |
| Styling | Tailwind CSS (CDN) |
| Components | Flowbite |
| Interactivity | HTMX |
| HTMX Helpers | FastHX |
| Icons | Heroicons |

**CDN Links:**
```html
<!-- Tailwind -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Flowbite -->
<link href="https://cdn.jsdelivr.net/npm/flowbite@2.5.2/dist/flowbite.min.css" rel="stylesheet" />
<script src="https://cdn.jsdelivr.net/npm/flowbite@2.5.2/dist/flowbite.min.js"></script>

<!-- HTMX -->
<script src="https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js"></script>

<!-- Heroicons -->
<script src="https://unpkg.com/heroicons@1.0.6/24/24/herooutline.js"></script>
```

---

## 3. Project Structure

```
ReOrchestra/app/templates/
├── base.html                    # Base layout with navbar, Tailwind, Flowbite, HTMX
├── components/
│   ├── navbar.html             # Top navigation
│   ├── stat_card.html          # Dashboard stat cards
│   ├── account_table.html     # Account list table
│   ├── task_table.html        # Task list table
│   ├── progress_bar.html       # Task progress visualization
│   ├── status_badge.html      # Status badges (green/yellow/red)
│   ├── modal.html              # Reusable modals
│   └── flash_messages.html     # Success/error toasts
└── pages/
    ├── dashboard.html           # Overview stats, queue control
    ├── accounts.html            # Account list/management
    ├── tasks.html               # Task list/creation
    ├── task_detail.html         # Single task with logs
    └── proxies.html             # Proxy list/management

ReOrchestra/app/static/
└── css/
    └── custom.css               # Custom styles if needed
```

---

## 4. Pages & Features

### 4.1 Dashboard (`/dashboard`)

**Purpose:** Overview of system health

**Stats Cards (4 across):**
| Card | API Endpoint | Data |
|------|--------------|------|
| Total Accounts | `GET /api/admin/stats` | `total_accounts` |
| Available | `GET /api/admin/stats` | `available` |
| Active Tasks | `GET /api/queue/status` | `queue.queued + queue.running` |
| Queue Status | `GET /api/queue/status` | `processing: true/false` |

**Content:**
- Queue control section: Start/Stop buttons with `POST /api/queue/start`, `POST /api/queue/stop?graceful=false`
- Recent tasks table (last 10, from `GET /api/tasks?page=1&per_page=10`)
- System health from `GET /api/admin/health`

**HTMX Features:**
- Auto-refresh stats every 30s: `hx-get="/api/admin/stats" hx-trigger="every 30s"`
- Queue start/stop via HTMX POST with `hx-replace-url="true"`

---

### 4.2 Accounts (`/accounts`)

**Purpose:** List, import, login, manage accounts

**Filter Tabs (horizontal):**
- All | Alive | Logged In | Rate Limited | Dead | Banned

**Search Bar:**
- Input field for username search
- `GET /api/accounts?search={query}&status={status}`

**Table Columns:**
| Column | Source |
|--------|--------|
| Username | `username` |
| Status | Badge (green=logged_in, yellow=rate_limited, red=dead) |
| Type | `account_type` |
| Karma | `karma_total` |
| Votes Today | `votes_today` |
| Last Used | `last_used` (formatted) |
| Actions | Login button, Delete button |

**Actions per row:**
| Action | Method | API |
|--------|--------|-----|
| Login | POST | `/api/accounts/login` with `{"account_ids": [id]}` |
| Delete | DELETE | `/api/accounts/{id}` with `hx-confirm` |

**Top Actions:**
- **Import** button → Opens modal with:
  - Textarea for pasting accounts (format: `user:pass` per line, or JSON array)
  - Account type dropdown
  - Submit: `POST /api/accounts/import`
- **Login Selected** → POST to `/api/accounts/login` with selected IDs
- **Delete Selected** → POST to `/api/accounts/batch-delete`

**Pagination:**
- Page numbers at bottom
- `GET /api/accounts?page={n}&per_page=50`

**HTMX Features:**
- Tab filter changes URL + swaps table content
- Search debounced, triggers after 300ms
- Modal forms with Flowbite modal

---

### 4.3 Tasks (`/tasks`)

**Purpose:** List/create/manage tasks

**Create Task Form (top section):**
```html
<form hx-post="/api/tasks" hx-target="#task-list" hx-swap="innerHTML">
  <select name="action_type">
    <option value="upvote_post">Upvote Post</option>
    <option value="downvote_post">Downvote Post</option>
    <option value="upvote_comment">Upvote Comment</option>
    <option value="downvote_comment">Downvote Comment</option>
    <option value="follow_user">Follow User</option>
    <option value="unfollow_user">Unfollow User</option>
    <option value="join_subreddit">Join Subreddit</option>
    <option value="leave_subreddit">Leave Subreddit</option>
    <option value="save_post">Save Post</option>
  </select>
  <input name="target_url" placeholder="https://old.reddit.com/r/..." required>
  <input name="workers_needed" type="number" value="10" min="1">
  <input name="priority" type="number" value="0">
  <button type="submit">Create Task</button>
</form>
```

**Filter Tabs:**
- All | Queued | Running | Completed | Partial | Failed

**Table Columns:**
| Column | Source |
|--------|--------|
| ID | `id` |
| Action | `action_type` |
| Target | `target_url` (truncated to 50 chars) |
| Progress | Bar: `workers_completed/workers_needed` |
| Status | Badge |
| Created | `created_at` (formatted) |
| Actions | Cancel, View |

**Progress Bar Component:**
```html
<div class="w-32 bg-gray-200 rounded-full h-3">
  <div class="bg-blue-600 h-3 rounded-full" style="width: {{ pct }}%"></div>
</div>
<span class="text-sm">{{ completed }}/{{ needed }}</span>
```

**Actions:**
| Action | Method | API |
|--------|--------|-----|
| View | GET (link) | `/tasks/{id}` |
| Cancel | POST | `/api/tasks/{id}/cancel` (with `hx-confirm`) |

**Pagination:**
- Page numbers at bottom
- `GET /api/tasks?page={n}&per_page=50`

**HTMX Features:**
- Auto-refresh running tasks every 5s: `hx-get="/api/tasks?status=running" hx-trigger="every 5s"`
- Create form submits via HTMX, appends to list
- Cancel triggers confirmation modal

---

### 4.4 Task Detail (`/tasks/{id}`)

**Purpose:** Single task details + live execution logs

**Task Info Card:**
| Field | Source |
|-------|--------|
| ID | `id` |
| Action Type | `action_type` |
| Target URL | `target_url` (full) |
| Status | Badge |
| Priority | `priority` |
| Progress | Bar + text |
| Created | `created_at` |
| Started | `started_at` |
| Completed | `completed_at` |

**Execution Logs Table:**
| Column | Source |
|--------|--------|
| Account | Username from `account_id` (JOIN) |
| Outcome | `outcome` (success=green, failed=red, cancelled=yellow) |
| Error | `error` message if failed |
| Duration | Calculated: `completed_at - created_at` in seconds |
| Timestamp | `created_at` |

**Actions:**
- **Cancel** button (if status == running): `POST /api/tasks/{id}/cancel`
- **Retry** button (if status == failed or partial): `POST /api/tasks/{id}/retry`
- **Back to Tasks** link: `/tasks`

**Auto-refresh:**
- If status == running or queued: refresh logs every 5s
- `hx-get="/tasks/{id}" hx-trigger="every 5s"`

---

### 4.5 Proxies (`/proxies`)

**Purpose:** Manage proxies

**Filter Tabs:**
- All | Active | Dead

**Top Actions:**
- **Import** button → Opens modal:
  - Textarea for proxy strings (format: `protocol://host:port` or `protocol://user:pass@host:port`)
  - Submit: `POST /api/proxies/import`
- **Replace Dead** button → Opens modal:
  - Textarea for new proxies
  - Submit: `POST /api/proxies/replace`

**Table Columns:**
| Column | Source |
|--------|--------|
| Proxy String | `proxy_string` (masked: `host:port` only) |
| Status | Badge |
| Provider | `provider` |
| Country | `country` |
| Fail Count | `fail_count` |
| Last Used | `last_used` |
| Actions | Mark Dead, Delete |

**Actions:**
| Action | Method | API |
|--------|--------|-----|
| Mark Dead | POST | `/api/proxies/mark-dead` with `{"proxy_id": id}` |
| Delete | DELETE | `/api/proxies/{id}` |

**Pagination:**
- Page numbers at bottom

---

## 5. API Integration Reference

### Account Endpoints
```
GET    /api/accounts                    # List (?status=&search=&page=&per_page=)
GET    /api/accounts/{id}              # Detail
POST   /api/accounts/import             # Bulk import
POST   /api/accounts/login              # Login accounts
POST   /api/accounts/logout             # Logout
DELETE /api/accounts/{id}              # Delete single
POST   /api/accounts/batch-delete      # Bulk delete
POST   /api/accounts/batch-login       # Bulk login
PATCH  /api/accounts/{id}             # Update account
```

### Task Endpoints
```
GET     /api/tasks                     # List (?status=&page=&per_page=)
POST    /api/tasks                     # Create task
GET     /api/tasks/{id}                # Detail with logs
POST    /api/tasks/{id}/cancel         # Cancel
POST    /api/tasks/{id}/retry          # Retry
POST    /api/tasks/{id}/priority       # Boost priority
```

### Queue Endpoints
```
GET    /api/queue/status                # Queue status
POST   /api/queue/start                # Start queue
POST   /api/queue/stop                 # Stop (?graceful=true|false)
GET    /api/queue                      # View queued/running tasks
```

### Admin Endpoints
```
GET    /api/admin/health                # System health
GET    /api/admin/stats                # Statistics
```

### Proxy Endpoints
```
GET    /api/proxies                    # List
POST   /api/proxies/import             # Import
DELETE /api/proxies/{id}              # Delete
POST   /api/proxies/replace            # Replace dead
POST   /api/proxies/mark-dead          # Mark dead
```

---

## 6. Response Formats

### Success
```json
{
  "success": true,
  "data": { ... }
}
```

### Error
```json
{
  "success": false,
  "error": "Error message"
}
```

---

## 7. HTMX Patterns

### 7.1 FastHX Integration

FastHX provides cleaner HTMX patterns for FastAPI. Use the `@hx` decorator for HTMX-aware responses.

**Setup in `main.py`:**
```python
from fasthx import FastHX

app = FastAPI(...)
hx = FastHX(app)

# Use @hx() for HTMX-aware template rendering
@hx(template="pages/dashboard.html")
async def dashboard(request: Request):
    stats = await get_stats()
    return {"stats": stats, "request": request}
```

**Key FastHX features:**
- `@hx()` - Renders template with context for HTMX requests
- `HXResponse` - For custom HTMX responses with triggers, redirects
- `request.hx` - Check if request is HTMX

### 7.2 Form Submission
```html
<form hx-post="/api/tasks" hx-target="#task-list" hx-swap="innerHTML">
```

### Delete with Confirmation
```html
<button hx-delete="/api/accounts/1"
        hx-confirm="Delete this account?"
        hx-target="#account-row-1"
        hx-swap="delete">
```

### Auto-refresh
```html
<div hx-get="/api/tasks/1"
     hx-trigger="every 5s"
     hx-swap="innerHTML">
```

### HTMX Response Headers (Backend returns)
- `HX-Trigger` - client-side events
- `HX-Redirect` - navigation
- `HX-Refresh` - reload page

---

## 8. Status Badges

```html
<!-- logged_in / active -->
<span class="px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
  {{ status }}
</span>

<!-- rate_limited -->
<span class="px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
  {{ status }}
</span>

<!-- dead / banned / failed -->
<span class="px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
  {{ status }}
</span>

<!-- queued -->
<span class="px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
  {{ status }}
</span>

<!-- running -->
<span class="px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
  {{ status }}
</span>
```

---

## 9. Navigation

**Navbar (Flowbite navbar component):**
```
ReOrchestra  |  Dashboard  |  Accounts  |  Tasks  |  Proxies  |  [Queue: Running/Stopped]
```

---

## 10. Color Scheme

| Purpose | Tailwind Class |
|---------|---------------|
| Primary | `blue-600` |
| Success | `green-600` |
| Warning | `yellow-500` |
| Danger | `red-600` |
| Gray | `gray-500` |
| Background | `gray-50` |
| Card | `white` |

---

## 11. Icons (Heroicons Outline)

| Element | Icon |
|---------|------|
| Plus | `herooutline-plus` |
| Trash | `herooutline-trash` |
| Play | `herooutline-play` |
| Stop | `herooutline-stop` |
| Check | `herooutline-check` |
| X | `herooutline-x` |
| Users | `herooutline-users` |
| List | `herooutline-list-bullet` |
| Chart | `herooutline-chart-bar` |
| Globe | `herooutline-globe-alt` |
| Clock | `herooutline-clock` |
| Refresh | `herooutline-arrow-path` |

---

## 12. Empty States

When no data:
```html
<div class="text-center py-8 text-gray-500">
  <p class="text-lg">No accounts found</p>
  <p class="text-sm">Import some accounts to get started</p>
</div>
```

---

## 13. Loading States

```html
<div hx-get="/api/accounts" hx-trigger="load" class="animate-pulse">
  <!-- Skeleton loader -->
  <div class="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
  <div class="h-4 bg-gray-200 rounded w-1/2"></div>
</div>
```

---

## 14. Toast Notifications

Flowbite toast component for flash messages:
```html
<div id="toast-success" class="hidden fixed bottom-5 right-5 ...">
  <div class="flex items-center">
    <div class="i-heroicons-check-circle-20-solid text-green-500"></div>
    <div class="ml-3">
      <p class="text-sm font-medium text-gray-900" id="toast-message"></p>
    </div>
  </div>
</div>
```

Handle `hx-trigger="settle"` for toast dismissal.

---

## 15. Responsive Breakpoints

| Size | Behavior |
|------|----------|
| Mobile (<640px) | Stack cards, hide less important columns |
| Tablet (640-1024px) | 2-column grids |
| Desktop (>1024px) | Full layout |

---

## 16. Deliverables

1. `app/templates/base.html` - Base layout
2. `app/templates/components/*.html` - Reusable components
3. `app/templates/pages/*.html` - All 5 page templates
4. Routes in `app/main.py` for serving templates (if needed, or serve from `/`)

---

## 17. Important Notes

1. **No JavaScript frameworks** - Pure HTML + Tailwind + Flowbite + HTMX
2. **Use Flowbite components** - Modals, tables, navbar, cards, badges, toasts
3. **HTMX for all interactivity** - Forms, refresh, delete, navigation
4. **Backend already exists** - Just build HTML templates
5. **Use Jinja2** template syntax `{{ variable }}` `{% for %}` `{% if %}`
6. **Plan swap targets** - Which elements get updated via HTMX
7. **Use existing API endpoints** - Don't need to create new endpoints
8. **Test with existing API** - API is fully functional at `localhost:8000`
