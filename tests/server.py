"""
Reddit Test Server - Simulates Reddit for testing without real network calls.

For vote actions: popup appears AFTER clicking the vote button (simulating Reddit behavior).
"""
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from typing import Optional
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.logging_config import setup_logging

setup_logging("test_server")
logger = logging.getLogger("test_server")

app = FastAPI(title="Reddit Test Server")

UPVOTE_COUNT = 42
DOWNVOTE_COUNT = 7

SCENARIOS = {"suspended", "locked", "rate_limited", "banned"}


@app.get("/post/{post_id}", response_class=HTMLResponse)
async def post_page(request: Request, post_id: str, scenario: Optional[str] = None):
    scenario = scenario if scenario in SCENARIOS else None

    return f'''<!DOCTYPE html>
<html>
<head>
    <title>r/test - Reddit Test Server</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; }}
        .vote-buttons {{ display: flex; gap: 10px; margin: 10px 0; }}
        .vote-btn {{ padding: 5px 15px; cursor: pointer; }}
        .vote-btn.upvoted {{ color: #ff4500; }}
        .vote-btn.downvoted {{ color: #7193ff; }}
        .modal-overlay {{ position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: none; align-items: center; justify-content: center; }}
        .modal-overlay.show {{ display: flex; }}
        .modal {{ background: white; padding: 30px; border-radius: 8px; text-align: center; }}
        .modal h2 {{ color: #d93a00; }}
    </style>
</head>
<body>
    <h1>r/test - Test Post {post_id}</h1>
    <p>This is a test post for testing ReOrchestra automation.</p>
    
    <div class="vote-buttons">
        <button class="vote-btn upvote" id="upvoteBtn" data-post-id="{post_id}">upvote</button>
        <span class="upvote-count">{UPVOTE_COUNT}</span>
        <button class="vote-btn downvote" id="downvoteBtn" data-post-id="{post_id}">downvote</button>
        <span class="downvote-count">{DOWNVOTE_COUNT}</span>
        <button class="vote-btn save" id="saveBtn">save</button>
    </div>
    
    <div id="scenario" data-scenario="{scenario or ''}" style="display:none"></div>
    <p>Scenario: {{scenario or 'none'}}</p>
    
    <div class="modal-overlay" id="modal">
        <div class="modal">
            <h2 id="modalTitle">Notice</h2>
            <p id="modalMessage"></p>
        </div>
    </div>
    
    <script>
    const upvoteBtn = document.getElementById('upvoteBtn');
    const downvoteBtn = document.getElementById('downvoteBtn');
    const saveBtn = document.getElementById('saveBtn');
    const modal = document.getElementById('modal');
    const modalTitle = document.getElementById('modalTitle');
    const modalMessage = document.getElementById('modalMessage');
    const scenarioEl = document.getElementById('scenario');
    const scenario = scenarioEl.dataset.scenario;
    
    upvoteBtn.addEventListener('click', function() {{
        upvoteBtn.classList.add('upvoted');
        upvoteBtn.textContent = 'upvote';
        
        // Show popup AFTER clicking based on scenario
        if (scenario === 'suspended') {{
            modalTitle.textContent = 'Account Suspended';
            modalMessage.textContent = 'Your account has been suspended due to unusual activity.';
            modal.classList.add('show');
        }} else if (scenario === 'locked') {{
            modalTitle.textContent = 'Account Locked';
            modalMessage.textContent = 'This account has been locked. You will need to reset your password.';
            modal.classList.add('show');
        }} else if (scenario === 'rate_limited') {{
            modalTitle.textContent = 'Rate Limit Exceeded';
            modalMessage.textContent = 'You are doing that too much. Please try again later.';
            modal.classList.add('show');
        }}
    }});
    
    downvoteBtn.addEventListener('click', function() {{
        downvoteBtn.classList.add('downvoted');
    }});
    
    saveBtn.addEventListener('click', function() {{
        saveBtn.textContent = 'saved';
    }});
    </script>
</body>
</html>'''


@app.get("/comment/{comment_id}", response_class=HTMLResponse)
async def comment_page(request: Request, comment_id: str, scenario: Optional[str] = None):
    scenario = scenario if scenario in SCENARIOS else None

    return f'''<!DOCTYPE html>
<html>
<head><title>Comment - Reddit Test Server</title>
<style>
    body {{ font-family: sans-serif; margin: 20px; }}
    .vote-btn {{ padding: 5px 15px; cursor: pointer; }}
    .modal-overlay {{ position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: none; align-items: center; justify-content: center; }}
    .modal-overlay.show {{ display: flex; }}
    .modal {{ background: white; padding: 30px; border-radius: 8px; text-align: center; }}
</style>
</head>
<body>
    <h1>Comment {comment_id}</h1>
    <p>This is a single comment's thread for testing.</p>
    
    <div class="vote-buttons">
        <button class="vote-btn upvote" id="upvoteBtn">upvote</button>
        <button class="vote-btn downvote" id="downvoteBtn">downvote</button>
    </div>
    
    <div id="scenario" data-scenario="{scenario or ''}" style="display:none"></div>
    
    <div class="modal-overlay" id="modal">
        <div class="modal">
            <h2 id="modalTitle">Notice</h2>
            <p id="modalMessage"></p>
        </div>
    </div>
    
    <script>
    const upvoteBtn = document.getElementById('upvoteBtn');
    const downvoteBtn = document.getElementById('downvoteBtn');
    const modal = document.getElementById('modal');
    const modalTitle = document.getElementById('modalTitle');
    const modalMessage = document.getElementById('modalMessage');
    const scenarioEl = document.getElementById('scenario');
    const scenario = scenarioEl.dataset.scenario;
    
    upvoteBtn.addEventListener('click', function() {{
        upvoteBtn.classList.add('upvoted');
        
        if (scenario === 'suspended') {{
            modalTitle.textContent = 'Account Suspended';
            modalMessage.textContent = 'Your account has been suspended due to unusual activity.';
            modal.classList.add('show');
        }} else if (scenario === 'locked') {{
            modalTitle.textContent = 'Account Locked';
            modalMessage.textContent = 'This account has been locked. You will need to reset your password.';
            modal.classList.add('show');
        }} else if (scenario === 'rate_limited') {{
            modalTitle.textContent = 'Rate Limit Exceeded';
            modalMessage.textContent = 'You are doing that too much. Please try again later.';
            modal.classList.add('show');
        }}
    }});
    </script>
</body>
</html>'''


@app.get("/user/{username}", response_class=HTMLResponse)
async def user_page(request: Request, username: str, scenario: Optional[str] = None):
    scenario = scenario if scenario in SCENARIOS else None

    return f'''<!DOCTYPE html>
<html>
<head><title>u/{username} - Reddit Test Server</title>
<style>
    body {{ font-family: sans-serif; margin: 20px; }}
    .banner {{ padding: 10px; margin-bottom: 20px; border-radius: 4px; display: none; }}
    .banner.banned {{ background: #fcc; color: #c00; display: block; }}
    .banner.suspended {{ background: #fce; color: #a00; display: block; }}
</style>
</head>
<body>
    <div class="banner" id="banner"></div>
    <h1>u/{username}</h1>
    <p>This is a user profile for testing.</p>
    <button class="follow-btn" id="followBtn">Follow</button>
    
    <div id="scenario" data-scenario="{scenario or ''}" style="display:none"></div>
    
    <script>
    const banner = document.getElementById('banner');
    const followBtn = document.getElementById('followBtn');
    const scenarioEl = document.getElementById('scenario');
    const scenario = scenarioEl.dataset.scenario;
    
    // Show banner BEFORE clicking (non-vote actions check header banner first)
    if (scenario === 'banned') {{
        banner.className = 'banner banned';
        banner.textContent = 'You are banned from Reddit.';
    }} else if (scenario === 'suspended') {{
        banner.className = 'banner suspended';
        banner.textContent = 'Your account is suspended.';
    }}
    
    followBtn.addEventListener('click', function() {{
        if (followBtn.textContent === 'Follow') {{
            followBtn.textContent = 'Unfollow';
        }} else {{
            followBtn.textContent = 'Follow';
        }}
    }});
    </script>
</body>
</html>'''


@app.get("/r/{subreddit}", response_class=HTMLResponse)
async def subreddit_page(request: Request, subreddit: str, scenario: Optional[str] = None):
    scenario = scenario if scenario in SCENARIOS else None

    return f'''<!DOCTYPE html>
<html>
<head><title>r/{subreddit} - Reddit Test Server</title>
<style>
    body {{ font-family: sans-serif; margin: 20px; }}
    .banner {{ padding: 10px; margin-bottom: 20px; border-radius: 4px; display: none; }}
    .banner.banned {{ background: #fcc; color: #c00; display: block; }}
    .banner.suspended {{ background: #fce; color: #a00; display: block; }}
</style>
</head>
<body>
    <div class="banner" id="banner"></div>
    <h1>r/{subreddit}</h1>
    <p>This is a subreddit for testing.</p>
    <button class="join-btn" id="joinBtn">Join</button>
    
    <div id="scenario" data-scenario="{scenario or ''}" style="display:none"></div>
    
    <script>
    const banner = document.getElementById('banner');
    const joinBtn = document.getElementById('joinBtn');
    const scenarioEl = document.getElementById('scenario');
    const scenario = scenarioEl.dataset.scenario;
    
    // Show banner BEFORE clicking (non-vote actions check header banner first)
    if (scenario === 'banned') {{
        banner.className = 'banner banned';
        banner.textContent = 'r/{subreddit} is banned.';
    }} else if (scenario === 'suspended') {{
        banner.className = 'banner suspended';
        banner.textContent = 'You are suspended from Reddit.';
    }}
    
    joinBtn.addEventListener('click', function() {{
        if (joinBtn.textContent === 'Join') {{
            joinBtn.textContent = 'Joined';
        }} else {{
            joinBtn.textContent = 'Join';
        }}
    }});
    </script>
</body>
</html>'''


@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html>
<head><title>Reddit Test Server</title></head>
<body>
    <h1>Reddit Test Server</h1>
    <p>Test endpoints:</p>
    <ul>
        <li><a href="/post/test123">Post Page</a></li>
        <li><a href="/comment/comment456">Comment Page</a></li>
        <li><a href="/user/testuser">User Profile</a></li>
        <li><a href="/r/testsubreddit">Subreddit Page</a></li>
    </ul>
    <h2>Scenarios</h2>
    <p>Add ?scenario=suspended|locked|rate_limited|banned to any page</p>
    <p><strong>Vote actions:</strong> popup appears AFTER clicking upvote/downvote</p>
    <p><strong>Non-vote actions:</strong> banner appears BEFORE clicking (check header first)</p>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
