from contextlib import asynccontextmanager
import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.api.routes import health, auth, admin, jobs, api_keys, remote_machines
from app.core.config import settings
from app.core.db import async_session

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
from app.core.rate_limit import limiter
from app.core.job_queue import job_queue
from app.core.ssh_pool import ssh_pool
from app.core.sse_bus import sse_bus
from app.services.auth_service import bootstrap_initial_admin
from app.services.download_service import DOWNLOAD_JOB_TYPE, download_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    global shutdown_event
    shutdown_event = asyncio.Event()
    async with async_session() as db:
        await bootstrap_initial_admin(db)
    # Background job queue: register handlers and start workers.
    job_queue.concurrency = settings.JOB_WORKER_CONCURRENCY
    job_queue.register(DOWNLOAD_JOB_TYPE, download_handler)
    await job_queue.start()
    try:
        yield
    finally:
        # Close all SSE connections first so uvicorn doesn't hang waiting for them.
        await sse_bus.close_all()
        await job_queue.stop()
        await ssh_pool.close_all()


app = FastAPI(title="Downloader API", lifespan=lifespan)

# Rate limiting (slowapi)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

upload_root = Path(settings.PROFILE_IMAGE_UPLOAD_DIR)
upload_root.mkdir(parents=True, exist_ok=True)
app.mount(settings.PROFILE_IMAGE_URL_PATH, StaticFiles(directory=str(upload_root), html=False), name="uploads")

app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.CORS_ORIGINS,
	allow_credentials=True,
	allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
	allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
)


@app.middleware("http")
async def security_headers(request, call_next):
	response = await call_next(request)
	response.headers.setdefault("X-Content-Type-Options", "nosniff")
	response.headers.setdefault("X-Frame-Options", "DENY")
	response.headers.setdefault("Referrer-Policy", "no-referrer")
	response.headers.setdefault("X-XSS-Protection", "0")
	if settings.SECURE_COOKIES:
		response.headers.setdefault(
			"Strict-Transport-Security", "max-age=31536000; includeSubDomains"
		)
	return response

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(jobs.router)
app.include_router(api_keys.router)
app.include_router(remote_machines.admin_router)
app.include_router(remote_machines.user_router)