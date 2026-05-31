"""Unit tests for the remote machine service, including SSH key path safety."""
import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.core import config as config_module
from app.core.db import async_session
from app.models.remote_machine import RemoteMachine, SSHAuthType
from app.schemas.remote_machine import RemoteMachineCreate, RemoteMachineUpdate
from app.services.remote_machine_service import (
    _validate_ssh_key_path,
    create_machine,
    delete_machine,
    get_machine_or_404,
    list_machines,
    update_machine,
)


async def _reset(session):
    await session.execute(text("DELETE FROM user_remote_machines"))
    await session.execute(text("DELETE FROM remote_machines"))
    await session.commit()


def _password_payload(name="m1", **overrides) -> RemoteMachineCreate:
    base = dict(
        name=name,
        host="example.com",
        port=22,
        username="remote",
        auth_type=SSHAuthType.password,
        password="s3cret",
        download_folder="/data/downloads",
    )
    base.update(overrides)
    return RemoteMachineCreate(**base)


# --- _validate_ssh_key_path ----------------------------------------------------


def test_validate_ssh_key_path_accepts_path_inside_allowed_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        config_module.settings, "SSH_KEY_ALLOWED_DIR", str(tmp_path), raising=False
    )
    key = tmp_path / "id_ed25519"
    key.write_text("dummy")

    resolved = _validate_ssh_key_path(str(key))
    assert resolved == str(key.resolve())


def test_validate_ssh_key_path_resolves_relative_path(tmp_path, monkeypatch):
    monkeypatch.setattr(
        config_module.settings, "SSH_KEY_ALLOWED_DIR", str(tmp_path), raising=False
    )
    resolved = _validate_ssh_key_path("id_ed25519")
    assert resolved == str((tmp_path / "id_ed25519").resolve())


def test_validate_ssh_key_path_rejects_escape_via_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(
        config_module.settings, "SSH_KEY_ALLOWED_DIR", str(tmp_path), raising=False
    )
    with pytest.raises(HTTPException) as exc:
        _validate_ssh_key_path("../../etc/shadow")
    assert exc.value.status_code == 400


def test_validate_ssh_key_path_rejects_absolute_outside_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(
        config_module.settings, "SSH_KEY_ALLOWED_DIR", str(tmp_path), raising=False
    )
    with pytest.raises(HTTPException) as exc:
        _validate_ssh_key_path("/etc/shadow")
    assert exc.value.status_code == 400


# --- CRUD ----------------------------------------------------------------------


async def test_create_machine_persists_and_encrypts_password():
    async with async_session() as session:
        await _reset(session)

        machine = await create_machine(_password_payload(), session)

        assert machine.id is not None
        assert machine.name == "m1"
        assert machine.encrypted_password is not None
        assert machine.encrypted_password != "s3cret"
        assert machine.ssh_key_path is None


async def test_create_machine_rejects_duplicate_name():
    async with async_session() as session:
        await _reset(session)
        await create_machine(_password_payload(name="dup"), session)

        with pytest.raises(HTTPException) as exc:
            await create_machine(_password_payload(name="dup"), session)
        assert exc.value.status_code == 409


async def test_create_machine_validates_ssh_key_path(tmp_path, monkeypatch):
    monkeypatch.setattr(
        config_module.settings, "SSH_KEY_ALLOWED_DIR", str(tmp_path), raising=False
    )
    async with async_session() as session:
        await _reset(session)

        with pytest.raises(HTTPException) as exc:
            await create_machine(
                _password_payload(
                    name="keymachine",
                    auth_type=SSHAuthType.key,
                    password=None,
                    ssh_key_path="/etc/shadow",
                ),
                session,
            )
        assert exc.value.status_code == 400


async def test_update_machine_changes_fields():
    async with async_session() as session:
        await _reset(session)
        machine = await create_machine(_password_payload(), session)

        updated = await update_machine(
            machine.id,
            RemoteMachineUpdate(host="newhost.example.com", port=2222),
            session,
        )

        assert updated.host == "newhost.example.com"
        assert updated.port == 2222


async def test_update_machine_rejects_name_clash():
    async with async_session() as session:
        await _reset(session)
        await create_machine(_password_payload(name="alpha"), session)
        beta = await create_machine(_password_payload(name="beta"), session)

        with pytest.raises(HTTPException) as exc:
            await update_machine(
                beta.id, RemoteMachineUpdate(name="alpha"), session
            )
        assert exc.value.status_code == 409


async def test_get_machine_or_404_raises_for_missing():
    async with async_session() as session:
        await _reset(session)
        with pytest.raises(HTTPException) as exc:
            await get_machine_or_404(999999, session)
        assert exc.value.status_code == 404


async def test_list_machines_paginates():
    async with async_session() as session:
        await _reset(session)
        for i in range(3):
            await create_machine(_password_payload(name=f"m{i}"), session)

        rows, total = await list_machines(session, page=1, page_size=2)
        assert total == 3
        assert len(rows) == 2


async def test_delete_machine_removes_row():
    async with async_session() as session:
        await _reset(session)
        machine = await create_machine(_password_payload(), session)

        await delete_machine(machine.id, session)

        assert await session.get(RemoteMachine, machine.id) is None
