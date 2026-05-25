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

settings = Settings()