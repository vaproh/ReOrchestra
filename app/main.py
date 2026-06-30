from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.config import get_settings
from app.database import init_db
from app.api.router import router

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized")
    yield
    # Graceful shutdown
    from app.services.queue_manager import QueueManager
    QueueManager.get().stop()
    logger.info("Shutting down")


app = FastAPI(
    title="ReOrchestra",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        },
    )


app.include_router(router, prefix="/api")

from app.gui import router as gui_router
app.include_router(gui_router, prefix="/gui")


@app.get("/")
async def root():
    return {"message": "ReOrchestra API", "version": "1.0.0", "docs": "/docs", "gui": "/gui"}
