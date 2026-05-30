"""Business logic for background jobs: creation, listing, retrieval, cancellation."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.job_queue import job_queue
from app.models.job import Job, JobStatus
from app.schemas.job import DownloadJobCreate, JobRead
from app.services.download_service import DOWNLOAD_JOB_TYPE


def _to_read(job: Job) -> JobRead:
    return JobRead(
        id=job.id,
        job_type=job.job_type,
        status=JobStatus(job.status),
        payload=json.loads(job.payload) if job.payload else None,
        result=json.loads(job.result) if job.result else None,
        error=job.error,
        progress=job.progress,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


async def create_download_job(
    data: DownloadJobCreate, user_id: int, db: AsyncSession
) -> JobRead:
    payload = {
        "url": data.url,
        "format": data.format,
        "audio_only": data.audio_only,
    }
    job = Job(
        user_id=user_id,
        job_type=DOWNLOAD_JOB_TYPE,
        status=JobStatus.queued,
        payload=json.dumps(payload),
        progress=0,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    await job_queue.enqueue(job.id)
    return _to_read(job)


async def list_jobs(
    user_id: int,
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status_filter: JobStatus | None = None,
) -> tuple[list[JobRead], int]:
    page = max(1, page)
    page_size = max(1, min(100, page_size))

    base = select(Job).where(Job.user_id == user_id)
    count_stmt = select(func.count()).select_from(Job).where(Job.user_id == user_id)
    if status_filter is not None:
        base = base.where(Job.status == status_filter)
        count_stmt = count_stmt.where(Job.status == status_filter)

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = (
        base.order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_to_read(job) for job in rows], total


async def get_job(job_id: int, user_id: int, db: AsyncSession) -> JobRead:
    job = await db.get(Job, job_id)
    if job is None or job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _to_read(job)


async def cancel_job(job_id: int, user_id: int, db: AsyncSession) -> JobRead:
    job = await db.get(Job, job_id)
    if job is None or job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if JobStatus(job.status).is_terminal:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job is already {job.status.value}",
        )
    # Only queued jobs can be reliably canceled in-process; running jobs are
    # marked canceled and their handler result is discarded on completion.
    job.status = JobStatus.canceled
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return _to_read(job)
