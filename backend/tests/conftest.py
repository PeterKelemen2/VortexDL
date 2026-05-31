import atexit
import asyncio
import os
import tempfile
from pathlib import Path

from httpx import AsyncClient, ASGITransport
import pytest
from sqlalchemy import text

# Ensure the backend config uses test-safe secrets and an isolated database.
os.environ.setdefault("JWT_SECRET", "test-secret-that-is-at-least-32-chars!!")
os.environ["INITIAL_ADMIN_USERNAME"] = ""
os.environ["INITIAL_ADMIN_EMAIL"] = ""
os.environ["INITIAL_ADMIN_PASSWORD"] = ""
os.environ["ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING"] = "false"
# Disable rate limiting so the test suite can hammer auth endpoints freely.
os.environ["RATE_LIMIT_ENABLED"] = "false"

# Use a temporary SQLite database file for test isolation.
_db_handle, _db_path = tempfile.mkstemp(prefix="vortex_dl_test_", suffix=".db")
os.close(_db_handle)
os.environ.setdefault("SQLALCHEMY_DATABASE_URI", f"sqlite+aiosqlite:///{_db_path}")
os.environ.setdefault("CORS_ORIGINS", "http://localhost")

from app.core.db import Base, engine
import app.models.user  # noqa: F401
import app.models.role  # noqa: F401
import app.models.refresh_token  # noqa: F401
from app.main import app


def _cleanup_db_file() -> None:
    try:
        Path(_db_path).unlink()
    except OSError:
        pass

atexit.register(_cleanup_db_file)


async def _initialize_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

async def _truncate_tables() -> None:
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM refresh_tokens"))
        await conn.execute(text("DELETE FROM users"))
        await conn.execute(text("DELETE FROM roles"))

asyncio.run(_initialize_database())

@pytest.fixture(scope="function")
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver"
    ) as client_instance:
        yield client_instance

@pytest.fixture(autouse=True)
async def cleanup_db():
    await _truncate_tables()
    yield
