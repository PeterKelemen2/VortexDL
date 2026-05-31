from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi import Header
from jose import jwt, JWTError
from datetime import datetime, timezone
from app.core.config import settings
from app.models.user import User
from app.models.refresh_token import RefreshToken
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_db
from sqlalchemy import select
from sqlalchemy.orm import selectinload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# Optional scheme so endpoints can fall back to API-key auth when no bearer token.
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
        )
        user_id: str = payload.get("sub")
        session_id = payload.get("sid")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    stmt = select(User).where(User.id == int(user_id)).options(selectinload(User.role), selectinload(User.images))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    if session_id is not None:
        try:
            session_id = int(session_id)
        except (TypeError, ValueError):
            raise credentials_exception

        token_stmt = select(RefreshToken).where(
            RefreshToken.id == session_id,
            RefreshToken.user_id == int(user_id),
            RefreshToken.revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        token_result = await db.execute(token_stmt)
        refresh_session = token_result.scalar_one_or_none()
        if refresh_session is None:
            raise credentials_exception
        setattr(user, "current_session_id", refresh_session.id)
    else:
        setattr(user, "current_session_id", None)

    return user

def require_role(role_name: str):
    async def role_dependency(current_user: User = Depends(get_current_user)):
        if current_user.role.name != role_name:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
    return role_dependency


async def get_current_user_flexible(
    token: str | None = Depends(oauth2_scheme_optional),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate via Bearer JWT or an ``X-API-Key`` header.

    Bearer tokens take precedence; if absent, a valid API key is accepted.
    """
    if token:
        return await get_current_user(token=token, db=db)

    if x_api_key:
        # Imported here to avoid a circular import at module load time.
        from app.services.api_key_service import resolve_api_key

        user = await resolve_api_key(x_api_key, db)
        if user is not None:
            # Eager-load the role for downstream authorization checks.
            stmt = (
                select(User)
                .where(User.id == user.id)
                .options(selectinload(User.role), selectinload(User.images))
            )
            full_user = (await db.execute(stmt)).scalar_one_or_none()
            if full_user is not None:
                setattr(full_user, "current_session_id", None)
                return full_user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
