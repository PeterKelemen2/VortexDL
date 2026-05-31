import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _read_version() -> str:
    """Read the canonical version from the VERSION file.

    Search order:
    1. APP_VERSION env var (allows CI/runtime override)
    2. VERSION file at the repo root (works for local dev and Docker)
    """
    if v := os.getenv("APP_VERSION"):
        return v.strip()
    # backend/app/core/config.py → parents[3] is the repo root when running
    # locally.  In the combined Docker image the file lands at /app/VERSION.
    candidates = [
        Path(__file__).resolve().parents[3] / "VERSION",
        Path("/app/VERSION"),
    ]
    for path in candidates:
        if path.exists():
            return path.read_text().strip()
    return "dev"


class Settings:
    APP_NAME = os.getenv("APP_NAME", "Downloader API")
    APP_VERSION: str = _read_version()
    DEBUG = os.getenv("DEBUG", "false") == "true"
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite+aiosqlite:////app/data/app.db")
    JWT_SECRET = os.getenv("JWT_SECRET")
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be set in environment")
    if len(JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters long (use a cryptographically random value)")
    JWT_ISSUER = os.getenv("JWT_ISSUER", "vortex_dl")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "vortex_dl")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    # Restrict to a vetted allowlist so a misconfigured environment can never
    # select the "none" algorithm (which would disable signature verification).
    if JWT_ALGORITHM not in {"HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}:
        raise RuntimeError(f"Unsupported JWT_ALGORITHM: {JWT_ALGORITHM!r}")
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()
    if COOKIE_SAMESITE not in {"lax", "strict", "none"}:
        COOKIE_SAMESITE = "lax"
    # Whether to set the Secure flag on auth cookies. Must be enabled in any
    # deployment served over HTTPS (including behind a TLS-terminating reverse
    # proxy, where the upstream request scheme appears as plain http).
    SECURE_COOKIES = os.getenv("SECURE_COOKIES", "false").lower() in ("1", "true", "yes")
    INITIAL_ADMIN_USERNAME = os.getenv("INITIAL_ADMIN_USERNAME")
    INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL")
    INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD")
    ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING = os.getenv("ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING", "false").lower() in ("1", "true", "yes")
    PROFILE_IMAGE_UPLOAD_DIR = os.getenv("PROFILE_IMAGE_UPLOAD_DIR", "./uploads")
    PROFILE_IMAGE_UPLOAD_SUBDIR = os.getenv("PROFILE_IMAGE_UPLOAD_SUBDIR", "profile_images")
    PROFILE_IMAGE_URL_PATH = os.getenv("PROFILE_IMAGE_URL_PATH", "/uploads")
    PROFILE_IMAGE_MAX_SIZE_MB = int(os.getenv("PROFILE_IMAGE_MAX_SIZE_MB", "5"))
    PROFILE_IMAGE_VARIANT_SIZES = {
        "avatar": int(os.getenv("PROFILE_IMAGE_VARIANT_AVATAR_SIZE", "120")),
        "thumbnail": int(os.getenv("PROFILE_IMAGE_VARIANT_THUMBNAIL_SIZE", "200")),
        "preview": int(os.getenv("PROFILE_IMAGE_VARIANT_PREVIEW_SIZE", "420")),
    }
    PROFILE_IMAGE_VARIANT_QUALITY = int(os.getenv("PROFILE_IMAGE_VARIANT_QUALITY", "85"))
    PROFILE_IMAGE_VARIANT_SEPARATOR = os.getenv("PROFILE_IMAGE_VARIANT_SEPARATOR", "__")
    CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]
    # A wildcard origin combined with credentialed requests (allow_credentials=True)
    # would let any site issue authenticated cross-origin calls. Disallow it.
    if "*" in CORS_ORIGINS:
        raise RuntimeError("CORS_ORIGINS must not contain '*' because credentialed CORS is enabled")

    # Public base URL of the frontend, used to build links in outgoing emails.
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")

    # --- SMTP / email delivery -------------------------------------------------
    # When SMTP_HOST is unset, EmailService runs in "console" mode: it logs the
    # rendered message instead of sending it, so the template works out of the box.
    SMTP_HOST = os.getenv("SMTP_HOST") or None
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME") or None
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD") or None
    SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")
    SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes")
    SMTP_TIMEOUT = int(os.getenv("SMTP_TIMEOUT", "10"))
    EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@localhost")
    EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", APP_NAME)

    # --- Email verification / password reset tokens ----------------------------
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS = int(os.getenv("EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS", "24"))
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "30"))
    # When true, newly registered users must verify their email before logging in.
    REQUIRE_EMAIL_VERIFICATION = os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").lower() in ("1", "true", "yes")

    # --- Rate limiting ---------------------------------------------------------
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("1", "true", "yes")
    RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "5/minute")
    RATE_LIMIT_REGISTER = os.getenv("RATE_LIMIT_REGISTER", "5/minute")
    RATE_LIMIT_REFRESH = os.getenv("RATE_LIMIT_REFRESH", "30/minute")
    RATE_LIMIT_PASSWORD_RESET = os.getenv("RATE_LIMIT_PASSWORD_RESET", "5/hour")
    RATE_LIMIT_EMAIL_VERIFICATION = os.getenv("RATE_LIMIT_EMAIL_VERIFICATION", "5/hour")
    RATE_LIMIT_DOWNLOAD = os.getenv("RATE_LIMIT_DOWNLOAD", "20/minute")

    # --- Logging --------------------------------------------------------------
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

    # --- Background job queue --------------------------------------------------
    # Number of concurrent in-process worker tasks pulling from the job queue.
    JOB_WORKER_CONCURRENCY = int(os.getenv("JOB_WORKER_CONCURRENCY", "2"))
    # Root directory where downloaded files are written (per-user subdirectories).
    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
    # Upper bound on the size of a single downloaded artifact, to bound disk usage
    # and prevent a single job from exhausting storage. Default: 10 GiB.
    DOWNLOAD_MAX_FILE_SIZE_BYTES = int(os.getenv("DOWNLOAD_MAX_FILE_SIZE_BYTES", str(10 * 1024 * 1024 * 1024)))

    # --- Remote (SSH/SFTP) downloads -------------------------------------------
    # Symmetric key used to encrypt stored remote-machine passwords at rest.
    # Derived from JWT_SECRET when unset so deployments work out of the box.
    REMOTE_SECRET_KEY = os.getenv("REMOTE_SECRET_KEY") or JWT_SECRET
    # Seconds an idle pooled SSH connection is kept alive before being recycled.
    SSH_CONNECT_TIMEOUT = int(os.getenv("SSH_CONNECT_TIMEOUT", "15"))
    # Directory that SSH private-key files must reside in. Operator-supplied
    # ssh_key_path values are confined to this directory (after resolving
    # symlinks/.. segments) so a malicious admin cannot point the SSH client at
    # arbitrary files such as /etc/shadow or other users' keys.
    SSH_KEY_ALLOWED_DIR = os.getenv("SSH_KEY_ALLOWED_DIR", "/app/ssh_keys")
    # Maximum number of entries returned by a single remote folder browse call.
    REMOTE_BROWSE_MAX_ENTRIES = int(os.getenv("REMOTE_BROWSE_MAX_ENTRIES", "1000"))

settings = Settings()