# Prompt for Antigravity AI

## IMPORTANT: Read FRONTEND_SPEC.md First

Before starting, read **`FRONTEND_SPEC.md`** - it is the **source of truth** for:
- Complete API endpoints with query parameters
- Response formats
- HTMX patterns
- Component examples
- Color scheme and styling
- All details about each page

This prompt is a summary. The spec has everything.

---

## Build the ReOrchestra Frontend

Build a complete web dashboard for ReOrchestra using **HTMX + Jinja2 + Tailwind CSS + Flowbite**.

### Tech Stack
- **Backend**: FastAPI (already built, running at localhost:8000)
- **Templates**: Jinja2
- **Styling**: Tailwind CSS via CDN
- **Components**: Flowbite
- **Interactivity**: HTMX
- **Icons**: Heroicons

### CDN Links (use these)
```html
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://cdn.jsdelivr.net/npm/flowbite@2.5.2/dist/flowbite.min.css" rel="stylesheet" />
<script src="https://cdn.jsdelivr.net/npm/flowbite@2.5.2/dist/flowbite.min.js"></script>
<script src="https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js"></script>
<script src="https://unpkg.com/heroicons@1.0.6/24/24/herooutline.js"></script>
```

### Project Structure
```
ReOrchestra/app/templates/
├── base.html                    # Base layout
├── components/
│   ├── navbar.html
│   ├── stat_card.html
│   ├── status_badge.html
│   ├── progress_bar.html
│   ├── account_table.html
│   ├── task_table.html
│   ├── modal.html
│   └── flash_messages.html
└── pages/
    ├── dashboard.html
    ├── accounts.html
    ├── tasks.html
    ├── task_detail.html
    └── proxies.html
```

---

## Pages to Build

### 1. Dashboard (`/dashboard`)
- 4 stat cards: Total Accounts, Available, Active Tasks, Queue Status
- Queue Start/Stop buttons (POST to `/api/queue/start`, `/api/queue/stop`)
- Recent tasks table (last 10)
- Auto-refresh stats every 30s

### 2. Accounts (`/accounts`)
- Filter tabs: All | Alive | Logged In | Rate Limited | Dead | Banned
- Search bar for username
- Table with: Username, Status badge, Type, Karma, Votes Today, Last Used, Login button, Delete button
- Top actions: Import (modal), Login Selected, Delete Selected
- Pagination
- HTMX: tab filters swap content, search debounced

### 3. Tasks (`/tasks`)
- Create task form at top: Action Type dropdown (all 9 types), Target URL, Workers Needed, Priority
- Filter tabs: All | Queued | Running | Completed | Partial | Failed
- Table with: ID, Action, Target (truncated), Progress bar, Status badge, Created, Cancel button, View link
- Pagination
- HTMX: auto-refresh running tasks every 5s, create form submits via HTMX

### 4. Task Detail (`/tasks/{id}`)
- Task info card: ID, Action, Target URL, Status, Priority, Progress bar, Created, Started, Completed
- Execution logs table: Account username, Outcome (color-coded), Error message, Duration, Timestamp
- Actions: Cancel (if running), Retry (if failed/partial)
- Auto-refresh logs every 5s if task is running

### 5. Proxies (`/proxies`)
- Filter tabs: All | Active | Dead
- Top actions: Import (modal), Replace Dead (modal)
- Table with: Proxy String (masked), Status, Provider, Country, Fail Count, Last Used, Mark Dead button, Delete button
- Pagination

---

## API Endpoints to Use

### Accounts
```
GET    /api/accounts                    # List (?status=&search=&page=&per_page=)
POST   /api/accounts/import             # Bulk import
POST   /api/accounts/login              # Login accounts
DELETE /api/accounts/{id}              # Delete
POST   /api/accounts/batch-delete      # Bulk delete
```

### Tasks
```
GET     /api/tasks                     # List
POST    /api/tasks                     # Create
GET     /api/tasks/{id}                # Detail with logs
POST    /api/tasks/{id}/cancel         # Cancel
POST    /api/tasks/{id}/retry          # Retry
```

### Queue
```
GET    /api/queue/status                # Status
POST   /api/queue/start                # Start
POST   /api/queue/stop                 # Stop (?graceful=true|false)
```

### Admin
```
GET    /api/admin/health                # Health
GET    /api/admin/stats                # Stats
```

### Proxies
```
GET    /api/proxies                    # List
POST   /api/proxies/import             # Import
DELETE /api/proxies/{id}              # Delete
POST   /api/proxies/replace            # Replace dead
POST   /api/proxies/mark-dead          # Mark dead
```

---

## Component Examples

### Status Badge
```html
<span class="px-2 py-1 rounded-full text-xs font-medium
    {% if status == 'logged_in' %}bg-green-100 text-green-800
    {% elif status == 'rate_limited' %}bg-yellow-100 text-yellow-800
    {% elif status == 'dead' or status == 'failed' %}bg-red-100 text-red-800
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
    <span class="text-sm text-gray-600">{{ completed }}/{{ needed }}</span>
</div>
```

### HTMX Delete with Confirmation
```html
<button hx-delete="/api/accounts/{{ id }}"
        hx-confirm="Delete account {{ username }}?"
        hx-target="#account-{{ id }}"
        hx-swap="outerHTML"
        class="text-red-600 hover:text-red-800">
    Delete
</button>
```

### HTMX Auto-refresh
```html
<div hx-get="/api/tasks"
     hx-trigger="every 5s"
     hx-swap="innerHTML">
    <!-- content -->
</div>
```

---

## Important Guidelines

1. **Read FRONTEND_SPEC.md first** - It is the source of truth
2. **Pure HTML + Tailwind + Flowbite + HTMX** - No JavaScript frameworks
3. **Use Flowbite components** - Modals, tables, navbar, cards, badges, toasts
4. **HTMX for all interactivity** - Forms, refresh, delete, swap
5. **Backend already exists** - Just build the HTML templates
6. **Use Jinja2 syntax** - `{{ variable }}`, `{% for %}`, `{% if %}`
7. **Plan swap targets** - Which elements get updated via HTMX
8. **Test against existing API** - API is fully functional

---

## Response Format

API returns:
```json
{
  "success": true,
  "data": { ... }
}
```

Handle in HTMX by checking `success` and showing toast messages.

---

## Styling

- Primary: `blue-600`
- Success: `green-600`
- Warning: `yellow-500`
- Danger: `red-600`
- Background: `gray-50`
- Cards: `white` with `shadow rounded-lg`

---

## Navigation

Navbar should link to: Dashboard | Accounts | Tasks | Proxies

Queue status indicator showing "Running" (green) or "Stopped" (red).

---

## Build Order Recommendation

1. `base.html` - Set up Tailwind, Flowbite, HTMX, navbar
2. `dashboard.html` - Stats + queue control
3. `accounts.html` - Account list + modals
4. `tasks.html` - Task list + create form
5. `task_detail.html` - Task detail + logs
6. `proxies.html` - Proxy list + modals

---

## Deliverables

Create all files in `ReOrchestra/app/templates/`:

1. `base.html`
2. `components/navbar.html`
3. `components/stat_card.html`
4. `components/status_badge.html`
5. `components/progress_bar.html`
6. `components/modal.html`
7. `pages/dashboard.html`
8. `pages/accounts.html`
9. `pages/tasks.html`
10. `pages/task_detail.html`
11. `pages/proxies.html`

---

## Questions?

If the spec is unclear or missing something, ask before building.

Good luck!
