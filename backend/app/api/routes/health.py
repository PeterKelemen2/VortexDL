from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "version": settings.APP_VERSION}