import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.dependencies import require_role, get_db, get_current_user
from app.models.role import Role
from app.models.user import User
from app.schemas.user import UserRead, UserListResponse, UserAdminUpdate, UserAdminDelete
from app.schemas.role import RoleRead
from app.services.user_service import get_all_users, update_user_by_admin, delete_user_by_admin

router = APIRouter(prefix="/admin", tags=["admin"])

CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_NAME = "csrf_token"


def _require_csrf(request: Request) -> None:
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(CSRF_HEADER_NAME)
    if not csrf_cookie or not csrf_header or not secrets.compare_digest(csrf_cookie, csrf_header):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")


@router.get("/users", response_model=UserListResponse)
async def list_users(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: None = Depends(require_role("admin")),
):
    return await get_all_users(db, page, page_size)


@router.get("/roles", response_model=List[RoleRead])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_role("admin")),
):
    stmt = select(Role)
    result = await db.execute(stmt)
    roles = result.scalars().all()
    return roles


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_update: UserAdminUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_role("admin")),
):
    _require_csrf(request)
    return await update_user_by_admin(db, user_id, user_update)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    delete_payload: UserAdminDelete,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_role("admin")),
):
    _require_csrf(request)
    await delete_user_by_admin(db, user_id, delete_payload.confirm_email, current_user.id)
    return None
