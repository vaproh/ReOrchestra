from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_server")

app = FastAPI(title="Reddit Test Server")
templates = Jinja2Templates(directory="tests/pages")

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


def reset_state(session_key: str) -> dict:
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


@app.get("/", response_class=HTMLResponse)
async def home():
    content = """
    <!DOCTYPE html>
    <html>
    <head><title>Reddit Test Server</title></head>
    <body>
        <h1>Reddit Test Server</h1>
        <p>Select a test page:</p>
        <ul>
            <li><a href="/post/test123">Post Page</a></li>
            <li><a href="/comment/comment456">Comment Page</a></li>
            <li><a href="/user/testuser">User Profile</a></li>
            <li><a href="/r/testsubreddit">Subreddit Page</a></li>
            <li><a href="/post/test123/save">Save Page</a></li>
        </ul>
        <h2>Scenario Examples</h2>
        <p>Add ?scenario=suspended|locked|rate_limited|banned to any page</p>
        <h2>Session State</h2>
        <ul>
            <li><a href="/api/state/default">Get State</a></li>
            <li><a href="/api/reset/default">Reset State</a></li>
        </ul>
    </body>
    </html>
    """
    return content


@app.get("/post/{post_id}", response_class=HTMLResponse)
async def post_page(request: Request, post_id: str, scenario: Optional[str] = None, session: Optional[str] = None):
    session_key = session or get_session_key(request)
    state = get_state(session_key)
    
    resp = templates.TemplateResponse(
        "post.html",
        {
            "request": request,
            "post_id": post_id,
            "scenario": scenario if scenario in SCENARIOS else None,
            "upvoted": state["upvoted_posts"],
            "downvoted": state["downvoted_posts"],
            "upvote_count": UPVOTE_COUNT + (1 if post_id in state["upvoted_posts"] else 0),
            "downvote_count": DOWNVOTE_COUNT + (1 if post_id in state["downvoted_posts"] else 0),
            "session_key": session_key,
        }
    )
    resp.set_cookie(key="session_key", value=session_key)
    return resp


@app.get("/comment/{comment_id}", response_class=HTMLResponse)
async def comment_page(request: Request, comment_id: str, scenario: Optional[str] = None, session: Optional[str] = None):
    session_key = session or get_session_key(request)
    state = get_state(session_key)
    
    resp = templates.TemplateResponse(
        "comment.html",
        {
            "request": request,
            "comment_id": comment_id,
            "scenario": scenario if scenario in SCENARIOS else None,
            "upvoted": state["upvoted_comments"],
            "session_key": session_key,
        }
    )
    resp.set_cookie(key="session_key", value=session_key)
    return resp


@app.get("/user/{username}", response_class=HTMLResponse)
async def user_page(request: Request, username: str, scenario: Optional[str] = None, session: Optional[str] = None):
    session_key = session or get_session_key(request)
    state = get_state(session_key)
    
    resp = templates.TemplateResponse(
        "user.html",
        {
            "request": request,
            "username": username,
            "scenario": scenario if scenario in SCENARIOS else None,
            "followed": state["followed_users"],
            "session_key": session_key,
        }
    )
    resp.set_cookie(key="session_key", value=session_key)
    return resp


@app.get("/r/{subreddit}", response_class=HTMLResponse)
async def subreddit_page(request: Request, subreddit: str, scenario: Optional[str] = None, session: Optional[str] = None):
    session_key = session or get_session_key(request)
    state = get_state(session_key)
    
    resp = templates.TemplateResponse(
        "subreddit.html",
        {
            "request": request,
            "subreddit": subreddit,
            "scenario": scenario if scenario in SCENARIOS else None,
            "joined": state["joined_subs"],
            "session_key": session_key,
        }
    )
    resp.set_cookie(key="session_key", value=session_key)
    return resp


@app.get("/post/{post_id}/save", response_class=HTMLResponse)
async def save_page(request: Request, post_id: str, scenario: Optional[str] = None, session: Optional[str] = None):
    session_key = session or get_session_key(request)
    state = get_state(session_key)
    
    resp = templates.TemplateResponse(
        "save.html",
        {
            "request": request,
            "post_id": post_id,
            "scenario": scenario if scenario in SCENARIOS else None,
            "saved": state["saved_posts"],
            "session_key": session_key,
        }
    )
    resp.set_cookie(key="session_key", value=session_key)
    return resp


@app.post("/action/upvote/post/{post_id}")
async def action_upvote_post(post_id: str, session: Optional[str] = Form(None), response: Response = None):
    session_key = session or "default"
    state = get_state(session_key)
    state["upvoted_posts"].add(post_id)
    state["downvoted_posts"].discard(post_id)
    logger.info(f"Upvote post {post_id} for session {session_key}")
    return RedirectResponse(url=f"/post/{post_id}?session={session_key}", status_code=303)


@app.post("/action/downvote/post/{post_id}")
async def action_downvote_post(post_id: str, session: Optional[str] = Form(None), response: Response = None):
    session_key = session or "default"
    state = get_state(session_key)
    state["downvoted_posts"].add(post_id)
    state["upvoted_posts"].discard(post_id)
    logger.info(f"Downvote post {post_id} for session {session_key}")
    return RedirectResponse(url=f"/post/{post_id}?session={session_key}", status_code=303)


@app.post("/action/upvote/comment/{comment_id}")
async def action_upvote_comment(comment_id: str, session: Optional[str] = Form(None), response: Response = None):
    session_key = session or "default"
    state = get_state(session_key)
    state["upvoted_comments"].add(comment_id)
    logger.info(f"Upvote comment {comment_id} for session {session_key}")
    return RedirectResponse(url=f"/comment/{comment_id}?session={session_key}", status_code=303)


@app.post("/action/follow/{username}")
async def action_follow_user(username: str, session: Optional[str] = Form(None), response: Response = None):
    session_key = session or "default"
    state = get_state(session_key)
    state["followed_users"].add(username)
    logger.info(f"Follow user {username} for session {session_key}")
    return RedirectResponse(url=f"/user/{username}?session={session_key}", status_code=303)


@app.post("/action/unfollow/{username}")
async def action_unfollow_user(username: str, session: Optional[str] = Form(None), response: Response = None):
    session_key = session or "default"
    state = get_state(session_key)
    state["followed_users"].discard(username)
    logger.info(f"Unfollow user {username} for session {session_key}")
    return RedirectResponse(url=f"/user/{username}?session={session_key}", status_code=303)


@app.post("/action/join/{subreddit}")
async def action_join_subreddit(subreddit: str, session: Optional[str] = Form(None), response: Response = None):
    session_key = session or "default"
    state = get_state(session_key)
    state["joined_subs"].add(subreddit)
    logger.info(f"Join subreddit {subreddit} for session {session_key}")
    return RedirectResponse(url=f"/r/{subreddit}?session={session_key}", status_code=303)


@app.post("/action/leave/{subreddit}")
async def action_leave_subreddit(subreddit: str, session: Optional[str] = Form(None), response: Response = None):
    session_key = session or "default"
    state = get_state(session_key)
    state["joined_subs"].discard(subreddit)
    logger.info(f"Leave subreddit {subreddit} for session {session_key}")
    return RedirectResponse(url=f"/r/{subreddit}?session={session_key}", status_code=303)


@app.post("/action/save/{post_id}")
async def action_save_post(post_id: str, session: Optional[str] = Form(None), response: Response = None):
    session_key = session or "default"
    state = get_state(session_key)
    state["saved_posts"].add(post_id)
    logger.info(f"Save post {post_id} for session {session_key}")
    return RedirectResponse(url=f"/post/{post_id}/save?session={session_key}", status_code=303)


@app.post("/action/unsave/{post_id}")
async def action_unsave_post(post_id: str, session: Optional[str] = Form(None), response: Response = None):
    session_key = session or "default"
    state = get_state(session_key)
    state["saved_posts"].discard(post_id)
    logger.info(f"Unsave post {post_id} for session {session_key}")
    return RedirectResponse(url=f"/post/{post_id}/save?session={session_key}", status_code=303)


@app.get("/api/state/{session_key}")
async def get_session_state(session_key: str):
    state = get_state(session_key)
    return {
        "upvoted_posts": list(state["upvoted_posts"]),
        "downvoted_posts": list(state["downvoted_posts"]),
        "upvoted_comments": list(state["upvoted_comments"]),
        "downvoted_comments": list(state["downvoted_comments"]),
        "followed_users": list(state["followed_users"]),
        "joined_subs": list(state["joined_subs"]),
        "saved_posts": list(state["saved_posts"]),
    }


@app.get("/api/reset/{session_key}")
async def reset_session_state(session_key: str):
    state = reset_state(session_key)
    return {"message": "State reset", "state": {
        "upvoted_posts": list(state["upvoted_posts"]),
        "downvoted_posts": list(state["downvoted_posts"]),
        "upvoted_comments": list(state["upvoted_comments"]),
        "downvoted_comments": list(state["downvoted_comments"]),
        "followed_users": list(state["followed_users"]),
        "joined_subs": list(state["joined_subs"]),
        "saved_posts": list(state["saved_posts"]),
    }}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
