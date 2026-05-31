"""Lightweight in-process asyncio job queue.

A small number of worker tasks pull job IDs off an :class:`asyncio.Queue`,
load the persisted :class:`~app.models.job.Job`, dispatch to a registered
handler based on ``job_type`` and persist the resulting status transition
(queued -> running -> finished / failed).

This is intentionally process-local and dependency-free. For a multi-process
or horizontally-scaled deployment, swap the queue/worker for an external broker
(e.g. Redis + RQ/Celery) while keeping the same ``Job`` model and service API.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional

from sqlalchemy import select

from app.core.db import async_session
from app.models.job import Job, JobStatus

logger = logging.getLogger("app.job_queue")


@dataclass
class JobContext:
    """Passed to handlers; exposes the payload and progress reporting."""

    job_id: int
    user_id: int
    payload: dict
    _progress_cb: Callable[[int, int], Awaitable[None]]

    async def update_progress(self, percent: int) -> None:
        await self._progress_cb(self.job_id, max(0, min(100, int(percent))))


# A handler receives a JobContext and returns a JSON-serializable result dict.
JobHandler = Callable[[JobContext], Awaitable[Optional[dict]]]


@dataclass
class JobQueue:
    concurrency: int = 2
    _queue: "asyncio.Queue[int]" = field(default_factory=asyncio.Queue)
    _handlers: dict[str, JobHandler] = field(default_factory=dict)
    _workers: list[asyncio.Task] = field(default_factory=list)
    _started: bool = False

    def register(self, job_type: str, handler: JobHandler) -> None:
        self._handlers[job_type] = handler

    async def enqueue(self, job_id: int) -> None:
        await self._queue.put(job_id)

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        # Re-enqueue any jobs left in a non-terminal state from a previous run.
        await self._requeue_orphans()
        for i in range(self.concurrency):
            self._workers.append(asyncio.create_task(self._worker(i), name=f"job-worker-{i}"))
        logger.info("Job queue started with %d workers", self.concurrency)

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        logger.info("Job queue stopped")

    async def _requeue_orphans(self) -> None:
        """Reset interrupted 'running' jobs back to 'queued' and enqueue all pending."""
        async with async_session() as db:
            result = await db.execute(
                select(Job).where(Job.status.in_([JobStatus.queued, JobStatus.running]))
            )
            jobs = result.scalars().all()
            for job in jobs:
                if job.status == JobStatus.running:
                    job.status = JobStatus.queued
                    job.started_at = None
                    job.progress = 0
            await db.commit()
            ids = [job.id for job in jobs]
        for job_id in ids:
            await self._queue.put(job_id)
        if ids:
            logger.info("Re-enqueued %d pending job(s) on startup", len(ids))

    async def _set_progress(self, job_id: int, percent: int) -> None:
        async with async_session() as db:
            job = await db.get(Job, job_id)
            if job and not JobStatus(job.status).is_terminal:
                job.progress = percent
                await db.commit()

    async def _worker(self, index: int) -> None:
        while True:
            try:
                job_id = await self._queue.get()
            except asyncio.CancelledError:
                break
            try:
                await self._process(job_id)
            except asyncio.CancelledError:
                break
            except Exception:  # noqa: BLE001 - worker must never die on a bad job
                logger.exception("Unhandled error processing job %s", job_id)
            finally:
                self._queue.task_done()

    async def _process(self, job_id: int) -> None:
        # Load + transition to running.
        async with async_session() as db:
            job = await db.get(Job, job_id)
            if job is None:
                logger.warning("Job %s not found; skipping", job_id)
                return
            if JobStatus(job.status).is_terminal:
                return
            handler = self._handlers.get(job.job_type)
            payload = json.loads(job.payload) if job.payload else {}
            user_id = job.user_id
            if handler is None:
                job.status = JobStatus.failed
                job.error = f"No handler registered for job_type '{job.job_type}'"
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()
                return
            job.status = JobStatus.running
            job.started_at = datetime.now(timezone.utc)
            await db.commit()

        ctx = JobContext(
            job_id=job_id,
            user_id=user_id,
            payload=payload,
            _progress_cb=self._set_progress,
        )

        # Run the handler outside the DB session so long work doesn't hold a connection.
        try:
            result = await handler(ctx)
            status = JobStatus.finished
            error = None
        except Exception as exc:  # noqa: BLE001 - capture failure on the job record
            logger.exception("Job %s failed", job_id)
            result = None
            status = JobStatus.failed
            error = str(exc)

        async with async_session() as db:
            job = await db.get(Job, job_id)
            if job is None:
                return
            job.status = status
            job.error = error
            job.result = json.dumps(result) if result is not None else None
            job.progress = 100 if status == JobStatus.finished else job.progress
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()


# Module singleton used by the application.
job_queue = JobQueue()
