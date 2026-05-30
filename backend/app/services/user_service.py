from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from datetime import datetime, timezone
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserRead, UserAdminUpdate, UserAdminDelete
from app.services.auth_service import validate_password_strength, hash_password

async def get_all_users(db: AsyncSession, page: int = 1, page_size: int = 10):
    count_stmt = select(func.count()).select_from(User)
    result = await db.execute(count_stmt)
    total = result.scalar_one()

    offset = (page - 1) * page_size
    stmt = (
        select(User)
        .options(selectinload(User.role))
        .order_by(User.id)
        .limit(page_size)
        .offset(offset)
    )
    result = await db.execute(stmt)
    users = result.scalars().all()

    total_pages = max((total + page_size - 1) // page_size, 1)
    return {
        'items': [
            UserRead(
                id=user.id,
                username=user.username,
                email=user.email,
                role=user.role.name,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            for user in users
        ],
        'page': page,
        'page_size': page_size,
        'total': total,
        'total_pages': total_pages,
    }


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    stmt = select(User).where(User.id == user_id).options(selectinload(User.role))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_user_by_admin(db: AsyncSession, user_id: int, user_update: UserAdminUpdate) -> UserRead:
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email is None:
        raise HTTPException(status_code=400, detail="Target user does not have an email address")

    if user_update.confirm_email != user.email:
        raise HTTPException(status_code=400, detail="Email confirmation does not match")

    changes_made = False

    if user_update.username is not None:
        new_username = user_update.username.strip()
        if not new_username:
            raise HTTPException(status_code=400, detail="Username cannot be empty")
        if new_username != user.username:
            stmt = select(User).where(User.username == new_username)
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            if existing_user and existing_user.id != user.id:
                raise HTTPException(status_code=400, detail="Username already taken")
            user.username = new_username
            changes_made = True

    if user_update.role is not None:
        if user_update.role != user.role.name:
            stmt = select(Role).where(Role.name == user_update.role)
            result = await db.execute(stmt)
            new_role = result.scalar_one_or_none()
            if new_role is None:
                raise HTTPException(status_code=400, detail="Invalid role")
            user.role_id = new_role.id
            changes_made = True

    if user_update.new_password is not None:
        if user_update.new_password != user_update.new_password_confirm:
            raise HTTPException(status_code=400, detail="Password confirmation does not match")
        validate_password_strength(user_update.new_password)
        user.hashed_password = hash_password(user_update.new_password)
        changes_made = True

    if not changes_made:
        raise HTTPException(status_code=400, detail="No changes were provided")

    user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)
    return UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role.name,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def delete_user_by_admin(db: AsyncSession, user_id: int, confirm_email: str, requester_id: int | None = None):
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email is None or confirm_email != user.email:
        raise HTTPException(status_code=400, detail="Email confirmation does not match")

    if requester_id is not None and user.id == requester_id:
        raise HTTPException(status_code=400, detail="Administrators cannot delete their own account from the admin panel")

    await db.delete(user)
    await db.commit()
    return None
