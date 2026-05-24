import pytest
from sqlalchemy import select, text

from app.core.db import async_session
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserRead
from app.services.user_service import get_all_users


@pytest.mark.asyncio
async def test_get_all_users_returns_empty_list():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        users = await get_all_users(session)
        assert users == []


@pytest.mark.asyncio
async def test_get_all_users_returns_user_read_objects():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            username="service1",
            email="service1@example.com",
            hashed_password="irrelevant",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        users = await get_all_users(session)
        assert len(users) == 1
        assert isinstance(users[0], UserRead)
        assert users[0].username == "service1"
        assert users[0].email == "service1@example.com"
        assert users[0].role == "user"
