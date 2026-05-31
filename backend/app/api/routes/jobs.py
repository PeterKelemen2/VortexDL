import asyncio

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_current_user_flexible, get_db
from app.core.rate_limit import limiter
from app.core.config import settings
from app.core.sse_bus import sse_bus
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
@limiter.limit(settings.RATE_LIMIT_DOWNLOAD)
async def enqueue_download(
    data: DownloadJobCreate,
    request: Request,
    current_user: User = Depends(get_current_user_flexible),
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    """Queue a yt-dlp download. Accepts a Bearer token or an X-API-Key header."""
    return await job_service.create_download_job(data, current_user.id, db)


@router.get("/stream")
async def stream_job_events(
    request: Request,
    token: str = Query(..., description="Bearer JWT (EventSource cannot set headers)"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Server-Sent Events stream of this user's job updates.

    The browser ``EventSource`` API cannot attach Authorization headers, so the
    access token is passed as a query parameter and validated here.
    """
    current_user = await get_current_user(token=token, db=db)
    queue = await sse_bus.subscribe(current_user.id)

    from app.core.sse_bus import _CLOSE

    async def event_generator():
        # How often we wake up to poll is_disconnected().  Must be short so a
        # browser that closes the EventSource (or a uvicorn hot-reload) is
        # detected quickly.  Keep-alive comments are sent less frequently so we
        # don't spam the wire; we just track accumulated idle time ourselves.
        poll_interval = 2.0
        keepalive_every = 20.0
        idle = 0.0
        try:
            # Prompt the client to reconnect after 5s if the connection drops.
            yield "retry: 5000\n\n"
            while True:
                # is_disconnected() is a non-blocking poll in Starlette; check
                # it at the top of every iteration so we exit promptly after the
                # browser closes the connection.
                if await request.is_disconnected():
                    break
                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=poll_interval)
                    idle = 0.0
                    # None / _CLOSE sentinel means the server is shutting down.
                    if payload is _CLOSE:
                        break
                    yield f"event: job_update\ndata: {payload}\n\n"
                except asyncio.TimeoutError:
                    idle += poll_interval
                    if idle >= keepalive_every:
                        yield ": keep-alive\n\n"
                        idle = 0.0
        finally:
            await sse_bus.unsubscribe(current_user.id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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


@router.get("/{job_id}/download")
async def download_job_file(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Stream a finished job's local artifact to the browser as an attachment."""
    path, filename = await job_service.get_job_file(job_id, current_user.id, db)
    return FileResponse(
        path=str(path),
        filename=filename,
        media_type="application/octet-stream",
    )


@router.post("/{job_id}/cancel", response_model=JobRead)
async def cancel_my_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    return await job_service.cancel_job(job_id, current_user.id, db)


@router.post("/{job_id}/retry", response_model=JobRead)
async def retry_my_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobRead:
    return await job_service.retry_job(job_id, current_user.id, db)
