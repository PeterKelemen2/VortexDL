
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.core.config import settings
from app.schemas.auth import TokenResponse, TokenRefreshRequest, RefreshTokenSession
from app.schemas.user import UserRead, UserRegister, UserLogin
from app.services.auth_service import (
    register_user,
    refresh_tokens,
    logout_refresh_token,
    list_refresh_sessions,
    revoke_refresh_session,
    revoke_all_refresh_sessions,
    get_user_info,
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="none",
        path="/auth",
        max_age=14 * 24 * 60 * 60,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        secure=not settings.DEBUG,
        samesite="none",
        path="/auth",
        max_age=0,
    )


@router.post("/register", response_model=UserRead)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    return await register_user(user_in, db)


@router.post("/login", response_model=TokenResponse)
async def login(
    form: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else None
    user_agent_header = request.headers.get('user-agent')
    print('[auth] login attempt', {
        'username': form.username,
        'client_ip': client_ip,
        'device_name': form.device_name,
        'user_agent': form.user_agent or user_agent_header,
    })
    token_response = await refresh_tokens(
        form,
        db,
        device_name=form.device_name,
        user_agent=form.user_agent or user_agent_header,
        client_ip=client_ip,
    )
    _set_refresh_cookie(response, token_response.refresh_token)
    return token_response


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    token_req: TokenRefreshRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token_req.refresh_token = token_req.refresh_token or request.cookies.get("refresh_token")
    token_response = await refresh_tokens(
        token_req,
        db,
        user_agent=request.headers.get("user-agent"),
    )
    _set_refresh_cookie(response, token_response.refresh_token)
    return token_response


@router.post("/logout")
async def logout(
    token_req: TokenRefreshRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token_req.refresh_token = token_req.refresh_token or request.cookies.get("refresh_token")
    _clear_refresh_cookie(response)
    await logout_refresh_token(token_req, db)
    return {"msg": "Logged out"}


@router.get("/sessions", response_model=list[RefreshTokenSession])
async def sessions(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    current_session_id = getattr(current_user, "current_session_id", None)
    return await list_refresh_sessions(db, current_user, current_session_id)


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await revoke_all_refresh_sessions(current_user, db)
    return None


@router.delete("/sessions/current", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_current_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_session_id = getattr(current_user, "current_session_id", None)
    if current_session_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active session to revoke")
    await revoke_refresh_session(current_session_id, current_user, db)
    return None


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
