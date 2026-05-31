"""yt-dlp download handler for the background job queue.

Registered against the ``download`` job type. Runs the (blocking) yt-dlp
extraction in a worker thread so the event loop is never blocked, reports coarse
progress back onto the job record, and optionally delivers the finished artifact
to a remote machine over SFTP.
"""
from __future__ import annotations

import asyncio
import logging
import posixpath
from pathlib import Path

from app.core.config import settings
from app.core.job_queue import JobContext
from app.core.ssh_pool import ssh_pool

logger = logging.getLogger("app.download")

DOWNLOAD_JOB_TYPE = "download"

# Maps the friendly quality choice to a yt-dlp format selector.
_QUALITY_FORMATS: dict[str, str] = {
    "best": "bestvideo+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
    "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]/best",
}


def _download_dir(user_id: int) -> Path:
    base = Path(settings.DOWNLOAD_DIR) / str(user_id)
    base.mkdir(parents=True, exist_ok=True)
    return base


def _build_ydl_opts(payload: dict, dest: Path) -> dict:
    quality = payload.get("quality", "best")
    audio_only = quality == "audio_only"
    container = payload.get("container", "auto")

    ydl_opts: dict = {
        "outtmpl": str(dest / "%(title)s.%(ext)s"),
        "noplaylist": not bool(payload.get("allow_playlist", False)),
        "quiet": True,
        "no_warnings": True,
        "no_overwrites": True,
        "postprocessors": [],
    }

    if audio_only:
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"].append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": payload.get("audio_format", "mp3"),
            }
        )
    else:
        ydl_opts["format"] = _QUALITY_FORMATS.get(quality, _QUALITY_FORMATS["best"])
        if container and container != "auto":
            ydl_opts["merge_output_format"] = container

    if payload.get("embed_subtitles"):
        ydl_opts["writesubtitles"] = True
        ydl_opts["subtitleslangs"] = ["all"]
        ydl_opts["postprocessors"].append({"key": "FFmpegEmbedSubtitle"})

    if payload.get("embed_metadata"):
        ydl_opts["postprocessors"].append(
            {"key": "FFmpegMetadata", "add_metadata": True, "add_chapters": True}
        )

    if payload.get("embed_music_metadata"):
        # Embed available tags (artist, title, album, etc.) into the output file.
        if not any(
            p.get("key") == "FFmpegMetadata" for p in ydl_opts["postprocessors"]
        ):
            ydl_opts["postprocessors"].append(
                {"key": "FFmpegMetadata", "add_metadata": True}
            )

    if payload.get("write_thumbnail"):
        ydl_opts["writethumbnail"] = True
        ydl_opts["postprocessors"].append({"key": "EmbedThumbnail", "already_have_thumbnail": False})

    return ydl_opts


def _unique_path(path: Path) -> Path:
    """Return a non-colliding path by appending _1, _2, … to the stem."""
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1


def _run_yt_dlp(payload: dict, dest: Path, progress_cb=None) -> dict:
    """Blocking yt-dlp invocation; executed in a worker thread."""
    try:
        from yt_dlp import YoutubeDL  # lazy import: optional dependency
    except ImportError as exc:  # pragma: no cover - depends on deployment
        raise RuntimeError(
            "yt-dlp is not installed. Add 'yt-dlp' to requirements and reinstall."
        ) from exc

    url = payload["url"]
    ydl_opts = _build_ydl_opts(payload, dest)
    if progress_cb is not None:
        def _hook(d: dict) -> None:
            if d.get("status") != "downloading":
                return
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            if total and total > 0:
                # Map yt-dlp 0–100% → job progress 15–90% (leaves room for init/post)
                raw = downloaded / total * 100
                progress_cb(int(15 + raw * 0.75))

        ydl_opts["progress_hooks"] = [_hook]
    try:
        from yt_dlp.utils import DownloadError
    except ImportError:
        DownloadError = Exception  # pragma: no cover

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # For playlists, take the first entry's filename for delivery purposes.
            entry = info
            if info and info.get("_type") == "playlist" and info.get("entries"):
                entry = info["entries"][0]
            # Use the post-processed filepath from requested_downloads when available;
            # prepare_filename() returns the pre-postprocessor name (wrong extension
            # after e.g. FFmpegExtractAudio converts webm → mp3).
            requested = (entry or {}).get("requested_downloads")
            if requested and requested[0].get("filepath"):
                filepath = requested[0]["filepath"]
            else:
                filepath = ydl.prepare_filename(entry) if entry else None

        # Rename to avoid collisions with previously downloaded files.
        if filepath:
            final_path = _unique_path(Path(filepath))
            if final_path != Path(filepath) and Path(filepath).exists():
                Path(filepath).rename(final_path)
                filepath = str(final_path)
    except DownloadError as exc:
        raise RuntimeError("Download failed. The URL may be unavailable or restricted.") from exc

    return {
        "title": (entry or {}).get("title"),
        "id": (entry or {}).get("id"),
        "ext": (entry or {}).get("ext"),
        "duration": (entry or {}).get("duration"),
        "uploader": (entry or {}).get("uploader"),
        "webpage_url": (entry or {}).get("webpage_url", url),
        "thumbnail": (entry or {}).get("thumbnail"),
        "filepath": filepath,
    }


def _safe_remote_path(root: str, subfolder: str | None, filename: str) -> str:
    """Resolve a remote destination path constrained to ``root``.

    Prevents path traversal: the resulting path must stay within the machine's
    configured download folder.
    """
    root_norm = posixpath.normpath(root)
    rel = (subfolder or "").strip().lstrip("/")
    target_dir = posixpath.normpath(posixpath.join(root_norm, rel))
    if target_dir != root_norm and not target_dir.startswith(root_norm + "/"):
        raise ValueError("Remote subfolder escapes the configured download folder")
    return posixpath.join(target_dir, filename)


async def _deliver_remote(payload: dict, local_path: Path) -> dict:
    """Upload the finished file to the assigned remote machine over SFTP."""
    from app.core.db import async_session
    from app.models.remote_machine import RemoteMachine

    machine_id = payload.get("remote_machine_id")
    async with async_session() as db:
        machine = await db.get(RemoteMachine, machine_id) if machine_id else None
    if machine is None:
        raise RuntimeError("Assigned remote machine no longer exists")
    if not machine.is_active:
        raise RuntimeError("Assigned remote machine is inactive")

    remote_path = _safe_remote_path(
        machine.download_folder, payload.get("remote_subfolder"), local_path.name
    )
    remote_dir = posixpath.dirname(remote_path)

    conn = await ssh_pool.get_connection(machine)
    async with conn.start_sftp_client() as sftp:
        await sftp.makedirs(remote_dir, exist_ok=True)
        await sftp.put(str(local_path), remote_path)

    logger.info("Uploaded job artifact to %s:%s", machine.host, remote_path)
    return {"remote_machine_id": machine.id, "remote_path": remote_path}


async def download_handler(ctx: JobContext) -> dict:
    url = ctx.payload.get("url")
    if not url:
        raise ValueError("Download job is missing a 'url'")

    destination = ctx.payload.get("destination_type", "local")

    await ctx.update_progress(5)
    dest = _download_dir(ctx.user_id)

    # Wire yt-dlp download progress → job progress (thread-safe via run_coroutine_threadsafe).
    loop = asyncio.get_event_loop()

    def _progress_cb(percent: int) -> None:
        asyncio.run_coroutine_threadsafe(ctx.update_progress(percent), loop)

    await ctx.update_progress(15)
    result = await asyncio.to_thread(_run_yt_dlp, ctx.payload, dest, _progress_cb)

    if destination in ("remote", "both"):
        filepath = result.get("filepath")
        if not filepath or not Path(filepath).exists():
            raise RuntimeError("Downloaded file not found for remote delivery")
        await ctx.update_progress(70)
        remote_info = await _deliver_remote(ctx.payload, Path(filepath))
        result.update(remote_info)

    result["destination_type"] = destination
    result["local_available"] = destination in ("local", "both")

    await ctx.update_progress(95)
    logger.info("Download finished for job %s: %s", ctx.job_id, result.get("title"))
    return result
