
import logging
import secrets

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user, get_current_user_flexible
from app.core.config import settings
from app.schemas.auth import (
    TokenResponse,
    TokenRefreshRequest,
    RefreshTokenSession,
    MessageResponse,
    EmailVerificationRequest,
    EmailVerificationConfirm,
    PasswordResetRequest,
    PasswordResetConfirm,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
    TwoFactorDisableRequest,
    TwoFactorStatusResponse,
    BackupCodesResponse,
)
from app.schemas.user import (
    UserImageCrop,
    UserImageRead,
    UserLogin,
    UserRead,
    UserRegister,
    UserUpdate,
)
from app.services.auth_service import (
    register_user,
    refresh_tokens,
    logout_refresh_token,
    list_refresh_sessions,
    revoke_refresh_session,
    revoke_all_refresh_sessions,
    get_user_info,
    update_current_user,
)
from app.services.account_service import (
    request_email_verification,
    verify_email,
    request_password_reset,
    reset_password,
)
from app.core.rate_limit import limiter
from app.services import twofactor_service
from app.services.user_image_service import (
    activate_user_profile_image,
    create_user_profile_image,
    list_user_profile_images,
    update_user_profile_image_crop,
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


logger = logging.getLogger(__name__)

def _cookie_settings(request: Request) -> dict:
    # Never trust the request scheme: behind a TLS-terminating proxy it appears as
    # plain http, which would silently drop the Secure flag in production. The
    # operator declares HTTPS explicitly via SECURE_COOKIES.
    secure = settings.SECURE_COOKIES
    same_site = settings.COOKIE_SAMESITE
    return {"secure": secure, "samesite": same_site}


def _set_refresh_cookie(response: Response, request: Request, refresh_token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        path="/auth",
        max_age=14 * 24 * 60 * 60,
        **_cookie_settings(request),
    )


def _clear_refresh_cookie(response: Response, request: Request) -> None:
    response.set_cookie(
        key="refresh_token",
        value="",
        httponly=True,
        path="/auth",
        max_age=0,
        **_cookie_settings(request),
    )


def _set_csrf_cookie(response: Response, request: Request, csrf_token: str) -> None:
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        path="/",
        max_age=14 * 24 * 60 * 60,
        **_cookie_settings(request),
    )


def _clear_csrf_cookie(response: Response, request: Request) -> None:
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value="",
        httponly=False,
        path="/",
        max_age=0,
        **_cookie_settings(request),
    )


def _require_csrf(request: Request) -> None:
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(CSRF_HEADER_NAME)
    if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")


@router.post("/register", response_model=UserRead)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register(user_in: UserRegister, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    return await register_user(user_in, db)


@router.post("/login", response_model=TokenResponse, response_model_exclude_none=True)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    form: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else None
    user_agent_header = request.headers.get('user-agent')
    logger.info(
        "Login attempt",
        extra={
            "username": form.username,
            "client_ip": client_ip,
            "device_name": form.device_name,
            "user_agent": form.user_agent or user_agent_header,
        },
    )
    token_response = await refresh_tokens(
        form,
        db,
        device_name=form.device_name,
        user_agent=form.user_agent or user_agent_header,
        client_ip=client_ip,
    )
    csrf_token = secrets.token_urlsafe(32)
    _set_refresh_cookie(response, request, token_response.refresh_token)
    _set_csrf_cookie(response, request, csrf_token)
    return TokenResponse(access_token=token_response.access_token)


@router.post("/refresh", response_model=TokenResponse, response_model_exclude_none=True)
@limiter.limit(settings.RATE_LIMIT_REFRESH)
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    _require_csrf(request)
    refresh_token = request.cookies.get("refresh_token")
    token_response = await refresh_tokens(
        TokenRefreshRequest(refresh_token=refresh_token),
        db,
        user_agent=request.headers.get("user-agent"),
    )
    # Only overwrite the cookies when the refresh token was actually rotated
    # (near-expiry case). Rotating the CSRF cookie on every access-token refresh
    # creates a race window: the browser may send a stale X-CSRF-Token header
    # (read via document.cookie) while the cookie jar already has the new value
    # from a concurrent response, causing a spurious 403 on rapid F5 presses.
    if token_response.refresh_token:
        csrf_token = secrets.token_urlsafe(32)
        _set_refresh_cookie(response, request, token_response.refresh_token)
        _set_csrf_cookie(response, request, csrf_token)
    return TokenResponse(access_token=token_response.access_token)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    _require_csrf(request)
    refresh_token = request.cookies.get("refresh_token")
    _clear_refresh_cookie(response, request)
    _clear_csrf_cookie(response, request)
    await logout_refresh_token(TokenRefreshRequest(refresh_token=refresh_token), db)
    return {"msg": "Logged out"}


@router.post("/verify-email/request", response_model=MessageResponse)
@limiter.limit(settings.RATE_LIMIT_EMAIL_VERIFICATION)
async def request_verification(
    payload: EmailVerificationRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    return await request_email_verification(payload, db)


@router.post("/verify-email", response_model=MessageResponse)
@limiter.limit(settings.RATE_LIMIT_EMAIL_VERIFICATION)
async def confirm_verification(
    payload: EmailVerificationConfirm,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    return await verify_email(payload, db)


@router.post("/password-reset/request", response_model=MessageResponse)
@limiter.limit(settings.RATE_LIMIT_PASSWORD_RESET)
async def request_reset(
    payload: PasswordResetRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    return await request_password_reset(payload, db)


@router.post("/password-reset", response_model=MessageResponse)
@limiter.limit(settings.RATE_LIMIT_PASSWORD_RESET)
async def confirm_reset(
    payload: PasswordResetConfirm,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    return await reset_password(payload, db)


@router.get("/2fa/status", response_model=TwoFactorStatusResponse)
async def twofactor_status(current_user: User = Depends(get_current_user)):
    return TwoFactorStatusResponse(enabled=current_user.totp_enabled)


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def twofactor_setup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    data = await twofactor_service.start_setup(current_user, db)
    return TwoFactorSetupResponse(**data)


@router.post("/2fa/verify", response_model=TwoFactorStatusResponse)
async def twofactor_verify(
    payload: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await twofactor_service.confirm_setup(current_user, payload.code, db)
    return TwoFactorStatusResponse(enabled=True)


@router.post("/2fa/disable", response_model=TwoFactorStatusResponse)
async def twofactor_disable(
    payload: TwoFactorDisableRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await twofactor_service.disable(current_user, payload.password, db)
    return TwoFactorStatusResponse(enabled=False)


@router.post("/2fa/backup-codes", response_model=BackupCodesResponse)
async def twofactor_regenerate_backup_codes(
    payload: TwoFactorVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    codes = await twofactor_service.regenerate_backup_codes(current_user, payload.code, db)
    return BackupCodesResponse(backup_codes=codes)


@router.get("/sessions", response_model=list[RefreshTokenSession])
async def sessions(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    current_session_id = getattr(current_user, "current_session_id", None)
    return await list_refresh_sessions(db, current_user, current_session_id)


@router.delete("/sessions", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_all_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_csrf(request)
    await revoke_all_refresh_sessions(current_user, db)
    return None


@router.delete("/sessions/current", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_current_session(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_csrf(request)
    current_session_id = getattr(current_user, "current_session_id", None)
    if current_session_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active session to revoke")
    await revoke_refresh_session(current_session_id, current_user, db)
    return None


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    request: Request,
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_csrf(request)
    await revoke_refresh_session(session_id, current_user, db)
    return None

@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user_flexible)):
    return get_user_info(current_user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    user_update: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_csrf(request)
    return await update_current_user(current_user, user_update, db)


@router.post("/me/avatar", response_model=UserImageRead)
async def upload_profile_image(
    request: Request,
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_csrf(request)
    return await create_user_profile_image(current_user, image, db)


@router.patch("/me/avatar/{image_id}", response_model=UserImageRead)
async def crop_profile_image(
    image_id: int,
    crop_request: UserImageCrop,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_csrf(request)
    return await update_user_profile_image_crop(current_user, image_id, crop_request, db)


@router.patch("/me/avatar/{image_id}/activate", response_model=UserImageRead)
async def activate_profile_image(
    image_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_csrf(request)
    return await activate_user_profile_image(current_user, image_id, db)


@router.get("/me/avatars", response_model=list[UserImageRead])
async def list_profile_images(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_user_profile_images(current_user, db)
