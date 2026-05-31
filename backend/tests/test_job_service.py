"""Unit tests for the background job service and download-path safety."""
import pytest
from fastapi import HTTPException
from sqlalchemy import select, text

from app.core.db import async_session
from app.models.job import JobStatus
from app.models.remote_machine import RemoteMachine, SSHAuthType
from app.models.role import Role
from app.models.user import User
from app.models.user_remote_machine import UserRemoteMachine
from app.schemas.job import DownloadDestination, DownloadJobCreate
from app.services.download_service import _safe_remote_path
from app.services.job_service import (
    create_download_job,
    get_job,
    list_jobs,
)


async def _reset(session):
    await session.execute(text("DELETE FROM jobs"))
    await session.execute(text("DELETE FROM user_remote_machines"))
    await session.execute(text("DELETE FROM remote_machines"))
    await session.execute(text("DELETE FROM users"))
    await session.execute(text("DELETE FROM roles"))
    await session.commit()


async def _make_user(session, username="jobuser", email="jobuser@example.com") -> User:
    role = (
        await session.execute(select(Role).where(Role.name == "user"))
    ).scalar_one_or_none()
    if role is None:
        role = Role(name="user", description="Default user role")
        session.add(role)
        await session.commit()
        await session.refresh(role)

    user = User(
        username=username,
        email=email,
        hashed_password="irrelevant",
        role=role,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def _make_machine(session, name="m1", active=True) -> RemoteMachine:
    machine = RemoteMachine(
        name=name,
        host="example.com",
        port=22,
        username="remote",
        auth_type=SSHAuthType.password,
        encrypted_password="enc",
        download_folder="/data/downloads",
        is_active=active,
    )
    session.add(machine)
    await session.commit()
    await session.refresh(machine)
    return machine


async def _assign(session, user_id: int, machine_id: int) -> None:
    session.add(UserRemoteMachine(user_id=user_id, remote_machine_id=machine_id))
    await session.commit()


# --- _safe_remote_path ---------------------------------------------------------


def test_safe_remote_path_joins_subfolder_and_filename():
    result = _safe_remote_path("/data/downloads", "videos", "clip.mp4")
    assert result == "/data/downloads/videos/clip.mp4"


def test_safe_remote_path_allows_empty_subfolder():
    result = _safe_remote_path("/data/downloads", None, "clip.mp4")
    assert result == "/data/downloads/clip.mp4"


def test_safe_remote_path_strips_leading_slash_on_subfolder():
    result = _safe_remote_path("/data/downloads", "/videos", "clip.mp4")
    assert result == "/data/downloads/videos/clip.mp4"


def test_safe_remote_path_rejects_traversal():
    with pytest.raises(ValueError):
        _safe_remote_path("/data/downloads", "../../etc", "passwd")


def test_safe_remote_path_strips_directory_from_filename():
    result = _safe_remote_path("/data/downloads", "videos", "../../clip.mp4")
    assert result == "/data/downloads/videos/clip.mp4"


def test_safe_remote_path_rejects_invalid_filename():
    with pytest.raises(ValueError):
        _safe_remote_path("/data/downloads", "videos", "..")


# --- create_download_job -------------------------------------------------------


async def test_create_local_download_job_is_queued():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)

        job = await create_download_job(
            DownloadJobCreate(url="https://example.com/video"), user.id, session
        )

        assert job.status == JobStatus.queued
        assert job.destination_type == "local"
        assert job.remote_machine_id is None


async def test_create_remote_job_requires_assignment():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)
        machine = await _make_machine(session)

        with pytest.raises(HTTPException) as exc:
            await create_download_job(
                DownloadJobCreate(
                    url="https://example.com/video",
                    destination_type=DownloadDestination.remote,
                    remote_machine_id=machine.id,
                ),
                user.id,
                session,
            )
        assert exc.value.status_code == 403


async def test_create_remote_job_with_assignment_succeeds():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)
        machine = await _make_machine(session)
        await _assign(session, user.id, machine.id)

        job = await create_download_job(
            DownloadJobCreate(
                url="https://example.com/video",
                destination_type=DownloadDestination.remote,
                remote_machine_id=machine.id,
            ),
            user.id,
            session,
        )

        assert job.status == JobStatus.queued
        assert job.remote_machine_id == machine.id


async def test_create_remote_job_unknown_machine_returns_404():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)

        with pytest.raises(HTTPException) as exc:
            await create_download_job(
                DownloadJobCreate(
                    url="https://example.com/video",
                    destination_type=DownloadDestination.remote,
                    remote_machine_id=999999,
                ),
                user.id,
                session,
            )
        assert exc.value.status_code == 404


async def test_create_remote_job_rejects_traversal_subfolder():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)
        machine = await _make_machine(session)
        await _assign(session, user.id, machine.id)

        with pytest.raises(HTTPException) as exc:
            await create_download_job(
                DownloadJobCreate(
                    url="https://example.com/video",
                    destination_type=DownloadDestination.remote,
                    remote_machine_id=machine.id,
                    remote_subfolder="../../etc",
                ),
                user.id,
                session,
            )
        assert exc.value.status_code == 400


async def test_create_remote_job_inactive_machine_returns_404():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)
        machine = await _make_machine(session, active=False)
        await _assign(session, user.id, machine.id)

        with pytest.raises(HTTPException) as exc:
            await create_download_job(
                DownloadJobCreate(
                    url="https://example.com/video",
                    destination_type=DownloadDestination.remote,
                    remote_machine_id=machine.id,
                ),
                user.id,
                session,
            )
        assert exc.value.status_code == 404


# --- list_jobs / get_job -------------------------------------------------------


async def test_list_jobs_is_scoped_to_user_and_paginated():
    async with async_session() as session:
        await _reset(session)
        owner = await _make_user(session, "owner", "owner@example.com")
        other = await _make_user(session, "other", "other@example.com")

        for _ in range(3):
            await create_download_job(
                DownloadJobCreate(url="https://example.com/v"), owner.id, session
            )
        await create_download_job(
            DownloadJobCreate(url="https://example.com/v"), other.id, session
        )

        items, total = await list_jobs(owner.id, session, page=1, page_size=2)
        assert total == 3
        assert len(items) == 2

        page2, total2 = await list_jobs(owner.id, session, page=2, page_size=2)
        assert total2 == 3
        assert len(page2) == 1


async def test_list_jobs_filters_by_status():
    async with async_session() as session:
        await _reset(session)
        user = await _make_user(session)
        await create_download_job(
            DownloadJobCreate(url="https://example.com/v"), user.id, session
        )

        queued, total = await list_jobs(
            user.id, session, status_filter=JobStatus.queued
        )
        assert total == 1
        assert all(j.status == JobStatus.queued for j in queued)

        finished, total_f = await list_jobs(
            user.id, session, status_filter=JobStatus.finished
        )
        assert total_f == 0
        assert finished == []


async def test_get_job_rejects_other_users_job():
    async with async_session() as session:
        await _reset(session)
        owner = await _make_user(session, "owner", "owner@example.com")
        attacker = await _make_user(session, "attacker", "attacker@example.com")
        job = await create_download_job(
            DownloadJobCreate(url="https://example.com/v"), owner.id, session
        )

        # Owner can read it.
        fetched = await get_job(job.id, owner.id, session)
        assert fetched.id == job.id

        # Another user cannot.
        with pytest.raises(HTTPException) as exc:
            await get_job(job.id, attacker.id, session)
        assert exc.value.status_code == 404


# --- schema validation ---------------------------------------------------------


def test_download_job_create_rejects_non_http_url():
    with pytest.raises(ValueError):
        DownloadJobCreate(url="file:///etc/passwd")


def test_download_job_create_requires_machine_for_remote():
    with pytest.raises(ValueError):
        DownloadJobCreate(
            url="https://example.com/v",
            destination_type=DownloadDestination.remote,
        )
