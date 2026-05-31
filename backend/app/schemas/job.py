from __future__ import annotations

import enum
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.job import JobStatus


class DownloadQuality(str, enum.Enum):
    best = "best"
    p1080 = "1080p"
    p720 = "720p"
    p480 = "480p"
    p360 = "360p"
    audio_only = "audio_only"


class AudioFormat(str, enum.Enum):
    mp3 = "mp3"
    aac = "aac"
    flac = "flac"
    opus = "opus"
    wav = "wav"


class ContainerFormat(str, enum.Enum):
    auto = "auto"
    mp4 = "mp4"
    mkv = "mkv"
    webm = "webm"


class DownloadDestination(str, enum.Enum):
    local = "local"
    remote = "remote"
    both = "both"


class DownloadJobCreate(BaseModel):
    """Request body for enqueuing a yt-dlp download."""

    url: Annotated[str, Field(min_length=1, max_length=2048)]

    # --- yt-dlp parameters ----------------------------------------------------
    quality: DownloadQuality = DownloadQuality.best
    audio_format: AudioFormat = AudioFormat.mp3
    container: ContainerFormat = ContainerFormat.auto
    embed_subtitles: bool = False
    embed_metadata: bool = False
    embed_music_metadata: bool = False
    allow_playlist: bool = False
    write_thumbnail: bool = False

    # --- delivery -------------------------------------------------------------
    destination_type: DownloadDestination = DownloadDestination.local
    remote_machine_id: int | None = None
    # Relative subfolder within the machine's configured download folder.
    remote_subfolder: str | None = Field(default=None, max_length=1024)

    @model_validator(mode="after")
    def _validate_remote(self) -> "DownloadJobCreate":
        if self.destination_type in (
            DownloadDestination.remote,
            DownloadDestination.both,
        ):
            if self.remote_machine_id is None:
                raise ValueError(
                    "remote_machine_id is required when destination_type is "
                    "'remote' or 'both'"
                )
        return self


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_type: str
    status: JobStatus
    payload: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    progress: int
    destination_type: str = "local"
    remote_machine_id: int | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobListResponse(BaseModel):
    items: list[JobRead]
    total: int
    page: int
    page_size: int
