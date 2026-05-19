from datetime import timedelta, datetime
from jose import jwt, JWTError
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from app.models.user import User
from app.models.refresh_token import RefreshToken
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
import hashlib

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 14

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

async def authenticate_user(session: AsyncSession, username: str, password: str):
    stmt = select(User).where(User.username == username).options(selectinload(User.role))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.hashed_password):
        return user
    return None

async def create_tokens(session: AsyncSession, user: User):
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.name},
        secret=settings.JWT_SECRET,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    raw_refresh = create_refresh_token()
    token_hash = hash_token(raw_refresh)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at
    )
    session.add(refresh_token)
    await session.commit()
    return access_token, raw_refresh

async def rotate_refresh_token(session: AsyncSession, user: User, old_token: RefreshToken):
    old_token.revoked = True
    await session.commit()
    return await create_tokens(session, user)
