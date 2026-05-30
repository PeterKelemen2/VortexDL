from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_current_user_flexible, get_db
from app.models.job import JobStatus
from app.models.user import User
from app.schemas.job import (
    DownloadJobCreate,
    JobListResponse,
    JobRead,
)
from app.services import job_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/downloads", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def enqueue_download(
    data: DownloadJobCreate,
    current_user: User = Depends(get_current_user_flexible),
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    """Queue a yt-dlp download. Accepts a Bearer token or an X-API-Key header."""
    return await job_service.create_download_job(data, current_user.id, db)


@router.get("", response_model=JobListResponse)
async def list_my_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: JobStatus | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    items, total = await job_service.list_jobs(
        current_user.id,
        db,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
    )
    return JobListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{job_id}", response_model=JobRead)
async def get_my_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    return await job_service.get_job(job_id, current_user.id, db)


@router.post("/{job_id}/cancel", response_model=JobRead)
async def cancel_my_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    return await job_service.cancel_job(job_id, current_user.id, db)
