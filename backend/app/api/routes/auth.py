
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.auth import TokenResponse, TokenRefreshRequest
from app.schemas.user import UserRead, UserRegister, UserLogin
from app.services.auth_service import (
    register_user,
    refresh_tokens,
    logout_refresh_token,
    get_user_info,
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRead)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    return await register_user(user_in, db)

@router.post("/login", response_model=TokenResponse)
async def login(form: UserLogin, db: AsyncSession = Depends(get_db)):
    return await refresh_tokens(form, db)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(token_req: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    return await refresh_tokens(token_req, db)

@router.post("/logout")
async def logout(token_req: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    return await logout_refresh_token(token_req, db)

@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return get_user_info(current_user)
