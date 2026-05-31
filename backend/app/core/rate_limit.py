"""Application-wide rate limiter (slowapi).

The limiter keys on the client's remote address. Limits are configured via env
vars (see ``app.core.config``) and applied as decorators on individual routes.
Set ``RATE_LIMIT_ENABLED=false`` to disable limiting globally (e.g. in tests).
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.RATE_LIMIT_ENABLED,
    headers_enabled=True,
)
