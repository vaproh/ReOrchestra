# ReOrchestra Frontend Specification

## Overview

ReOrchestra is a bulk Reddit account automation tool. This spec defines a lightweight dashboard for managing 500-1000 Reddit accounts with the worker queue system.

**Tech Stack:**
- **TailwindCSS** via CDN (JIT, no build step)
- **HTMX** for interactivity (no JavaScript framework)
- **Vanilla JavaScript** for simple interactions
- **No npm/build step** - served directly by FastAPI

---

## 1. Page Structure

### 1.1 Pages

| Route | File | Purpose |
|-------|------|---------|
| `/` | `index.html` | Dashboard overview |
| `/accounts` | `accounts.html` | Account list with filters and bulk actions |
| `/workers` | `workers.html` | Worker pool status and management |
| `/tasks` | `tasks.html` | Task queue list |
| `/dead-letter` | `dead-letter.html` | Failed tasks |
| `/queue` | `queue.html` | Queue processor controls |
| `/proxies` | `proxies.html` | Proxy management |
| `/settings` | `settings.html` | App configuration |

### 1.2 Layout Structure

```
┌─────────────────────────────────────────────────────────────┐
│  [Logo] ReOrchestra          [Queue: Running] [Camofox: ✓] │
├──────────┬────────────────────────────────────────────────────┤
│ Sidebar  │  Main Content Area                               │
│          │                                                    │
│ Dashboard│  <Page-specific content>                          │
│ Accounts │                                                    │
│ Workers  │                                                    │
│ Tasks    │                                                    │
│ Dead Ltr │                                                    │
│ Queue    │                                                    │
│ Proxies  │                                                    │
│ Settings │                                                    │
└──────────┴────────────────────────────────────────────────────┘
```

**Implementation:**
- `layout.html` - shared layout (sidebar + main wrapper)
- Pages use server-side includes or HTMX partial templates
- FastAPI serves static HTML files from `frontend/` directory

---

## 2. Tech Stack Details

### 2.1 TailwindCSS CDN Setup

```html
<!-- In <head> of layout.html -->
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    darkMode: 'class',
    theme: {
      extend: {
        colors: {
          canvas: '#010102',
          surface: {
            1: '#0f1011',
            2: '#141516',
            3: '#18191a',
          },
          accent: '#ff4500',
        }
      }
    }
  }
</script>
<style>
  /* Custom fonts */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');
</style>
```

### 2.2 HTMX Setup

```html
<!-- Before </body> -->
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
<script src="https://unpkg.com/htmx.org@1.9.10/dist/ext/client-side-templates.js"></script>
```

### 2.3 HTMX Patterns Used

| Pattern | HTMX Attribute | Use Case |
|---------|---------------|----------|
| GET data | `hx-get="/api/..."` | Load table data |
| POST form | `hx-post="/api/..."` | Submit forms |
| Poll | `hx-trigger="every 5s"` | Auto-refresh |
| Target | `hx-target="#element-id"` | Where to put response |
| Swap | `hx-swap="innerHTML"` | How to insert content |
| Confirm | `hx-confirm="Are you sure?"` | Destructive actions |

### 2.4 Why This Stack?

| Requirement | Solution |
|-------------|----------|
| VPS resource usage | Minimal - no Node.js, just static HTML + small JS |
| No build step | TailwindCDN JIT compiles on-demand |
| FastAPI integration | Serve from `app.mount("/static", StaticFiles(directory="frontend"))` |
| AntiGravity IDE | Generates clean HTML/CSS, HTMX adds interactivity |
| Dark theme | Tailwind `dark:` classes + CSS variables |

---

## 3. API Integration

### 3.1 Endpoints Per Page

#### Dashboard (`index.html`)
| Endpoint | Method | Purpose | Polling |
|----------|--------|---------|---------|
| `/api/admin/stats` | GET | System statistics | 30s |
| `/api/admin/health` | GET | Camofox health | 30s |
| `/api/queue/status` | GET | Queue running state | 10s |

#### Accounts (`accounts.html`)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/accounts` | GET | Paginated account list |
| `/api/accounts/import` | POST | Bulk import |
| `/api/accounts/login` | POST | Login selected |
| `/api/accounts/{id}` | PATCH | Update account |
| `/api/accounts/{id}` | DELETE | Delete account |

#### Tasks (`tasks.html`)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/tasks` | GET | Recent tasks |
| `/api/tasks` | POST | Create task |
| `/api/tasks/{id}/cancel` | POST | Cancel task |
| `/api/tasks/{id}/retry` | POST | Retry task |
| `/api/tasks/{id}/priority` | POST | Boost priority |

#### Workers (`workers.html`)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/workers` | GET | All workers |
| `/api/workers/{id}/pause` | POST | Pause worker |
| `/api/workers/{id}/resume` | POST | Resume worker |

#### Queue (`queue.html`)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/queue` | GET | Active queue |
| `/api/queue/start` | POST | Start processor |
| `/api/queue/stop` | POST | Stop processor |

#### Proxies (`proxies.html`)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/proxies` | GET | All proxies |
| `/api/proxies/import` | POST | Bulk import |
| `/api/proxies/mark-dead` | POST | Mark dead |
| `/api/proxies/replace` | POST | Replace dead |

### 3.2 HTMX API Pattern

```html
<!-- Example: Load accounts table -->
<div id="accounts-table"
     hx-get="/api/accounts"
     hx-trigger="load"
     hx-swap="innerHTML">
  Loading...
</div>

<!-- Example: Refresh every 10 seconds -->
<div hx-get="/api/queue/status"
     hx-trigger="every 10s"
     hx-swap="innerHTML">
  ...
</div>

<!-- Example: Form submission -->
<form hx-post="/api/accounts/import"
      hx-target="#import-result"
      hx-swap="innerHTML">
  ...
</form>
```

---

## 4. File Structure

```
frontend/
├── layout.html              # Shared layout (sidebar, header)
├── index.html               # Dashboard
├── accounts.html            # Accounts page
├── workers.html             # Workers page
├── tasks.html               # Tasks page
├── dead-letter.html          # Dead letter queue
├── queue.html               # Queue controls
├── proxies.html             # Proxies page
├── settings.html            # Settings page
├── css/
│   └── custom.css           # Custom styles beyond Tailwind
├── js/
│   └── app.js               # Simple vanilla JS utilities
├── partials/                # HTMX partial templates
│   ├── account-row.html
│   ├── task-row.html
│   ├── worker-row.html
│   └── stats-card.html
└── SPEC.md
```

### 4.1 Layout Pattern

```html
<!-- layout.html structure -->
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ReOrchestra</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/htmx.org@1.9.10"></script>
  <!-- Tailwind config -->
</head>
<body class="bg-canvas text-gray-100">

  <div class="flex h-screen">
    <!-- Sidebar -->
    <aside class="w-56 bg-surface-1 border-r border-hairline">
      <nav class="p-4">
        <!-- Nav links -->
      </nav>
    </aside>

    <!-- Main content -->
    <main class="flex-1 overflow-auto p-6">
      <!-- Page content injected here -->
      {% block content %}{% endblock %}
    </main>
  </div>

</body>
</html>
```

**Note:** For simplicity without a template engine, each page includes the full HTML structure. A future improvement could use Jinja2 templates served by FastAPI.

---

## 5. Design Tokens (Dark Theme)

### 5.1 Color Palette

```css
:root {
  /* Canvas - main background */
  --canvas: #010102;

  /* Surfaces - cards, panels */
  --surface-1: #0f1011;
  --surface-2: #141516;
  --surface-3: #18191a;

  /* Borders */
  --hairline: #23252a;
  --hairline-strong: #34343a;

  /* Text */
  --ink: #f7f8f8;
  --ink-muted: #d0d6e0;
  --ink-subtle: #8a8f98;

  /* Accent - Reddit Orange */
  --accent: #ff4500;
  --accent-hover: #ff5722;

  /* Semantic */
  --success: #27a644;
  --warning: #ffc107;
  --error: #f85149;
  --info: #58a6ff;
}
```

### 5.2 Tailwind Extended Colors

```html
<script>
tailwind.config = {
  theme: {
    extend: {
      colors: {
        canvas: '#010102',
        surface: {
          1: '#0f1011',
          2: '#141516', 
          3: '#18191a',
        },
        hairline: '#23252a',
        accent: '#ff4500',
        success: '#27a644',
        warning: '#ffc107',
        error: '#f85149',
        info: '#58a6ff',
      }
    }
  }
}
</script>
```

### 5.3 Typography

- **Font:** Inter (Google Fonts)
- **Fallback:** -apple-system, BlinkMacSystemFont, sans-serif
- **Mono:** JetBrains Mono for code/IDs

---

## 6. Components

### 6.1 Button

```html
<!-- Primary button -->
<button class="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-md font-medium">
  Action
</button>

<!-- Secondary button -->
<button class="px-4 py-2 bg-surface-2 hover:bg-surface-3 text-gray-200 rounded-md border border-hairline">
  Cancel
</button>

<!-- Danger button -->
<button class="px-4 py-2 bg-error hover:bg-red-600 text-white rounded-md">
  Delete
</button>

<!-- Disabled state -->
<button class="px-4 py-2 bg-gray-600 text-gray-400 rounded-md cursor-not-allowed" disabled>
  Disabled
</button>
```

### 6.2 Input

```html
<input type="text" 
       class="w-full px-3 py-2 bg-surface-2 border border-hairline rounded-md text-gray-100 placeholder-gray-500 focus:outline-none focus:border-accent"
       placeholder="Search...">
```

### 6.3 Badge/Status

```html
<!-- Success -->
<span class="px-2 py-1 text-xs font-medium rounded bg-success/20 text-success">Active</span>

<!-- Warning -->
<span class="px-2 py-1 text-xs font-medium rounded bg-warning/20 text-warning">Warning</span>

<!-- Error -->
<span class="px-2 py-1 text-xs font-medium rounded bg-error/20 text-error">Failed</span>

<!-- Neutral -->
<span class="px-2 py-1 text-xs font-medium rounded bg-gray-600/20 text-gray-400">Pending</span>
```

### 6.4 Card

```html
<div class="bg-surface-1 border border-hairline rounded-lg p-4">
  <h3 class="text-lg font-medium mb-2">Card Title</h3>
  <p class="text-gray-400">Card content goes here.</p>
</div>
```

### 6.5 Table

```html
<table class="w-full">
  <thead class="bg-surface-2 text-gray-400 text-sm">
    <tr>
      <th class="px-4 py-2 text-left">Column 1</th>
      <th class="px-4 py-2 text-left">Column 2</th>
    </tr>
  </thead>
  <tbody class="divide-y divide-hairline">
    <tr class="hover:bg-surface-2">
      <td class="px-4 py-2">Data 1</td>
      <td class="px-4 py-2">Data 2</td>
    </tr>
  </tbody>
</table>
```

### 6.6 Modal (HTMX + Alpine.js alternative)

For simplicity, use browser `window.confirm()` for confirmations and inline form panels instead of modals.

Alternative: Use HTMX to load a form into a hidden div and show it.

---

## 7. Page Layouts

### 7.1 Dashboard (`index.html`)

```
┌─────────────────────────────────────────────────────────────┐
│ Stats Grid (4 cards)                                         │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐             │
│ │Accounts │ │Workers  │ │ Tasks   │ │Actions  │             │
│ │   500   │ │  45     │ │   12    │ │  2,340  │             │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘             │
├─────────────────────────────────────────────────────────────┤
│ ┌────────────────────────┐ ┌────────────────────────────┐  │
│ │ Health Status           │ │ Queue Status                │  │
│ │ • Camofox: Connected ✓  │ │ • Running: Yes              │  │
│ │ • Database: OK ✓       │ │ • [Stop Queue]              │  │
│ └────────────────────────┘ └────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│ Recent Tasks (last 5)                                        │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ #123 upvote_post  reddit.com/...  ✓ Completed          │ │
│ │ #124 downvote_post reddit.com/...  ⟳ Running 2/5       │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Accounts Page (`accounts.html`)

```
┌─────────────────────────────────────────────────────────────┐
│ Filters: [Status ▼] [Type ▼] [Search........] [Import]     │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ☐ │ Username    │ Status      │ Proxy    │ Votes │ Act │ │
│ ├───┼─────────────┼─────────────┼──────────┼───────┼─────┤ │
│ │ ☐ │ user1       │ ● logged_in │ proxy1   │  150  │ ⋯   │ │
│ │ ☐ │ user2       │ ● fresh     │ —        │   0   │ ⋯   │ │
│ │ ☐ │ user3       │ ● banned    │ proxy2   │  890  │ ⋯   │ │
│ └─────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────┤
│ Showing 1-50 of 500  [< Prev] [1] [2] [3]... [Next >]      │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 Tasks Page (`tasks.html`)

```
┌─────────────────────────────────────────────────────────────┐
│ Filters: [Status ▼] [+ New Task]                            │
├─────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ID   │ Action      │ Target         │ Progress │ Status │ │
│ ├──────┼─────────────┼────────────────┼──────────┼────────┤ │
│ │ #156 │ upvote_post │ reddit.com/r/..│ ████░░ 2/5│ running│ │
│ │ #155 │ join_subredd│ reddit.com/r/..│ ████████✓│  done │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Interaction Patterns

### 8.1 Form Submission (HTMX)

```html
<!-- Create Task Form -->
<form hx-post="/api/tasks"
      hx-target="#task-result"
      hx-swap="innerHTML"
      class="space-y-4">
  
  <div>
    <label class="block text-sm font-medium mb-1">Action Type</label>
    <select name="action_type" required
            class="w-full bg-surface-2 border border-hairline rounded-md px-3 py-2">
      <option value="upvote_post">Upvote Post</option>
      <option value="downvote_post">Downvote Post</option>
      <option value="follow_user">Follow User</option>
      <!-- etc -->
    </select>
  </div>

  <div>
    <label class="block text-sm font-medium mb-1">Target URL</label>
    <input type="url" name="target_url" required
           class="w-full bg-surface-2 border border-hairline rounded-md px-3 py-2">
  </div>

  <div>
    <label class="block text-sm font-medium mb-1">Workers</label>
    <input type="number" name="workers_needed" value="1" min="1"
           class="w-full bg-surface-2 border border-hairline rounded-md px-3 py-2">
  </div>

  <button type="submit" class="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-md">
    Create Task
  </button>
</form>

<div id="task-result"></div>
```

### 8.2 Confirmation (HTMX)

```html
<!-- Destructive action with confirmation -->
<button hx-post="/api/accounts/123"
        hx-confirm="Are you sure you want to delete this account?"
        class="px-4 py-2 bg-error hover:bg-red-600 text-white rounded-md">
  Delete Account
</button>
```

### 8.3 Polling (HTMX)

```html
<!-- Queue status - refresh every 10 seconds -->
<div hx-get="/api/queue/status"
     hx-trigger="every 10s"
     hx-swap="innerHTML">
  <!-- Content replaced by HTMX -->
</div>

<!-- Worker activity - refresh every 5 seconds when visible -->
<div hx-get="/api/workers"
     hx-trigger="every 5s"
     hx-swap="innerHTML">
  <!-- Content replaced by HTMX -->
</div>
```

### 8.4 Loading States

```html
<!-- Use HTMX indicators -->
<div hx-get="/api/workers"
     hx-trigger="every 5s"
     hx-swap="innerHTML"
     hx-indicator="#worker-spinner">
  <!-- Worker content -->
</div>
<img id="worker-spinner" class="htmx-indicator" src="/static/spinner.svg" />
```

### 8.5 Toast Notifications (Vanilla JS)

For simplicity, use browser alerts or a simple JS toast:

```javascript
// Simple toast implementation
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `fixed top-4 right-4 px-4 py-2 rounded-md text-white ${
    type === 'error' ? 'bg-red-600' : 
    type === 'success' ? 'bg-green-600' : 'bg-blue-600'
  }`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 5000);
}

// HTMX response handler
document.body.addEventListener('htmx:afterRequest', (event) => {
  if (event.detail.successful) {
    showToast('Action completed', 'success');
  }
});
```

---

## 9. API Response Handling

### 9.1 HTMX Response Pattern

HTMX expects HTML responses. For simplicity, FastAPI can return partial HTML snippets:

```python
@router.get("/partials/accounts")
async def accounts_partial(db: Session = Depends(get_db)):
    accounts = db.query(Account).limit(50).all()
    html = render_template("partials/account-list.html", accounts=accounts)
    return HTMLResponse(html)
```

### 9.2 JSON API with HTMX

If using JSON API with client-side rendering:

```html
<div hx-get="/api/accounts"
     hx-trigger="load"
     hx-headers='{"Accept": "application/json"}'
     hx-swap="innerHTML"
     hx-vals='js:{page: 1}'>
</div>
```

### 9.3 Error Handling

```html
<!-- Show error in toast -->
<script>
document.body.addEventListener('htmx:responseError', (event) => {
  showToast('Request failed: ' + event.detail.xhr.statusText, 'error');
});
</script>
```

---

## 10. Responsive Design

### 10.1 Breakpoints (Tailwind)

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Mobile | `<640px` | Single column, stacked cards |
| Tablet | `640-1024px` | Collapsible sidebar |
| Desktop | `>1024px` | Full sidebar |

### 10.2 Mobile Nav

```html
<!-- Mobile: Hamburger menu -->
<button class="md:hidden" onclick="document.getElementById('sidebar').classList.toggle('hidden')">
  ☰
</button>
```

---

## 11. FastAPI Integration

### 11.1 Static File Serving

```python
# In app/main.py
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount frontend static files
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

### 11.2 Template Responses

For HTML partials, use Jinja2 templates:

```python
from fastapi import Request
from fastapi.responses import HTMLResponse
import jinja2

env = jinja2.Environment(loader=jinja2.FileSystemLoader("frontend/partials"))

@router.get("/partials/accounts")
async def accounts_partial(request: Request, db: Session = Depends(get_db)):
    accounts = db.query(Account).limit(50).all()
    template = env.get_template("account-list.html")
    html = template.render(accounts=accounts)
    return HTMLResponse(html)
```

---

## 12. Implementation Priority

### Phase 1: Core Pages
1. `layout.html` - shared layout with sidebar
2. `index.html` - dashboard with stats
3. `accounts.html` - account list with filters
4. `tasks.html` - task list and creation

### Phase 2: Management Pages
5. `workers.html` - worker list
6. `queue.html` - queue controls
7. `dead-letter.html` - failed tasks

### Phase 3: Additional Pages
8. `proxies.html` - proxy management
9. `settings.html` - app settings

---

## 13. Future Improvements (Out of Scope)

- WebSocket real-time updates
- Multi-user authentication
- Task scheduling (cron)
- Advanced analytics
- Mobile app

---

## 14. AntiGravity IDE Notes

When generating code:

1. **Use Tailwind classes** for all styling - no inline styles
2. **HTMX attributes** for interactivity - `hx-get`, `hx-post`, `hx-trigger`
3. **Dark theme by default** - `class="dark"` on html element
4. **Semantic HTML** - proper `<button>`, `<input>`, `<table>` tags
5. **Accessible** - proper `aria-*` labels on interactive elements
