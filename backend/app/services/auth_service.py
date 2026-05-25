from fastapi import HTTPException
from app.schemas.user import UserRead, UserRegister, UserLogin, UserUpdate
from app.schemas.auth import TokenResponse, TokenRefreshRequest
from app.models.role import Role
from app.models.user import User
from app.models.refresh_token import RefreshToken
import logging

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import sqlalchemy as sa
from sqlalchemy.orm import selectinload
from datetime import timedelta, datetime, timezone
import asyncio
import hashlib
import re
import socket

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 14
PASSWORD_MIN_LENGTH = 12
PASSWORD_SPECIAL_RE = re.compile(r"[!@#$%^&*()_+\-=[\]{};':\"\\|,.<>/?]")

logger = logging.getLogger(__name__)


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def resolve_hostname(ip: str | None) -> str | None:
    """Attempt a reverse DNS lookup of the client IP.
    Returns the short hostname (stripped of domain) or None on failure."""
    if not ip or ip in ("127.0.0.1", "::1"):
        return None
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, socket.gethostbyaddr, ip)
        # result[0] is the full FQDN; take only the first label
        return result[0].split(".")[0]
    except (socket.herror, socket.gaierror, OSError):
        return None


def detect_device_os(user_agent: str | None) -> str:
    if not user_agent:
        return "other"

    ua = user_agent.lower()
    if "android" in ua:
        return "android"
    if any(keyword in ua for keyword in ("iphone", "ipad", "ipod")):
        return "ios"
    if "macintosh" in ua or "mac os x" in ua:
        return "macos"
    if "windows" in ua:
        return "windows"
    if "linux" in ua and "android" not in ua:
        return "linux"
    return "other"


def detect_device_name(user_agent: str | None) -> str | None:
    """Extract a human-readable device name from the User-Agent string.

    Examples:
      "Mozilla/5.0 (Linux; Android 15; 23053RN02Y) ..."  → "Android 15 23053RN02Y"
      "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 ...)"     → "iPhone (iOS 17.0)"
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."    → "Windows 10"
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"  → "macOS 10.15.7"
    """
    if not user_agent:
        return None

    ua = user_agent

    # Android: extract version and device model
    # UA pattern: (Linux; Android <version>; <model>)
    m = re.search(r"Android\s+([\d.]+);\s*([^;)]+)", ua, re.IGNORECASE)
    if m:
        version = m.group(1).strip()
        model = m.group(2).strip()
        return f"Android {version} {model}"

    # iPhone / iPad / iPod: extract iOS version
    m = re.search(r"(iPhone|iPad|iPod).*?OS\s+([\d_]+)", ua, re.IGNORECASE)
    if m:
        device = m.group(1)
        ios_version = m.group(2).replace("_", ".")
        return f"{device} (iOS {ios_version})"

    # Windows: map NT version to marketing name
    m = re.search(r"Windows NT\s+([\d.]+)", ua, re.IGNORECASE)
    if m:
        nt_map = {"10.0": "10/11", "6.3": "8.1", "6.2": "8", "6.1": "7", "6.0": "Vista"}
        nt = m.group(1)
        win = nt_map.get(nt, nt)
        return f"Windows {win}"

    # macOS: extract version
    m = re.search(r"Mac OS X\s+([\d_]+)", ua, re.IGNORECASE)
    if m:
        macos_version = m.group(1).replace("_", ".")
        return f"macOS {macos_version}"

    # Linux desktop fallback
    if re.search(r"linux", ua, re.IGNORECASE) and "android" not in ua.lower():
        return "Linux PC"

    return None


async def authenticate_user(session: AsyncSession, username: str, password: str):
    stmt = select(User).where(User.username == username).options(selectinload(User.role))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.hashed_password):
        return user
    return None


async def create_tokens(
    session: AsyncSession,
    user: User,
    device_name: str | None = None,
    resolved_name: str | None = None,
    device_os: str | None = None,
    user_agent: str | None = None,
):
    raw_refresh = create_refresh_token()
    token_hash = hash_token(raw_refresh)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    if device_os is None:
        device_os = detect_device_os(user_agent)

    # Prefer the browser-supplied device name when available.
    parsed_name = detect_device_name(user_agent)
    if device_name is not None:
        normalized = device_name.strip().lower()
        generic = normalized in {
            'linux',
            'linux x86_64',
            'linux armv8',
            'linux arm64',
            'android',
            'ios',
            'macos',
            'windows',
        }
        if generic and parsed_name:
            device_name = parsed_name
    if device_name is None:
        device_name = parsed_name or device_os

    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        resolved_name=resolved_name,
        device_os=device_os,
        device_name=device_name,
        user_agent=user_agent[:1024] if user_agent else None,
        expires_at=expires_at,
    )
    session.add(refresh_token)
    await session.commit()
    await session.refresh(refresh_token)

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.name, "sid": refresh_token.id},
        secret=settings.JWT_SECRET,
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
        algorithm=settings.JWT_ALGORITHM,
    )
    return access_token, raw_refresh


async def rotate_refresh_token(
    session: AsyncSession,
    user: User,
    old_token: RefreshToken,
    device_name: str | None = None,
    user_agent: str | None = None,
):
    old_token.revoked = True
    await session.commit()
    return await create_tokens(
        session,
        user,
        device_name=device_name,
        resolved_name=old_token.resolved_name,
        device_os=old_token.device_os,
        user_agent=user_agent,
    )


async def ensure_roles_exist(db: AsyncSession) -> dict[str, Role]:
    role_names = {"admin": "Administrator role", "user": "Default user role"}
    stmt = select(Role).where(Role.name.in_(role_names.keys()))
    result = await db.execute(stmt)
    existing = {role.name: role for role in result.scalars().all()}

    for role_name, desc in role_names.items():
        if role_name not in existing:
            role = Role(name=role_name, description=desc)
            db.add(role)
            existing[role_name] = role

    if any(role.id is None for role in existing.values()):
        await db.commit()
        for role in existing.values():
            await db.refresh(role)

    return existing


def validate_password_strength(password: str) -> None:
    errors: list[str] = []
    if len(password) < PASSWORD_MIN_LENGTH:
        errors.append(f"at least {PASSWORD_MIN_LENGTH} characters")
    if " " in password:
        errors.append("no spaces")
    if not re.search(r"[A-Z]", password):
        errors.append("an uppercase letter")
    if not (re.search(r"\d", password) or PASSWORD_SPECIAL_RE.search(password)):
        errors.append("a digit or a special character")

    if errors:
        raise HTTPException(
            status_code=400,
            detail=("Password must contain " + ", ".join(errors[:-1]) + " and " + errors[-1])
            if len(errors) > 1
            else f"Password must contain {errors[0]}"
        )


async def bootstrap_initial_admin(db: AsyncSession):
    username = settings.INITIAL_ADMIN_USERNAME
    email = settings.INITIAL_ADMIN_EMAIL
    password = settings.INITIAL_ADMIN_PASSWORD
    force_elevate = settings.ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING

    if bool(username or email or password) and not all((username, email, password)):
        raise RuntimeError(
            "INITIAL_ADMIN_USERNAME, INITIAL_ADMIN_EMAIL, and INITIAL_ADMIN_PASSWORD must all be set to bootstrap the initial admin account"
        )

    if not all((username, email, password)):
        logger.debug("Admin bootstrap skipped because initial admin credentials are incomplete")
        return

    existing = await ensure_roles_exist(db)
    admin_role = existing["admin"]

    stmt = select(User).where(User.role_id == admin_role.id).limit(1)
    result = await db.execute(stmt)
    admin_user = result.scalar_one_or_none()
    if admin_user is not None:
        logger.debug("Admin bootstrap skipped because an admin account already exists: %s", admin_user.username)
        return

    stmt = select(User).where((User.username == username) | (User.email == email)).limit(1)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        if existing_user.role_id == admin_role.id:
            logger.debug("Existing account %s already has admin privileges", existing_user.username)
            return
        if force_elevate:
            existing_user.role_id = admin_role.id
            await db.commit()
            logger.info("Elevated existing user %s to admin via bootstrap", existing_user.username)
        else:
            logger.info("Admin bootstrap found existing user %s but did not elevate; set ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING=true to promote", existing_user.username)
        return

    try:
        validate_password_strength(password)
    except HTTPException as exc:
        logger.error("Initial admin bootstrap failed: %s", exc.detail)
        raise RuntimeError(exc.detail)

    hashed_pw = hash_password(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_pw,
        role_id=admin_role.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("Created initial admin account %s via bootstrap", username)


async def register_user(user_in: UserRegister, db: AsyncSession):
    # Check if passwords match and are strong enough
    if user_in.password != user_in.password_confirm:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    username = user_in.username.strip()
    email = user_in.email.strip().lower()

    validate_password_strength(user_in.password)

    stmt = select(User).where(User.username == username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")

    email_stmt = select(User).where(User.email == email)
    email_result = await db.execute(email_stmt)
    if email_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    existing = await ensure_roles_exist(db)
    assigned_role = existing["user"]

    hashed_pw = hash_password(user_in.password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_pw,
        role_id=assigned_role.id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserRead(
        id=user.id,
        username=user.username,
        email=user.email,
        role=assigned_role.name,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


async def refresh_tokens(
    data,
    db: AsyncSession,
    device_name: str | None = None,
    user_agent: str | None = None,
    device_os: str | None = None,
    client_ip: str | None = None,
):
    if isinstance(data, UserLogin):
        user = await authenticate_user(db, data.username, data.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        resolved_name = await resolve_hostname(client_ip)
        logger.info(
            "User login successful",
            extra={
                "username": data.username,
                "client_ip": client_ip,
                "received_device_name": data.device_name,
                "resolved_name": resolved_name,
                "user_agent": user_agent,
            },
        )
        access_token, refresh_token = await create_tokens(
            db,
            user,
            device_name=data.device_name,
            resolved_name=resolved_name,
            device_os=device_os,
            user_agent=user_agent,
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    elif isinstance(data, TokenRefreshRequest):
        if not data.refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token required")

        token_hash_val = hash_token(data.refresh_token)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash_val,
            RefreshToken.revoked == False
        )
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()
        if not db_token or _ensure_utc(db_token.expires_at) < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        # FIX: load user with role eagerly to avoid lazy-load issues
        user_stmt = select(User).where(User.id == db_token.user_id).options(selectinload(User.role))
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        db_token.last_used_at = datetime.now(timezone.utc)
        await db.commit()
        access_token, new_refresh = await rotate_refresh_token(
            db,
            user,
            db_token,
            device_name=device_name,
            user_agent=user_agent,
        )
        return TokenResponse(access_token=access_token, refresh_token=new_refresh)
    else:
        raise HTTPException(status_code=400, detail="Invalid request")


async def logout_refresh_token(token_req: TokenRefreshRequest, db: AsyncSession):
    if not token_req.refresh_token:
        return {"msg": "Logged out"}

    token_hash_val = hash_token(token_req.refresh_token)
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash_val,
        RefreshToken.revoked == False
    )
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()
    if db_token:
        db_token.revoked = True
        await db.commit()
    return {"msg": "Logged out"}


async def revoke_all_refresh_sessions(user: User, db: AsyncSession):
    stmt = update(RefreshToken).where(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
    ).values(revoked=True)
    await db.execute(stmt)
    await db.commit()
    return {"msg": "All sessions revoked"}


async def list_refresh_sessions(db: AsyncSession, user: User, current_session_id: int | None = None):
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.now(timezone.utc),
    )
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    for session_obj in sessions:
        setattr(session_obj, 'current', session_obj.id == current_session_id)
    return sessions


async def revoke_refresh_session(session_id: int, user: User, db: AsyncSession):
    stmt = select(RefreshToken).where(
        RefreshToken.id == session_id,
        RefreshToken.user_id == user.id,
    )
    result = await db.execute(stmt)
    db_token = result.scalar_one_or_none()
    if not db_token or db_token.revoked:
        raise HTTPException(status_code=404, detail="Session not found")

    db_token.revoked = True
    await db.commit()
    return {"msg": "Session revoked"}


def get_user_info(current_user: User):
    # NOTE: caller must ensure current_user.role and current_user.images are eagerly loaded
    active_image = None
    for image in getattr(current_user, 'images', []):
        if image.is_active:
            active_image = image
            break

    return UserRead(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.name,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        profile_image=active_image,
    )


async def update_current_user(current_user: User, user_update: UserUpdate, db: AsyncSession):
    should_change_username = bool(user_update.username and user_update.username.strip() and user_update.username.strip() != current_user.username)
    should_change_password = bool(user_update.new_password)

    if not should_change_username and not should_change_password:
        return get_user_info(current_user)

    if not user_update.current_password:
        raise HTTPException(status_code=400, detail="Current password is required to update profile")

    if not verify_password(user_update.current_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid current password")

    if should_change_username:
        new_username = user_update.username.strip()
        stmt = select(User).where(User.username == new_username)
        result = await db.execute(stmt)
        existing_user = result.scalar_one_or_none()
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Username already taken")
        current_user.username = new_username

    if should_change_password:
        if user_update.new_password != user_update.new_password_confirm:
            raise HTTPException(status_code=400, detail="Password confirmation does not match")
        validate_password_strength(user_update.new_password)
        current_user.hashed_password = hash_password(user_update.new_password)

    current_user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(current_user)
    return get_user_info(current_user)