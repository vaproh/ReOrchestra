/**
 * ReOrchestra — app.js
 * Vanilla JS utilities: toasts, API fetch, HTMX handlers, demo data, renders
 */

/* =====================================================
   TOAST SYSTEM
   ===================================================== */
const ToastIcons = {
  success: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>`,
  error:   `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M18 6L6 18M6 6l12 12"/></svg>`,
  info:    `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>`,
  warning: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><path d="M12 9v4M12 17h.01"/></svg>`,
};

function ensureToastContainer() {
  let c = document.getElementById('toast-container');
  if (!c) {
    c = document.createElement('div');
    c.id = 'toast-container';
    document.body.appendChild(c);
  }
  return c;
}

function showToast(message, type = 'info', duration = 4000) {
  const container = ensureToastContainer();
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `${ToastIcons[type] || ''}<span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('out');
    toast.addEventListener('animationend', () => toast.remove());
  }, duration);
}

/* =====================================================
   HTMX EVENT HANDLERS
   ===================================================== */
document.addEventListener('DOMContentLoaded', () => {
  // HTMX success feedback
  document.body.addEventListener('htmx:afterRequest', (e) => {
    if (!e.detail.successful) return;
    const method = e.detail.requestConfig?.verb?.toUpperCase();
    if (method === 'POST' || method === 'DELETE' || method === 'PATCH') {
      showToast('Action completed successfully', 'success');
    }
  });

  // HTMX error feedback
  document.body.addEventListener('htmx:responseError', (e) => {
    const status = e.detail.xhr?.status;
    showToast(`Request failed (${status || 'network error'})`, 'error');
  });

  // HTMX send indicator
  document.body.addEventListener('htmx:beforeSend', (e) => {
    const indicator = e.detail.elt.querySelector('.htmx-indicator');
    if (indicator) indicator.style.display = 'inline-flex';
  });
  document.body.addEventListener('htmx:afterOnLoad', (e) => {
    const indicator = e.detail.elt.querySelector('.htmx-indicator');
    if (indicator) indicator.style.display = '';
  });
});

/* =====================================================
   SIDEBAR MOBILE TOGGLE
   ===================================================== */
function initSidebar() {
  const toggle = document.getElementById('sidebar-toggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (!toggle || !sidebar) return;

  toggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });
  overlay?.addEventListener('click', () => {
    sidebar.classList.remove('open');
  });
}

/* =====================================================
   CHECKBOX SELECT ALL
   ===================================================== */
function initSelectAll(selectAllId, rowCheckboxClass, bulkBarId, countId) {
  const selectAll = document.getElementById(selectAllId);
  const bulkBar  = document.getElementById(bulkBarId);
  const countEl  = document.getElementById(countId);
  if (!selectAll) return;

  function updateBulkBar() {
    const checked = document.querySelectorAll(`.${rowCheckboxClass}:checked`);
    if (bulkBar) {
      bulkBar.classList.toggle('visible', checked.length > 0);
    }
    if (countEl) countEl.textContent = checked.length;
  }

  selectAll.addEventListener('change', () => {
    document.querySelectorAll(`.${rowCheckboxClass}`).forEach(cb => {
      cb.checked = selectAll.checked;
    });
    updateBulkBar();
  });

  document.querySelectorAll(`.${rowCheckboxClass}`).forEach(cb => {
    cb.addEventListener('change', () => {
      const all = document.querySelectorAll(`.${rowCheckboxClass}`);
      selectAll.indeterminate = [...all].some(c => c.checked) && ![...all].every(c => c.checked);
      selectAll.checked = [...all].every(c => c.checked);
      updateBulkBar();
    });
  });
}

/* =====================================================
   COLLAPSIBLE PANELS
   ===================================================== */
function initCollapsible(toggleId, panelId) {
  const toggle = document.getElementById(toggleId);
  const panel  = document.getElementById(panelId);
  if (!toggle || !panel) return;

  // Set initial max-height
  function expand() {
    panel.style.maxHeight = panel.scrollHeight + 'px';
    panel.classList.remove('collapsed');
    toggle.setAttribute('aria-expanded', 'true');
  }
  function collapse() {
    panel.style.maxHeight = '0';
    panel.classList.add('collapsed');
    toggle.setAttribute('aria-expanded', 'false');
  }

  panel.classList.add('collapsed');
  panel.style.maxHeight = '0';

  toggle.addEventListener('click', () => {
    if (panel.classList.contains('collapsed')) expand();
    else collapse();
  });
}

/* =====================================================
   API UTILITIES
   ===================================================== */
const API_BASE = '/api';

async function apiFetch(path, options = {}) {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn(`[ReOrchestra] API ${path} failed:`, err.message);
    return null;
  }
}

/* =====================================================
   RENDER HELPERS
   ===================================================== */
function statusBadge(status) {
  const map = {
    active:       ['badge-success', 'Active'],
    logged_in:    ['badge-success', 'Logged In'],
    fresh:        ['badge-info',    'Fresh'],
    suspended:    ['badge-error',   'Suspended'],
    banned:       ['badge-error',   'Banned'],
    burned:       ['badge-error',   'Burned'],
    paused:       ['badge-warning', 'Paused'],
    running:      ['badge-accent',  'Running'],
    pending:      ['badge-neutral', 'Pending'],
    completed:    ['badge-success', 'Completed'],
    failed:       ['badge-error',   'Failed'],
    cancelled:    ['badge-neutral', 'Cancelled'],
    dead:         ['badge-error',   'Dead'],
    healthy:      ['badge-success', 'Healthy'],
    idle:         ['badge-neutral', 'Idle'],
  };
  const [cls, label] = map[status] || ['badge-neutral', status || 'Unknown'];
  return `<span class="badge ${cls}">${label}</span>`;
}

function actionLabel(action) {
  const labels = {
    upvote_post:        '⬆ Upvote Post',
    downvote_post:      '⬇ Downvote Post',
    upvote_comment:     '⬆ Upvote Comment',
    downvote_comment:   '⬇ Downvote Comment',
    follow_user:        '👤 Follow User',
    unfollow_user:      '👤 Unfollow',
    join_subreddit:     '🔗 Join Sub',
    leave_subreddit:    '🔗 Leave Sub',
    save_post:          '🔖 Save Post',
  };
  return labels[action] || action;
}

function truncUrl(url, max = 40) {
  if (!url) return '—';
  try {
    const u = new URL(url);
    const path = u.pathname + u.search;
    return path.length > max ? path.slice(0, max) + '…' : path;
  } catch {
    return url.length > max ? url.slice(0, max) + '…' : url;
  }
}

function progressBar(done, total) {
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;
  const cls = pct >= 100 ? 'success' : '';
  return `
    <div class="flex items-center gap-2">
      <div class="progress-bar">
        <div class="progress-bar-fill ${cls}" style="width:${pct}%"></div>
      </div>
      <span class="text-xs text-ink-subtle">${done}/${total}</span>
    </div>`;
}

function timeAgo(iso) {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s/60)}m ago`;
  if (s < 86400) return `${Math.floor(s/3600)}h ago`;
  return `${Math.floor(s/86400)}d ago`;
}

/* =====================================================
   DASHBOARD — load stats
   ===================================================== */
async function loadDashboardStats() {
  const [stats, health, queueStatus] = await Promise.all([
    apiFetch('/admin/stats'),
    apiFetch('/admin/health'),
    apiFetch('/queue/status'),
  ]);

  if (stats) {
    setTextSafe('stat-accounts', stats.total_accounts ?? '—');
    setTextSafe('stat-workers',  stats.active_workers  ?? '—');
    setTextSafe('stat-tasks',    stats.running_tasks    ?? '—');
    setTextSafe('stat-actions',  stats.actions_today    ?? '—');
  }

  if (health) {
    const camofoxOk = health.camofox === 'ok' || health.camofox === true;
    const dbOk      = health.database === 'ok' || health.database === true;
    setHtmlSafe('health-camofox', camofoxOk
      ? `<span class="badge badge-success">Connected</span>`
      : `<span class="badge badge-error">Disconnected</span>`);
    setHtmlSafe('health-db', dbOk
      ? `<span class="badge badge-success">OK</span>`
      : `<span class="badge badge-error">Error</span>`);
  }

  if (queueStatus) {
    const running = queueStatus.running === true || queueStatus.status === 'running';
    setHtmlSafe('queue-status-dot', `<span class="status-dot ${running ? 'running' : 'stopped'}"></span>`);
    setTextSafe('queue-status-text', running ? 'Running' : 'Stopped');
  }
}

async function loadRecentTasks() {
  const tasks = await apiFetch('/tasks?limit=10');
  const tbody = document.getElementById('recent-tasks-body');
  if (!tbody) return;
  if (tasks === null) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p style="color:var(--error)">⚠ Cannot connect to API.</p></div></td></tr>`;
    return;
  }
  if (!tasks.length) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p>No tasks yet.</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = tasks.map(t => `
    <tr>
      <td><span class="code-pill">#${t.id}</span></td>
      <td><span class="text-xs">${actionLabel(t.action_type)}</span></td>
      <td><span class="mono text-xs text-ink-subtle" title="${t.target_url}">${truncUrl(t.target_url)}</span></td>
      <td>${progressBar(t.completed_workers ?? 0, t.workers_needed ?? 1)}</td>
      <td>${statusBadge(t.status)}</td>
    </tr>
  `).join('');
}

/* =====================================================
   ACCOUNTS PAGE
   ===================================================== */
async function loadAccounts(page = 1, status = '', search = '') {
  const params = new URLSearchParams({ page, limit: 50 });
  if (status) params.set('status', status);
  if (search) params.set('search', search);
  const accounts = await apiFetch(`/accounts?${params}`);
  const tbody = document.getElementById('accounts-tbody');
  if (!tbody) return;
  // null means API error — show error state
  if (accounts === null) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><p style="color:var(--error)">⚠ Cannot connect to API. Is the backend running?</p></div></td></tr>`;
    return;
  }
  if (!accounts.length) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><p>No accounts yet. Import some to get started.</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = accounts.map(a => `
    <tr>
      <td><input type="checkbox" class="account-cb" value="${a.id}"></td>
      <td>
        <div class="flex items-center gap-2">
          <span class="font-medium text-ink">${a.username}</span>
        </div>
      </td>
      <td>${statusBadge(a.status)}</td>
      <td><span class="mono text-xs text-ink-subtle">${a.proxy_host || '—'}</span></td>
      <td><span class="text-ink-subtle text-xs">${a.daily_votes ?? 0}</span></td>
      <td><span class="text-ink-subtle text-xs">${a.weekly_votes ?? 0}</span></td>
      <td>
        <div class="flex items-center gap-1">
          <button class="btn btn-sm btn-ghost" onclick="loginAccount(${a.id})" data-tooltip="Login">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
          </button>
          <button class="btn btn-sm btn-danger" onclick="deleteAccount(${a.id})" data-tooltip="Delete">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/></svg>
          </button>
        </div>
      </td>
    </tr>
  `).join('');
  initSelectAll('select-all-accounts', 'account-cb', 'bulk-action-bar', 'selected-count');
}

async function loginAccount(id) {
  showToast(`Logging in account #${id}…`, 'info');
  const res = await apiFetch(`/accounts/login`, { method: 'POST', body: JSON.stringify({ account_id: id }) });
  if (res) showToast(`Account #${id} login initiated`, 'success');
  else showToast(`Login failed for account #${id}`, 'error');
}

async function deleteAccount(id) {
  if (!confirm(`Delete account #${id}? This cannot be undone.`)) return;
  const res = await apiFetch(`/accounts/${id}`, { method: 'DELETE' });
  if (res !== null) {
    showToast(`Account #${id} deleted`, 'success');
    loadAccounts();
  } else {
    showToast(`Failed to delete account #${id}`, 'error');
  }
}

/* =====================================================
   TASKS PAGE
   ===================================================== */
async function loadTasks(status = '') {
  const params = new URLSearchParams({ limit: 50 });
  if (status) params.set('status', status);
  const tasks = await apiFetch(`/tasks?${params}`);
  const tbody = document.getElementById('tasks-tbody');
  if (!tbody) return;
  if (tasks === null) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><p style="color:var(--error)">⚠ Cannot connect to API. Is the backend running?</p></div></td></tr>`;
    return;
  }
  if (!tasks.length) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><p>No tasks yet. Create one to get started.</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = tasks.map(t => `
    <tr>
      <td><span class="code-pill">#${t.id}</span></td>
      <td><span class="text-xs">${actionLabel(t.action_type)}</span></td>
      <td><span class="mono text-xs text-ink-subtle" title="${t.target_url}">${truncUrl(t.target_url, 35)}</span></td>
      <td>${progressBar(t.completed_workers ?? 0, t.workers_needed ?? 1)}</td>
      <td>${statusBadge(t.status)}</td>
      <td>
        <div class="flex items-center gap-1">
          ${t.status === 'running' || t.status === 'pending'
            ? `<button class="btn btn-sm btn-ghost" onclick="cancelTask(${t.id})">Cancel</button>` : ''}
          ${t.status === 'failed'
            ? `<button class="btn btn-sm btn-secondary" onclick="retryTask(${t.id})">Retry</button>` : ''}
        </div>
      </td>
    </tr>
  `).join('');
}

async function cancelTask(id) {
  if (!confirm(`Cancel task #${id}?`)) return;
  await apiFetch(`/tasks/${id}/cancel`, { method: 'POST' });
  showToast(`Task #${id} cancelled`, 'info');
  loadTasks();
}

async function retryTask(id) {
  await apiFetch(`/tasks/${id}/retry`, { method: 'POST' });
  showToast(`Task #${id} queued for retry`, 'success');
  loadTasks();
}

/* =====================================================
   WORKERS PAGE
   ===================================================== */
async function loadWorkers() {
  const workers = await apiFetch('/workers');
  const tbody = document.getElementById('workers-tbody');
  if (!tbody) return;
  if (workers === null) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p style="color:var(--error)">⚠ Cannot connect to API. Is the backend running?</p></div></td></tr>`;
    return;
  }
  if (!workers.length) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p>No workers yet. Create workers from the Accounts page.</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = workers.map(w => `
    <tr>
      <td><span class="code-pill">W${w.id}</span></td>
      <td><span class="text-sm font-medium">${w.username || `Account #${w.account_id}`}</span></td>
      <td>${statusBadge(w.status)}</td>
      <td><span class="text-xs text-ink-subtle">${w.current_task ? `Task #${w.current_task}` : '—'}</span></td>
      <td>
        <div class="flex items-center gap-1">
          ${w.status === 'active'
            ? `<button class="btn btn-sm btn-ghost" onclick="pauseWorker(${w.id})">Pause</button>` : ''}
          ${w.status === 'paused'
            ? `<button class="btn btn-sm btn-success" onclick="resumeWorker(${w.id})">Resume</button>` : ''}
        </div>
      </td>
    </tr>
  `).join('');
}

async function pauseWorker(id) {
  await apiFetch(`/workers/${id}/pause`, { method: 'POST' });
  showToast(`Worker W${id} paused`, 'info');
  loadWorkers();
}
async function resumeWorker(id) {
  await apiFetch(`/workers/${id}/resume`, { method: 'POST' });
  showToast(`Worker W${id} resumed`, 'success');
  loadWorkers();
}

/* =====================================================
   QUEUE PAGE
   ===================================================== */
async function loadQueueStatus() {
  const status = await apiFetch('/queue/status');
  if (status === null) {
    setHtmlSafe('q-status-dot', `<span class="status-dot stopped"></span>`);
    setTextSafe('q-status-text', 'API Offline');
    setTextSafe('q-pending', '—');
    setTextSafe('q-running', '—');
    setTextSafe('q-completed', '—');
    
    // Also mark active tasks as failed to load
    const activeTbody = document.getElementById('queue-active-tasks');
    if (activeTbody) {
      activeTbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p style="color:var(--error)">⚠ Cannot connect to API.</p></div></td></tr>`;
    }
    return;
  }
  const running = status.running === true || status.status === 'running';
  setHtmlSafe('q-status-dot',  `<span class="status-dot ${running ? 'running' : 'stopped'}"></span>`);
  setTextSafe('q-status-text', running ? 'Running' : 'Stopped');
  setTextSafe('q-pending',    status.pending_tasks ?? '—');
  setTextSafe('q-running',    status.running_tasks ?? '—');
  setTextSafe('q-completed',  status.completed_today ?? '—');

  const startBtn = document.getElementById('q-start-btn');
  const stopBtn  = document.getElementById('q-stop-btn');
  if (startBtn) startBtn.disabled = running;
  if (stopBtn)  stopBtn.disabled  = !running;
}

async function startQueue() {
  const res = await apiFetch('/queue/start', { method: 'POST' });
  if (res !== null) { showToast('Queue processor started', 'success'); loadQueueStatus(); }
  else showToast('Failed to start queue', 'error');
}
async function stopQueue() {
  if (!confirm('Stop the queue processor? In-flight tasks will complete.')) return;
  const res = await apiFetch('/queue/stop', { method: 'POST' });
  if (res !== null) { showToast('Queue processor stopped', 'info'); loadQueueStatus(); }
  else showToast('Failed to stop queue', 'error');
}

async function loadQueueTasks() {
  const tasks = await apiFetch('/tasks?status=running,pending&limit=10');
  const tbody = document.getElementById('queue-active-tasks');
  if (!tbody) return;
  if (tasks === null) {
    // API error is handled by loadQueueStatus which sets the API Offline message.
    return; 
  }
  if (!tasks.length) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p>No tasks currently in queue.</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = tasks.map(t => `
    <tr>
      <td><span class="code-pill">#${t.id}</span></td>
      <td><span class="text-xs">${actionLabel(t.action_type)}</span></td>
      <td><span class="badge ${t.priority === 'High' ? 'badge-error' : 'badge-neutral'}">${t.priority || 'Normal'}</span></td>
      <td>
        <div class="flex items-center gap-2">
          <div class="progress-bar"><div class="progress-bar-fill" style="width:${(t.completed_workers/t.workers_needed)*100 || 0}%"></div></div>
          <span class="text-xs" style="color:var(--ink-subtle)">${t.completed_workers ?? 0}/${t.workers_needed ?? 1}</span>
        </div>
      </td>
      <td>${statusBadge(t.status)}</td>
    </tr>
  `).join('');
}

/* =====================================================
   DEAD LETTER PAGE
   ===================================================== */
async function loadDeadLetter() {
  const tasks = await apiFetch('/tasks?status=failed&limit=100');
  const tbody = document.getElementById('dead-letter-tbody');
  if (!tbody) return;
  if (tasks === null) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><p style="color:var(--error)">⚠ Cannot connect to API. Is the backend running?</p></div></td></tr>`;
    return;
  }
  if (!tasks.length) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><p>No failed tasks. 🎉</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = tasks.map(t => `
    <tr>
      <td><span class="code-pill">#${t.id}</span></td>
      <td><span class="text-xs">${actionLabel(t.action_type)}</span></td>
      <td><span class="mono text-xs text-ink-subtle" title="${t.target_url}">${truncUrl(t.target_url, 35)}</span></td>
      <td><span class="text-xs text-error">${t.error_message || t.outcome || 'Unknown error'}</span></td>
      <td><span class="text-xs text-ink-subtle">${t.attempts ?? 0}/3</span></td>
      <td>
        <button class="btn btn-sm btn-secondary" onclick="retryTask(${t.id})">Retry</button>
      </td>
    </tr>
  `).join('');
}

/* =====================================================
   PROXIES PAGE
   ===================================================== */
async function loadProxies() {
  const proxies = await apiFetch('/proxies');
  const tbody = document.getElementById('proxies-tbody');
  if (!tbody) return;
  if (proxies === null) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p style="color:var(--error)">⚠ Cannot connect to API. Is the backend running?</p></div></td></tr>`;
    return;
  }
  if (!proxies.length) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p>No proxies yet. Import some above.</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = proxies.map(p => `
    <tr>
      <td><span class="mono text-xs">${p.host}:${p.port}</span></td>
      <td><span class="text-xs uppercase text-ink-subtle">${p.protocol || 'http'}</span></td>
      <td><span class="text-xs text-ink-subtle">${p.assigned_accounts ?? 0}</span></td>
      <td>${statusBadge(p.status || 'active')}</td>
      <td>
        <button class="btn btn-sm btn-ghost" onclick="markProxyDead(${p.id})">Mark Dead</button>
      </td>
    </tr>
  `).join('');
}

async function markProxyDead(id) {
  await apiFetch(`/proxies/${id}/mark-dead`, { method: 'POST' });
  showToast(`Proxy #${id} marked as dead`, 'warning');
  loadProxies();
}

/* =====================================================
   UTILS
   ===================================================== */
function setTextSafe(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
function setHtmlSafe(id, val) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = val;
}

// Number formatting
function fmtNum(n) {
  if (n === null || n === undefined) return '—';
  return Number(n).toLocaleString();
}

/* =====================================================
   AUTO-REFRESH
   ===================================================== */
function startPolling(fn, intervalMs) {
  fn(); // immediate
  return setInterval(fn, intervalMs);
}

/* =====================================================
   PAGE INIT — called by each page's inline script
   ===================================================== */
window.ReOrchestra = {
  showToast, initSidebar, initSelectAll, initCollapsible,
  loadDashboardStats, loadRecentTasks,
  loadAccounts, loginAccount, deleteAccount,
  loadTasks, cancelTask, retryTask,
  loadWorkers, pauseWorker, resumeWorker,
  loadQueueStatus, loadQueueTasks, startQueue, stopQueue,
  loadDeadLetter, loadProxies, markProxyDead,
  startPolling, statusBadge, actionLabel, truncUrl, progressBar,
};
