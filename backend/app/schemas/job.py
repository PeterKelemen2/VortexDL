from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.job import JobStatus


class DownloadJobCreate(BaseModel):
    """Request body for enqueuing a yt-dlp download."""

    url: Annotated[str, Field(min_length=1, max_length=2048)]
    # Optional yt-dlp format selector, e.g. "bestvideo+bestaudio/best".
    format: str | None = Field(default=None, max_length=255)
    # Optional audio-only extraction flag.
    audio_only: bool = False


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_type: str
    status: JobStatus
    payload: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    progress: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobListResponse(BaseModel):
    items: list[JobRead]
    total: int
    page: int
    page_size: int
