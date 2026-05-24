from fastapi import HTTPException
from app.schemas.user import UserRead, UserRegister, UserLogin
from app.schemas.auth import TokenResponse, TokenRefreshRequest
from app.models.role import Role
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sqlalchemy as sa
from sqlalchemy.orm import selectinload
from datetime import timedelta, datetime
import asyncio
import hashlib
import re
import socket

ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 14


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
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

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
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
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
    return await create_tokens(session, user, device_name=device_name, user_agent=user_agent)


async def register_user(user_in: UserRegister, db: AsyncSession):
    # Check if user exists
    if user_in.password != user_in.password_confirm:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    stmt = select(User).where(User.username == user_in.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already registered")

    # Ensure roles exist
    role_names = {"admin": "Administrator role", "user": "Default user role"}
    existing_roles = {}
    for role_name, desc in role_names.items():
        role_stmt = select(Role).where(Role.name == role_name)
        role_result = await db.execute(role_stmt)
        role = role_result.scalar_one_or_none()
        if not role:
            role = Role(name=role_name, description=desc)
            db.add(role)
            await db.commit()
            await db.refresh(role)
        existing_roles[role_name] = role or await db.scalar(select(Role).where(Role.name == role_name))

    # Determine if this is the first user
    user_count = await db.scalar(select(sa.func.count()).select_from(User))
    if user_count == 0:
        assigned_role = existing_roles["admin"]
    else:
        assigned_role = existing_roles["user"]

    hashed_pw = hash_password(user_in.password)
    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pw,
        role_id=assigned_role.id,
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
        print('[auth] refresh_tokens login', {
            'username': data.username,
            'client_ip': client_ip,
            'received_device_name': data.device_name,
            'resolved_name': resolved_name,
            'user_agent': user_agent,
        })
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
        token_hash_val = hash_token(data.refresh_token)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash_val,
            RefreshToken.revoked == False
        )
        result = await db.execute(stmt)
        db_token = result.scalar_one_or_none()
        if not db_token or db_token.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        # FIX: load user with role eagerly to avoid lazy-load issues
        user_stmt = select(User).where(User.id == db_token.user_id).options(selectinload(User.role))
        user_result = await db.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        db_token.last_used_at = datetime.utcnow()
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


async def list_refresh_sessions(db: AsyncSession, user: User, current_session_id: int | None = None):
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user.id,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.utcnow(),
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
    # NOTE: caller must ensure current_user.role is eagerly loaded
    return UserRead(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role.name,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
    )