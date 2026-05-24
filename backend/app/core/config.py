import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME = os.getenv("APP_NAME", "Downloader API")
    DEBUG = os.getenv("DEBUG", "false") == "true"
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite+aiosqlite:///./app.db")
    JWT_SECRET = os.getenv("JWT_SECRET")
    if not JWT_SECRET:
        raise RuntimeError("JWT_SECRET must be set in environment")
    JWT_ISSUER = os.getenv("JWT_ISSUER", "ytdlp_client")
    JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "ytdlp_client")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    COOKIE_SAMESITE = os.getenv("COOKIE_SAMESITE", "lax").lower()
    if COOKIE_SAMESITE not in {"lax", "strict", "none"}:
        COOKIE_SAMESITE = "lax"
    INITIAL_ADMIN_USERNAME = os.getenv("INITIAL_ADMIN_USERNAME")
    INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL")
    INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD")
    ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING = os.getenv("ADMIN_BOOTSTRAP_FORCE_ELEVATE_EXISTING", "false").lower() in ("1", "true", "yes")
    CORS_ORIGINS = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()]

settings = Settings()