import bcrypt as _bcrypt
from jose import jwt
from datetime import datetime, timedelta
import hashlib
import base64
import secrets


def _prehash_password(password: str) -> bytes:
    """SHA-256 prehash so bcrypt always receives a fixed 44-byte input.

    bcrypt >= 4.0 raises ValueError for passwords > 72 bytes. Hashing first
    ensures every unique password maps to a unique, fixed-length input and
    sidesteps the limit entirely.
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)  # always 44 bytes


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(_prehash_password(password), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(_prehash_password(plain), hashed.encode("utf-8"))

def create_access_token(
    data: dict,
    secret: str,
    expires_delta: timedelta,
    issuer: str | None = None,
    audience: str | None = None,
    algorithm: str = "HS256",
) -> str:
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + expires_delta
    to_encode.update({"exp": expire, "iat": now, "nbf": now})
    if issuer is not None:
        to_encode["iss"] = issuer
    if audience is not None:
        to_encode["aud"] = audience
    return jwt.encode(to_encode, secret, algorithm=algorithm)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)