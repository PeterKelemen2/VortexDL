import pytest
from fastapi import HTTPException
from sqlalchemy import select, text

from app.core.db import async_session
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserRead, UserAdminUpdate
from app.services.user_service import get_all_users, update_user_by_admin, delete_user_by_admin


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


@pytest.mark.asyncio
async def test_update_user_by_admin_can_change_username():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            username="service2",
            email="service2@example.com",
            hashed_password="irrelevant",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        updated = await update_user_by_admin(
            session,
            user.id,
            UserAdminUpdate(username="updated-service2", confirm_email=user.email),
        )

        assert updated.username == "updated-service2"
        assert updated.email == user.email
        assert updated.role == "user"


@pytest.mark.asyncio
async def test_update_user_by_admin_rejects_incorrect_email():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            username="service3",
            email="service3@example.com",
            hashed_password="irrelevant",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        with pytest.raises(HTTPException) as exc_info:
            await update_user_by_admin(
                session,
                user.id,
                UserAdminUpdate(username="updated-service3", confirm_email="wrong@example.com"),
            )

        assert exc_info.value.status_code == 400
        assert "Email confirmation does not match" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_delete_user_by_admin_removes_user():
    async with async_session() as session:
        await session.execute(text("DELETE FROM users"))
        await session.execute(text("DELETE FROM roles"))
        await session.commit()

        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

        user = User(
            username="service4",
            email="service4@example.com",
            hashed_password="irrelevant",
            role=role,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        await delete_user_by_admin(session, user.id, user.email)

        stmt = select(User).where(User.id == user.id)
        result = await session.execute(stmt)
        deleted_user = result.scalar_one_or_none()
        assert deleted_user is None
