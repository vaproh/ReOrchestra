"""
Reddit Test Server - Simulates Reddit for testing without real network calls.

Serves fake Reddit pages with configurable scenarios (suspended, locked, rate_limited, banned).
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

sessions_state: dict = {}

SCENARIOS = {"suspended", "locked", "rate_limited", "banned"}

UPVOTE_COUNT = 42
DOWNVOTE_COUNT = 7


def get_session_key(request: Request) -> str:
    return request.cookies.get("session_key", "default")


def get_state(session_key: str) -> dict:
    if session_key not in sessions_state:
        sessions_state[session_key] = {
            "upvoted_posts": set(),
            "downvoted_posts": set(),
            "upvoted_comments": set(),
            "downvoted_comments": set(),
            "followed_users": set(),
            "joined_subs": set(),
            "saved_posts": set(),
        }
    return sessions_state[session_key]


def build_post_html(post_id: str, scenario: Optional[str], upvoted: set, downvoted: set, session_key: str) -> str:
    upvoted_class = "upvoted" if post_id in upvoted else ""
    downvoted_class = "downvoted" if post_id in downvoted else ""
    upvote_count = UPVOTE_COUNT + (1 if post_id in upvoted else 0)
    downvote_count = DOWNVOTE_COUNT + (1 if post_id in downvoted else 0)
    
    popup_html = ""
    if scenario == "suspended":
        popup_html = '''
        <div class="modal-overlay">
            <div class="modal">
                <h2>Account Suspended</h2>
                <p>Your account has been suspended due to unusual activity.</p>
            </div>
        </div>'''
    elif scenario == "locked":
        popup_html = '''
        <div class="modal-overlay">
            <div class="modal">
                <h2>Account Locked</h2>
                <p>This account has been locked. You will need to reset your password.</p>
            </div>
        </div>'''
    elif scenario == "rate_limited":
        popup_html = '''
        <div class="modal-overlay">
            <div class="modal">
                <h2>Rate Limit Exceeded</h2>
                <p>You are doing that too much. Please try again later.</p>
            </div>
        </div>'''

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
        .modal-overlay {{ position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; }}
        .modal {{ background: white; padding: 30px; border-radius: 8px; text-align: center; }}
        .modal h2 {{ color: #d93a00; }}
    </style>
</head>
<body>
    <h1>r/test - Test Post {post_id}</h1>
    <p>This is a test post for testing ReOrchestra automation.</p>
    
    {popup_html}
    
    <div class="vote-buttons">
        <button class="vote-btn upvote {upvoted_class}" onclick="toggleUpvote()">upvote</button>
        <span class="upvote-count">{upvote_count}</span>
        <button class="vote-btn downvote {downvoted_class}" onclick="toggleDownvote()">downvote</button>
        <span class="downvote-count">{downvote_count}</span>
        <button class="vote-btn save" onclick="savePost()">save</button>
    </div>
    
    <p>Session: {session_key}</p>
    <p>Scenario: {scenario or 'none'}</p>
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
        <li><a href="/post/test123/save">Save Page</a></li>
    </ul>
    <h2>Scenarios</h2>
    <p>Add ?scenario=suspended|locked|rate_limited|banned to any page</p>
</body>
</html>"""


@app.get("/post/{post_id}", response_class=HTMLResponse)
async def post_page(request: Request, post_id: str, scenario: Optional[str] = None, session: Optional[str] = None):
    session_key = session or get_session_key(request)
    state = get_state(session_key)
    
    response = HTMLResponse(
        content=build_post_html(post_id, scenario if scenario in SCENARIOS else None, 
                               state["upvoted_posts"], state["downvoted_posts"], session_key)
    )
    response.set_cookie(key="session_key", value=session_key)
    return response


@app.get("/comment/{comment_id}", response_class=HTMLResponse)
async def comment_page(request: Request, comment_id: str, scenario: Optional[str] = None, session: Optional[str] = None):
    session_key = session or get_session_key(request)
    state = get_state(session_key)
    
    popup_html = ""
    if scenario == "suspended":
        popup_html = '<div class="modal-overlay"><div class="modal"><h2>Account Suspended</h2><p>Your account has been suspended due to unusual activity.</p></div></div>'
    elif scenario == "locked":
        popup_html = '<div class="modal-overlay"><div class="modal"><h2>Account Locked</h2><p>This account has been locked.</p></div></div>'
    elif scenario == "rate_limited":
        popup_html = '<div class="modal-overlay"><div class="modal"><h2>Rate Limit Exceeded</h2><p>You are doing that too much.</p></div></div>'
    
    response = HTMLResponse(content=f'''<!DOCTYPE html>
<html>
<head><title>Comment - Reddit Test Server</title>
<style>
    body {{ font-family: sans-serif; margin: 20px; }}
    .vote-btn {{ padding: 5px 15px; cursor: pointer; }}
    .modal-overlay {{ position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; }}
    .modal {{ background: white; padding: 30px; border-radius: 8px; text-align: center; }}
</style>
</head>
<body>
    <h1>Comment {comment_id}</h1>
    <p>This is a single comment's thread for testing.</p>
    {popup_html}
    <div class="vote-buttons">
        <button class="vote-btn upvote">upvote</button>
        <button class="vote-btn downvote">downvote</button>
    </div>
</body>
</html>''')
    response.set_cookie(key="session_key", value=session_key)
    return response


@app.get("/user/{username}", response_class=HTMLResponse)
async def user_page(request: Request, username: str, scenario: Optional[str] = None, session: Optional[str] = None):
    session_key = session or get_session_key(request)
    state = get_state(session_key)
    
    is_following = username in state["followed_users"]
    
    banner_html = ""
    if scenario == "banned":
        banner_html = '<div class="banner banned">You are banned from Reddit.</div>'
    elif scenario == "suspended":
        banner_html = '<div class="banner suspended">Your account is suspended.</div>'
    
    response = HTMLResponse(content=f'''<!DOCTYPE html>
<html>
<head><title>u/{username} - Reddit Test Server</title>
<style>
    body {{ font-family: sans-serif; margin: 20px; }}
    .banner {{ padding: 10px; margin-bottom: 20px; border-radius: 4px; }}
    .banner.banned {{ background: #fcc; color: #c00; }}
    .banner.suspended {{ background: #fce; color: #a00; }}
</style>
</head>
<body>
    {banner_html}
    <h1>u/{username}</h1>
    <p>This is a user profile for testing.</p>
    <button class="follow-btn">{"Unfollow" if is_following else "Follow"}</button>
</body>
</html>''')
    response.set_cookie(key="session_key", value=session_key)
    return response


@app.get("/r/{subreddit}", response_class=HTMLResponse)
async def subreddit_page(request: Request, subreddit: str, scenario: Optional[str] = None, session: Optional[str] = None):
    session_key = session or get_session_key(request)
    state = get_state(session_key)
    
    is_joined = subreddit in state["joined_subs"]
    
    banner_html = ""
    if scenario == "banned":
        banner_html = '<div class="banner banned">r/{subreddit} is banned.</div>'
    elif scenario == "suspended":
        banner_html = '<div class="banner suspended">You are suspended from Reddit.</div>'
    
    response = HTMLResponse(content=f'''<!DOCTYPE html>
<html>
<head><title>r/{subreddit} - Reddit Test Server</title>
<style>
    body {{ font-family: sans-serif; margin: 20px; }}
    .banner {{ padding: 10px; margin-bottom: 20px; border-radius: 4px; }}
    .banner.banned {{ background: #fcc; color: #c00; }}
    .banner.suspended {{ background: #fce; color: #a00; }}
</style>
</head>
<body>
    {banner_html}
    <h1>r/{subreddit}</h1>
    <p>This is a subreddit for testing.</p>
    <button class="join-btn">{"Leave" if is_joined else "Join"}</button>
</body>
</html>''')
    response.set_cookie(key="session_key", value=session_key)
    return response


@app.get("/api/state/{session_key}")
async def get_state_api(session_key: str):
    return sessions_state.get(session_key, {})


@app.get("/api/reset/{session_key}")
async def reset_state_api(session_key: str):
    sessions_state[session_key] = {
        "upvoted_posts": set(),
        "downvoted_posts": set(),
        "upvoted_comments": set(),
        "downvoted_comments": set(),
        "followed_users": set(),
        "joined_subs": set(),
        "saved_posts": set(),
    }
    return {"status": "reset"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
