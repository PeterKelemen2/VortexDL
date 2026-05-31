import asyncio

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_current_user_flexible, get_db
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
async def enqueue_download(
    data: DownloadJobCreate,
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

    from app.main import shutdown_event

    async def event_generator():
        try:
            # Prompt the client to reconnect after 5s if the connection drops.
            yield "retry: 5000\n\n"
            while True:
                if await request.is_disconnected():
                    break
                if shutdown_event and shutdown_event.is_set():
                    break

                # Race the next event against disconnection / shutdown so we
                # never block the server from reloading/stopping for long.
                get_task = asyncio.ensure_future(queue.get())
                shutdown_task = asyncio.ensure_future(
                    shutdown_event.wait() if shutdown_event else asyncio.sleep(25.0)
                )
                done, pending = await asyncio.wait(
                    {get_task, shutdown_task},
                    timeout=25.0,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pending:
                    t.cancel()

                if shutdown_task in done or (shutdown_event and shutdown_event.is_set()):
                    break
                if await request.is_disconnected():
                    break
                if get_task in done:
                    try:
                        payload = get_task.result()
                        yield f"event: job_update\ndata: {payload}\n\n"
                    except Exception:
                        pass
                else:
                    # Both timed out — send keep-alive
                    yield ": keep-alive\n\n"
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
