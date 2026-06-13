"""
Main application entry point for Drootle Lead AI.
Handles API routing, application startup events, and health checks.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import traceback

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

@app.middleware("http")
async def log_all_requests(request: Request, call_next):
    logger.info(f">>> REQUEST: {request.method} {request.url.path} from {request.client}")
    try:
        response = await call_next(request)
        logger.info(f"<<< RESPONSE: {request.method} {request.url.path} -> {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"!!! MIDDLEWARE CRASH: {request.method} {request.url.path} -> {e}\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"error": str(e)})

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

@app.post("/ping")
async def ping_post(request: Request):
    """Bare POST test endpoint — bypasses all routers"""
    body = await request.body()
    logger.info(f"PING POST received, body length: {len(body)}")
    return {"status": "pong", "body_length": len(body)}

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

if os.path.exists("frontend/dist"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"))
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        return FileResponse("frontend/dist/index.html")
