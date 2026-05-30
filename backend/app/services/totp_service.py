"""TOTP-based two-factor authentication.

Handles secret generation, provisioning-URI/QR rendering, code verification
and single-use backup codes. Secrets are stored as base32 on the user record;
backup codes are stored bcrypt-hashed (never in plaintext).
"""
from __future__ import annotations

import base64
import io
import json
import secrets

import pyotp

from app.core.config import settings
from app.core.security import hash_password, verify_password

BACKUP_CODE_COUNT = 10


def generate_secret() -> str:
    return pyotp.random_base32()


def provisioning_uri(secret: str, account_name: str) -> str:
    issuer = settings.APP_NAME
    return pyotp.TOTP(secret).provisioning_uri(name=account_name, issuer_name=issuer)


def qr_data_uri(otpauth_uri: str) -> str:
    """Render the provisioning URI as a base64 PNG data URI for the frontend."""
    import qrcode  # lazy import; only needed during enrollment

    img = qrcode.make(otpauth_uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def verify_code(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    # Allow +/- one 30s window to tolerate clock drift.
    return pyotp.TOTP(secret).verify(code.strip(), valid_window=1)


def generate_backup_codes() -> tuple[list[str], str]:
    """Return (plaintext_codes, json_of_hashed_codes). Plaintext shown once."""
    plaintext = [f"{secrets.token_hex(4)}-{secrets.token_hex(4)}" for _ in range(BACKUP_CODE_COUNT)]
    hashed = [hash_password(code) for code in plaintext]
    return plaintext, json.dumps(hashed)


def consume_backup_code(stored_json: str | None, code: str) -> str | None:
    """If `code` matches an unused backup code, return updated JSON with it removed.

    Returns None when the code does not match any stored backup code.
    """
    if not stored_json or not code:
        return None
    try:
        hashed_codes: list[str] = json.loads(stored_json)
    except (ValueError, TypeError):
        return None
    code = code.strip()
    for index, hashed in enumerate(hashed_codes):
        if verify_password(code, hashed):
            remaining = hashed_codes[:index] + hashed_codes[index + 1 :]
            return json.dumps(remaining)
    return None
