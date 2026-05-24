from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import health, auth, admin
from app.core.config import settings
from app.core.db import async_session
from app.services.auth_service import bootstrap_initial_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session() as db:
        await bootstrap_initial_admin(db)
    yield


app = FastAPI(title="Downloader API", lifespan=lifespan)

app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.CORS_ORIGINS,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)