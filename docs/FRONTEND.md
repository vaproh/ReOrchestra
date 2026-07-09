# Frontend Specification

Web dashboard for ReOrchestra built with HTMX + Jinja2 + Tailwind + Flowbite.

**URL:** `http://localhost:8000`

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + FastHX |
| Templates | Jinja2 |
| Styling | Tailwind CSS (CDN) |
| Components | Flowbite |
| Interactivity | HTMX |
| Icons | Heroicons |

### Dependencies

```toml
jinja2>=3.0
python-multipart>=0.0.6
httpx>=0.24
```

### CDN Links

```html
<!-- Tailwind -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Flowbite -->
<link href="https://cdn.jsdelivr.net/npm/flowbite@2.5.2/dist/flowbite.min.css" rel="stylesheet" />
<script src="https://cdn.jsdelivr.net/npm/flowbite@2.5.2/dist/flowbite.min.js"></script>

<!-- HTMX -->
<script src="https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js"></script>
```

---

## Project Structure

```
app/
├── api/
│   └── frontend.py        # Page routes
├── templates/
│   ├── base.html           # Base layout with navbar
│   ├── pages/
│   │   ├── dashboard.html     # Stats overview
│   │   ├── accounts.html       # Account management
│   │   ├── tasks.html         # Task list + creation
│   │   ├── task_detail.html   # Task detail + logs
│   │   ├── proxies.html       # Proxy management
│   │   └── system.html        # System health + logs
│   └── components/
│       ├── stat_card.html      # Dashboard stat cards
│       ├── status_badge.html   # Status badges
│       └── progress_bar.html   # Task progress
└── static/
    └── css/
        └── custom.css          # Custom styles
```

---

## Pages

| Route | Page | Purpose |
|-------|------|---------|
| `/` | Redirect | → `/dashboard` |
| `/dashboard` | dashboard.html | Stats, queue control, recent activity |
| `/accounts` | accounts.html | Account list, import, login, delete |
| `/tasks` | tasks.html | Task list, create form, filters |
| `/tasks/{id}` | task_detail.html | Task detail with execution logs |
| `/proxies` | proxies.html | Proxy list, import, mark dead |
| `/system` | system.html | System health, log streaming |

### HTMX Partial Routes

| Route | Purpose |
|-------|---------|
| `/htmx/queue-status` | Queue status pill (auto-refresh 15s) |
| `/htmx/stats` | Stats cards partial (auto-refresh 30s) |

---

## API Integration

Frontend makes HTMX requests to API endpoints (prefix `/api`):

### Endpoints Used

**Accounts:**
```
GET    /api/accounts              # List (?status=&search=&page=&per_page=)
POST   /api/accounts/import      # Bulk import
POST   /api/accounts/login        # Login
DELETE /api/accounts/{id}         # Delete
POST   /api/accounts/batch-delete # Bulk delete
```

**Tasks:**
```
GET     /api/tasks                # List
POST    /api/tasks                # Create
GET     /api/tasks/{id}          # Detail
POST    /api/tasks/{id}/cancel    # Cancel
POST    /api/tasks/{id}/retry     # Retry
```

**Queue:**
```
GET    /api/queue/status          # Status
POST   /api/queue/start           # Start
POST   /api/queue/stop            # Stop
```

**Admin:**
```
GET    /api/admin/health          # Health
GET    /api/admin/stats           # Stats
```

**Proxies:**
```
GET    /api/proxies               # List
POST   /api/proxies/import        # Import
DELETE /api/proxies/{id}          # Delete
POST   /api/proxies/replace        # Replace dead
POST   /api/proxies/mark-dead      # Mark dead
```

---

## HTMX Patterns

### Form Submission
```html
<form hx-post="/api/tasks"
      hx-target="#task-list"
      hx-swap="innerHTML">
```

### Delete with Confirmation
```html
<button hx-delete="/api/accounts/{{ id }}"
        hx-confirm="Delete this account?"
        hx-target="#account-{{ id }}"
        hx-swap="delete">
```

### Auto-refresh
```html
<div hx-get="/htmx/stats"
     hx-trigger="every 30s"
     hx-swap="innerHTML">
```

### Search with Debounce
```html
<input hx-get="/accounts"
       hx-trigger="keyup changed delay:400ms"
       hx-target="#accounts-table"
       name="search">
```

---

## Components

### Status Badge
```html
<span class="px-2 py-1 rounded-full text-xs font-medium
    {% if status == 'logged_in' %}bg-green-100 text-green-800
    {% elif status == 'rate_limited' %}bg-yellow-100 text-yellow-800
    {% elif status in ['dead', 'failed'] %}bg-red-100 text-red-800
    {% elif status == 'running' %}bg-blue-100 text-blue-800
    {% else %}bg-gray-100 text-gray-800{% endif %}">
    {{ status }}
</span>
```

### Progress Bar
```html
<div class="flex items-center gap-2">
    <div class="w-32 bg-gray-200 rounded-full h-3">
        <div class="bg-blue-600 h-3 rounded-full" style="width: {{ pct }}%"></div>
    </div>
    <span class="text-sm">{{ completed }}/{{ needed }}</span>
</div>
```

### Stat Card
```html
<div class="bg-white rounded-lg shadow p-4">
    <p class="text-gray-500 text-sm">{{ title }}</p>
    <p class="text-2xl font-bold">{{ value }}</p>
</div>
```

---

## Color Scheme

| Purpose | Tailwind Class |
|---------|---------------|
| Primary | `blue-600` |
| Success | `green-600` |
| Warning | `yellow-500` |
| Danger | `red-600` |
| Background | `gray-50` |
| Card | `white` |

---

## Auto-refresh Intervals

| Element | Interval | Route |
|---------|----------|-------|
| Queue status pill | 15s | `/htmx/queue-status` |
| Stats cards | 30s | `/htmx/stats` |
| Running tasks | 5s | `/tasks?status=running` |
| Task detail | 5s | `/tasks/{id}` (if running) |
| System health | 30s | `/system` |

---

## Adding New Pages

1. Create template in `app/templates/pages/`
2. Add route in `app/api/frontend.py`
3. Use `TemplateResponse` with `request` and context data
4. Add navbar link in `base.html`

Example route:
```python
@frontend_router.get("/new-page", response_class=HTMLResponse)
async def new_page(request: Request):
    return templates.TemplateResponse(
        "pages/new_page.html",
        {"request": request}
    )
```
