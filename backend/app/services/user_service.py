from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.user import User
from app.schemas.user import UserRead

async def get_all_users(db: AsyncSession):
    stmt = select(User).options(selectinload(User.role))
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [
        UserRead(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role.name,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        for user in users
    ]
