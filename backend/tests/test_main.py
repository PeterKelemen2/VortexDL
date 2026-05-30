import pytest
from fastapi import FastAPI
from sqlalchemy import select, text

from app.core.config import settings
from app.core.db import async_session
from app.main import lifespan
from app.models.user import User


@pytest.mark.asyncio
async def test_lifespan_bootstraps_initial_admin(monkeypatch):
    monkeypatch.setattr(settings, "INITIAL_ADMIN_USERNAME", "startupadmin")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_EMAIL", "startup@example.com")
    monkeypatch.setattr(settings, "INITIAL_ADMIN_PASSWORD", "Password123!")
    monkeypatch.setattr(settings, "ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING", False)

    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.commit()

    async with lifespan(FastAPI()):
        pass

    async with async_session() as session:
        stmt = select(User).where(User.username == "startupadmin")
        result = await session.execute(stmt)
        admin_user = result.scalar_one_or_none()

    assert admin_user is not None
    assert admin_user.username == "startupadmin"
    assert admin_user.email == "startup@example.com"
