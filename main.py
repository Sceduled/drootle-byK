"""
Main application entry point for Drootle Lead AI.
Handles API routing, application startup events, and health checks.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from core.database import test_connection as test_db
from core.redis import test_connection as test_redis
from api.routes import webhooks, dashboard, auth
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from core.limiter import limiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Drootle Lead AI")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

@app.on_event("startup")
async def startup_event():
    logger.info("Testing PostgreSQL connection...")
    db_ok = await test_db()
    logger.info(f"PostgreSQL connection: {'OK' if db_ok else 'FAILED'}")

    logger.info("Testing Redis connection...")
    redis_ok = await test_redis()
    logger.info(f"Redis connection: {'OK' if redis_ok else 'FAILED'}")

    logger.info("ARQ worker ready")
    logger.info("Drootle Lead AI started")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "drootle-lead-ai"}

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

if os.path.exists("frontend/dist"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"))
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse("frontend/dist/index.html")
