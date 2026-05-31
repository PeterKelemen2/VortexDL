"""Symmetric encryption for remote-machine secrets stored at rest.

Passwords for SSH targets must never be persisted in plaintext. We derive a
stable Fernet key from ``settings.REMOTE_SECRET_KEY`` and use it to encrypt and
decrypt those secrets transparently in the service layer.
"""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    # Fernet requires a 32-byte urlsafe base64 key; derive one deterministically.
    digest = hashlib.sha256(settings.REMOTE_SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:  # pragma: no cover - corrupted/rotated key
        raise RuntimeError(
            "Failed to decrypt stored remote-machine secret (key mismatch?)"
        ) from exc
