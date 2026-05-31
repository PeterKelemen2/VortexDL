"""Remote machine management (admin) and assigned-machine access (users)."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user, get_db, require_role
from app.models.user import User
from app.schemas.remote_machine import (
    AssignedUserRead,
    AssignUserRequest,
    ConnectionTestResult,
    RemoteBrowseResult,
    RemoteMachineAssignmentRead,
    RemoteMachineCreate,
    RemoteMachineListResponse,
    RemoteMachineRead,
    RemoteMachineUpdate,
)
from app.services import remote_machine_service

CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_COOKIE_NAME = "csrf_token"


def _require_csrf(request: Request) -> None:
    csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
    csrf_header = request.headers.get(CSRF_HEADER_NAME)
    if (
        not csrf_cookie
        or not csrf_header
        or not secrets.compare_digest(csrf_cookie, csrf_header)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token"
        )


# --- Admin router -------------------------------------------------------------

admin_router = APIRouter(
    prefix="/admin/remote-machines", tags=["remote-machines-admin"]
)


@admin_router.get("", response_model=RemoteMachineListResponse)
async def list_machines(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_role("admin")),
) -> RemoteMachineListResponse:
    items, total = await remote_machine_service.list_machines(
        db, page=page, page_size=page_size
    )
    return RemoteMachineListResponse(
        items=[RemoteMachineRead.model_validate(m) for m in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@admin_router.post(
    "", response_model=RemoteMachineRead, status_code=status.HTTP_201_CREATED
)
async def create_machine(
    data: RemoteMachineCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_role("admin")),
) -> RemoteMachineRead:
    _require_csrf(request)
    machine = await remote_machine_service.create_machine(data, db)
    return RemoteMachineRead.model_validate(machine)


@admin_router.patch("/{machine_id}", response_model=RemoteMachineRead)
async def update_machine(
    machine_id: int,
    data: RemoteMachineUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_role("admin")),
) -> RemoteMachineRead:
    _require_csrf(request)
    machine = await remote_machine_service.update_machine(machine_id, data, db)
    return RemoteMachineRead.model_validate(machine)


@admin_router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_machine(
    machine_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_role("admin")),
) -> Response:
    _require_csrf(request)
    await remote_machine_service.delete_machine(machine_id, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.post("/{machine_id}/test", response_model=ConnectionTestResult)
async def test_machine(
    machine_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_role("admin")),
) -> ConnectionTestResult:
    _require_csrf(request)
    return await remote_machine_service.test_machine(machine_id, db)


@admin_router.get("/{machine_id}/users", response_model=list[AssignedUserRead])
async def list_machine_users(
    machine_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_role("admin")),
) -> list[AssignedUserRead]:
    users = await remote_machine_service.list_assigned_users(machine_id, db)
    return [AssignedUserRead.model_validate(u) for u in users]


@admin_router.post("/{machine_id}/users", status_code=status.HTTP_204_NO_CONTENT)
async def assign_user(
    machine_id: int,
    data: AssignUserRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_role("admin")),
) -> Response:
    _require_csrf(request)
    await remote_machine_service.assign_user(machine_id, data.user_id, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.delete(
    "/{machine_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def unassign_user(
    machine_id: int,
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_role("admin")),
) -> Response:
    _require_csrf(request)
    await remote_machine_service.unassign_user(machine_id, user_id, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- User router --------------------------------------------------------------

user_router = APIRouter(prefix="/remote-machines", tags=["remote-machines"])


@user_router.get("", response_model=list[RemoteMachineAssignmentRead])
async def list_my_machines(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RemoteMachineAssignmentRead]:
    machines = await remote_machine_service.list_user_machines(current_user.id, db)
    return [RemoteMachineAssignmentRead.model_validate(m) for m in machines]


@user_router.get("/{machine_id}/browse", response_model=RemoteBrowseResult)
async def browse_machine(
    machine_id: int,
    path: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RemoteBrowseResult:
    return await remote_machine_service.browse_machine(
        machine_id,
        current_user.id,
        path,
        db,
        max_entries=settings.REMOTE_BROWSE_MAX_ENTRIES,
    )
