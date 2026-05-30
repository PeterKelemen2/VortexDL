"""yt-dlp download handler for the background job queue.

Registered against the ``download`` job type. Runs the (blocking) yt-dlp
extraction in a worker thread so the event loop is never blocked, and reports
coarse progress back onto the job record.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.core.config import settings
from app.core.job_queue import JobContext

logger = logging.getLogger("app.download")

DOWNLOAD_JOB_TYPE = "download"


def _download_dir(user_id: int) -> Path:
    base = Path(settings.DOWNLOAD_DIR) / str(user_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _run_yt_dlp(url: str, fmt: str | None, audio_only: bool, dest: Path) -> dict:
    """Blocking yt-dlp invocation; executed in a worker thread."""
    try:
        from yt_dlp import YoutubeDL  # lazy import: optional dependency
    except ImportError as exc:  # pragma: no cover - depends on deployment
        raise RuntimeError(
            "yt-dlp is not installed. Add 'yt-dlp' to requirements and reinstall."
        ) from exc

    ydl_opts: dict = {
        "outtmpl": str(dest / "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    if audio_only:
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}
        ]
    elif fmt:
        ydl_opts["format"] = fmt

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    return {
        "title": info.get("title"),
        "id": info.get("id"),
        "ext": info.get("ext"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "webpage_url": info.get("webpage_url", url),
        "filepath": ydl.prepare_filename(info) if info else None,
    }


async def download_handler(ctx: JobContext) -> dict:
    url = ctx.payload.get("url")
    if not url:
        raise ValueError("Download job is missing a 'url'")
    fmt = ctx.payload.get("format")
    audio_only = bool(ctx.payload.get("audio_only", False))

    await ctx.update_progress(5)
    dest = _download_dir(ctx.user_id)

    await ctx.update_progress(15)
    result = await asyncio.to_thread(_run_yt_dlp, url, fmt, audio_only, dest)

    await ctx.update_progress(95)
    logger.info("Download finished for job %s: %s", ctx.job_id, result.get("title"))
    return result
