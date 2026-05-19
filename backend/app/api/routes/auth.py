
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.auth import TokenResponse, TokenRefreshRequest
from app.schemas.user import UserCreate, UserRead
from app.services.auth_service import authenticate_user, create_tokens, hash_token, rotate_refresh_token
from app.models.user import User
from app.models.role import Role
from app.models.refresh_token import RefreshToken
from app.core.security import hash_password
from app.core.config import settings
from sqlalchemy import select
from datetime import datetime

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRead)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    stmt = select(User).where(User.username == user_in.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")
    # Assign default role
    role_stmt = select(Role).where(Role.name == "user")
    role_result = await db.execute(role_stmt)
    role = role_result.scalar_one_or_none()
    if not role:
        # Create default role if missing
        role = Role(name="user", description="Default user role")
        db.add(role)
        await db.commit()
        await db.refresh(role)
    hashed_pw = hash_password(user_in.password)
    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pw,
        role_id=role.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        role=role.name,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )

@router.post("/login", response_model=TokenResponse)
async def login(form: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form.username, form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token, refresh_token = await create_tokens(db, user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(token_req: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash_val = hash_token(token_req.refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash_val, RefreshToken.revoked == False)
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()
    if not db_token or db_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    user_stmt = select(User).where(User.id == db_token.user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    db_token.last_used_at = datetime.utcnow()
    await db.commit()
    access_token, new_refresh = await rotate_refresh_token(db, user, db_token)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)

@router.post("/logout")
async def logout(token_req: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    token_hash_val = hash_token(token_req.refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash_val, RefreshToken.revoked == False)
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()
    if db_token:
        db_token.revoked = True
        await db.commit()
    return {"msg": "Logged out"}

@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return UserRead(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.name,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )
