
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.schemas.auth import TokenResponse, TokenRefreshRequest, RefreshTokenSession
from app.schemas.user import UserRead, UserRegister, UserLogin
from app.services.auth_service import (
    register_user,
    refresh_tokens,
    logout_refresh_token,
    list_refresh_sessions,
    revoke_refresh_session,
    get_user_info,
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserRead)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    return await register_user(user_in, db)

@router.post("/login", response_model=TokenResponse)
async def login(form: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    client_ip = request.client.host if request.client else None
    user_agent_header = request.headers.get('user-agent')
    print('[auth] login attempt', {
        'username': form.username,
        'client_ip': client_ip,
        'device_name': form.device_name,
        'user_agent': form.user_agent or user_agent_header,
    })
    return await refresh_tokens(
        form,
        db,
        device_name=form.device_name,
        user_agent=form.user_agent or user_agent_header,
        client_ip=client_ip,
    )

@router.post("/refresh", response_model=TokenResponse)
async def refresh(token_req: TokenRefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    return await refresh_tokens(
        token_req,
        db,
        user_agent=request.headers.get("user-agent"),
    )

@router.post("/logout")
async def logout(token_req: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    return await logout_refresh_token(token_req, db)

@router.get("/sessions", response_model=list[RefreshTokenSession])
async def sessions(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    current_session_id = getattr(current_user, "current_session_id", None)
    return await list_refresh_sessions(db, current_user, current_session_id)

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await revoke_refresh_session(session_id, current_user, db)
    return None

@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return get_user_info(current_user)
