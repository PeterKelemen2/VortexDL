"""Business logic for background jobs: creation, listing, retrieval, cancellation."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.job_queue import job_queue
from app.models.job import Job, JobStatus
from app.models.remote_machine import RemoteMachine
from app.models.user_remote_machine import UserRemoteMachine
from app.schemas.job import DownloadDestination, DownloadJobCreate, JobRead
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
        destination_type=job.destination_type,
        remote_machine_id=job.remote_machine_id,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


async def _assert_machine_access(
    user_id: int, machine_id: int, db: AsyncSession
) -> RemoteMachine:
    """Ensure the user is assigned to an active machine; raise 403/404 otherwise."""
    machine = await db.get(RemoteMachine, machine_id)
    if machine is None or not machine.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Remote machine not found"
        )
    assignment = (
        await db.execute(
            select(UserRemoteMachine).where(
                UserRemoteMachine.user_id == user_id,
                UserRemoteMachine.remote_machine_id == machine_id,
            )
        )
    ).scalar_one_or_none()
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this remote machine",
        )
    return machine


async def create_download_job(
    data: DownloadJobCreate, user_id: int, db: AsyncSession
) -> JobRead:
    remote_machine_id: int | None = None
    if data.destination_type in (
        DownloadDestination.remote,
        DownloadDestination.both,
    ):
        await _assert_machine_access(user_id, data.remote_machine_id, db)
        remote_machine_id = data.remote_machine_id

    payload = {
        "url": data.url,
        "quality": data.quality.value,
        "audio_format": data.audio_format.value,
        "container": data.container.value,
        "embed_subtitles": data.embed_subtitles,
        "embed_metadata": data.embed_metadata,
        "embed_music_metadata": data.embed_music_metadata,
        "allow_playlist": data.allow_playlist,
        "write_thumbnail": data.write_thumbnail,
        "destination_type": data.destination_type.value,
        "remote_machine_id": remote_machine_id,
        "remote_subfolder": data.remote_subfolder,
    }
    job = Job(
        user_id=user_id,
        job_type=DOWNLOAD_JOB_TYPE,
        status=JobStatus.queued,
        payload=json.dumps(payload),
        progress=0,
        destination_type=data.destination_type.value,
        remote_machine_id=remote_machine_id,
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


async def get_job_file(
    job_id: int, user_id: int, db: AsyncSession
) -> tuple[Path, str]:
    """Resolve the local artifact path for a finished job (browser download)."""
    job = await db.get(Job, job_id)
    if job is None or job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if JobStatus(job.status) != JobStatus.finished:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Job is not finished"
        )
    result = json.loads(job.result) if job.result else {}
    if not result.get("local_available", True):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This job has no locally available file",
        )
    filepath = result.get("filepath")
    if not filepath:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
        )
    path = Path(filepath)
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File no longer exists"
        )
    # Build a clean download filename from the reported title so the browser
    # never sees any _1/_2 deduplication suffix added on the backend.
    title = result.get("title", "").strip()
    ext = path.suffix  # includes the leading dot, e.g. ".mp3"
    if title and ext:
        # Strip characters that are unsafe in Content-Disposition filenames.
        safe_title = "".join(c if c not in r'\/:*?"<>|' else "_" for c in title)
        download_name = f"{safe_title}{ext}"
    else:
        download_name = path.name
    return path, download_name


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


async def retry_job(job_id: int, user_id: int, db: AsyncSession) -> JobRead:
    """Re-queue a failed or canceled job using its original payload."""
    job = await db.get(Job, job_id)
    if job is None or job.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if JobStatus(job.status) not in (JobStatus.failed, JobStatus.canceled):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only failed or canceled jobs can be retried",
        )
    job.status = JobStatus.queued
    job.error = None
    job.result = None
    job.progress = 0
    job.started_at = None
    job.finished_at = None
    await db.commit()
    await db.refresh(job)
    await job_queue.enqueue(job.id)
    return _to_read(job)

