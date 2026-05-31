"""Pooled SSH/SFTP connections to remote download targets.

asyncssh connections are relatively expensive to establish, so we keep one live
connection per :class:`~app.models.remote_machine.RemoteMachine` and reuse it
across download transfers and folder-browsing requests. Connections are created
lazily, health-checked on reuse, and rebuilt transparently if they have dropped.

Security model:
* Host keys are pinned Trust-On-First-Use. The first successful connection
  records the server's host-key fingerprint on the machine record; subsequent
  connections must match it, otherwise the connection is refused (mitigates
  man-in-the-middle attacks).
* Passwords are decrypted only in-memory immediately before connecting.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import asyncssh

from app.core.config import settings
from app.core.ssh_crypto import decrypt_secret
from app.models.remote_machine import RemoteMachine, SSHAuthType

logger = logging.getLogger("app.ssh_pool")


class HostKeyMismatchError(Exception):
    """Raised when a server's host key does not match the pinned fingerprint."""


def fingerprint_for(conn: asyncssh.SSHClientConnection) -> str:
    """Return a stable fingerprint string for the connected server's host key."""
    key = conn.get_server_host_key()
    return key.get_fingerprint() if key is not None else ""


@dataclass
class _PooledConnection:
    conn: asyncssh.SSHClientConnection
    fingerprint: str


class SSHConnectionPool:
    """Process-local pool keyed by remote machine id."""

    def __init__(self) -> None:
        self._connections: dict[int, _PooledConnection] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _lock_for(self, machine_id: int) -> asyncio.Lock:
        async with self._global_lock:
            lock = self._locks.get(machine_id)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[machine_id] = lock
            return lock

    def _build_options(self, machine: RemoteMachine) -> asyncssh.SSHClientConnectionOptions:
        kwargs: dict = {
            "username": machine.username,
            "known_hosts": None,  # we pin the fingerprint ourselves (TOFU)
        }
        if machine.auth_type == SSHAuthType.password:
            if not machine.encrypted_password:
                raise ValueError("Remote machine has no stored password")
            kwargs["password"] = decrypt_secret(machine.encrypted_password)
        else:
            if not machine.ssh_key_path:
                raise ValueError("Remote machine has no SSH key path configured")
            kwargs["client_keys"] = [machine.ssh_key_path]
        return asyncssh.SSHClientConnectionOptions(**kwargs)

    async def _connect(self, machine: RemoteMachine) -> _PooledConnection:
        options = self._build_options(machine)
        conn = await asyncio.wait_for(
            asyncssh.connect(
                machine.host,
                port=machine.port,
                options=options,
            ),
            timeout=settings.SSH_CONNECT_TIMEOUT,
        )
        fp = fingerprint_for(conn)
        # Trust-On-First-Use: enforce a previously pinned fingerprint.
        if machine.host_key_fingerprint and machine.host_key_fingerprint != fp:
            conn.close()
            await conn.wait_closed()
            raise HostKeyMismatchError(
                "Remote host key fingerprint changed; refusing to connect"
            )
        return _PooledConnection(conn=conn, fingerprint=fp)

    @staticmethod
    def _is_alive(pooled: _PooledConnection) -> bool:
        # asyncssh marks a connection closed via its transport.
        return not pooled.conn.is_closed()

    async def get_connection(
        self, machine: RemoteMachine
    ) -> asyncssh.SSHClientConnection:
        """Return a live connection for the machine, creating one if needed."""
        lock = await self._lock_for(machine.id)
        async with lock:
            pooled = self._connections.get(machine.id)
            if pooled is not None and self._is_alive(pooled):
                return pooled.conn
            if pooled is not None:
                self._safe_close(pooled.conn)
            pooled = await self._connect(machine)
            self._connections[machine.id] = pooled
            return pooled.conn

    async def test_connection(self, machine: RemoteMachine) -> str:
        """Open a fresh connection (bypassing the pool) and return its fingerprint.

        Used by the admin "Test Connection" action. When the machine has no
        pinned fingerprint yet, the caller persists the returned value (TOFU).
        """
        pooled = await self._connect(machine)
        fp = pooled.fingerprint
        # Keep the freshly opened connection in the pool for immediate reuse.
        existing = self._connections.get(machine.id)
        if existing is not None:
            self._safe_close(existing.conn)
        self._connections[machine.id] = pooled
        return fp

    async def invalidate(self, machine_id: int) -> None:
        """Drop any pooled connection for a machine (after edits/deletes)."""
        lock = await self._lock_for(machine_id)
        async with lock:
            pooled = self._connections.pop(machine_id, None)
            if pooled is not None:
                self._safe_close(pooled.conn)

    @staticmethod
    def _safe_close(conn: asyncssh.SSHClientConnection) -> None:
        try:
            conn.close()
        except Exception:  # noqa: BLE001 - best-effort cleanup
            logger.debug("Error closing SSH connection", exc_info=True)

    async def close_all(self) -> None:
        async with self._global_lock:
            for pooled in self._connections.values():
                self._safe_close(pooled.conn)
            self._connections.clear()
        logger.info("Closed all pooled SSH connections")


# Module singleton used by the application.
ssh_pool = SSHConnectionPool()
