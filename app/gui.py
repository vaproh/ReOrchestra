from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.config import get_settings

router = APIRouter()
settings = get_settings()


GUI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Reddit Automation</title>
<style>
  :root {
    --bg: #0e1113;
    --panel: #161b22;
    --border: #30363d;
    --text: #c9d1d9;
    --muted: #8b949e;
    --accent: #ff4500;
    --accent2: #58a6ff;
    --ok: #23d18b;
    --err: #f85149;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  }
  header {
    padding: 16px 24px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 12px;
  }
  header h1 { margin: 0; font-size: 18px; color: var(--accent); }
  header .sub { color: var(--muted); font-size: 13px; }
  main { padding: 24px; max-width: 1100px; margin: 0 auto; }
  .row { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .panel {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
  }
  .panel h2 { margin: 0 0 12px 0; font-size: 14px; color: var(--accent2); }
  .status { display: flex; flex-direction: column; gap: 8px; }
  .status .item { display: flex; align-items: center; gap: 8px; font-size: 13px; }
  .dot { width: 10px; height: 10px; border-radius: 50%; background: var(--muted); }
  .dot.ok { background: var(--ok); }
  .dot.err { background: var(--err); }
  .dot.unk { background: var(--muted); }
  label { display: block; font-size: 12px; color: var(--muted); margin: 8px 0 4px; }
  input, select {
    width: 100%;
    padding: 8px 10px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    font-size: 13px;
  }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  button {
    margin-top: 12px;
    width: 100%;
    padding: 10px;
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
  }
  button:hover { filter: brightness(1.1); }
  button:disabled { opacity: 0.5; cursor: not-allowed; }
  button.secondary { background: #21262d; border: 1px solid var(--border); }
  button.secondary:hover { background: #30363d; }
  .log {
    background: #000;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    height: 280px;
    overflow-y: auto;
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 12px;
    line-height: 1.5;
  }
  .log .line { white-space: pre-wrap; word-break: break-word; }
  .log .ok { color: var(--ok); }
  .log .err { color: var(--err); }
  .log .info { color: var(--accent2); }
  .log .muted { color: var(--muted); }
  .tabs { display: flex; gap: 8px; margin-bottom: 12px; }
  .tabs button { width: auto; flex: 1; }
  .result { font-size: 13px; margin-top: 10px; color: var(--muted); }
  a.vnc { color: var(--accent2); font-size: 13px; text-decoration: none; }
  a.vnc:hover { text-decoration: underline; }
</style>
</head>
<body>
<header>
  <h1>Reddit Automation</h1>
  <span class="sub" id="version">v1.0</span>
</header>
<main>
  <div class="row">
    <div class="panel">
      <h2>System Status</h2>
      <div class="status">
        <div class="item"><span class="dot unk" id="dot-camofox"></span> <span id="st-camofox">Camofox: checking...</span></div>
        <div class="item"><span class="dot unk" id="dot-api"></span> <span id="st-api">API: checking...</span></div>
        <div class="item"><span class="dot unk" id="dot-slots"></span> <span id="st-slots">Slots: checking...</span></div>
        <div class="item"><span class="dot unk" id="dot-db"></span> <span id="st-db">DB: checking...</span></div>
        <div class="item" id="vnc-item" style="display:none">
          <span class="dot ok"></span>
          <span>VNC: </span>
          <a class="vnc" id="vnc-link" target="_blank">Open VNC</a>
        </div>
      </div>
      <button class="secondary" onclick="refreshStatus()">Refresh</button>
    </div>

    <div class="panel">
      <h2>Account Stats</h2>
      <div class="status">
        <div class="item"><span id="stat-total">0</span> total accounts</div>
        <div class="item"><span id="stat-active">0</span> active</div>
        <div class="item"><span id="stat-dead">0</span> dead</div>
        <div class="item"><span id="stat-proxies">0</span> proxies</div>
        <div class="item"><span id="stat-votes-today">0</span> votes today</div>
      </div>
    </div>

    <div class="panel">
      <h2>Login Account</h2>
      <label>Username</label>
      <input type="text" id="login-username" placeholder="username">
      <label>Password</label>
      <input type="text" id="login-password" placeholder="password">
      <label>Headless</label>
      <select id="login-headless"><option value="false">No (watch)</option><option value="true">Yes (headless)</option></select>
      <button onclick="loginAccount()">Login</button>
      <div class="result" id="login-result"></div>
    </div>
  </div>

  <div class="row">
    <div class="panel">
      <h2>Upvote Post</h2>
      <label>Post URL</label>
      <input type="text" id="upvote-url" placeholder="https://www.reddit.com/r/.../comments/xyz/...">
      <label>Account username</label>
      <input type="text" id="upvote-username" placeholder="account username">
      <button id="upvote-btn" onclick="doVote('up')">Upvote</button>
      <div class="result" id="upvote-result"></div>
    </div>

    <div class="panel">
      <h2>Downvote Post</h2>
      <label>Post URL</label>
      <input type="text" id="downvote-url" placeholder="https://www.reddit.com/r/.../comments/xyz/...">
      <label>Account username</label>
      <input type="text" id="downvote-username" placeholder="account username">
      <button id="downvote-btn" onclick="doVote('down')">Downvote</button>
      <div class="result" id="downvote-result"></div>
    </div>

    <div class="panel">
      <h2>Verify Vote</h2>
      <label>Post URL</label>
      <input type="text" id="verify-url" placeholder="https://www.reddit.com/r/.../comments/xyz/...">
      <label>Account username</label>
      <input type="text" id="verify-username" placeholder="account username">
      <button class="secondary" onclick="verifyVote()">Verify</button>
      <div class="result" id="verify-result"></div>
    </div>
  </div>

  <div class="panel">
    <h2>Log</h2>
    <div class="log" id="log">
      <div class="line muted">Ready.</div>
    </div>
  </div>
</main>

<script>
function log(msg, cls) {
  const el = document.getElementById('log');
  const line = document.createElement('div');
  line.className = 'line ' + (cls || 'muted');
  const ts = new Date().toLocaleTimeString();
  line.textContent = '[' + ts + '] ' + msg;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

async function api(path, method, body) {
  const opts = { method: method || 'GET', headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const resp = await fetch('/api' + path, opts);
  return resp.json();
}

async function refreshStatus() {
  // Camofox
  try {
    const r = await fetch('/api/admin/health').catch(() => null);
    const data = r ? await r.json() : null;
    const dot = document.getElementById('dot-camofox');
    const txt = document.getElementById('st-camofox');
    if (data && data.data && data.data.camofox) {
      const ok = !!data.data.camofox.connected;
      dot.className = 'dot ' + (ok ? 'ok' : 'err');
      txt.textContent = 'Camofox: ' + (ok ? 'Connected' : 'Disconnected') + (data.data.camofox.url ? ' (' + data.data.camofox.url + ')' : '');
    } else {
      dot.className = 'dot err';
      txt.textContent = 'Camofox: not configured';
    }
  } catch (e) {
    document.getElementById('dot-camofox').className = 'dot err';
    document.getElementById('st-camofox').textContent = 'Camofox: error';
  }

  // API
  try {
    const r = await fetch('/');
    const ok = r.ok;
    document.getElementById('dot-api').className = 'dot ' + (ok ? 'ok' : 'err');
    document.getElementById('st-api').textContent = 'API: ' + (ok ? 'Running' : 'Error');
  } catch (e) {
    document.getElementById('dot-api').className = 'dot err';
    document.getElementById('st-api').textContent = 'API: offline';
  }

  // Slots
  try {
    const r = await fetch('/api/admin/stats').catch(() => null);
    const data = r ? await r.json() : null;
    const dot = document.getElementById('dot-slots');
    const txt = document.getElementById('st-slots');
    if (data && data.data && data.data.slots) {
      const s = data.data.slots;
      const ok = s.running > 0;
      dot.className = 'dot ' + (ok ? 'ok' : (s.crashed > 0 ? 'err' : 'unk'));
      txt.textContent = 'Slots: ' + s.running + '/' + s.total + ' running (cap: ' + s.total_capacity + ')';
    } else {
      dot.className = 'dot unk';
      txt.textContent = 'Slots: no data';
    }
  } catch (e) {
    document.getElementById('dot-slots').className = 'dot unk';
    document.getElementById('st-slots').textContent = 'Slots: error';
  }

  // DB check
  try {
    const r = await fetch('/api/accounts?limit=1').catch(() => null);
    const ok = r && r.ok;
    document.getElementById('dot-db').className = 'dot ' + (ok ? 'ok' : 'err');
    document.getElementById('st-db').textContent = 'DB: ' + (ok ? 'Connected' : 'Error');
  } catch (e) {
    document.getElementById('dot-db').className = 'dot err';
    document.getElementById('st-db').textContent = 'DB: offline';
  }

  // Account stats
  try {
    const r = await fetch('/api/admin/stats').catch(() => null);
    const data = r ? await r.json() : null;
    if (data && data.data && data.data.accounts) {
      const a = data.data.accounts;
      document.getElementById('stat-total').textContent = a.total || 0;
      document.getElementById('stat-active').textContent = a.active || 0;
      document.getElementById('stat-dead').textContent = a.dead || 0;
      document.getElementById('stat-proxies').textContent = a.proxies || 0;
      document.getElementById('stat-votes-today').textContent = a.votes_today || 0;
    }
  } catch (e) {
    // silently fail for stats
  }
}

async function loginAccount() {
  const username = document.getElementById('login-username').value;
  const password = document.getElementById('login-password').value;
  const headless = document.getElementById('login-headless').value === 'true';
  if (!username || !password) { log('Enter username + password', 'err'); return; }
  log('Logging in ' + username + '...', 'info');
  try {
    const data = await api('/accounts/login', 'POST', {
      account_ids: [],
      force: false,
      options: { headless: headless }
    });
    log('Login result: ' + JSON.stringify(data.data), data.data && data.data.logged_in > 0 ? 'ok' : 'err');
    document.getElementById('login-result').textContent = JSON.stringify(data.data);
  } catch (e) {
    log('Login failed: ' + e.message, 'err');
    document.getElementById('login-result').textContent = 'Error: ' + e.message;
  }
}

async function doVote(dir) {
  const url = document.getElementById(dir + 'vote-url').value;
  const username = document.getElementById(dir + 'vote-username').value;
  if (!url || !username) { log('Enter URL + username', 'err'); return; }
  log('Voting ' + dir + ' via browser for ' + username + ' on ' + url, 'info');
  try {
    const data = await api('/actions/' + dir + 'vote', 'POST', {
      account_ids: [],
      filters: {},
      username: username,
      target_url: url
    });
    const d = data.data || {};
    log('Vote result: ' + (d.succeeded || 0) + '/' + (d.total || 0) + ' succeeded', d.succeeded > 0 ? 'ok' : 'err');
    if (d.results) d.results.forEach(r => log('  -> ' + r.username + ': ' + (r.success ? 'OK' : 'FAIL ' + (r.error || '')), r.success ? 'ok' : 'err'));
    document.getElementById(dir + 'vote-result').textContent = JSON.stringify(data.data);
  } catch (e) {
    log('Vote failed: ' + e.message, 'err');
    document.getElementById(dir + 'vote-result').textContent = 'Error: ' + e.message;
  }
}

async function verifyVote() {
  const url = document.getElementById('verify-url').value;
  const username = document.getElementById('verify-username').value;
  if (!url || !username) { log('Enter URL + username', 'err'); return; }
  log('Verifying vote for ' + username + '...', 'info');
  try {
    // First need account_id - look up accounts list
    const list = await api('/accounts?search=' + encodeURIComponent(username));
    const accs = (list.data && list.data.accounts) || [];
    const acc = accs.find(a => a.username === username);
    if (!acc) { log('Account not found: ' + username, 'err'); return; }
    log('Found account id=' + acc.id, 'muted');
    document.getElementById('verify-result').textContent = 'Account id: ' + acc.id;
  } catch (e) {
    log('Verify failed: ' + e.message, 'err');
    document.getElementById('verify-result').textContent = 'Error: ' + e.message;
  }
}

refreshStatus();
setInterval(refreshStatus, 30000);
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def gui():
    return GUI_HTML